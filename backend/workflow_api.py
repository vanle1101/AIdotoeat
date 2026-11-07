"""Persistent API workflows used by the dashboard's action buttons.

The endpoints in this module store reviewable requests and local settings. A
record is never counted as revenue until an owner verifies a payment.
"""
from __future__ import annotations

import hmac
import ipaddress
import json
import os
import re
import sqlite3
import uuid
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Body, HTTPException, Query, Request
from fastapi.responses import FileResponse

from apps_library import TOOL_DEFINITIONS
from config import APPS_DIR, CONFIG
from database import get_connection

router = APIRouter()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _admin(request: Request) -> bool:
    expected = os.getenv("AUTOPROFIT_ADMIN_API_KEY", "")
    supplied = request.headers.get("X-Admin-Key", "")
    return bool(expected and supplied and hmac.compare_digest(expected, supplied))


def _require_admin(request: Request) -> None:
    if not os.getenv("AUTOPROFIT_ADMIN_API_KEY", ""):
        raise HTTPException(status_code=503, detail="Quản trị chưa được cấu hình trên máy chủ.")
    if not _admin(request):
        raise HTTPException(status_code=403, detail="Cần khóa quản trị hợp lệ.")


def _decode(value: Any, fallback: Any = None) -> Any:
    try:
        return json.loads(value) if value is not None else fallback
    except (TypeError, ValueError):
        return fallback


def _setting(key: str, default: Any = None) -> Any:
    conn = get_connection()
    try:
        row = conn.execute("SELECT value FROM system_state WHERE key = ?", ("workflow:" + key,)).fetchone()
        return _decode(row["value"], default) if row else default
    finally:
        conn.close()


def _set_setting(key: str, value: Any) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO system_state(key, value, updated_at) VALUES(?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            ("workflow:" + key, json.dumps(value, ensure_ascii=False), _now()),
        )
        conn.commit()
    finally:
        conn.close()


def _record(kind: str, payload: Dict[str, Any], status: str = "PENDING_REVIEW", record_id: Optional[str] = None) -> Dict[str, Any]:
    record_id = record_id or str(uuid.uuid4())
    now = _now()
    payload = dict(payload)
    payload["id"] = record_id
    payload["status"] = status
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO workflow_records(id, kind, status, payload_json, created_at, updated_at) VALUES(?, ?, ?, ?, ?, ?)",
            (record_id, kind, status, json.dumps(payload, ensure_ascii=False), now, now),
        )
        conn.commit()
    finally:
        conn.close()
    return {**payload, "created_at": now, "updated_at": now}


def _get_record(kind: str, record_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM workflow_records WHERE kind=? AND id=?", (kind, record_id)).fetchone()
        if not row:
            return None
        return {**(_decode(row["payload_json"], {}) or {}), "id": row["id"], "status": row["status"],
                "created_at": row["created_at"], "updated_at": row["updated_at"]}
    finally:
        conn.close()


def _list_records(kind: str, limit: int = 200) -> list[Dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM workflow_records WHERE kind=? ORDER BY created_at DESC LIMIT ?", (kind, limit)
        ).fetchall()
        return [{**(_decode(row["payload_json"], {}) or {}), "id": row["id"], "status": row["status"],
                 "created_at": row["created_at"], "updated_at": row["updated_at"]} for row in rows]
    finally:
        conn.close()


def _update_record(kind: str, record_id: str, status: str, patch: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    current = _get_record(kind, record_id)
    if not current:
        raise HTTPException(status_code=404, detail="Bản ghi không tồn tại.")
    payload = {**current, **(patch or {}), "id": record_id, "status": status}
    updated = _now()
    conn = get_connection()
    try:
        conn.execute("UPDATE workflow_records SET status=?, payload_json=?, updated_at=? WHERE kind=? AND id=?",
                     (status, json.dumps(payload, ensure_ascii=False), updated, kind, record_id))
        conn.commit()
    finally:
        conn.close()
    payload["updated_at"] = updated
    return payload


def _audit(action: str, kind: Optional[str] = None, record_id: Optional[str] = None,
           actor: str = "system", details: Optional[Dict[str, Any]] = None) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO workflow_events(action, record_kind, record_id, actor, details_json, created_at) VALUES(?, ?, ?, ?, ?, ?)",
            (action, kind, record_id, actor, json.dumps(details or {}, ensure_ascii=False), _now()),
        )
        conn.commit()
    finally:
        conn.close()


def _products() -> list[Dict[str, Any]]:
    result = []
    for tool in TOOL_DEFINITIONS:
        override = _setting("product:" + tool["slug"], {}) or {}
        price = float(override.get("price_usd", tool["price_usd"]))
        result.append({
            "id": tool["slug"], "product_id": tool["slug"], "slug": tool["slug"],
            "name": override.get("name", tool["name"]), "category": tool["category"],
            "price_usd": price, "display_price": f"${price:.2f}",
            "price_vnd": round(price * 25500), "description": override.get("description", tool["description"]),
            "demo_url": f"/apps/{tool['slug']}.html", "download_url": f"/api/products/{tool['slug']}/download",
            "pricing_model": override.get("pricing_model", "FIXED"),
            "base_price_usd": float(override.get("base_price_usd", price)),
            "min_price_usd": float(override.get("min_price_usd", max(0.5, price * 0.8))),
            "max_price_usd": float(override.get("max_price_usd", max(price * 3, price + 1))),
            "target_gross_margin": override.get("target_gross_margin"),
            "max_discount_pct": float(override.get("max_discount_pct", 20)),
        })
    return result


def _find_product(slug: str) -> Optional[Dict[str, Any]]:
    aliases = {
        "github-vietqr-crypto-payment-link-maker": "vietqr-crypto-payment-generator",
        "github-defi-stablecoin-apy-yield-optimizer": "defi-staking-yield-compounder",
        "github-papaparse-csv-to-json-converter": "papaparse-csv-to-json-cleaner",
        "github-css-glassmorphism-landing-builder": "css-glassmorphism-card-builder",
    }
    clean = aliases.get(slug, slug.removeprefix("github-"))
    return next((item for item in _products() if item["slug"] == clean), None)


def _insert_transaction(source: str, amount_usd: float, payment_method: str, tx_hash: Optional[str] = None,
                        amount_vnd: Optional[float] = None) -> None:
    conn = get_connection()
    try:
        if tx_hash and conn.execute("SELECT 1 FROM transactions WHERE lower(tx_hash)=lower(?)", (tx_hash,)).fetchone():
            raise HTTPException(status_code=409, detail="Mã giao dịch đã được ghi nhận.")
        conn.execute(
            "INSERT INTO transactions(tx_hash, source, amount_usd, amount_vnd, payment_method, status, created_at) VALUES(?, ?, ?, ?, ?, 'PAID_VERIFIED', ?)",
            (tx_hash, source, amount_usd, amount_vnd, payment_method, _now()),
        )
        conn.commit()
    finally:
        conn.close()


def _verify_workflow_payment(kind: str, record_id: str, amount_usd: float, payment_method: str,
                             statement_reference: str, amount_vnd: Optional[float],
                             patch: Dict[str, Any], audit_action: str) -> Dict[str, Any]:
    """Record owner-attested payment and status change atomically."""
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM workflow_records WHERE kind=? AND id=?", (kind, record_id)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Bản ghi không tồn tại.")
        current = {**(_decode(row["payload_json"], {}) or {}), "id": row["id"], "status": row["status"]}
        if row["status"] == "PAID_VERIFIED":
            conn.rollback()
            return {**current, "already_verified": True}
        if conn.execute("SELECT 1 FROM transactions WHERE lower(tx_hash)=lower(?)", (statement_reference,)).fetchone():
            raise HTTPException(status_code=409, detail="Mã giao dịch đã được ghi nhận.")

        now = _now()
        payload = {**current, **patch, "id": record_id, "status": "PAID_VERIFIED"}
        conn.execute(
            "INSERT INTO transactions(tx_hash, source, amount_usd, amount_vnd, payment_method, status, created_at) "
            "VALUES(?, ?, ?, ?, ?, 'PAID_VERIFIED', ?)",
            (statement_reference, f"{kind}:{record_id}", amount_usd, amount_vnd, payment_method, now),
        )
        conn.execute(
            "UPDATE workflow_records SET status='PAID_VERIFIED', payload_json=?, updated_at=? WHERE kind=? AND id=?",
            (json.dumps(payload, ensure_ascii=False), now, kind, record_id),
        )
        conn.execute(
            "INSERT INTO workflow_events(action, record_kind, record_id, actor, details_json, created_at) "
            "VALUES(?, ?, ?, 'owner', ?, ?)",
            (audit_action, kind, record_id, json.dumps({"amount_usd": amount_usd, "payment_reference": statement_reference}, ensure_ascii=False), now),
        )
        conn.commit()
        return {**payload, "updated_at": now}
    except HTTPException:
        conn.rollback()
        raise
    except sqlite3.Error:
        conn.rollback()
        raise HTTPException(status_code=503, detail="Không thể lưu kết quả đối soát thanh toán.")
    finally:
        conn.close()


@router.post("/api/admin/auth/verify")
def verify_admin_key(request: Request):
    if not os.getenv("AUTOPROFIT_ADMIN_API_KEY", ""):
        raise HTTPException(status_code=503, detail="Máy chủ chưa cấu hình khóa quản trị.")
    if not _admin(request):
        raise HTTPException(status_code=403, detail="Khóa quản trị không hợp lệ.")
    return {"verified": True, "status": "owner_admin"}


@router.get("/api/audit-logs")
def audit_logs(request: Request, limit: int = Query(default=100, ge=1, le=500)):
    if not _admin(request):
        return {"items": [], "total": 0, "status": "owner_auth_required"}
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM workflow_events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        items = [{"id": row["id"], "action": row["action"], "record_kind": row["record_kind"],
                  "record_id": row["record_id"], "actor": row["actor"],
                  "details": _decode(row["details_json"], {}), "created_at": row["created_at"]} for row in rows]
        return {"items": items, "total": len(items), "status": "observed"}
    finally:
        conn.close()


@router.get("/api/opportunities")
def opportunities():
    items = _list_records("opportunity")
    return {"items": items, "total": len(items), "status": "observed" if items else "no_data", "source": "local_workflow_records"}


@router.get("/api/leads")
def leads(request: Request):
    if not _admin(request):
        return {"items": [], "total": None, "status": "owner_auth_required"}
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, name, email, company, source, need, stage, fit_score, proposal_text, country, created_at FROM leads ORDER BY id DESC LIMIT 200"
        ).fetchall()
        items = []
        for row in rows:
            item = dict(row)
            item["custom_proposal"] = item.pop("proposal_text", None)
            item["requires_owner_approval"] = item.get("stage") in {"NEW", "AUDIT_PENDING", "PROPOSAL_DRAFT"}
            items.append(item)
        return {"items": items, "total": len(items), "status": "observed" if items else "no_data"}
    finally:
        conn.close()


@router.get("/api/products")
def products():
    items = _products()
    return {"items": items, "total": len(items), "status": "observed"}


@router.put("/api/products/{product_id}")
def update_product(product_id: str, request: Request, payload: Dict[str, Any] = Body(...)):
    _require_admin(request)
    product = _find_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Sản phẩm không tồn tại.")
    name = str(payload.get("name", product["name"])).strip()[:160]
    description = str(payload.get("problem_solved", payload.get("description", product["description"]))).strip()[:1000]
    try:
        price = float(payload.get("price_usd", product["price_usd"]))
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="Giá phải là số hợp lệ.")
    if not name or not 0.5 <= price <= 10000:
        raise HTTPException(status_code=422, detail="Tên sản phẩm hoặc mức giá ngoài giới hạn.")
    settings = _setting("product:" + product["slug"], {}) or {}
    settings.update({"name": name, "description": description, "price_usd": round(price, 2), "base_price_usd": round(price, 2)})
    _set_setting("product:" + product["slug"], settings)
    _audit("product_updated", "product", product["slug"], "owner", {"price_usd": round(price, 2)})
    return {"status": "updated", "product": _find_product(product["slug"])}


@router.get("/api/products/{slug}/download")
def download_product(slug: str):
    product = _find_product(slug)
    if not product:
        raise HTTPException(status_code=404, detail="Sản phẩm không tồn tại trong catalog.")
    path = APPS_DIR / f"{product['slug']}.html"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Tệp HTML của sản phẩm chưa được tạo.")
    return FileResponse(path, filename=f"{product['slug']}.html", media_type="text/html")


@router.get("/api/marketing")
def marketing():
    items = _list_records("marketing", 200)
    return {"items": items, "total": len(items), "status": "observed" if items else "no_data"}


@router.post("/api/marketing/generate/{product_id}")
def generate_marketing(product_id: str, request: Request):
    product = _find_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Sản phẩm không tồn tại.")
    title = f"{product['name']} — công cụ trực tuyến"
    description = product["description"]
    keywords = ", ".join([product["name"], product["category"], "công cụ trực tuyến"])
    body = f"{description}\n\nDùng thử miễn phí tại {product['demo_url']}. Giá hiện tại: ${product['price_usd']:.2f} USD."
    record = _record("marketing", {"product_id": product["id"], "title": title, "asset_type": "SEO_DRAFT",
                                    "channel": "WEBSITE", "target_keywords": keywords,
                                    "content_body": body, "visits": 0, "conversions": 0}, "DRAFT")
    _audit("marketing_draft_created", "marketing", record["id"], "owner" if _admin(request) else "system")
    return {"status": "created", "asset": record, "source": "local_template"}


@router.get("/api/employees")
def employees(request: Request):
    try:
        from core.roles import list_all_roles
        roles = list_all_roles()
    except Exception:
        roles = []
    items = [{"id": role.role_id, "name": role.name, "role": role.role_id, "department": role.department,
              "status": "IDLE", "runtime_connected": False} for role in roles]
    dynamic = _list_records("employee_proposal", 200)
    if not _admin(request):
        dynamic = [item for item in dynamic if item.get("status") in {"APPROVED_PENDING_RUNTIME", "RETIRED"}]
    items.extend({"id": item["id"], "employee_id": item["id"], "name": item.get("full_name_vi"),
                  "role": item.get("role_code"), "department": item.get("department_id"),
                  "status": item["status"], "runtime_connected": False,
                  "appearance": item.get("appearance", {})} for item in dynamic)
    active = sum(item["status"] == "RUNNING" for item in items)
    return {"items": items, "total": len(items), "active_count": active,
            "status": "observed" if items else "no_data", "source": "core.roles + workflow_records"}


@router.post("/api/employees/propose")
def propose_employee(payload: Dict[str, Any] = Body(...), request: Request = None):
    role_code = re.sub(r"[^A-Z0-9_\-]", "", str(payload.get("role_code", "")).upper())[:48]
    full_name = str(payload.get("full_name_vi", "")).strip()[:100]
    job_title = str(payload.get("job_title_vi", "")).strip()[:160]
    if not role_code or not full_name or not job_title:
        raise HTTPException(status_code=422, detail="Cần mã vai trò, tên nhân viên và chức danh.")
    if payload.get("auto_approve"):
        _require_admin(request)
    auto_approve = bool(payload.get("auto_approve"))
    lifecycle_state = "APPROVED_PENDING_RUNTIME" if auto_approve else "PENDING_APPROVAL"
    record = _record("employee_proposal", {
        "role_code": role_code, "full_name_vi": full_name,
        "full_name_en": str(payload.get("full_name_en", full_name))[:100],
        "department_id": str(payload.get("department_id", ""))[:80],
        "job_title_vi": job_title, "primary_mission_vi": str(payload.get("primary_mission_vi", ""))[:1000],
        "business_justification": str(payload.get("business_justification", ""))[:1000],
        "skills": payload.get("skills", [])[:40] if isinstance(payload.get("skills", []), list) else [],
        "authorized_tools": payload.get("authorized_tools", [])[:40] if isinstance(payload.get("authorized_tools", []), list) else [],
        "runtime_connected": False,
        "approved_by": "owner" if auto_approve else None,
    }, lifecycle_state)
    _audit("employee_proposal_approved" if auto_approve else "employee_proposed", "employee_proposal", record["id"], "owner" if _admin(request) else "visitor",
           {"runtime_connected": False})
    return {"id": record["id"], "employee_id": record["id"], "full_name_vi": full_name,
            "full_name_en": record["full_name_en"], "assigned_workstation_id": None,
            "lifecycle_state": lifecycle_state, "runtime_connected": False}


@router.post("/api/employees/{employee_id}/approve")
def approve_employee(employee_id: str, request: Request):
    _require_admin(request)
    updated = _update_record("employee_proposal", employee_id, "APPROVED_PENDING_RUNTIME", {"approved_by": "owner"})
    _audit("employee_proposal_approved", "employee_proposal", employee_id, "owner")
    return {"status": updated["status"], "runtime_connected": False}


@router.post("/api/employees/{employee_id}/retire")
def retire_employee(employee_id: str, request: Request, payload: Dict[str, Any] = Body(default={} )):
    _require_admin(request)
    updated = _update_record("employee_proposal", employee_id, "RETIRED", {"retirement_reason": str(payload.get("reason", ""))[:300]})
    _audit("employee_retired", "employee_proposal", employee_id, "owner")
    return {"status": updated["status"]}


@router.put("/api/employees/{employee_id}/appearance")
def update_employee_appearance(employee_id: str, request: Request, payload: Dict[str, Any] = Body(...)):
    _require_admin(request)
    employee = _get_record("employee_proposal", employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhân viên mở rộng.")
    appearance = {key: value for key, value in payload.items() if key in {"avatar", "color", "outfit", "scale", "offset"}}
    updated = _update_record("employee_proposal", employee_id, employee["status"], {"appearance": appearance})
    return {"id": employee_id, "appearance": updated["appearance"]}


@router.post("/api/leads/auto-approve-all")
def prepare_leads_for_review(request: Request):
    _require_admin(request)
    conn = get_connection()
    try:
        rows = conn.execute("SELECT id, proposal_text FROM leads WHERE proposal_text IS NOT NULL AND trim(proposal_text) != '' AND stage NOT IN ('PROPOSAL_APPROVED','CONTACTED')").fetchall()
        conn.execute("UPDATE leads SET stage='PROPOSAL_DRAFT' WHERE proposal_text IS NOT NULL AND trim(proposal_text) != '' AND stage NOT IN ('PROPOSAL_APPROVED','CONTACTED')")
        conn.commit()
        count = len(rows)
    finally:
        conn.close()
    _audit("leads_prepared_for_review", "lead", None, "owner", {"count": count})
    return {"total_leads": count, "status": "WAITING_OWNER_REVIEW", "sent_to_customers": False}


@router.post("/api/leads/{lead_id}/approve-proposal")
def approve_lead_proposal(lead_id: str, request: Request):
    _require_admin(request)
    conn = get_connection()
    try:
        row = conn.execute("SELECT id, proposal_text FROM leads WHERE id=?", (lead_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Khách hàng tiềm năng không tồn tại.")
        if not row["proposal_text"]:
            raise HTTPException(status_code=409, detail="Lead chưa có nội dung đề xuất để duyệt.")
        conn.execute("UPDATE leads SET stage='PROPOSAL_APPROVED' WHERE id=?", (lead_id,))
        conn.commit()
    finally:
        conn.close()
    _audit("lead_proposal_approved", "lead", str(lead_id), "owner", {"sent_to_customer": False})
    return {"status": "PROPOSAL_APPROVED", "sent_to_customer": False}


@router.post("/api/public/advertising-inquiries", status_code=202)
def submit_advertising_inquiry(payload: Dict[str, Any] = Body(...)):
    name = str(payload.get("sponsor_name", "")).strip()[:120]
    email = str(payload.get("contact_email", "")).strip().lower()[:254]
    target = str(payload.get("target_url", "")).strip()[:500]
    headline = str(payload.get("ad_copy_headline", "")).strip()[:180]
    if not name or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email) or not headline:
        raise HTTPException(status_code=422, detail="Tên, email hợp lệ và nội dung quảng cáo là bắt buộc.")
    parsed = urlparse(target)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=422, detail="Liên kết đích phải là URL http hoặc https.")
    price = 4.99 if payload.get("package_code") == "HOMEPAGE_3D_BILLBOARD" else 2.99
    record = _record("advertising_inquiry", {"sponsor_name": name, "contact_email": email,
        "package_code": str(payload.get("package_code", "STANDARD"))[:60], "target_url": target,
        "ad_copy_headline": headline, "quoted_price_usd": price,
        "payment_proof_ref": str(payload.get("payment_proof_ref", "")).strip()[:120] or None,
        "payment_verified": False}, "PENDING_PAYMENT")
    _audit("advertising_inquiry_submitted", "advertising_inquiry", record["id"], "visitor")
    return {"accepted": True, "id": record["id"], "status": record["status"]}


@router.get("/api/public/advertising-inquiries")
def list_advertising_inquiries(request: Request):
    if not _admin(request):
        return {"items": [], "inquiries": [], "active_verified_sponsors": [], "total": None, "status": "owner_auth_required"}
    items = _list_records("advertising_inquiry")
    verified = [item for item in items if item.get("status") == "PAID_VERIFIED"]
    return {"items": items, "inquiries": items, "active_verified_sponsors": verified,
            "total": len(items), "status": "observed" if items else "no_data"}


@router.post("/api/admin/advertising-inquiries/{inquiry_id}/verify")
def verify_advertising_inquiry(inquiry_id: str, request: Request, payload: Dict[str, Any] = Body(default={} )):
    _require_admin(request)
    inquiry = _get_record("advertising_inquiry", inquiry_id)
    if not inquiry:
        raise HTTPException(status_code=404, detail="Yêu cầu quảng cáo không tồn tại.")
    if inquiry["status"] == "PAID_VERIFIED":
        return {"status": "PAID_VERIFIED", "already_verified": True, "campaign_activated": False}
    statement_reference = str(payload.get("statement_reference", "")).strip()[:120]
    if len(statement_reference) < 4:
        raise HTTPException(status_code=422, detail="Nhập mã tham chiếu trên sao kê ngân hàng sau khi đã đối chiếu khoản tiền.")
    amount_usd = float(inquiry.get("quoted_price_usd") or 0)
    if amount_usd <= 0:
        raise HTTPException(status_code=409, detail="Yêu cầu quảng cáo không có số tiền hợp lệ.")
    updated = _verify_workflow_payment("advertising_inquiry", inquiry_id, amount_usd,
        "MANUAL_BANK_REVIEW", statement_reference, round(amount_usd * 25500), {
        "payment_verified": True, "verified_by": "owner_manual_statement",
        "owner_statement_reference": statement_reference,
    }, "advertising_payment_verified")
    return {"status": updated["status"], "campaign_activated": False}


@router.post("/api/public/donations", status_code=202)
def submit_donation(payload: Dict[str, Any] = Body(...)):
    currency = str(payload.get("currency", "")).upper()
    amount_vnd = float(payload.get("amount_vnd") or 0)
    amount_usd = float(payload.get("amount_usd") or payload.get("pledged_amount_usd") or 0)
    if currency == "VND" and amount_vnd < 2000:
        raise HTTPException(status_code=422, detail="Khoản ủng hộ tối thiểu là 2.000 VND.")
    if currency == "USD" and amount_usd < 1:
        raise HTTPException(status_code=422, detail="Khoản ủng hộ tối thiểu là 1 USD.")
    if currency not in {"VND", "USD"}:
        raise HTTPException(status_code=422, detail="Loại tiền không hợp lệ.")
    record = _record("donation", {"supporter_name": str(payload.get("supporter_name", "Anonymous Supporter"))[:100],
        "target_employee_id": str(payload.get("target_employee_id", "PROJECT_WIDE"))[:80],
        "message": str(payload.get("message", ""))[:500],
        "tx_hash_or_ref": str(payload.get("tx_hash_or_ref", "")).strip()[:120] or None,
        "currency": currency, "amount_vnd": amount_vnd if currency == "VND" else None,
        "amount_usd": amount_usd if currency == "USD" else None,
        "payment_method": str(payload.get("payment_method", ""))[:40], "payment_verified": False}, "PENDING_VERIFICATION")
    _audit("donation_submitted", "donation", record["id"], "visitor")
    return {"accepted": True, "id": record["id"], "status": record["status"]}


@router.get("/api/public/donations")
def list_donations(request: Request):
    if not _admin(request):
        return {"items": [], "total": None, "verified_donations_usd": None, "status": "owner_auth_required"}
    items = _list_records("donation")
    for item in items:
        item["pledged_amount_usd"] = round(float(item.get("amount_usd") or (float(item.get("amount_vnd") or 0) / 25500)), 2)
    verified_total = round(sum(item["pledged_amount_usd"] for item in items if item.get("status") == "PAID_VERIFIED"), 2)
    return {"items": items, "total": len(items), "verified_donations_usd": verified_total,
            "status": "observed" if items else "no_data"}


@router.post("/api/admin/donations/{donation_id}/verify")
def verify_donation(donation_id: str, request: Request, payload: Dict[str, Any] = Body(default={} )):
    _require_admin(request)
    donation = _get_record("donation", donation_id)
    if not donation:
        raise HTTPException(status_code=404, detail="Khoản ủng hộ không tồn tại.")
    if donation.get("status") == "PAID_VERIFIED":
        return {"status": "PAID_VERIFIED", "already_verified": True}
    statement_reference = str(payload.get("statement_reference", "")).strip()[:120]
    if len(statement_reference) < 4:
        raise HTTPException(status_code=422, detail="Nhập mã tham chiếu trên sao kê ngân hàng sau khi đã đối chiếu khoản tiền.")
    amount_usd = float(donation.get("amount_usd") or (float(donation.get("amount_vnd") or 0) / 25500))
    updated = _verify_workflow_payment("donation", donation_id, amount_usd,
        donation.get("payment_method", "MANUAL"), statement_reference, donation.get("amount_vnd"), {
        "payment_verified": True, "verified_by": "owner_manual_statement",
        "owner_statement_reference": statement_reference,
    }, "donation_payment_verified")
    return {"status": "PAID_VERIFIED", "revenue_recorded": not updated.get("already_verified", False),
            "already_verified": updated.get("already_verified", False)}


@router.get("/api/settings/budgets")
def get_budgets(request: Request):
    budgets = _setting("budgets", {"operating_mode": "GUARDED_AUTONOMY", "max_daily_tasks": 5,
        "daily_budget_limit_usd": 0, "monthly_budget_limit_usd": 0, "task_budget_limit_usd": 0})
    if not _admin(request):
        return {"status": "owner_auth_required", "settings": None}
    return {"status": "observed", "settings": budgets, **budgets}


@router.put("/api/settings/budgets")
def update_budgets(request: Request, payload: Dict[str, Any] = Body(...)):
    _require_admin(request)
    try:
        values = {"operating_mode": str(payload.get("operating_mode", "GUARDED_AUTONOMY")),
            "max_daily_tasks": int(payload.get("max_daily_tasks", 5)),
            "daily_budget_limit_usd": float(payload.get("daily_budget_limit_usd", 0)),
            "monthly_budget_limit_usd": float(payload.get("monthly_budget_limit_usd", 0)),
            "task_budget_limit_usd": float(payload.get("task_budget_limit_usd", 0))}
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="Giá trị cấu hình phải là số hợp lệ.")
    if values["operating_mode"] not in {"SIMULATION", "ASSISTED", "GUARDED_AUTONOMY"} or not 1 <= values["max_daily_tasks"] <= 100 or any(v < 0 or v > 100000 for k, v in values.items() if k.endswith("_usd")):
        raise HTTPException(status_code=422, detail="Cấu hình vượt giới hạn an toàn.")
    _set_setting("budgets", values)
    _audit("budget_settings_updated", "settings", "budgets", "owner", values)
    return {"status": "saved", "settings": values, **values}


@router.get("/api/payout-policies")
def get_payout_policy(request: Request):
    policy = _setting("payout_policy", {"minimum_payout_threshold_usd": 20, "max_payout_amount_usd": 500,
        "max_total_employees": 15, "max_employees_per_day": 3, "require_owner_confirmation": True,
        "approved_destinations": []})
    if not _admin(request):
        return {"status": "owner_auth_required", "policy": {"require_owner_confirmation": True}}
    return {"status": "observed", "policy": policy}


@router.put("/api/payout-policies")
def update_payout_policy(request: Request, payload: Dict[str, Any] = Body(...)):
    _require_admin(request)
    try:
        policy = {"minimum_payout_threshold_usd": float(payload.get("minimum_payout_threshold_usd", 20)),
            "max_payout_amount_usd": float(payload.get("max_payout_amount_usd", 500)),
            "max_total_employees": int(payload.get("max_total_employees", 15)),
            "max_employees_per_day": int(payload.get("max_employees_per_day", 3)),
            "require_owner_confirmation": True, "approved_destinations": []}
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="Chính sách chứa giá trị không hợp lệ.")
    if policy["minimum_payout_threshold_usd"] < 0 or policy["max_payout_amount_usd"] < policy["minimum_payout_threshold_usd"] or not 1 <= policy["max_total_employees"] <= 100 or not 1 <= policy["max_employees_per_day"] <= 20:
        raise HTTPException(status_code=422, detail="Chính sách vượt giới hạn hợp lệ.")
    _set_setting("payout_policy", policy)
    _audit("payout_policy_updated", "settings", "payout_policy", "owner")
    return {"status": "saved", "policy": policy}


@router.post("/api/public/aads-config")
def update_aads_config(request: Request, payload: Dict[str, Any] = Body(...)):
    _require_admin(request)
    unit_id = str(payload.get("aads_unit_id", "")).strip()
    if not re.fullmatch(r"\d{5,12}", unit_id) or unit_id == "517750":
        raise HTTPException(status_code=422, detail="Cần mã Ad Unit A-Ads 5-12 chữ số, không dùng User ID.")
    settings = _setting("aads", {}) or {}
    settings["top_ad_unit_id"] = unit_id
    _set_setting("aads", settings)
    _audit("aads_unit_updated", "settings", "aads", "owner", {"unit_id": unit_id})
    return {**settings, "status": "saved"}


@router.post("/api/public/notebook/interact")
def notebook_interact(payload: Dict[str, Any] = Body(...)):
    question = str(payload.get("question", "")).strip()[:1000]
    role = str(payload.get("target_agent_role", "CUSTOMER_SUPPORT_AGENT"))[:80]
    if not question:
        raise HTTPException(status_code=422, detail="Hãy nhập câu hỏi.")
    names = {"SALES_AGENT": "Đặng Quân", "CUSTOMER_SUPPORT_AGENT": "Ngô Mai",
             "FINANCE_AGENT": "Bảo Trâm", "RESEARCH_AGENT": "Lê Minh", "PRODUCT_AGENT": "Hoàng Bách"}
    name = names.get(role, "Trợ lý AUTOProfit")
    if any(word in question.lower() for word in ("giá", "price", "gói", "tool")):
        reply = "Catalog hiện có 12 Web App; giá được hiển thị tại mục Sản phẩm. Thanh toán chỉ được xác nhận sau khi chủ cửa hàng đối soát."
    elif any(word in question.lower() for word in ("khách", "lead", "đơn", "doanh thu")):
        reply = "Mình chỉ có thể trả lời từ dữ liệu đã lưu. Lead, đơn chờ thanh toán và doanh thu đã xác minh được tách riêng trong dashboard."
    else:
        reply = "Mục trò chuyện AI chưa nối nhà cung cấp mô hình. Đây là phản hồi tự động theo quy tắc; bạn có thể xem số liệu đã ghi nhận trong dashboard."
    _audit("visitor_notebook_interaction", "notebook", None, "visitor", {"role": role})
    return {"message_id": str(uuid.uuid4()), "agent_role": role, "agent_human_name": name,
            "visitor_name": str(payload.get("visitor_name", "Khách ghé thăm"))[:80],
            "inner_thought": "", "reply_message": reply, "status": "rules_based",
            "message_type": "SYSTEM_STATUS", "llm_connected": False}


@router.get("/api/public/donations/health")
def donation_health():
    return {"status": "ok"}


@router.post("/api/opportunities/analyze-freelance-job")
def analyze_freelance_job(payload: Dict[str, Any] = Body(...)):
    title = str(payload.get("title", "")).strip()[:200]
    requirements = str(payload.get("requirements", "")).strip()[:4000]
    if not title or not requirements:
        raise HTTPException(status_code=422, detail="Cần tiêu đề và yêu cầu dự án.")
    budget = payload.get("published_budget_usd")
    budget = float(budget) if budget not in (None, "") else None
    signals = sum(1 for word in ("website", "seo", "html", "audit", "automation", "json", "python") if word in (title + " " + requirements).lower())
    fit = min(95, 35 + signals * 8 + (10 if budget and budget >= 100 else 0))
    reason = "Điểm phù hợp dựa trên từ khóa kỹ thuật và ngân sách được cung cấp; cần người xem xét nguồn và yêu cầu trước khi gửi." 
    proposal = f"Chào bạn,\n\nMình đã xem yêu cầu “{title}”. AUTOProfit có thể hỗ trợ phân tích phạm vi, kiểm toán kỹ thuật và đề xuất hướng triển khai.\n\nPhạm vi cần xác nhận:\n{requirements[:700]}\n\nVui lòng xác nhận tiêu chí nghiệm thu và thời hạn để chốt báo giá.\n\nBản nháp này chưa được gửi tự động."
    record = _record("opportunity", {"name": title, "title": title,
        "platform": str(payload.get("platform", "Manual"))[:80], "source_url": str(payload.get("source_url", ""))[:500],
        "requirements": requirements, "published_budget_usd": budget, "fit_score": fit,
        "total_score": fit, "selection_or_rejection_reason": reason,
        "drafted_proposal": proposal, "source": "manual_user_input", "contacted": False}, "REVIEW_REQUIRED")
    return {"id": record["id"], "fit_score": fit, "selection_or_rejection_reason": reason,
            "drafted_proposal": proposal, "status": "REVIEW_REQUIRED", "saved": True}


@router.post("/api/internet/live-scan")
def live_internet_scan():
    url = "https://hn.algolia.com/api/v1/search_by_date?tags=show_hn&hitsPerPage=10"
    request = urllib.request.Request(url, headers={"User-Agent": "AUTOProfitDashboard/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=7) as response:
            data = json.loads(response.read(1_500_000).decode("utf-8"))
    except (OSError, ValueError, urllib.error.URLError):
        return {"status": "source_unavailable", "source": "Hacker News Algolia API", "items": [],
                "audited_live_websites": [], "created_leads": [], "total_opportunities_in_db": len(_list_records("opportunity"))}
    saved = []
    for hit in data.get("hits", [])[:10]:
        title = str(hit.get("title") or "").strip()
        link = str(hit.get("url") or "").strip()
        if not title or not link or not urlparse(link).scheme.startswith("http"):
            continue
        existing = next((item for item in _list_records("opportunity", 200) if item.get("source_url") == link), None)
        if existing:
            continue
        saved.append(_record("opportunity", {"name": title, "title": title, "source_url": link,
            "source": "Hacker News Show HN", "points": int(hit.get("points") or 0),
            "created_at_source": hit.get("created_at"), "contacted": False,
            "selection_or_rejection_reason": "Nguồn công khai; cần kiểm tra thủ công trước khi liên hệ."}, "REVIEW_REQUIRED"))
    items = _list_records("opportunity")
    return {"status": "observed", "source": "Hacker News Algolia API", "items": saved,
            "audited_live_websites": [], "created_leads": [], "total_opportunities_in_db": len(items),
            "message": "Đã thu thập bài Show HN công khai; chưa crawl website và chưa tạo lead khách hàng."}


def _audit_html(html: str) -> Dict[str, Any]:
    lower = html.lower()
    issues, fixes = [], []
    if not re.search(r"<title\b[^>]*>\s*[^<]{2,}", html, re.I):
        issues.append("Trang chưa có thẻ title hữu ích.")
        fixes.append("<title>Tiêu đề mô tả nội dung trang</title>")
    if not re.search(r"<meta\b[^>]*name=[\"']description[\"'][^>]*content=[\"'][^\"']{20,}", html, re.I):
        issues.append("Thiếu meta description dài tối thiểu 20 ký tự.")
        fixes.append('<meta name="description" content="Mô tả ngắn, đúng nội dung và lợi ích của trang.">')
    h1_count = len(re.findall(r"<h1\b", html, re.I))
    if h1_count != 1:
        issues.append(f"Trang có {h1_count} thẻ H1; nên có đúng một H1 chính.")
        fixes.append("<h1>Tiêu đề chính của trang</h1>")
    images = re.findall(r"<img\b[^>]*>", html, re.I)
    missing_alt = sum(1 for image in images if not re.search(r"\balt\s*=", image, re.I))
    if missing_alt:
        issues.append(f"Có {missing_alt} ảnh chưa có thuộc tính alt.")
        fixes.append('<img src="image.webp" alt="Mô tả ngắn về hình ảnh">')
    score = max(0, 100 - 20 * len(issues))
    if not html.strip():
        score = 0
        issues.append("Không nhận được nội dung HTML để kiểm tra.")
    return {"overall_health_score": score, "identified_issues": issues,
            "ready_to_paste_fixes": fixes, "html_bytes": len(html.encode("utf-8")),
            "checks_run": ["title", "meta_description", "h1", "image_alt"]}


@router.post("/api/products/live-audit-demo")
def live_audit(payload: Dict[str, Any] = Body(...)):
    html = str(payload.get("html_content", ""))
    if len(html.encode("utf-8")) > 1_000_000:
        raise HTTPException(status_code=413, detail="HTML tối đa 1 MB.")
    if not html.strip():
        raise HTTPException(status_code=422, detail="Dán mã HTML vào ô đầu vào; URL chỉ được ghi chú, máy chủ không tự crawl URL.")
    report = _audit_html(html)
    price = 29.0
    proposal = f"Bản nháp kiểm toán cho {str(payload.get('business_name', 'Website'))[:120]}: phát hiện {len(report['identified_issues'])} vấn đề trong HTML được cung cấp. Giá dịch vụ tham khảo ${price:.2f}; cần chủ sở hữu rà soát trước khi gửi."
    lead_id = None
    if payload.get("save_as_lead"):
        conn = get_connection()
        try:
            cursor = conn.execute("INSERT INTO leads(name, company, source, need, stage, fit_score, proposal_text, created_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                (str(payload.get("business_name", "Website prospect"))[:120], str(payload.get("target_url", ""))[:250],
                 "local_html_audit", "Website technical audit", "AUDIT_PENDING", report["overall_health_score"], proposal, _now()))
            lead_id = cursor.lastrowid
            conn.commit()
        finally:
            conn.close()
    return {"status": "completed", "price_usd": price, "audit_report": report,
            "custom_proposal_draft": proposal, "lead_id": lead_id, "source": "user_supplied_html"}


@router.get("/api/pricing/catalog")
def pricing_catalog():
    return {"items": _products(), "total": len(TOOL_DEFINITIONS), "status": "observed"}


@router.put("/api/pricing/catalog/{product_id}")
def update_pricing(product_id: str, request: Request, payload: Dict[str, Any] = Body(...)):
    _require_admin(request)
    product = _find_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Sản phẩm không tồn tại.")
    try:
        values = {"pricing_model": str(payload.get("pricing_model", "FIXED")),
                  "base_price_usd": float(payload.get("base_price_usd", product["price_usd"])),
                  "target_gross_margin": float(payload.get("target_gross_margin", 0.65)),
                  "min_price_usd": float(payload.get("min_price_usd", product["min_price_usd"])),
                  "max_price_usd": float(payload.get("max_price_usd", product["max_price_usd"])),
                  "max_discount_pct": float(payload.get("max_discount_pct", 20))}
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="Cấu hình giá phải là số hợp lệ.")
    if values["pricing_model"] not in {"FIXED", "TIERED", "COST_PLUS"} or not 0.5 <= values["min_price_usd"] <= values["base_price_usd"] <= values["max_price_usd"] <= 10000 or not 0 <= values["target_gross_margin"] <= 0.95 or not 0 <= values["max_discount_pct"] <= 80:
        raise HTTPException(status_code=422, detail="Cấu hình giá vi phạm giới hạn giá/min/max/discount.")
    settings = _setting("product:" + product["slug"], {}) or {}
    old_price = float(settings.get("base_price_usd", product["price_usd"]))
    settings.update(values)
    settings["price_usd"] = values["base_price_usd"]
    _set_setting("product:" + product["slug"], settings)
    _record("price_change", {"product_id": product["slug"], "previous_price_usd": old_price,
        "new_price_usd": values["base_price_usd"], "reason": str(payload.get("reason", "Owner update"))[:300]}, "APPLIED")
    _audit("pricing_config_updated", "product", product["slug"], "owner", values)
    return {"status": "saved", "product": _find_product(product["slug"])}


@router.get("/api/pricing/history")
def pricing_history(request: Request):
    if not _admin(request):
        return {"items": [], "total": None, "status": "owner_auth_required"}
    items = _list_records("price_change") + _list_records("pricing_quote")
    items.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return {"items": items[:200], "total": len(items), "status": "observed" if items else "no_data"}


@router.get("/api/pricing/recommendations")
def pricing_recommendations(request: Request):
    if not _admin(request):
        return {"items": [], "total": None, "status": "owner_auth_required"}
    items = _list_records("pricing_recommendation")
    return {"items": items, "total": len(items), "status": "observed" if items else "no_data"}


@router.post("/api/pricing/recommendations/generate")
def generate_pricing_recommendations(request: Request):
    _require_admin(request)
    existing = _list_records("pricing_recommendation")
    created = []
    for product in _products():
        current = product["price_usd"]
        suggested = min(product["max_price_usd"], round(current * 1.05, 2))
        if suggested <= current:
            continue
        created.append(_record("pricing_recommendation", {"product_id": product["id"], "product_name": product["name"],
            "current_price_usd": current, "recommended_price_usd": suggested,
            "basis": "Quy tắc cục bộ +5%; không phải phân tích AI hay dữ liệu thị trường.",
            "source": "deterministic_local_rule"}, "PENDING_REVIEW"))
    _audit("pricing_recommendations_generated", "pricing_recommendation", None, "owner", {"created": len(created)})
    return {"status": "created", "count": len(created), "items": created, "source": "deterministic_local_rule"}


@router.post("/api/pricing/recommendations/{recommendation_id}/review")
def review_pricing_recommendation(recommendation_id: str, request: Request, payload: Dict[str, Any] = Body(...)):
    _require_admin(request)
    action = str(payload.get("action", "")).upper()
    if action not in {"APPROVE", "REJECT"}:
        raise HTTPException(status_code=422, detail="Hành động chỉ được là APPROVE hoặc REJECT.")
    recommendation = _get_record("pricing_recommendation", recommendation_id)
    if not recommendation:
        raise HTTPException(status_code=404, detail="Đề xuất giá không tồn tại.")
    if recommendation["status"] != "PENDING_REVIEW":
        raise HTTPException(status_code=409, detail="Đề xuất này đã được xử lý.")
    if action == "APPROVE":
        product = _find_product(recommendation["product_id"])
        settings = _setting("product:" + product["slug"], {}) or {}
        settings["price_usd"] = recommendation["recommended_price_usd"]
        settings["base_price_usd"] = recommendation["recommended_price_usd"]
        _set_setting("product:" + product["slug"], settings)
    status = "APPROVED" if action == "APPROVE" else "REJECTED"
    _update_record("pricing_recommendation", recommendation_id, status, {"reviewed_by": "owner", "review_reason": str(payload.get("reason", ""))[:300]})
    _audit("pricing_recommendation_reviewed", "pricing_recommendation", recommendation_id, "owner", {"action": action})
    return {"status": status, "applied": action == "APPROVE"}


@router.post("/api/pricing/quote")
def calculate_quote(payload: Dict[str, Any] = Body(...)):
    product = _find_product(str(payload.get("product_id", "")))
    if not product:
        raise HTTPException(status_code=404, detail="Sản phẩm không tồn tại trong catalog.")
    try:
        quantity = int(payload.get("quantity_units", 1))
        complexity = float(payload.get("complexity_multiplier", 1))
        discount = float(payload.get("discount_usd", 0))
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="Số lượng, độ phức tạp hoặc giảm giá không hợp lệ.")
    if not 1 <= quantity <= 1000 or not 0.5 <= complexity <= 5 or discount < 0:
        raise HTTPException(status_code=422, detail="Số lượng/độ phức tạp/giảm giá nằm ngoài giới hạn.")
    tier = str(payload.get("tier_code", "GROWTH")).upper()
    tier_mult = {"STARTER": 0.8, "GROWTH": 1.0, "PRO": 1.5, "ENTERPRISE": 2.0}.get(tier)
    urgency = str(payload.get("urgency_level", "STANDARD")).upper()
    urgency_mult = {"STANDARD": 1.0, "RUSH": 1.25, "ASAP": 1.5}.get(urgency)
    if tier_mult is None or urgency_mult is None:
        raise HTTPException(status_code=422, detail="Tier hoặc mức khẩn cấp không hợp lệ.")
    base = product["base_price_usd"]
    subtotal = base * tier_mult * urgency_mult * complexity * quantity
    min_total = product["min_price_usd"] * quantity
    max_total = product["max_price_usd"] * quantity
    custom = payload.get("custom_quoted_price_usd")
    if custom not in (None, ""):
        try:
            subtotal = float(custom)
        except (TypeError, ValueError):
            raise HTTPException(status_code=422, detail="Báo giá riêng phải là số hợp lệ.")
    if subtotal < min_total or subtotal > max_total:
        raise HTTPException(status_code=422, detail=f"Báo giá phải trong khoảng ${min_total:.2f}–${max_total:.2f}.")
    max_discount = subtotal * product["max_discount_pct"] / 100
    if discount > max_discount:
        raise HTTPException(status_code=422, detail=f"Mức giảm tối đa là ${max_discount:.2f} theo cấu hình.")
    net = round(subtotal - discount, 2)
    quote_id = str(uuid.uuid4())
    quote = {"quote_id": quote_id, "product_id": product["id"], "pricing_model": product["pricing_model"],
        "selected_tier_code": tier, "quantity_units": quantity, "urgency_level": urgency,
        "subtotal_usd": round(subtotal, 2), "discount_usd": round(discount, 2), "net_total_usd": net,
        "estimated_gross_profit_usd": None, "estimated_gross_margin_pct": None,
        "cost_breakdown": {"total_estimated_cost_usd": None, "enforced_minimum_price_usd": min_total,
                           "cost_data_status": "not_connected"},
        "status": "LOCKED" if payload.get("lock_quote") else "PREVIEW"}
    if payload.get("lock_quote"):
        _record("pricing_quote", quote, "LOCKED", quote_id)
    return {"quote": quote, "source": "local_catalog_rules"}


@router.get("/api/orders")
def list_orders(request: Request):
    if not _admin(request):
        return {"items": [], "total": None, "status": "owner_auth_required"}
    items = _list_records("order")
    return {"items": items, "total": len(items), "status": "observed" if items else "no_data"}


@router.post("/api/orders", status_code=201)
def create_order(request: Request, payload: Dict[str, Any] = Body(...)):
    _require_admin(request)
    customer_id = str(payload.get("customer_id", "")).strip()[:80]
    product = _find_product(str(payload.get("product_id", "")))
    if not customer_id or not product:
        raise HTTPException(status_code=422, detail="Chọn khách hàng và sản phẩm hợp lệ.")
    try:
        discount = float(payload.get("discount_usd", 0))
        units = int(payload.get("quantity_units", 1))
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="Số lượng hoặc giảm giá không hợp lệ.")
    quote_id = str(payload.get("quote_id") or "").strip()
    if quote_id:
        quote = _get_record("pricing_quote", quote_id)
        if not quote or quote.get("product_id") != product["id"]:
            raise HTTPException(status_code=409, detail="Báo giá khóa không tồn tại hoặc không khớp sản phẩm.")
        amount = float(quote["net_total_usd"])
    else:
        if not 1 <= units <= 1000 or discount < 0 or discount > product["price_usd"] * product["max_discount_pct"] / 100:
            raise HTTPException(status_code=422, detail="Số lượng/giảm giá vượt giới hạn.")
        amount = round(max(product["min_price_usd"] * units, product["price_usd"] * units - discount), 2)
    if not 0 < amount <= product["max_price_usd"] * max(1, units):
        raise HTTPException(status_code=422, detail="Tổng đơn hàng ngoài giới hạn giá.")
    order_id = str(uuid.uuid4())
    number = "AP-" + datetime.now(timezone.utc).strftime("%Y%m%d") + "-" + order_id[:6].upper()
    record = _record("order", {"order_number": number, "customer_id": customer_id, "product_id": product["id"],
        "product_name": product["name"], "payment_provider": str(payload.get("payment_provider", "BANK_TRANSFER"))[:40],
        "discount_usd": discount, "quantity_units": units, "quote_id": quote_id or None,
        "proposal_text": str(payload.get("custom_proposal", ""))[:2000], "net_amount_usd": amount,
        "net_amount_vnd": round(amount * 25500), "payment_reference": None}, "PENDING_PAYMENT", order_id)
    _audit("order_created", "order", order_id, "owner", {"amount_usd": amount})
    return {**record, "order_id": order_id}


@router.post("/api/payments/submit-mbbank-proof", status_code=202)
def submit_bank_proof(request: Request, payload: Dict[str, Any] = Body(...)):
    order_id = str(payload.get("order_id", ""))
    order = _get_record("order", order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng.")
    if order["status"] in {"PAID_VERIFIED", "FULFILLED"}:
        raise HTTPException(status_code=409, detail="Đơn hàng đã được xác minh thanh toán.")
    reference = str(payload.get("bank_tx_ref", "")).strip()[:120]
    try:
        amount = float(payload.get("amount_vnd", 0))
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="Số tiền VND không hợp lệ.")
    if len(reference) < 4 or amount <= 0:
        raise HTTPException(status_code=422, detail="Cần mã giao dịch và số tiền chuyển khoản.")
    if abs(amount - float(order["net_amount_vnd"])) > 1:
        raise HTTPException(status_code=409, detail="Số tiền chuyển khoản không khớp đơn hàng.")
    updated = _update_record("order", order_id, "PENDING_VERIFICATION", {"payment_reference": reference,
        "submitted_amount_vnd": amount, "payment_method": "MB_BANK_TRANSFER"})
    _audit("bank_payment_proof_submitted", "order", order_id, "owner")
    return {"status": updated["status"], "message": "Đã lưu mã tham chiếu. Cần đối chiếu sao kê trước khi ghi nhận doanh thu."}


@router.post("/api/payments/verify-mbbank-tx")
def verify_bank_payment(request: Request, payload: Dict[str, Any] = Body(...)):
    _require_admin(request)
    order_id = str(payload.get("order_id", ""))
    order = _get_record("order", order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng.")
    reference = str(payload.get("bank_tx_ref", "")).strip()[:120]
    if order.get("status") != "PENDING_VERIFICATION" or reference != order.get("payment_reference"):
        raise HTTPException(status_code=409, detail="Mã tham chiếu không khớp yêu cầu đang chờ đối soát.")
    try:
        amount_vnd = float(payload.get("amount_vnd", order["net_amount_vnd"]))
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="Số tiền VND không hợp lệ.")
    if abs(amount_vnd - float(order["net_amount_vnd"])) > 1:
        raise HTTPException(status_code=409, detail="Số tiền sao kê không khớp đơn hàng.")
    _insert_transaction("order:" + order_id, float(order["net_amount_usd"]), "MB_BANK_TRANSFER", reference, amount_vnd)
    _update_record("order", order_id, "PAID_VERIFIED", {"verified_by": "owner_manual_statement", "payment_reference": reference})
    _audit("bank_payment_verified", "order", order_id, "owner")
    return {"status": "PAID_VERIFIED", "order_number": order["order_number"], "revenue_recorded": True}


def _verify_bsc_receipt(tx_hash: str, expected_usd: float) -> float:
    wallet = os.getenv("AUTOPROFIT_BSC_USDT_WALLET", "0xe55dd69db44609553fe54e30498f0d3a705acb9e").strip().lower()
    rpc_url = os.getenv("AUTOPROFIT_BSC_RPC_URL", "https://bsc-dataseed.binance.org/").strip()
    token = os.getenv("AUTOPROFIT_BSC_USDT_CONTRACT", "0x55d398326f99059ff775485246999027b3197955").lower()
    if not wallet:
        raise HTTPException(status_code=503, detail="Chưa cấu hình ví nhận USDT BEP20 trên máy chủ; không thể xác minh hoặc giao hàng tự động.")
    if not re.fullmatch(r"0x[0-9a-fA-F]{64}", tx_hash):
        raise HTTPException(status_code=422, detail="TxHash phải có dạng 0x và 64 ký tự hex.")
    if not re.fullmatch(r"0x[0-9a-f]{40}", wallet) or not re.fullmatch(r"0x[0-9a-f]{40}", token):
        raise HTTPException(status_code=503, detail="Cấu hình ví hoặc hợp đồng USDT BEP20 không hợp lệ.")
    body = json.dumps({"jsonrpc": "2.0", "method": "eth_getTransactionReceipt", "params": [tx_hash], "id": 1}).encode()
    request = urllib.request.Request(rpc_url, data=body, headers={"Content-Type": "application/json", "User-Agent": "AUTOProfit/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            data = json.loads(response.read(256_000).decode("utf-8"))
    except (OSError, ValueError, urllib.error.URLError):
        raise HTTPException(status_code=503, detail="Không truy cập được BSC RPC; khoản thanh toán chưa được xác minh.")
    receipt = data.get("result")
    if not receipt:
        raise HTTPException(status_code=404, detail="Không tìm thấy giao dịch trên BNB Smart Chain.")
    if str(receipt.get("status", "")).lower() != "0x1":
        raise HTTPException(status_code=409, detail="Giao dịch blockchain thất bại.")
    transfer_topic = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
    expected_topic = "0x" + wallet[2:].rjust(64, "0")
    amount = 0.0
    for log in receipt.get("logs", []):
        topics = [str(value).lower() for value in log.get("topics", [])]
        if str(log.get("address", "")).lower() == token and len(topics) >= 3 and topics[0] == transfer_topic and topics[2] == expected_topic:
            try:
                amount += int(str(log.get("data", "0x0")), 16) / 10**18
            except ValueError:
                continue
    if amount + 0.000001 < expected_usd:
        raise HTTPException(status_code=409, detail="Số USDT chuyển vào ví nhận thấp hơn giá trị đơn hàng.")
    return amount


@router.post("/api/payments/verify-bsc-tx")
def verify_bsc_order_payment(request: Request, payload: Dict[str, Any] = Body(...)):
    _require_admin(request)
    order_id = str(payload.get("order_id", ""))
    order = _get_record("order", order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng.")
    amount = _verify_bsc_receipt(str(payload.get("tx_hash", "")).lower(), float(order["net_amount_usd"]))
    _insert_transaction("order:" + order_id, amount, "BSC_USDT_BEP20", str(payload["tx_hash"]).lower())
    _update_record("order", order_id, "PAID_VERIFIED", {"tx_hash": str(payload["tx_hash"]).lower(), "verified_by": "bsc_rpc"})
    _audit("bsc_payment_verified", "order", order_id, "system", {"amount_usd": amount})
    return {"status": "PAID_VERIFIED", "order_number": order["order_number"], "amount_usd": amount}


@router.post("/api/public/orders/verify-bsc-tx")
def verify_public_bsc_payment(payload: Dict[str, Any] = Body(...)):
    slug = str(payload.get("item_slug", payload.get("product_slug", "")))
    product = _find_product(slug)
    if not product:
        raise HTTPException(status_code=404, detail="Sản phẩm không tồn tại.")
    email = str(payload.get("buyer_email", "")).strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(status_code=422, detail="Cần email hợp lệ để lưu đơn hàng.")
    tx_hash = str(payload.get("tx_hash", "")).lower()
    amount = _verify_bsc_receipt(tx_hash, float(product["price_usd"]))
    order = _record("order", {"order_number": "WEB-" + tx_hash[2:10].upper(), "customer_id": email,
        "customer_email": email, "product_id": product["id"], "product_name": product["name"],
        "payment_provider": "BSC_USDT_BEP20", "tx_hash": tx_hash, "net_amount_usd": amount,
        "net_amount_vnd": round(amount * 25500), "verified_by": "bsc_rpc"}, "PAID_VERIFIED")
    _insert_transaction("order:" + order["id"], amount, "BSC_USDT_BEP20", tx_hash)
    _audit("public_bsc_payment_verified", "order", order["id"], "system", {"product_id": product["id"]})
    return {"accepted": True, "order_id": order["id"], "status": "PAID_VERIFIED", "amount_usd": amount,
            "product_slug": product["id"], "download_url": product["download_url"]}


@router.get("/api/orders/{order_id}/deliver")
def deliver_order(order_id: str, request: Request):
    _require_admin(request)
    order = _get_record("order", order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng.")
    if order["status"] not in {"PAID_VERIFIED", "FULFILLED"}:
        raise HTTPException(status_code=402, detail="Đơn hàng chưa được xác minh thanh toán.")
    product = _find_product(order["product_id"])
    if not product:
        raise HTTPException(status_code=404, detail="Tệp bàn giao không còn trong catalog.")
    if order["status"] != "FULFILLED":
        _update_record("order", order_id, "FULFILLED", {"delivered_at": _now()})
        _audit("order_delivery_unlocked", "order", order_id, "owner")
    return {"order_number": order["order_number"], "status": "FULFILLED",
            "product": {"name": product["name"], "download_url": product["download_url"], "executable_python_code": None},
            "support_and_refund_policy": "Tải tệp HTML của sản phẩm sau khi thanh toán đã được xác minh.",
            "download_url": product["download_url"]}


@router.post("/api/tasks/{task_id}/approve")
def approve_task(task_id: str, request: Request):
    _require_admin(request)
    try:
        task_number = int(task_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Mã task không hợp lệ.")
    from dashboard_data import CORE_DB_PATH
    conn = sqlite3.connect(str(CORE_DB_PATH))
    try:
        row = conn.execute("SELECT id, status FROM tasks WHERE id=?", (task_number,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Task không tồn tại.")
        if row[1] not in {"WAITING_OWNER", "PENDING", "WAITING_APPROVAL"}:
            raise HTTPException(status_code=409, detail="Task không còn chờ duyệt.")
        conn.execute("UPDATE tasks SET status='APPROVED', updated_at=? WHERE id=?", (_now(), task_number))
        conn.commit()
    finally:
        conn.close()
    _audit("task_approved", "task", str(task_number), "owner", {"execution_started": False})
    return {"status": "APPROVED", "execution_started": False, "message": "Đã duyệt task; worker thực thi chưa được kết nối."}


def _set_system_status(status: str, reason: Optional[str] = None) -> Dict[str, Any]:
    state = _setting("system", {"system_status": "RUNNING", "operating_mode": "GUARDED_AUTONOMY"}) or {}
    state["system_status"] = status
    state["emergency_reason"] = reason
    state["updated_at"] = _now()
    _set_setting("system", state)
    return state


@router.post("/api/system/pause")
def pause_system(request: Request):
    _require_admin(request)
    state = _set_system_status("PAUSED")
    _audit("system_paused", "system", None, "owner")
    return state


@router.post("/api/system/resume")
def resume_system(request: Request):
    _require_admin(request)
    state = _set_system_status("RUNNING")
    _audit("system_resumed", "system", None, "owner")
    return state


@router.post("/api/system/emergency-stop")
def emergency_stop(request: Request, payload: Dict[str, Any] = Body(...)):
    _require_admin(request)
    reason = str(payload.get("reason", "Owner requested emergency stop"))[:300]
    state = _set_system_status("EMERGENCY_STOP", reason)
    _audit("emergency_stop_requested", "system", None, "owner", {"reason": reason, "worker_interrupted": False})
    return {**state, "worker_interrupted": False, "message": "Dừng khẩn cấp đã được ghi nhận; tác vụ đang chạy không bị ngắt vì chưa có worker điều khiển."}


@router.post("/api/agents/run-cycle")
def run_agent_cycle(request: Request):
    _require_admin(request)
    state = _setting("system", {"system_status": "RUNNING"}) or {}
    if state.get("system_status") in {"PAUSED", "EMERGENCY_STOP"}:
        raise HTTPException(status_code=409, detail=f"Hệ thống đang ở trạng thái {state['system_status']}.")
    _audit("agent_cycle_requested", "system", None, "owner", {"status": "not_connected"})
    return {"status": "not_connected", "reason": "Bộ thực thi chu kỳ AI chưa được kết nối; chưa có task nào được khởi chạy.",
            "tasks_started": 0, "honest_status_summary": "Worker thực thi chưa được cấu hình."}


@router.post("/api/github-web-factory/auto-harvest")
def auto_harvest(payload: Dict[str, Any] = Body(...), request: Request = None):
    _require_admin(request)
    topic = str(payload.get("query_topic", "")).strip()[:80]
    if not topic:
        raise HTTPException(status_code=422, detail="Nhập chủ đề cần tìm.")
    return {"status": "discovery_not_connected", "query_topic": topic, "items": [], "newly_built": [],
            "total_webapps": len(TOOL_DEFINITIONS),
            "message": "Chưa có quy trình xác minh giấy phép và đóng gói repository bên ngoài; chưa tạo ứng dụng mới."}
