"""Fee-free bank-transfer order-to-cash workflow with an append-only receipt ledger."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from fastapi import APIRouter, Body, Header, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from config import CONFIG
from database import get_connection
from core.config import OUTPUTS_DIR

router = APIRouter()
STAGING_DIR = OUTPUTS_DIR / "staging"

ASSURANCE_MANUAL = "OWNER_MANUAL_ATTESTATION"
PROVENANCE_MANUAL = "owner_checked_account_statement_and_attested_receipt"
_EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
_IDEM_RE = re.compile(r"[A-Za-z0-9._:-]{8,180}")
_TERMINAL = {"CLOSED", "CANCELLED"}


class StrictPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LeadPayload(StrictPayload):
    product_id: str = Field(min_length=3, max_length=100, pattern=r"^[a-z0-9-]+$")
    email: str = Field(min_length=5, max_length=254)
    name: str = Field(default="", max_length=120)
    contact_consent: bool
    test_mode: bool = False


class QuotePayload(StrictPayload):
    scope: str = Field(min_length=10, max_length=2000)
    proposal_minor: int = Field(gt=0, le=10**12)
    expires_in_days: int = Field(default=7, ge=1, le=30)


class ClaimPayload(StrictPayload):
    claimed_minor: int = Field(gt=0, le=10**12)
    transfer_reference: str = Field(default="", max_length=120)
    note: str = Field(default="", max_length=300)


class VerifyPayload(StrictPayload):
    confirm_funds_received: bool
    amount_received_minor: int = Field(gt=0, le=10**12)
    statement_reference: str = Field(min_length=4, max_length=120)
    statement_note: str = Field(default="", max_length=300)


class RejectPayload(StrictPayload):
    reason: str = Field(min_length=4, max_length=300)


class RefundPayload(StrictPayload):
    amount_minor: int = Field(gt=0, le=10**12)
    transfer_reference: str = Field(min_length=4, max_length=120)
    reason: str = Field(min_length=4, max_length=300)


class DisputePayload(StrictPayload):
    amount_minor: int = Field(gt=0, le=10**12)
    reference: str = Field(min_length=4, max_length=120)
    reason: str = Field(min_length=4, max_length=300)


class ResolveDisputePayload(StrictPayload):
    outcome: Literal["WON", "LOST"]
    reason: str = Field(min_length=4, max_length=300)


class FulfillPayload(StrictPayload):
    artifact_id: str = Field(min_length=3, max_length=160, pattern=r"^[a-z0-9][a-z0-9.-]{1,159}$")


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _iso(value: datetime | None = None) -> str:
    return (value or _now()).isoformat().replace("+00:00", "Z")


def _connect() -> sqlite3.Connection:
    conn = get_connection()
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _secret() -> bytes:
    value = os.getenv("AUTOPROFIT_ORDER_TOKEN_SECRET", "").strip()
    if len(value) < 32:
        raise HTTPException(status_code=503, detail="Order access signing is not configured.")
    return value.encode("utf-8")


def _require_admin(request: Request) -> None:
    from workflow_api import _require_admin as require
    require(request)


def _test_mode_requested(request: Request, requested: bool) -> bool:
    if not requested:
        return False
    enabled = os.getenv("AUTOPROFIT_TEST_MODE_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
    environment = os.getenv("AUTOPROFIT_ENV", "development").strip().lower()
    expected = os.getenv("AUTOPROFIT_TEST_MODE_KEY", "").strip()
    supplied = request.headers.get("X-Test-Mode-Key", "")
    if (not enabled or environment == "production" or len(expected) < 32 or not supplied
            or not hmac.compare_digest(expected, supplied)):
        raise HTTPException(status_code=403, detail="Explicit TEST mode is disabled or not authorized.")
    return True


def _require_idempotency(value: str | None) -> str:
    key = (value or "").strip()
    if not _IDEM_RE.fullmatch(key):
        raise HTTPException(status_code=422, detail="A safe Idempotency-Key (8-180 characters) is required.")
    return key


def _canonical_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def _bearer(request: Request) -> str:
    value = request.headers.get("authorization", "")
    scheme, _, token = value.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Buyer authorization is required.")
    return token.strip()


def _issue_buyer_token(order: sqlite3.Row | dict[str, Any]) -> str:
    expires = str(order["buyer_token_expires_at"])
    message = f"buyer:v1:{order['id']}:{order['buyer_nonce']}:{expires}".encode()
    signature = hmac.new(_secret(), message, hashlib.sha256).hexdigest()
    return f"v1.{order['buyer_nonce']}.{signature}"


def _authorize_buyer(order: sqlite3.Row | dict[str, Any], request: Request) -> None:
    token = _bearer(request)
    expected = _issue_buyer_token(order)
    if not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=404, detail="Order not found.")
    try:
        expiry = datetime.fromisoformat(str(order["buyer_token_expires_at"]).replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=404, detail="Order not found.")
    if expiry <= _now():
        raise HTTPException(status_code=410, detail="Buyer access has expired.")


def _normalize_reference(value: str) -> str:
    normalized = re.sub(r"[^A-Z0-9]", "", value.strip().upper())
    if len(normalized) < 4 or len(normalized) > 120:
        raise HTTPException(status_code=422, detail="A transfer reference of 4-120 letters or digits is required.")
    return normalized


def _bank_scope() -> str:
    if not CONFIG.BANK_NAME or not CONFIG.BANK_ACCOUNT_NO or not CONFIG.BANK_ACCOUNT_NAME:
        raise HTTPException(status_code=503, detail="Bank transfer checkout is not configured.")
    raw = f"{CONFIG.BANK_NAME.upper()}:{CONFIG.BANK_ACCOUNT_NO}"
    return "bank:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _bank_ready() -> bool:
    return bool(CONFIG.BANK_NAME and CONFIG.BANK_ACCOUNT_NO and CONFIG.BANK_ACCOUNT_NAME)


def _event(conn: sqlite3.Connection, order_id: str, from_state: str | None,
           to_state: str, action: str, actor: str, *, idempotency_key: str,
           trace_id: str, assurance_level: str | None = None,
           provenance: str | None = None, details: dict[str, Any] | None = None) -> None:
    conn.execute(
        """INSERT INTO cash_events(order_id,from_state,to_state,action,actor,assurance_level,
           provenance,details_json,idempotency_key,trace_id,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (order_id, from_state, to_state, action, actor, assurance_level, provenance,
         json.dumps(details or {}, ensure_ascii=False, sort_keys=True), idempotency_key,
         trace_id, _iso()),
    )


def _transition(conn: sqlite3.Connection, order: sqlite3.Row | dict[str, Any],
                to_state: str, action: str, actor: str, *, idempotency_key: str,
                details: dict[str, Any] | None = None,
                assurance_level: str | None = None, provenance: str | None = None) -> None:
    from_state = str(order["state"])
    if from_state == to_state:
        _event(conn, order["id"], from_state, to_state, action, actor,
               idempotency_key=idempotency_key, trace_id=order["trace_id"],
               assurance_level=assurance_level, provenance=provenance, details=details)
        return
    cur = conn.execute("UPDATE cash_orders SET state=?,updated_at=? WHERE id=? AND state=?",
                       (to_state, _iso(), order["id"], from_state))
    if cur.rowcount != 1:
        raise HTTPException(status_code=409, detail="Order changed in another session.")
    _event(conn, order["id"], from_state, to_state, action, actor,
           idempotency_key=idempotency_key, trace_id=order["trace_id"],
           assurance_level=assurance_level, provenance=provenance, details=details)


def _get_order(conn: sqlite3.Connection, order_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM cash_orders WHERE id=?", (order_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Order not found.")
    return row


def _create_or_get_product(slug: str) -> dict[str, Any]:
    from workflow_api import _find_product
    item = _find_product(slug)
    if not item:
        raise HTTPException(status_code=404, detail="Product is not available for a quote.")
    return item


def _public_order(order: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    invoice_minor = order["invoice_minor"]
    outstanding_minor = max(0, int(invoice_minor or 0) - int(order["paid_minor"]))
    return {
        "order_id": order["id"], "order_number": order["order_number"], "state": order["state"],
        "test_mode": bool(order["is_test"]) if "is_test" in order.keys() else False,
        "product": {"id": order["product_slug"], "name": order["product_name"]},
        "estimated_value": ({"amount_minor": order["estimate_minor"], "currency": order["estimate_currency"],
                              "label": "ESTIMATE_ONLY"} if order["estimate_minor"] is not None else None),
        "proposal_amount": ({"amount_minor": order["proposal_minor"], "currency": order["proposal_currency"],
                             "label": "OWNER_PROPOSAL"} if order["proposal_minor"] is not None else None),
        "invoice_total": ({"amount_minor": invoice_minor, "currency": order["invoice_currency"],
                           "label": "ISSUED_INVOICE_TOTAL"} if invoice_minor is not None else None),
        "pending_invoice": ({"amount_minor": outstanding_minor, "currency": order["invoice_currency"],
                             "label": "OUTSTANDING_INVOICE_BALANCE"}
                            if invoice_minor is not None and outstanding_minor > 0 else None),
        "paid_minor": int(order["paid_minor"]), "refunded_minor": int(order["refunded_minor"]),
        "charged_back_minor": int(order["charged_back_minor"]),
        "settled_minor": int(order["paid_minor"]) - int(order["refunded_minor"]) - int(order["charged_back_minor"]),
        "owner_confirmed_receipts": {"amount_minor": int(order["paid_minor"]),
                                     "currency": order["invoice_currency"] or "VND",
                                     "assurance_level": ASSURANCE_MANUAL,
                                     "provenance": PROVENANCE_MANUAL},
        "settled_balance": {"amount_minor": int(order["paid_minor"]) - int(order["refunded_minor"]) - int(order["charged_back_minor"]),
                            "currency": order["invoice_currency"] or "VND"},
        "currency": order["invoice_currency"], "buyer_access_expires_at": order["buyer_token_expires_at"],
    }


@router.get("/api/cash/catalog")
def cash_catalog():
    from workflow_api import _products
    return {"items": [{"id": p["id"], "name": p["name"], "estimate": {
        "amount_minor": round(float(p["price_usd"]) * 100), "currency": "USD",
        "label": "ESTIMATE_ONLY_NO_FX"}, "checkout_url": f"/checkout.html?product={p['id']}"}
        for p in _products()], "payment_method": "BANK_TRANSFER", "payment_configured": _bank_ready(),
        "note": "USD catalog values are estimates only. Quotes and bank settlement are VND; no FX conversion is applied."}


@router.post("/api/cash/leads", status_code=201)
def create_cash_lead(payload: LeadPayload, request: Request,
                     idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    if not payload.contact_consent:
        raise HTTPException(status_code=422, detail="Consent to receive an owner response is required.")
    test_mode = _test_mode_requested(request, payload.test_mode)
    email = payload.email.strip().lower()
    if not _EMAIL_RE.fullmatch(email):
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    key = _require_idempotency(idempotency_key)
    try:
        _secret()
        product = _create_or_get_product(payload.product_id)
    except HTTPException:
        raise
    body = {"product_id": product["id"], "email": email, "name": payload.name.strip(), "test_mode": test_mode}
    fingerprint = _canonical_hash(body)
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        existing = conn.execute("SELECT * FROM cash_orders WHERE idempotency_key=?", (key,)).fetchone()
        if existing:
            if existing["idempotency_hash"] != fingerprint:
                raise HTTPException(status_code=409, detail="Idempotency-Key was used for a different checkout.")
            token = _issue_buyer_token(existing)
            conn.commit()
            return {"order_id": existing["id"], "state": existing["state"],
                    "buyer_access_token": token, "token_type": "Bearer",
                    "expires_at": existing["buyer_token_expires_at"], "test_mode": bool(existing["is_test"]), "replayed": True}
        now = _now()
        order_id = str(uuid.uuid4())
        nonce = secrets.token_urlsafe(24)
        expires = _iso(now + timedelta(days=365))
        trace_id = str(uuid.uuid4())
        estimate = round(float(product["price_usd"]) * 100) if product.get("price_usd") is not None else None
        conn.execute(
            """INSERT INTO cash_orders(id,state,product_slug,product_name,customer_name,customer_email,
               contact_consent,estimate_minor,estimate_currency,buyer_nonce,buyer_token_expires_at,
               trace_id,idempotency_key,idempotency_hash,created_at,updated_at,is_test)
               VALUES(?,'LEAD',?,?,?,?,1,?,'USD',?,?,?,?,?,?,?,?)""",
            (order_id, product["id"], product["name"], payload.name.strip() or None, email,
             estimate, nonce, expires, trace_id, key, fingerprint, _iso(now), _iso(now), int(test_mode)),
        )
        _event(conn, order_id, None, "LEAD", "lead_received", "buyer",
               idempotency_key=f"lead:{key}", trace_id=trace_id,
               details={"product_slug": product["id"], "contact_consent": True})
        order = conn.execute("SELECT * FROM cash_orders WHERE id=?", (order_id,)).fetchone()
        token = _issue_buyer_token(order)
        conn.commit()
        return {"order_id": order_id, "state": "LEAD", "buyer_access_token": token,
                "token_type": "Bearer", "expires_at": expires, "test_mode": test_mode, "replayed": False,
                "estimate": {"amount_minor": estimate, "currency": "USD", "label": "ESTIMATE_ONLY_NO_FX"}}
    except HTTPException:
        conn.rollback()
        raise
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise HTTPException(status_code=409, detail="Duplicate checkout request or ledger conflict.") from exc
    finally:
        conn.close()


@router.get("/api/cash/orders/{order_id}")
def buyer_order(order_id: str, request: Request):
    conn = _connect()
    try:
        order = _get_order(conn, order_id)
        _authorize_buyer(order, request)
        result = _public_order(order)
        quote = conn.execute("SELECT id,scope,proposal_minor,currency,status,expires_at FROM cash_quotes WHERE id=?",
                             (order["current_quote_id"],)).fetchone() if order["current_quote_id"] else None
        result["quote"] = dict(quote) if quote else None
        delivery = conn.execute("SELECT id,artifact_id,status,expires_at,revoked_at FROM cash_deliveries WHERE order_id=?",
                                (order_id,)).fetchone()
        result["delivery"] = dict(delivery) if delivery else None
        claim = conn.execute("SELECT id,status,claimed_minor,currency FROM cash_claims WHERE order_id=? ORDER BY created_at DESC LIMIT 1",
                             (order_id,)).fetchone()
        result["latest_claim"] = dict(claim) if claim else None
        return result
    finally:
        conn.close()


@router.post("/api/cash/admin/leads/{order_id}/quotes", status_code=201)
def create_quote(order_id: str, request: Request, payload: QuotePayload,
                 idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    _require_admin(request)
    key = _require_idempotency(idempotency_key)
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        order = _get_order(conn, order_id)
        if order["state"] not in {"LEAD", "QUOTE_DRAFT", "QUOTE_APPROVED"}:
            raise HTTPException(status_code=409, detail="A quote cannot be changed after an order is placed.")
        body = {"order_id": order_id, "scope": payload.scope.strip(),
                "proposal_minor": payload.proposal_minor, "expires_in_days": payload.expires_in_days}
        fingerprint = _canonical_hash(body)
        existing = conn.execute("SELECT * FROM cash_quotes WHERE idempotency_key=?", (key,)).fetchone()
        if existing:
            if existing["payload_hash"] != fingerprint:
                raise HTTPException(status_code=409, detail="Idempotency-Key was used for a different quote.")
            conn.commit()
            return {"quote_id": existing["id"], "order_id": order_id, "status": existing["status"],
                    "proposal_amount": {"amount_minor": existing["proposal_minor"], "currency": existing["currency"]},
                    "replayed": True}
        if order["state"] == "QUOTE_APPROVED" and order["current_quote_id"]:
            conn.execute("UPDATE cash_quotes SET status='SUPERSEDED',updated_at=? WHERE id=? AND status='APPROVED'",
                         (_iso(), order["current_quote_id"]))
        version = int(conn.execute("SELECT COALESCE(MAX(version),0)+1 FROM cash_quotes WHERE order_id=?",
                                   (order_id,)).fetchone()[0])
        quote_id = str(uuid.uuid4())
        now = _now()
        expires = _iso(now + timedelta(days=payload.expires_in_days))
        conn.execute(
            """INSERT INTO cash_quotes(id,order_id,version,scope,proposal_minor,currency,status,
               expires_at,idempotency_key,payload_hash,created_at,updated_at)
               VALUES(?,?,?,?,?,'VND','DRAFT',?,?,?,?,?)""",
            (quote_id, order_id, version, payload.scope.strip(), payload.proposal_minor,
             expires, key, fingerprint, _iso(now), _iso(now)),
        )
        _transition(conn, order, "QUOTE_DRAFT", "quote_drafted", "owner",
                    idempotency_key=f"quote:{key}:draft", details={"quote_id": quote_id, "version": version})
        conn.execute("UPDATE cash_orders SET current_quote_id=?,proposal_minor=?,proposal_currency='VND',updated_at=? WHERE id=?",
                     (quote_id, payload.proposal_minor, _iso(now), order_id))
        conn.commit()
        return {"quote_id": quote_id, "order_id": order_id, "version": version, "status": "DRAFT",
                "proposal_amount": {"amount_minor": payload.proposal_minor, "currency": "VND", "label": "OWNER_PROPOSAL"},
                "expires_at": expires, "replayed": False}
    except HTTPException:
        conn.rollback()
        raise
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise HTTPException(status_code=409, detail="Quote idempotency or version conflict.") from exc
    finally:
        conn.close()


@router.post("/api/cash/admin/quotes/{quote_id}/approve")
def approve_quote(quote_id: str, request: Request):
    _require_admin(request)
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        quote = conn.execute("SELECT * FROM cash_quotes WHERE id=?", (quote_id,)).fetchone()
        if not quote:
            raise HTTPException(status_code=404, detail="Quote not found.")
        if quote["status"] == "APPROVED":
            conn.commit()
            return {"quote_id": quote_id, "status": "APPROVED", "replayed": True}
        if quote["status"] != "DRAFT":
            raise HTTPException(status_code=409, detail="Quote is not awaiting approval.")
        if datetime.fromisoformat(quote["expires_at"].replace("Z", "+00:00")) <= _now():
            conn.execute("UPDATE cash_quotes SET status='EXPIRED',updated_at=? WHERE id=?", (_iso(), quote_id))
            conn.commit()
            raise HTTPException(status_code=410, detail="Quote has expired.")
        order = _get_order(conn, quote["order_id"])
        if order["current_quote_id"] != quote_id or order["state"] != "QUOTE_DRAFT":
            raise HTTPException(status_code=409, detail="This quote is no longer current.")
        now = _iso()
        conn.execute("UPDATE cash_quotes SET status='APPROVED',approved_by='owner',approved_at=?,updated_at=? WHERE id=?",
                     (now, now, quote_id))
        conn.execute("UPDATE cash_orders SET proposal_minor=?,proposal_currency='VND',updated_at=? WHERE id=?",
                     (quote["proposal_minor"], now, quote["order_id"]))
        _transition(conn, order, "QUOTE_APPROVED", "quote_approved", "owner",
                    idempotency_key=f"quote:{quote_id}:approved", details={"quote_id": quote_id})
        conn.commit()
        return {"quote_id": quote_id, "status": "APPROVED", "replayed": False}
    except HTTPException:
        if conn.in_transaction:
            conn.rollback()
        raise
    except sqlite3.Error as exc:
        conn.rollback()
        raise HTTPException(status_code=503, detail="Quote approval could not be persisted.") from exc
    finally:
        conn.close()


@router.post("/api/cash/quotes/{quote_id}/accept")
def accept_quote(quote_id: str, request: Request,
                 idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    key = _require_idempotency(idempotency_key)
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        quote = conn.execute("SELECT * FROM cash_quotes WHERE id=?", (quote_id,)).fetchone()
        if not quote:
            raise HTTPException(status_code=404, detail="Quote not found.")
        order = _get_order(conn, quote["order_id"])
        _authorize_buyer(order, request)
        # An explicitly authenticated TEST order in non-production may rehearse
        # quote acceptance without exposing or requiring real payout settings.
        # Every real order still requires owner-configured bank transfer details.
        is_test = bool(order["is_test"]) if "is_test" in order.keys() else False
        if not _bank_ready() and not is_test:
            raise HTTPException(status_code=503, detail="Fee-free bank transfer checkout is not configured by the owner.")
        if order["state"] in {"ORDER_PLACED", "AWAITING_PAYMENT", "CLAIM_SUBMITTED", "PAYMENT_EVIDENCE_REVIEW",
                               "VERIFIED", "FULFILLED", "CLOSED", "REFUNDED", "DISPUTED"}:
            if order["current_quote_id"] == quote_id and order["order_number"]:
                if order["acceptance_key"] and order["acceptance_key"] != key:
                    raise HTTPException(status_code=409, detail="This order was already accepted with a different idempotency key.")
                conn.commit()
                return {"order_id": order["id"], "order_number": order["order_number"],
                        "state": order["state"], "replayed": True}
            raise HTTPException(status_code=409, detail="Order cannot accept this quote.")
        if quote["status"] != "APPROVED" or order["state"] != "QUOTE_APPROVED" or order["current_quote_id"] != quote_id:
            raise HTTPException(status_code=409, detail="Quote is not approved and current.")
        if datetime.fromisoformat(quote["expires_at"].replace("Z", "+00:00")) <= _now():
            raise HTTPException(status_code=410, detail="Quote has expired.")
        now = _iso()
        order_number = "AP-" + _now().strftime("%Y%m%d") + "-" + order["id"][:6].upper()
        conn.execute("UPDATE cash_quotes SET status='ACCEPTED',accepted_at=?,updated_at=? WHERE id=?",
                     (now, now, quote_id))
        conn.execute("UPDATE cash_orders SET order_number=?,invoice_minor=?,invoice_currency='VND',acceptance_key=?,updated_at=? WHERE id=?",
                     (order_number, quote["proposal_minor"], key, now, order["id"]))
        _transition(conn, order, "ORDER_PLACED", "quote_accepted_order_placed", "buyer",
                    idempotency_key=f"accept:{quote_id}:placed", details={"quote_id": quote_id})
        latest = _get_order(conn, order["id"])
        _transition(conn, latest, "AWAITING_PAYMENT", "invoice_issued", "system",
                    idempotency_key=f"accept:{quote_id}:invoice", details={"currency": "VND"})
        conn.commit()
        return {"order_id": order["id"], "order_number": order_number,
                "state": "AWAITING_PAYMENT", "replayed": False}
    except HTTPException:
        conn.rollback()
        raise
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise HTTPException(status_code=409, detail="Order acceptance conflict.") from exc
    finally:
        conn.close()


@router.get("/api/cash/orders/{order_id}/payment-instructions")
def payment_instructions(order_id: str, request: Request):
    conn = _connect()
    try:
        order = _get_order(conn, order_id)
        _authorize_buyer(order, request)
        if order["state"] not in {"AWAITING_PAYMENT", "CLAIM_SUBMITTED", "PAYMENT_EVIDENCE_REVIEW"}:
            raise HTTPException(status_code=409, detail="This order is not awaiting bank transfer.")
        if not _bank_ready():
            raise HTTPException(status_code=503, detail="Bank transfer checkout is not configured.")
        memo = "AP" + order["id"].replace("-", "")[:10].upper()
        outstanding = max(0, int(order["invoice_minor"] or 0) - int(order["paid_minor"]))
        if outstanding <= 0:
            raise HTTPException(status_code=409, detail="No invoice balance remains to be paid.")
        return {"order_number": order["order_number"],
                "amount": {"amount_minor": outstanding, "currency": "VND", "label": "OUTSTANDING_INVOICE_BALANCE"},
                "invoice_total": {"amount_minor": order["invoice_minor"], "currency": "VND", "label": "ISSUED_INVOICE_TOTAL"},
                "owner_confirmed_receipts_minor": int(order["paid_minor"]),
                "payment_method": "BANK_TRANSFER", "bank": CONFIG.BANK_NAME,
                "account_number": CONFIG.BANK_ACCOUNT_NO, "account_name": CONFIG.BANK_ACCOUNT_NAME,
                "transfer_memo": memo,
                "warning": "Transfer instructions and QR codes are not proof of receipt. Your claim stays pending until the owner checks the receiving account statement."}
    finally:
        conn.close()


@router.post("/api/cash/orders/{order_id}/claims", status_code=202)
def submit_claim(order_id: str, request: Request, payload: ClaimPayload,
                 idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    key = _require_idempotency(idempotency_key)
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        order = _get_order(conn, order_id)
        _authorize_buyer(order, request)
        body = {"order_id": order_id, "claimed_minor": payload.claimed_minor,
                "reference": payload.transfer_reference.strip(), "note": payload.note.strip()}
        fingerprint = _canonical_hash(body)
        existing = conn.execute("SELECT * FROM cash_claims WHERE idempotency_key=?", (key,)).fetchone()
        if existing:
            if existing["payload_hash"] != fingerprint or existing["order_id"] != order_id:
                raise HTTPException(status_code=409, detail="Idempotency-Key was used for a different payment claim.")
            conn.commit()
            return {"claim_id": existing["id"], "state": order["state"], "claim_status": existing["status"], "replayed": True}
        if order["state"] != "AWAITING_PAYMENT":
            raise HTTPException(status_code=409, detail="This order is not accepting another payment claim.")
        pending = conn.execute("SELECT 1 FROM cash_claims WHERE order_id=? AND status IN ('CLAIM_SUBMITTED','IN_REVIEW') LIMIT 1",
                               (order_id,)).fetchone()
        if pending:
            raise HTTPException(status_code=409, detail="A payment claim is already awaiting owner review.")
        claim_id = str(uuid.uuid4())
        now = _iso()
        conn.execute(
            """INSERT INTO cash_claims(id,order_id,claimed_minor,currency,submitted_reference,buyer_note,
               status,payload_hash,idempotency_key,created_at,updated_at)
               VALUES(?,?,?,'VND',?,?,'CLAIM_SUBMITTED',?,?,?,?)""",
            (claim_id, order_id, payload.claimed_minor, body["reference"] or None,
             body["note"] or None, fingerprint, key, now, now),
        )
        _transition(conn, order, "CLAIM_SUBMITTED", "payment_claim_submitted", "buyer",
                    idempotency_key=f"claim:{key}:submitted", details={"claim_id": claim_id})
        latest = _get_order(conn, order_id)
        conn.execute("UPDATE cash_claims SET status='IN_REVIEW',updated_at=? WHERE id=?", (_iso(), claim_id))
        _transition(conn, latest, "PAYMENT_EVIDENCE_REVIEW", "payment_evidence_review_started", "system",
                    idempotency_key=f"claim:{key}:review", details={"claim_id": claim_id})
        conn.commit()
        return {"claim_id": claim_id, "state": "PAYMENT_EVIDENCE_REVIEW", "claim_status": "IN_REVIEW",
                "payment_verified": False, "revenue_recorded": False, "replayed": False}
    except HTTPException:
        conn.rollback()
        raise
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise HTTPException(status_code=409, detail="Duplicate or conflicting payment claim.") from exc
    finally:
        conn.close()


@router.get("/api/cash/admin/orders")
def admin_cash_orders(request: Request, limit: int = 100):
    _require_admin(request)
    if not 1 <= limit <= 200:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 200.")
    conn = _connect()
    try:
        rows = conn.execute("SELECT * FROM cash_orders ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return {"items": [{**_public_order(row), "customer": {"name": row["customer_name"],
                    "email": row["customer_email"]}, "trace_id": row["trace_id"]} for row in rows],
                "total": len(rows)}
    finally:
        conn.close()


@router.get("/api/cash/admin/claims")
def admin_claims(request: Request, limit: int = 100):
    _require_admin(request)
    if not 1 <= limit <= 200:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 200.")
    conn = _connect()
    try:
        rows = conn.execute(
            """SELECT c.id,c.order_id,c.claimed_minor,c.currency,c.submitted_reference,c.buyer_note,
               c.status,c.created_at,o.order_number,o.customer_email,o.product_name,o.invoice_minor
               FROM cash_claims c JOIN cash_orders o ON o.id=c.order_id
               ORDER BY c.created_at DESC LIMIT ?""", (limit,)).fetchall()
        return {"items": [dict(row) for row in rows], "total": len(rows)}
    finally:
        conn.close()


@router.post("/api/cash/admin/claims/{claim_id}/verify")
def verify_claim(claim_id: str, request: Request, payload: VerifyPayload,
                 idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    _require_admin(request)
    key = _require_idempotency(idempotency_key)
    if payload.confirm_funds_received is not True:
        raise HTTPException(status_code=422, detail="Owner must affirm funds were seen in the receiving account statement.")
    reference = _normalize_reference(payload.statement_reference)
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        replay = conn.execute("SELECT * FROM cash_transactions WHERE idempotency_key=?", (key,)).fetchone()
        if replay:
            replay_order = conn.execute("SELECT is_test FROM cash_orders WHERE id=?", (replay["order_id"],)).fetchone()
            replay_test = bool(replay_order["is_test"]) if replay_order else False
            scope = "test:nonproduction" if replay_test else _bank_scope()
            if (replay["claim_id"] != claim_id or int(replay["amount_minor"]) != payload.amount_received_minor
                    or replay["reference_scope"] != scope or replay["reference_normalized"] != reference):
                raise HTTPException(status_code=409, detail="Idempotency-Key was already used for different receipt evidence.")
            conn.commit()
            return {"transaction_id": replay["id"], "order_id": replay["order_id"],
                    "status": "VERIFIED", "assurance_level": replay["assurance_level"],
                    "revenue_recorded": not replay_test, "test_mode": replay_test, "replayed": True}
        claim = conn.execute("SELECT * FROM cash_claims WHERE id=?", (claim_id,)).fetchone()
        if not claim:
            raise HTTPException(status_code=404, detail="Payment claim not found.")
        order = _get_order(conn, claim["order_id"])
        is_test = bool(order["is_test"]) if "is_test" in order.keys() else False
        scope = "test:nonproduction" if is_test else _bank_scope()
        if order["state"] != "PAYMENT_EVIDENCE_REVIEW" or claim["status"] != "IN_REVIEW":
            raise HTTPException(status_code=409, detail="Claim is not awaiting payment evidence review.")
        if payload.amount_received_minor != int(claim["claimed_minor"]):
            raise HTTPException(status_code=409, detail="Statement amount does not match this buyer claim. Reject it and request a corrected claim before verification.")
        transaction_id = str(uuid.uuid4())
        now = _iso()
        conn.execute(
            """INSERT INTO cash_transactions(id,order_id,claim_id,amount_minor,currency,payment_method,
               reference_scope,reference_normalized,assurance_level,provenance,verified_by,verified_at,
               idempotency_key,trace_id,created_at) VALUES(?,?,?,?,'VND','BANK_TRANSFER',?,?,?,?,?,?,?,?,?)""",
            (transaction_id, order["id"], claim_id, payload.amount_received_minor, scope, reference,
             ASSURANCE_MANUAL, PROVENANCE_MANUAL, "owner", now, key, order["trace_id"], now),
        )
        conn.execute("UPDATE cash_claims SET status='VERIFIED',updated_at=? WHERE id=?", (now, claim_id))
        paid = int(order["paid_minor"]) + payload.amount_received_minor
        conn.execute("UPDATE cash_orders SET paid_minor=?,updated_at=? WHERE id=?", (paid, now, order["id"]))
        latest = _get_order(conn, order["id"])
        next_state = "VERIFIED" if paid >= int(order["invoice_minor"] or 0) else "AWAITING_PAYMENT"
        _transition(conn, latest, next_state, "bank_receipt_owner_verified", "owner",
                    idempotency_key=f"receipt:{key}:state", assurance_level=ASSURANCE_MANUAL,
                    provenance=PROVENANCE_MANUAL,
                    details={"claim_id": claim_id, "transaction_id": transaction_id,
                             "amount_minor": payload.amount_received_minor, "currency": "VND"})
        conn.commit()
        return {"transaction_id": transaction_id, "claim_id": claim_id, "order_id": order["id"],
                "state": next_state, "amount": {"amount_minor": payload.amount_received_minor, "currency": "VND"},
                "assurance_level": ASSURANCE_MANUAL, "provenance": PROVENANCE_MANUAL,
                "settled_balance": {"amount_minor": paid - int(order["refunded_minor"]), "currency": "VND"},
                "revenue_recorded": not is_test, "test_mode": is_test, "replayed": False}
    except HTTPException:
        conn.rollback()
        raise
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        if "UNIQUE constraint failed" in str(exc):
            raise HTTPException(status_code=409, detail="This bank transfer reference or idempotency key was already recorded.") from exc
        raise HTTPException(status_code=409, detail="Payment ledger conflict.") from exc
    except sqlite3.Error as exc:
        conn.rollback()
        raise HTTPException(status_code=503, detail="Payment verification could not be persisted.") from exc
    finally:
        conn.close()


@router.post("/api/cash/admin/claims/{claim_id}/reject")
def reject_claim(claim_id: str, request: Request, payload: RejectPayload,
                 idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    _require_admin(request)
    key = _require_idempotency(idempotency_key)
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        claim = conn.execute("SELECT * FROM cash_claims WHERE id=?", (claim_id,)).fetchone()
        if not claim:
            raise HTTPException(status_code=404, detail="Payment claim not found.")
        order = _get_order(conn, claim["order_id"])
        if claim["status"] == "REJECTED":
            conn.commit()
            return {"claim_id": claim_id, "state": order["state"], "replayed": True}
        if claim["status"] != "IN_REVIEW" or order["state"] != "PAYMENT_EVIDENCE_REVIEW":
            raise HTTPException(status_code=409, detail="Claim is not awaiting review.")
        now = _iso()
        conn.execute("UPDATE cash_claims SET status='REJECTED',rejection_reason=?,updated_at=? WHERE id=?",
                     (payload.reason.strip(), now, claim_id))
        conn.execute("UPDATE cash_orders SET state='AWAITING_PAYMENT',updated_at=? WHERE id=?",
                     (now, order["id"]))
        _event(conn, order["id"], "PAYMENT_EVIDENCE_REVIEW", "AWAITING_PAYMENT", "payment_claim_rejected",
               "owner", idempotency_key=f"reject:{key}", trace_id=order["trace_id"],
               details={"claim_id": claim_id, "reason": payload.reason.strip()})
        conn.commit()
        return {"claim_id": claim_id, "state": "AWAITING_PAYMENT", "replayed": False}
    except HTTPException:
        conn.rollback()
        raise
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise HTTPException(status_code=409, detail="Rejection idempotency conflict.") from exc
    finally:
        conn.close()


@router.post("/api/cash/admin/orders/{order_id}/cancel")
def cancel_order(order_id: str, request: Request, payload: RejectPayload,
                 idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    _require_admin(request)
    key = _require_idempotency(idempotency_key)
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        order = _get_order(conn, order_id)
        if order["state"] == "CANCELLED":
            conn.commit()
            return {"order_id": order_id, "state": "CANCELLED", "replayed": True}
        if order["state"] not in {"LEAD", "QUOTE_DRAFT", "QUOTE_APPROVED", "ORDER_PLACED", "AWAITING_PAYMENT",
                                   "CLAIM_SUBMITTED", "PAYMENT_EVIDENCE_REVIEW"} or int(order["paid_minor"]):
            raise HTTPException(status_code=409, detail="This order can no longer be cancelled; use refund/dispute handling.")
        conn.execute("UPDATE cash_orders SET cancel_reason=?,updated_at=? WHERE id=?",
                     (payload.reason.strip(), _iso(), order_id))
        _transition(conn, order, "CANCELLED", "order_cancelled", "owner",
                    idempotency_key=f"cancel:{key}", details={"reason": payload.reason.strip()})
        conn.commit()
        return {"order_id": order_id, "state": "CANCELLED", "replayed": False}
    except HTTPException:
        conn.rollback()
        raise
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise HTTPException(status_code=409, detail="Cancellation idempotency conflict.") from exc
    finally:
        conn.close()


def _record_adjustment(order_id: str, request: Request, *, adjustment_type: str,
                       amount_minor: int, reference_value: str, reason: str,
                       key_header: str | None) -> dict[str, Any]:
    _require_admin(request)
    key = _require_idempotency(key_header)
    reference = _normalize_reference(reference_value)
    scope = _bank_scope()
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        replay = conn.execute("SELECT * FROM cash_adjustments WHERE idempotency_key=?", (key,)).fetchone()
        if replay:
            if (replay["order_id"] != order_id or replay["adjustment_type"] != adjustment_type
                    or int(replay["amount_minor"]) != amount_minor or replay["reference_scope"] != scope
                    or replay["reference_normalized"] != reference or replay["reason"] != reason.strip()):
                raise HTTPException(status_code=409, detail="Idempotency-Key was already used for a different adjustment.")
            conn.commit()
            return {"adjustment_id": replay["id"], "order_id": replay["order_id"],
                    "state": "REFUNDED" if adjustment_type == "REFUND" else "DISPUTED", "replayed": True}
        order = _get_order(conn, order_id)
        if order["state"] not in {"VERIFIED", "FULFILLED", "DISPUTED", "REFUNDED", "CLOSED"}:
            raise HTTPException(status_code=409, detail="Only verified receipts can be refunded or disputed.")
        prior = int(conn.execute(
            """SELECT COALESCE(SUM(CASE
                 WHEN adjustment_type IN ('REFUND','CHARGEBACK') THEN amount_minor
                 WHEN adjustment_type='CHARGEBACK_REVERSAL' THEN -amount_minor ELSE 0 END),0)
               FROM cash_adjustments WHERE order_id=?""", (order_id,)).fetchone()[0])
        if amount_minor > int(order["paid_minor"]) - prior:
            raise HTTPException(status_code=409, detail="Adjustment exceeds the remaining settled amount.")
        if adjustment_type == "REFUND" and order["state"] == "DISPUTED":
            raise HTTPException(status_code=409, detail="Resolve the dispute before recording a refund.")
        adjustment_id = str(uuid.uuid4())
        now = _iso()
        conn.execute(
            """INSERT INTO cash_adjustments(id,order_id,adjustment_type,amount_minor,currency,
               reference_scope,reference_normalized,assurance_level,provenance,reason,verified_by,
               occurred_at,idempotency_key,trace_id,created_at)
               VALUES(?,?,?,?,'VND',?,?,'OWNER_MANUAL_ATTESTATION',?,?,?,?,?,?,?)""",
            (adjustment_id, order_id, adjustment_type, amount_minor, scope, reference,
             "owner_attested_outgoing_transfer_or_chargeback", reason.strip(), "owner", now,
             key, order["trace_id"], now),
        )
        if adjustment_type == "REFUND":
            conn.execute("UPDATE cash_orders SET refunded_minor=refunded_minor+?,updated_at=? WHERE id=?",
                         (amount_minor, now, order_id))
            target = "REFUNDED"
        else:
            conn.execute("UPDATE cash_orders SET charged_back_minor=charged_back_minor+?,updated_at=? WHERE id=?",
                         (amount_minor, now, order_id))
            target = "DISPUTED"
        latest = _get_order(conn, order_id)
        if latest["state"] != target:
            _transition(conn, latest, target, adjustment_type.lower(), "owner",
                        idempotency_key=f"adjustment:{key}:state",
                        assurance_level="OWNER_MANUAL_ATTESTATION",
                        provenance="owner_attested_outgoing_transfer_or_chargeback",
                        details={"adjustment_id": adjustment_id, "amount_minor": amount_minor, "currency": "VND"})
        else:
            _event(conn, order_id, target, target, adjustment_type.lower(), "owner",
                   idempotency_key=f"adjustment:{key}:state", trace_id=order["trace_id"],
                   assurance_level="OWNER_MANUAL_ATTESTATION",
                   provenance="owner_attested_outgoing_transfer_or_chargeback",
                   details={"adjustment_id": adjustment_id, "amount_minor": amount_minor, "currency": "VND"})
        conn.execute("UPDATE cash_deliveries SET status='REVOKED',revoked_at=?,updated_at=? WHERE order_id=? AND status='ACTIVE'",
                     (now, now, order_id))
        conn.commit()
        return {"adjustment_id": adjustment_id, "order_id": order_id, "state": target,
                "amount": {"amount_minor": amount_minor, "currency": "VND"},
                "assurance_level": "OWNER_MANUAL_ATTESTATION", "settled_balance": {
                    "amount_minor": int(order["paid_minor"]) - prior - amount_minor, "currency": "VND"},
                "replayed": False}
    except HTTPException:
        conn.rollback()
        raise
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        if "UNIQUE constraint failed" in str(exc):
            raise HTTPException(status_code=409, detail="Transfer reference or idempotency key was already recorded.") from exc
        raise HTTPException(status_code=409, detail="Adjustment ledger conflict.") from exc
    except sqlite3.Error as exc:
        conn.rollback()
        raise HTTPException(status_code=503, detail="Adjustment could not be persisted.") from exc
    finally:
        conn.close()


@router.post("/api/cash/admin/orders/{order_id}/refund")
def refund_order(order_id: str, request: Request, payload: RefundPayload,
                idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    return _record_adjustment(order_id, request, adjustment_type="REFUND", amount_minor=payload.amount_minor,
                              reference_value=payload.transfer_reference, reason=payload.reason,
                              key_header=idempotency_key)


@router.post("/api/cash/admin/orders/{order_id}/chargeback")
def chargeback_order(order_id: str, request: Request, payload: DisputePayload,
                     idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    return _record_adjustment(order_id, request, adjustment_type="CHARGEBACK", amount_minor=payload.amount_minor,
                              reference_value=payload.reference, reason=payload.reason,
                              key_header=idempotency_key)


@router.post("/api/cash/admin/orders/{order_id}/dispute/resolve")
def resolve_dispute(order_id: str, request: Request, payload: ResolveDisputePayload,
                    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    _require_admin(request)
    key = _require_idempotency(idempotency_key)
    outcome = payload.outcome
    reason = payload.reason.strip()
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        event_key = f"dispute:{key}"
        replay = conn.execute("SELECT * FROM cash_events WHERE idempotency_key=?", (event_key,)).fetchone()
        if replay:
            recorded = json.loads(replay["details_json"] or "{}")
            if (replay["order_id"] != order_id or replay["action"] != "dispute_resolved"
                    or recorded.get("outcome") != outcome or recorded.get("reason") != reason):
                raise HTTPException(status_code=409, detail="Idempotency-Key was already used for a different dispute resolution.")
            conn.commit()
            return {"order_id": order_id, "state": replay["to_state"], "outcome": outcome, "replayed": True}
        order = _get_order(conn, order_id)
        if order["state"] != "DISPUTED":
            raise HTTPException(status_code=409, detail="Order has no open dispute.")
        prior_dispute = conn.execute(
            """SELECT from_state FROM cash_events WHERE order_id=? AND action='chargeback'
               AND from_state IN ('VERIFIED','FULFILLED','REFUNDED','CLOSED')
               ORDER BY id DESC LIMIT 1""", (order_id,)
        ).fetchone()
        restored_state = str(prior_dispute["from_state"]) if prior_dispute else "VERIFIED"
        target = restored_state if outcome == "WON" else "CLOSED"
        if outcome == "WON":
            chargebacks = conn.execute(
                """SELECT a.* FROM cash_adjustments a
                   WHERE a.order_id=? AND a.adjustment_type='CHARGEBACK'
                     AND NOT EXISTS (SELECT 1 FROM cash_adjustments r WHERE r.reverses_adjustment_id=a.id)""",
                (order_id,),
            ).fetchall()
            reversed_total = 0
            for original in chargebacks:
                now = _iso()
                reversal_key = f"dispute:{key}:reversal:{original['id']}"
                reversal_ref = f"REV-{original['reference_normalized']}"[:120]
                conn.execute(
                    """INSERT INTO cash_adjustments(id,order_id,adjustment_type,amount_minor,currency,
                       reference_scope,reference_normalized,assurance_level,provenance,reason,
                       reverses_adjustment_id,verified_by,occurred_at,idempotency_key,trace_id,created_at)
                       VALUES(?,?,'CHARGEBACK_REVERSAL',?,'VND',?,?,'OWNER_MANUAL_ATTESTATION',?,?,?,?,?,?,?,?)""",
                    (str(uuid.uuid4()), order_id, original["amount_minor"], original["reference_scope"],
                     reversal_ref, "owner_attested_bank_dispute_reversal", reason,
                     original["id"], "owner", now, reversal_key, order["trace_id"], now),
                )
                reversed_total += int(original["amount_minor"])
            if reversed_total:
                conn.execute("UPDATE cash_orders SET charged_back_minor=MAX(0,charged_back_minor-?),updated_at=? WHERE id=?",
                             (reversed_total, _iso(), order_id))
        _transition(conn, order, target, "dispute_resolved", "owner", idempotency_key=event_key,
                    details={"outcome": outcome, "reason": reason})
        if outcome == "WON":
            delivery = conn.execute("SELECT * FROM cash_deliveries WHERE order_id=?", (order_id,)).fetchone()
            if (target == "FULFILLED" and delivery
                    and datetime.fromisoformat(delivery["expires_at"].replace("Z", "+00:00")) > _now()):
                conn.execute("UPDATE cash_deliveries SET status='ACTIVE',revoked_at=NULL,updated_at=? WHERE id=?",
                             (_iso(), delivery["id"]))
        conn.commit()
        return {"order_id": order_id, "state": target, "outcome": outcome, "replayed": False}
    except HTTPException:
        conn.rollback()
        raise
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise HTTPException(status_code=409, detail="Dispute resolution idempotency conflict.") from exc
    finally:
        conn.close()


@router.post("/api/cash/admin/orders/{order_id}/close")
def close_order(order_id: str, request: Request,
                idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    _require_admin(request)
    key = _require_idempotency(idempotency_key)
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        order = _get_order(conn, order_id)
        if order["state"] == "CLOSED":
            conn.commit()
            return {"order_id": order_id, "state": "CLOSED", "replayed": True}
        if order["state"] not in {"VERIFIED", "FULFILLED", "REFUNDED", "DISPUTED"}:
            raise HTTPException(status_code=409, detail="Only settled, refunded, or resolved orders can be closed.")
        _transition(conn, order, "CLOSED", "order_closed", "owner", idempotency_key=f"close:{key}")
        conn.commit()
        return {"order_id": order_id, "state": "CLOSED", "replayed": False}
    except HTTPException:
        conn.rollback()
        raise
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise HTTPException(status_code=409, detail="Close idempotency conflict.") from exc
    finally:
        conn.close()


def _validated_artifact_path(artifact_id: str) -> tuple[Path, dict[str, Any]]:
    if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,159}", artifact_id):
        raise HTTPException(status_code=404, detail="Staging artifact not found.")
    root = STAGING_DIR.resolve()
    path = (root / f"{artifact_id}.zip").resolve()
    if path.parent != root or not path.is_file():
        raise HTTPException(status_code=404, detail="Staging artifact not found.")
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if not sidecar.is_file():
        raise HTTPException(status_code=409, detail="Staging artifact integrity sidecar is missing.")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    expected_line = f"{digest}  {path.name}"
    if expected_line not in sidecar.read_text(encoding="ascii", errors="ignore").splitlines():
        raise HTTPException(status_code=409, detail="Staging artifact integrity check failed.")
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)) or any("\\" in name or PurePosixPath(name).is_absolute()
                                                    or ".." in PurePosixPath(name).parts for name in names):
                raise HTTPException(status_code=409, detail="Staging artifact contains unsafe paths.")
            manifest = json.loads(archive.read("BUILD_MANIFEST.json"))
            file_hashes = manifest.get("files") or {}
            for name, expected in file_hashes.items():
                clean = PurePosixPath(name)
                if (clean.is_absolute() or ".." in clean.parts or "\\" in name
                        or name not in names or hashlib.sha256(archive.read(name)).hexdigest() != expected):
                    raise HTTPException(status_code=409, detail="Staging artifact internal file hash failed.")
    except HTTPException:
        raise
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, AttributeError) as exc:
        raise HTTPException(status_code=409, detail="Staging artifact manifest is invalid.") from exc
    if (not isinstance(manifest, dict) or manifest.get("status") != "STAGING_QA_PASS"
            or manifest.get("quality_score") != 100 or not isinstance(file_hashes, dict)
            or not file_hashes or manifest.get("product_id") != artifact_id):
        raise HTTPException(status_code=409, detail="Only a fully QA-passed package with matching identity can be delivered.")
    return path, manifest


@router.post("/api/cash/admin/orders/{order_id}/fulfill")
def fulfill_order(order_id: str, request: Request, payload: FulfillPayload):
    _require_admin(request)
    _secret()
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        order = _get_order(conn, order_id)
        if order["state"] == "FULFILLED":
            delivery = conn.execute("SELECT * FROM cash_deliveries WHERE order_id=?", (order_id,)).fetchone()
            if not delivery:
                raise HTTPException(status_code=409, detail="Fulfilled order is missing its delivery record.")
            if delivery["artifact_id"] != payload.artifact_id:
                raise HTTPException(status_code=409, detail="Order was already fulfilled with a different artifact.")
            conn.commit()
            return {"order_id": order_id, "delivery_id": delivery["id"], "artifact_id": delivery["artifact_id"],
                    "expires_at": delivery["expires_at"],
                    "status": delivery["status"], "replayed": True}
        if order["state"] != "VERIFIED":
            raise HTTPException(status_code=409, detail="Only fully verified orders can be fulfilled.")
        artifact_id = payload.artifact_id
        _validated_artifact_path(artifact_id)
        slug = str(order["product_slug"] or "")
        delivery_id = str(uuid.uuid4())
        now = _now()
        expires = _iso(now + timedelta(days=7))
        key = f"cash-delivery:{order_id}"
        conn.execute(
            """INSERT INTO cash_deliveries(id,order_id,product_slug,artifact_id,status,expires_at,idempotency_key,
               trace_id,created_at,updated_at) VALUES(?,?,?,?,'ACTIVE',?,?,?,?,?)""",
            (delivery_id, order_id, slug, artifact_id, expires, key, order["trace_id"], _iso(now), _iso(now)),
        )
        _transition(conn, order, "FULFILLED", "digital_delivery_authorized", "owner",
                    idempotency_key=f"{key}:event", details={"delivery_id": delivery_id,
                                                              "expires_at": expires, "product_slug": slug})
        conn.commit()
        return {"order_id": order_id, "delivery_id": delivery_id, "artifact_id": artifact_id, "expires_at": expires,
                "status": "ACTIVE", "replayed": False}
    except HTTPException:
        conn.rollback()
        raise
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise HTTPException(status_code=409, detail="Delivery already exists or order state changed.") from exc
    finally:
        conn.close()


@router.get("/api/cash/deliveries/{delivery_id}/download")
def download_delivery(delivery_id: str, request: Request):
    conn = _connect()
    try:
        delivery = conn.execute("SELECT * FROM cash_deliveries WHERE id=?", (delivery_id,)).fetchone()
        if not delivery:
            raise HTTPException(status_code=404, detail="Delivery not found.")
        order = _get_order(conn, delivery["order_id"])
        _authorize_buyer(order, request)
        expires = datetime.fromisoformat(delivery["expires_at"].replace("Z", "+00:00"))
        if delivery["status"] != "ACTIVE" or delivery["revoked_at"] or expires <= _now():
            raise HTTPException(status_code=410, detail="Delivery authorization has expired or was revoked.")
        if order["state"] not in {"FULFILLED"}:
            raise HTTPException(status_code=403, detail="Order is not eligible for download.")
        path, _manifest = _validated_artifact_path(delivery["artifact_id"])
        conn.execute("UPDATE cash_deliveries SET download_count=download_count+1,updated_at=? WHERE id=?",
                     (_iso(), delivery_id))
        conn.commit()
        return FileResponse(path, media_type="application/zip", filename=path.name,
                            headers={"Cache-Control": "private, no-store", "X-Delivery-Expires-At": delivery["expires_at"]})
    finally:
        conn.close()


@router.get("/api/cash/admin/summary")
def cash_summary(request: Request):
    _require_admin(request)
    conn = _connect()
    try:
        inbound = conn.execute("SELECT t.currency,SUM(t.amount_minor) AS amount,COUNT(*) AS count FROM cash_transactions t JOIN cash_orders o ON o.id=t.order_id WHERE o.is_test=0 GROUP BY t.currency").fetchall()
        adjustments = conn.execute("SELECT a.currency,SUM(a.amount_minor) AS amount,a.adjustment_type FROM cash_adjustments a JOIN cash_orders o ON o.id=a.order_id WHERE o.is_test=0 GROUP BY a.currency,a.adjustment_type").fetchall()
        test_records_excluded = int(conn.execute("SELECT COUNT(*) FROM cash_orders WHERE is_test=1").fetchone()[0])
        net: dict[str, int] = {str(row["currency"]): int(row["amount"] or 0) for row in inbound}
        for row in adjustments:
            currency = str(row["currency"])
            direction = 1 if row["adjustment_type"] == "CHARGEBACK_REVERSAL" else -1
            net[currency] = net.get(currency, 0) + direction * int(row["amount"] or 0)
        return {"source": "cash_transactions_and_immutable_adjustments", "assurance_label": "OWNER_MANUAL_ATTESTATION",
                "test_records_excluded": test_records_excluded,
                "settled_balance_by_currency": [{"currency": currency, "amount_minor": amount,
                    "label": "VERIFIED_RECEIPTS_LESS_REFUNDS_AND_CHARGEBACKS"}
                    for currency, amount in sorted(net.items())],
                "verified_receipts": {str(row["currency"]): int(row["count"]) for row in inbound},
                "estimated_value": "excluded", "proposal_amount": "excluded", "pending_invoice": "excluded",
                "buyer_claims": "excluded", "legacy_transactions": "excluded_until_reconciled_with_currency_and_provenance",
                "fx_conversion": "none"}
    finally:
        conn.close()


@router.get("/api/cash/admin/orders/{order_id}/transactions")
def cash_order_transactions(order_id: str, request: Request):
    _require_admin(request)
    conn = _connect()
    try:
        _get_order(conn, order_id)
        receipts = conn.execute(
            """SELECT id,claim_id,amount_minor,currency,payment_method,reference_scope,reference_normalized,
                      assurance_level,provenance,verified_by,verified_at,trace_id
               FROM cash_transactions WHERE order_id=? ORDER BY verified_at,id""", (order_id,)
        ).fetchall()
        adjustments = conn.execute(
            """SELECT id,adjustment_type,amount_minor,currency,reference_scope,reference_normalized,
                      assurance_level,provenance,reason,reverses_adjustment_id,verified_by,occurred_at,trace_id
               FROM cash_adjustments WHERE order_id=? ORDER BY occurred_at,id""", (order_id,)
        ).fetchall()
        return {"receipts": [dict(row) for row in receipts], "adjustments": [dict(row) for row in adjustments],
                "assurance_label": ASSURANCE_MANUAL}
    finally:
        conn.close()


@router.get("/api/cash/admin/orders/{order_id}/events")
def cash_order_events(order_id: str, request: Request):
    _require_admin(request)
    conn = _connect()
    try:
        _get_order(conn, order_id)
        rows = conn.execute("""SELECT id,from_state,to_state,action,actor,assurance_level,provenance,
                             details_json,trace_id,created_at FROM cash_events WHERE order_id=? ORDER BY id""",
                            (order_id,)).fetchall()
        return {"items": [{**dict(row), "details": json.loads(row["details_json"] or "{}")} for row in rows]}
    finally:
        conn.close()
