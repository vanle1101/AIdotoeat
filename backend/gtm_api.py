"""Compliant GTM preview, consent-aware inbound CRM and first-party metrics."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from difflib import SequenceMatcher
import re
import sqlite3
import uuid
import zipfile
from pathlib import Path
from typing import Any, Mapping

from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from database import get_connection
from modules.gtm_studio import (
    CAMPAIGN_ID, COMMUNITY_POLICIES, CONSENT_VERSION, EXPERIMENT,
    STAGING_PACKAGE, STAGING_DIR, can_approve_community_draft, parse_utm,
)

router = APIRouter()
BOT_USER_AGENT = re.compile(r"(?:bot\b|crawler|spider|headlesschrome|playwright|selenium|webdriver|uptime|monitoring)", re.I)
CONTACT_RATE_LIMIT = (3, 3600)
EVENT_RATE_LIMIT = (30, 60)


class ContactPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=254)
    company: str = Field(default="", max_length=160)
    need: str = Field(min_length=5, max_length=1200)
    website: str = Field(default="", max_length=300)
    contact_consent: bool
    analytics_consent: bool = False
    campaign_id: str = Field(max_length=100)
    page_path: str = Field(default="/offers/website-snapshot-audit/", max_length=200)
    session_id: str | None = Field(default=None, max_length=36)
    utm: dict[str, Any] = Field(default_factory=dict)


class OptOutPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    email: str = Field(min_length=3, max_length=254)


class EventPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    event_name: str
    event_id: str = Field(min_length=8, max_length=64)
    campaign_id: str = Field(max_length=100)
    page_path: str = Field(min_length=1, max_length=200)
    session_id: str = Field(min_length=36, max_length=36)
    analytics_consent: bool
    utm: dict[str, Any] = Field(default_factory=dict)
    internal_test: bool = False


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _require_admin(request: Request) -> None:
    from workflow_api import _require_admin as require
    require(request)


def _ensure_id(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return str(uuid.UUID(value))
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(status_code=422, detail="Session identifier is invalid.")


def _clean_text(value: str, limit: int) -> str:
    text = " ".join(value.replace("\x00", " ").split()).strip()
    if len(text) > limit or re.search(r"<\s*/?\s*[a-z!][^>]*>", text, re.I):
        raise HTTPException(status_code=422, detail="Text is too long or contains markup.")
    return text


def _bot_or_internal(request: Request, payload_internal: bool = False) -> bool:
    host = request.client.host.lower() if request.client else ""
    return bool(
        payload_internal or host in {"testclient", "localhost", "127.0.0.1", "::1"}
        or request.headers.get("x-internal-test", "").lower() == "true"
        or BOT_USER_AGENT.search(request.headers.get("user-agent", ""))
    )


def _insert_event(conn: sqlite3.Connection, *, event_name: str, page_path: str,
                  source: str, occurred_at: str, lead_id: int | None = None,
                  transaction_id: int | None = None, session_id: str | None = None,
                  utm: Mapping[str, str] | None = None, internal_test: bool = False,
                  dedupe_key: str | None = None, event_id: str | None = None) -> bool:
    if internal_test:
        return False
    normalized = parse_utm(utm or {})
    cursor = conn.execute(
        """INSERT OR IGNORE INTO gtm_analytics_events
           (event_id,event_name,campaign_id,session_id,page_path,utm_source,utm_medium,utm_campaign,
            utm_content,lead_id,transaction_id,source,occurred_at,internal_test,dedupe_key)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (event_id or str(uuid.uuid4()), event_name, CAMPAIGN_ID, session_id, page_path,
         normalized.get("utm_source"), normalized.get("utm_medium"), normalized.get("utm_campaign"),
         normalized.get("utm_content"), lead_id, transaction_id, source, occurred_at, 0, dedupe_key),
    )
    return cursor.rowcount == 1


def _staged_drafts() -> tuple[dict[str, Any], dict[str, Any]]:
    path = STAGING_DIR / STAGING_PACKAGE
    if not path.is_file():
        raise HTTPException(status_code=503, detail="GTM preview package is not staged yet.")
    sidecar = path.with_suffix(path.suffix + ".sha256")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if not sidecar.is_file() or digest not in sidecar.read_text(encoding="ascii", errors="ignore"):
        raise HTTPException(status_code=409, detail="GTM preview package integrity check failed.")
    try:
        with zipfile.ZipFile(path) as archive:
            drafts = json.loads(archive.read("drafts/community-drafts.json"))
            manifest = json.loads(archive.read("BUILD_MANIFEST.json"))
    except (OSError, ValueError, KeyError, zipfile.BadZipFile):
        raise HTTPException(status_code=409, detail="GTM preview package is malformed.")
    return drafts, manifest


@router.get("/api/gtm/experiment")
def gtm_experiment():
    return {"campaign": EXPERIMENT, "status": "staging_only", "publication_performed": False}


@router.get("/api/gtm/policies")
def gtm_channel_policies():
    return {"items": COMMUNITY_POLICIES, "status": "policy_reviewed_recheck_before_posting"}


@router.get("/api/gtm/artifact")
def download_gtm_artifact(request: Request):
    _require_admin(request)
    path = STAGING_DIR / STAGING_PACKAGE
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if not path.is_file() or not sidecar.is_file():
        raise HTTPException(status_code=404, detail="Staging artifact not found.")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest not in sidecar.read_text(encoding="ascii", errors="ignore"):
        raise HTTPException(status_code=409, detail="Staging artifact integrity check failed.")
    return FileResponse(path, media_type="application/zip", filename=path.name,
                        headers={"X-Artifact-SHA256": digest})


@router.get("/api/gtm/admin/drafts")
def list_gtm_drafts(request: Request):
    _require_admin(request)
    drafts, manifest = _staged_drafts()
    return {"campaign_id": CAMPAIGN_ID, "drafts": drafts, "policies": manifest.get("community_policies", {}),
            "publication_gate": manifest.get("publication_gate"), "status": "draft_preview_only"}


@router.post("/api/gtm/admin/publication-queue")
def enqueue_publication_draft(request: Request, payload: dict[str, Any] = Body(...)):
    _require_admin(request)
    channel = str(payload.get("channel") or "")
    drafts, _ = _staged_drafts()
    draft = drafts.get(channel)
    if not draft:
        raise HTTPException(status_code=422, detail="Unknown community draft channel.")
    policy = COMMUNITY_POLICIES[channel]
    draft_hash = hashlib.sha256((draft["title"] + "\n" + draft["body"]).encode()).hexdigest()
    queue_id = "pub_" + hashlib.sha256(f"{CAMPAIGN_ID}:{channel}:{draft_hash}".encode()).hexdigest()[:20]
    now = _now()
    conn = get_connection()
    try:
        conn.execute(
            """INSERT OR IGNORE INTO gtm_publication_queue
               (id,campaign_id,channel,draft_key,title,body,draft_hash,status,policy_url,
                policy_checked_date,human_rewritten,community_rules_rechecked,owner_requested_at,created_at,updated_at)
               VALUES(?,?,?,?,?,? ,?,'PENDING_REVIEW',?,?,0,0,?,?,?)""",
            (queue_id, CAMPAIGN_ID, channel, channel, draft["title"], draft["body"], draft_hash,
             policy["source_url"], policy["checked_date"], now, now, now),
        )
        conn.commit()
        row = conn.execute("SELECT id,status,channel,policy_url,policy_checked_date,created_at FROM gtm_publication_queue WHERE id=?", (queue_id,)).fetchone()
        return {"item": dict(row), "public_post_created": False}
    finally:
        conn.close()


@router.get("/api/gtm/admin/publication-queue")
def get_publication_queue(request: Request):
    _require_admin(request)
    conn = get_connection()
    try:
        rows = conn.execute("SELECT id,campaign_id,channel,title,body,status,policy_url,policy_checked_date,human_rewritten,community_rules_rechecked,owner_requested_at,owner_decided_at,owner_decision_reason FROM gtm_publication_queue ORDER BY created_at DESC").fetchall()
        return {"items": [dict(row) for row in rows], "total": len(rows), "public_post_created": False}
    finally:
        conn.close()


@router.post("/api/gtm/admin/publication-queue/{queue_id}/review")
def review_publication_draft(queue_id: str, request: Request, payload: dict[str, Any] = Body(...)):
    _require_admin(request)
    title = _clean_text(str(payload.get("title") or ""), 240)
    body = _clean_text(str(payload.get("body") or ""), 6000)
    if not title or not body:
        raise HTTPException(status_code=422, detail="A human-reviewed title and body are required.")
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM gtm_publication_queue WHERE id=?", (queue_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Draft is not in the approval queue.")
        if row["status"] not in {"PENDING_REVIEW", "BLOCKED", "APPROVED_FOR_MANUAL_POST"}:
            raise HTTPException(status_code=409, detail="This draft is not reviewable.")
        new_hash = hashlib.sha256((title + "\n" + body).encode()).hexdigest()
        original_text = f"{row['title']}\n{row['body']}".casefold()
        rewritten_text = f"{title}\n{body}".casefold()
        rewritten = bool(
            payload.get("human_rewrite_attested") is True
            and new_hash != row["draft_hash"]
            and SequenceMatcher(None, original_text, rewritten_text).ratio() <= .70
        )
        review = {"channel": row["channel"], "human_rewritten": rewritten,
                  "human_rewrite_required": True,
                  "community_rules_rechecked": payload.get("community_rules_rechecked") is True}
        eligible, reason = can_approve_community_draft(review)
        approved = bool(eligible and payload.get("owner_approved") is True)
        status = "APPROVED_FOR_MANUAL_POST" if approved else "BLOCKED" if not eligible else "REJECTED"
        reason = "owner approved for manual posting only; no posting integration exists" if approved else reason if not eligible else str(payload.get("reason") or "owner_rejected")[:240]
        now = _now()
        conn.execute(
            """UPDATE gtm_publication_queue SET title=?,body=?,draft_hash=?,status=?,human_rewritten=?,
               community_rules_rechecked=?,owner_decided_at=?,owner_decision_reason=?,updated_at=? WHERE id=?""",
            (title, body, new_hash, status, int(rewritten), int(review["community_rules_rechecked"]), now, reason, now, queue_id),
        )
        conn.commit()
        return {"id": queue_id, "status": status, "reason": reason, "published": False}
    finally:
        conn.close()


@router.post("/api/gtm/admin/publication-queue/{queue_id}/publish")
def publish_draft(queue_id: str, request: Request):
    _require_admin(request)
    return JSONResponse(status_code=409, content={
        "detail": "No publication credentials or posting adapter are configured; copy an approved manual draft only after checking current community rules.",
        "published": False,
    })


@router.post("/api/gtm/leads", status_code=202)
def create_inbound_lead(payload: ContactPayload, request: Request):
    if _bot_or_internal(request):
        return {"accepted": False, "status": "internal_or_automated_traffic_ignored"}
    if payload.website.strip():
        return {"accepted": False, "status": "request_ignored"}
    allowed_paths = {"/offers/website-snapshot-audit/", "/landing.html"}
    if payload.campaign_id != CAMPAIGN_ID or payload.contact_consent is not True:
        raise HTTPException(status_code=422, detail="Explicit contact permission for this campaign is required.")
    if payload.page_path not in allowed_paths:
        raise HTTPException(status_code=422, detail="Page path is not allowlisted.")
    name = _clean_text(payload.name, 100)
    company = _clean_text(payload.company, 160) if payload.company else ""
    need = _clean_text(payload.need, 1200)
    email = payload.email.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email) or re.search(r"\s", email):
        raise HTTPException(status_code=422, detail="Provide a valid reply email.")
    session = _ensure_id(payload.session_id) if payload.analytics_consent else None
    now = _now()
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            """INSERT INTO leads(name,email,company,source,need,stage,fit_score,proposal_text,country,created_at,
               gtm_consent_status,gtm_consent_at,gtm_consent_version,gtm_contact_provenance,
               gtm_permission_evidence,gtm_campaign_id,gtm_suppressed)
               VALUES(?,?,?,'inbound_gtm_contact_form',?,'NEW',NULL,NULL,NULL,?,'OPTED_IN',?,?,'self_submitted_inbound',?, ?,0)""",
            (name, email, company or None, need, now, now, CONSENT_VERSION,
             "Explicit checkbox: reply only to the submitted snapshot-audit inquiry.", CAMPAIGN_ID),
        )
        lead_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        _insert_event(conn, event_name="contact_submit", page_path=payload.page_path,
                      source="inbound_contact_form", occurred_at=now, lead_id=lead_id,
                      session_id=session if payload.analytics_consent else None,
                      utm=payload.utm if payload.analytics_consent else {},
                      dedupe_key=f"lead:{lead_id}:contact_submit")
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        raise HTTPException(status_code=503, detail="Could not store the inquiry safely.")
    finally:
        conn.close()
    return {"accepted": True, "status": "OWNER_REVIEW_PENDING", "email_sent": False}


@router.post("/api/gtm/opt-out", status_code=202)
def opt_out_contact(payload: OptOutPayload, request: Request):
    if _bot_or_internal(request):
        return {"accepted": True, "status": "if_present_contact_is_suppressed"}
    email = payload.email.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(status_code=422, detail="Provide a valid email address.")
    now = _now()
    conn = get_connection()
    try:
        conn.execute(
            """UPDATE leads SET gtm_suppressed=1,gtm_suppressed_at=?,gtm_consent_status='REVOKED',
               gtm_owner_approved_at=NULL,gtm_approved_proposal_hash=NULL
               WHERE lower(email)=?""", (now, email),
        )
        conn.commit()
    finally:
        conn.close()
    return {"accepted": True, "status": "if_present_contact_is_suppressed"}


@router.post("/api/gtm/events", status_code=202)
def record_gtm_event(payload: EventPayload, request: Request):
    if payload.internal_test or _bot_or_internal(request, payload.internal_test):
        return {"accepted": False, "status": "internal_or_automated_traffic_ignored"}
    if payload.event_name not in {"landing_view", "demo_start"}:
        raise HTTPException(status_code=422, detail="This event must be generated by a validated CRM or owner action.")
    if payload.campaign_id != CAMPAIGN_ID or not payload.analytics_consent:
        raise HTTPException(status_code=422, detail="A valid campaign and analytics opt-in are required.")
    session = _ensure_id(payload.session_id)
    allowed_paths = {"/offers/website-snapshot-audit/", "/landing.html", "/demo/seo-opengraph-meta-generator.html"}
    if payload.page_path not in allowed_paths or "?" in payload.page_path or "#" in payload.page_path:
        raise HTTPException(status_code=422, detail="Page path is not allowlisted.")
    now = _now()
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        inserted = _insert_event(conn, event_name=payload.event_name, page_path=payload.page_path,
                                 source="consented_first_party_browser", occurred_at=now,
                                 session_id=session, utm=payload.utm,
                                 dedupe_key=f"browser:{payload.event_id}", event_id=payload.event_id)
        conn.commit()
        return {"accepted": inserted, "status": "recorded" if inserted else "duplicate_ignored"}
    finally:
        conn.close()


@router.get("/api/gtm/admin/leads")
def list_gtm_leads(request: Request):
    _require_admin(request)
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT id,name,email,company,source,need,stage,created_at,gtm_consent_status,
               gtm_consent_at,gtm_contact_provenance,gtm_campaign_id,gtm_suppressed,
               gtm_owner_approved_at,gtm_last_outreach_at,gtm_outreach_count
               FROM leads WHERE gtm_campaign_id=? ORDER BY id DESC LIMIT 200""", (CAMPAIGN_ID,)
        ).fetchall()
        return {"items": [dict(row) for row in rows], "total": len(rows)}
    finally:
        conn.close()


@router.post("/api/gtm/admin/leads/{lead_id}/qualify")
def qualify_lead(lead_id: int, request: Request, payload: dict[str, Any] = Body(...)):
    _require_admin(request)
    if payload.get("owner_confirmed_problem") is not True:
        raise HTTPException(status_code=422, detail="Owner confirmation that the stated problem is qualified is required.")
    now = _now()
    conn = get_connection()
    try:
        row = conn.execute("SELECT id,gtm_consent_status,gtm_suppressed FROM leads WHERE id=? AND gtm_campaign_id=?", (lead_id, CAMPAIGN_ID)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Campaign inquiry not found.")
        if row["gtm_consent_status"] != "OPTED_IN" or row["gtm_suppressed"]:
            raise HTTPException(status_code=409, detail="Contact permission is absent or revoked.")
        conn.execute("UPDATE leads SET stage='QUALIFIED_INQUIRY' WHERE id=?", (lead_id,))
        _insert_event(conn, event_name="qualified_inquiry", page_path="/offers/website-snapshot-audit/",
                      source="owner_reviewed_inbound", occurred_at=now, lead_id=lead_id,
                      dedupe_key=f"lead:{lead_id}:qualified")
        conn.commit()
        return {"lead_id": lead_id, "status": "QUALIFIED_INQUIRY"}
    finally:
        conn.close()


@router.put("/api/gtm/admin/leads/{lead_id}/proposal")
def save_personalized_proposal(lead_id: int, request: Request, payload: dict[str, Any] = Body(...)):
    _require_admin(request)
    proposal = _clean_text(str(payload.get("proposal") or ""), 6000)
    if len(proposal) < 80:
        raise HTTPException(status_code=422, detail="A personalized proposal draft needs at least 80 characters.")
    now = _now()
    conn = get_connection()
    try:
        row = conn.execute("SELECT id,gtm_consent_status,gtm_suppressed FROM leads WHERE id=? AND gtm_campaign_id=?", (lead_id, CAMPAIGN_ID)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Campaign inquiry not found.")
        if row["gtm_consent_status"] != "OPTED_IN" or row["gtm_suppressed"]:
            raise HTTPException(status_code=409, detail="Contact permission is absent or revoked.")
        conn.execute("UPDATE leads SET proposal_text=?,stage='PROPOSAL_DRAFT',gtm_owner_approved_at=NULL,gtm_approved_proposal_hash=NULL WHERE id=?",
                     (proposal, lead_id))
        conn.commit()
        return {"lead_id": lead_id, "status": "PROPOSAL_DRAFT", "proposal_sha256": hashlib.sha256(proposal.encode()).hexdigest(), "sent": False}
    finally:
        conn.close()


@router.post("/api/gtm/admin/leads/{lead_id}/approve-proposal")
def approve_proposal(lead_id: int, request: Request, payload: dict[str, Any] = Body(default={})):
    _require_admin(request)
    now = datetime.now(timezone.utc)
    conn = get_connection()
    try:
        row = conn.execute("SELECT proposal_text,gtm_consent_status,gtm_suppressed,gtm_last_outreach_at,gtm_outreach_count FROM leads WHERE id=? AND gtm_campaign_id=?", (lead_id, CAMPAIGN_ID)).fetchone()
        if not row or not row["proposal_text"]:
            raise HTTPException(status_code=404, detail="Campaign proposal draft not found.")
        if row["gtm_consent_status"] != "OPTED_IN" or row["gtm_suppressed"]:
            raise HTTPException(status_code=409, detail="Contact permission is absent or revoked.")
        if int(row["gtm_outreach_count"] or 0) >= 2:
            raise HTTPException(status_code=429, detail="The two-contact cadence cap has been reached.")
        if row["gtm_last_outreach_at"]:
            previous = datetime.fromisoformat(row["gtm_last_outreach_at"].replace("Z", "+00:00"))
            if now - previous < timedelta(days=14):
                raise HTTPException(status_code=429, detail="Wait at least 14 days before another contact.")
        proposal_hash = hashlib.sha256(row["proposal_text"].encode()).hexdigest()
        conn.execute("UPDATE leads SET gtm_owner_approved_at=?,gtm_approved_proposal_hash=? WHERE id=?",
                     (_now(), proposal_hash, lead_id))
        conn.commit()
        return {"lead_id": lead_id, "status": "APPROVED_FOR_MANUAL_1_TO_1_REVIEW", "proposal_sha256": proposal_hash, "email_sent": False}
    finally:
        conn.close()


@router.post("/api/gtm/admin/leads/{lead_id}/record-proposal-sent")
def record_proposal_sent(lead_id: int, request: Request, payload: dict[str, Any] = Body(...)):
    _require_admin(request)
    if payload.get("owner_attests_manually_sent") is not True:
        raise HTTPException(status_code=422, detail="Record only after the owner manually sent this one-to-one proposal.")
    channel = str(payload.get("channel") or "owner_manually_sent")[:60]
    if channel != "owner_manually_sent":
        raise HTTPException(status_code=422, detail="Unsupported one-to-one contact channel.")
    now = datetime.now(timezone.utc)
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT proposal_text,gtm_consent_status,gtm_suppressed,gtm_owner_approved_at,gtm_approved_proposal_hash,gtm_outreach_count,gtm_last_outreach_at FROM leads WHERE id=? AND gtm_campaign_id=?", (lead_id, CAMPAIGN_ID)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Campaign inquiry not found.")
        if row["gtm_consent_status"] != "OPTED_IN" or row["gtm_suppressed"]:
            raise HTTPException(status_code=409, detail="Contact permission is absent or revoked.")
        if not row["proposal_text"] or not row["gtm_owner_approved_at"]:
            raise HTTPException(status_code=409, detail="The current proposal has not been approved by the owner.")
        proposal_hash = hashlib.sha256(row["proposal_text"].encode()).hexdigest()
        if proposal_hash != row["gtm_approved_proposal_hash"]:
            raise HTTPException(status_code=409, detail="Approved proposal changed; review it again.")
        if int(row["gtm_outreach_count"] or 0) >= 2:
            raise HTTPException(status_code=429, detail="The two-contact cadence cap has been reached.")
        if row["gtm_last_outreach_at"]:
            last = datetime.fromisoformat(row["gtm_last_outreach_at"].replace("Z", "+00:00"))
            if now - last < timedelta(days=14):
                raise HTTPException(status_code=429, detail="Wait at least 14 days before another contact.")
        sent_at = _now()
        conn.execute("UPDATE leads SET gtm_last_outreach_at=?,gtm_outreach_count=gtm_outreach_count+1,stage='CONTACTED',gtm_owner_approved_at=NULL,gtm_approved_proposal_hash=NULL WHERE id=?",
                     (sent_at, lead_id))
        _insert_event(conn, event_name="proposal_sent", page_path="/offers/website-snapshot-audit/",
                      source=channel, occurred_at=sent_at, lead_id=lead_id,
                      dedupe_key=f"lead:{lead_id}:proposal:{int(row['gtm_outreach_count'] or 0)+1}")
        conn.commit()
        return {"lead_id": lead_id, "status": "MANUALLY_SENT_ATTESTED", "email_sent_by_system": False}
    finally:
        conn.close()


@router.post("/api/gtm/admin/leads/{lead_id}/customer-reply")
def record_customer_reply(lead_id: int, request: Request):
    _require_admin(request)
    now = _now()
    conn = get_connection()
    try:
        row = conn.execute("SELECT id FROM leads WHERE id=? AND gtm_campaign_id=?", (lead_id, CAMPAIGN_ID)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Campaign inquiry not found.")
        _insert_event(conn, event_name="customer_reply", page_path="/offers/website-snapshot-audit/",
                      source="owner_attested_customer_reply", occurred_at=now, lead_id=lead_id,
                      dedupe_key=f"lead:{lead_id}:reply:{now[:10]}")
        conn.commit()
        return {"lead_id": lead_id, "status": "reply_recorded_without_message_content"}
    finally:
        conn.close()


@router.post("/api/gtm/admin/leads/{lead_id}/accepted-quote")
def record_accepted_quote(lead_id: int, request: Request, payload: dict[str, Any] = Body(...)):
    _require_admin(request)
    if payload.get("owner_confirms_customer_acceptance") is not True:
        raise HTTPException(status_code=422, detail="Customer acceptance must be confirmed by the owner.")
    now = _now()
    conn = get_connection()
    try:
        row = conn.execute("SELECT id,gtm_consent_status,gtm_suppressed FROM leads WHERE id=? AND gtm_campaign_id=?", (lead_id, CAMPAIGN_ID)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Campaign inquiry not found.")
        if row["gtm_consent_status"] != "OPTED_IN" or row["gtm_suppressed"]:
            raise HTTPException(status_code=409, detail="Contact permission is absent or revoked.")
        _insert_event(conn, event_name="accepted_quote", page_path="/offers/website-snapshot-audit/",
                      source="owner_attested_customer_acceptance", occurred_at=now, lead_id=lead_id,
                      dedupe_key=f"lead:{lead_id}:accepted_quote")
        conn.execute("UPDATE leads SET stage='QUOTE_ACCEPTED' WHERE id=?", (lead_id,))
        conn.commit()
        return {"lead_id": lead_id, "status": "accepted_quote_recorded"}
    finally:
        conn.close()


@router.post("/api/gtm/admin/leads/{lead_id}/verified-payment")
def record_verified_payment(lead_id: int, request: Request, payload: dict[str, Any] = Body(...)):
    _require_admin(request)
    try:
        transaction_id = int(payload.get("transaction_id"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="Select a verified transaction ledger id.")
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        lead = conn.execute("SELECT id,stage FROM leads WHERE id=? AND gtm_campaign_id=?", (lead_id, CAMPAIGN_ID)).fetchone()
        tx = conn.execute("SELECT id,status FROM transactions WHERE id=?", (transaction_id,)).fetchone()
        if not lead or not tx:
            raise HTTPException(status_code=404, detail="Inquiry or transaction ledger entry not found.")
        if tx["status"] != "PAID_VERIFIED":
            raise HTTPException(status_code=409, detail="Only an already verified payment can be linked.")
        if lead["stage"] != "QUOTE_ACCEPTED":
            raise HTTPException(status_code=409, detail="Record customer quote acceptance before linking payment.")
        inserted = _insert_event(conn, event_name="verified_payment", page_path="/offers/website-snapshot-audit/",
                                 source="owner_linked_verified_transaction_ledger", occurred_at=_now(), lead_id=lead_id,
                                 transaction_id=transaction_id, dedupe_key=f"lead:{lead_id}:verified-payment:{transaction_id}")
        conn.commit()
        return {"lead_id": lead_id, "transaction_id": transaction_id,
                "status": "verified_payment_linked" if inserted else "already_linked",
                "channel_roi": None, "roi_status": "not_claimed_unverified_channel_attribution"}
    finally:
        conn.close()


@router.get("/api/gtm/admin/kpis")
def gtm_kpis(request: Request):
    _require_admin(request)
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT event_name,COUNT(*) AS event_count,COUNT(DISTINCT session_id) AS sessions
               FROM gtm_analytics_events WHERE campaign_id=? AND internal_test=0 GROUP BY event_name""", (CAMPAIGN_ID,)
        ).fetchall()
        values = {row["event_name"]: {"events": int(row["event_count"]), "consented_sessions": int(row["sessions"])} for row in rows}
        landing = values.get("landing_view", {}).get("consented_sessions", 0)
        demo = values.get("demo_start", {}).get("consented_sessions", 0)
        inquiries = values.get("contact_submit", {}).get("events", 0)
        def pct(n: int, d: int) -> float | None:
            return round(100 * n / d, 1) if d else None
        return {
            "campaign_id": CAMPAIGN_ID, "status": "observed" if values else "no_data",
            "counts": values, "rates": {
                "demo_start_per_consented_landing_session_pct": {"value": pct(demo, landing), "label": "estimate_from_consented_sessions"},
                "contact_inquiry_per_consented_landing_session_pct": {"value": pct(inquiries, landing), "label": "estimate_from_consent_limited_sessions"},
            },
            "utm_attribution": "visitor_supplied_unverified; counts are not channel proof",
            "verified_revenue_usd": None,
            "channel_roi": None,
            "roi_status": "not_claimed_until_verified_transaction_and_channel_attribution_are_both_supported",
            "cash_budget_usd": 0,
            "cash_spend_usd": 0,
            "events_are_unique_people": False,
        }
    finally:
        conn.close()
