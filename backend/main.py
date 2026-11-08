"""
AUTOProfit AI Enterprise - Full-Stack FastAPI Backend
High-Performance, Zero-Downtime, SQLite WAL Powered Live Backend.
"""
import sys
import os
import asyncio
import copy
import hmac
import ipaddress
import json
import re
import sqlite3
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fastapi import Body, FastAPI, HTTPException, Query, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from config import CONFIG, APPS_DIR
from database import consume_rate_limit, get_connection, init_db
from apps_library import TOOL_DEFINITIONS, requires_owner_quote
from dashboard_data import (
    CORE_DB_PATH,
    active_agent_ids,
    current_max_event_id,
    dashboard_summary,
    dashboard_operations_summary,
    events_after,
    list_core_tasks,
    list_activity,
    task_event_by_id,
)
from business_engine import EngineRuntime, ensure_schema, runtime_enabled

_engine_runtime: Optional[EngineRuntime] = None


@asynccontextmanager
async def app_lifespan(_app: FastAPI):
    global _engine_runtime
    if runtime_enabled():
        _engine_runtime = EngineRuntime()
        _engine_runtime.start()
    try:
        yield
    finally:
        if _engine_runtime:
            _engine_runtime.stop()
            _engine_runtime = None

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
try:
    from core.roles import list_all_roles
except Exception:
    list_all_roles = None

init_db()
ensure_schema()

app = FastAPI(
    title="AUTOProfit AI Enterprise Engine",
    version="4.5.0",
    description="Local-first durable business engine with owner-controlled approvals",
    lifespan=app_lifespan,
)

# Register the complete dashboard workflows before the static frontend mount.
# This router supplies persistence and validation for the controls in the UI.
from workflow_api import router as workflow_router, _audit as audit_workflow_event, _verify_bsc_receipt
app.include_router(workflow_router)
from business_api import router as business_engine_router
app.include_router(business_engine_router)
from product_studio_api import router as product_studio_router
app.include_router(product_studio_router)
from gtm_api import router as gtm_router
app.include_router(gtm_router)
from order_cash import router as order_cash_router
app.include_router(order_cash_router)
from optimization_api import router as optimization_router
app.include_router(optimization_router)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

# System capabilities and runtime mode. Business values are read from data stores.
SYSTEM_STATE = {
    "operating_mode": "GUARDED_AUTONOMY",
    "system_status": "IDLE",
    "emergency_reason": None,
    "payment_mode": "not_configured",
    "ai_provider": "NOT_CONNECTED",
    "ai_provider_mode": "NO_VERIFIED_PROVIDER_SESSION",
    "backend_health": "ONLINE",
    "deployment_architecture": "FastAPI + SQLite"
}


class TelemetryPayload(BaseModel):
    session_id: str = Field(min_length=16, max_length=80)
    path: Optional[str] = Field(default=None, max_length=300)
    internal_test: bool = False


class PaymentReportPayload(BaseModel):
    product_slug: str = Field(min_length=3, max_length=80, pattern=r"^[a-z0-9-]+$")
    payment_method: str = Field(pattern=r"^(BANK_TRANSFER|BINANCE_PAY)$")
    customer_email: Optional[str] = Field(default=None, max_length=254)
    reference: Optional[str] = Field(default=None, max_length=120)


def _validate_telemetry_request(request: Request, session_id: str) -> str:
    try:
        uuid.UUID(session_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=422, detail="Invalid browser session identifier")
    origin = request.headers.get("origin")
    if origin:
        origin_parts = urlparse(origin)
        origin_host = origin_parts.netloc.lower()
        request_host = request.headers.get("host", "").lower()
        if origin_parts.scheme not in {"http", "https"} or not origin_host or origin_host != request_host:
            raise HTTPException(status_code=403, detail="Cross-origin telemetry is not accepted")
    return session_id


def _is_admin(request: Request) -> bool:
    expected = os.getenv("AUTOPROFIT_ADMIN_API_KEY", "")
    provided = request.headers.get("X-Admin-Key", "")
    return bool(
        request.url.scheme == "https"
        and len(expected) >= 32
        and provided
        and hmac.compare_digest(expected, provided)
    )


_PUBLIC_RATE_LIMITS = {
    "/api/telemetry/pageview": (30, 60),
    "/api/telemetry/heartbeat": (60, 60),
    "/api/public/payment-reports": (5, 3600),
    "/api/public/payment-reports/status": (10, 300),
    "/api/payments/submit-mbbank-proof": (5, 3600),
    "/api/public/orders/verify-bsc-tx": (5, 3600),
    "/api/public/advertising-inquiries": (3, 3600),
    "/api/public/donations": (3, 3600),
    "/api/employees/propose": (10, 60),
    "/api/public/notebook/interact": (30, 60),
    "/api/opportunities/analyze-freelance-job": (10, 60),
    "/api/internet/live-scan": (3, 60),
    "/api/products/live-audit-demo": (10, 60),
    "/api/gtm/events": (30, 60),
    "/api/gtm/leads": (3, 3600),
    "/api/gtm/opt-out": (10, 3600),
    "/api/cash/leads": (5, 3600),
    "/api/cash/orders": (30, 60),
    "/api/admin/auth/verify": (10, 300),
}


@app.middleware("http")
async def enforce_same_origin_and_rate_limits(request: Request, call_next):
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        origin = request.headers.get("origin")
        if origin:
            parts = urlparse(origin)
            request_host = request.headers.get("host", "").lower()
            if (parts.scheme != request.url.scheme or not parts.netloc
                    or parts.netloc.lower() != request_host):
                return JSONResponse(status_code=403, content={"detail": "Cross-origin mutations are not accepted"})

    policy = _PUBLIC_RATE_LIMITS.get(request.url.path)
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and policy is None and request.url.path.startswith("/api/"):
        # Cover mutating routes outside the public-form list and /api/admin
        # namespace too (for example /api/system and /api/orders).
        policy = (120, 60)
    if request.url.path.startswith("/api/admin/") and request.url.path != "/api/admin/auth/verify":
        policy = (30, 60)
    if request.url.path.startswith("/api/gtm/admin/"):
        policy = (30, 60)
    if request.url.path.startswith("/api/cash/admin/"):
        policy = (30, 60)
    elif request.url.path.startswith("/api/cash/orders/") and request.url.path.endswith("/claims"):
        policy = (5, 3600)
    elif request.url.path.startswith("/api/cash/quotes/") and request.url.path.endswith("/accept"):
        policy = (10, 3600)
    if policy and request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        client_host = request.client.host if request.client else "unknown"
        if client_host in {"127.0.0.1", "::1", "testclient"}:
            forwarded = request.headers.get("x-real-ip", "").strip()
            try:
                ipaddress.ip_address(forwarded)
                client_host = forwarded
            except ValueError:
                pass
        scope = f"{request.url.path}:{client_host}"
        try:
            allowed = consume_rate_limit(scope, policy[0], policy[1])
        except sqlite3.Error:
            return JSONResponse(status_code=503, content={"detail": "Request protection is unavailable"})
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests; try again later"},
                headers={"Retry-After": str(policy[1])},
            )
    return await call_next(request)

# -------------------------------------------------------------
# CORE API ENDPOINTS
# -------------------------------------------------------------

@app.get("/api/health")
def api_health():
    return {
        "status": "ok",
        "backend_health": "ONLINE",
        "engine": "AutoProfit FastAPI Enterprise v4.5",
        "database": "SQLite Persistent WAL (ONLINE)",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/ready")
def api_ready():
    """Read-only readiness probe with no database paths or secret values."""
    checks: dict[str, str] = {"database": "unavailable", "migrations": "unavailable"}
    try:
        conn = get_connection()
        try:
            integrity = str(conn.execute("PRAGMA quick_check").fetchone()[0])
            version_row = conn.execute("SELECT COALESCE(MAX(version),0) FROM schema_migrations").fetchone()
            version = int(version_row[0]) if version_row else 0
            checks["database"] = "ready" if integrity == "ok" else "integrity_check_failed"
            checks["migrations"] = "current" if version >= 13 else "outdated"
            checks["schema_version"] = str(version)
        finally:
            conn.close()
    except (sqlite3.Error, OSError, TypeError, ValueError):
        checks["database"] = "unavailable"
    ready = checks["database"] == "ready" and checks["migrations"] == "current"
    checks["internal_worker"] = "enabled" if runtime_enabled() else "disabled_by_config"
    provider = os.getenv("AUTOPROFIT_LLM_PROVIDER", "auto").strip().lower()
    if provider == "template":
        checks["model_provider"] = "degraded_mode"
    elif provider == "auto":
        checks["model_provider"] = "not_health_checked_optional"
    elif provider == "openai_compatible":
        remote_fields = ("AUTOPROFIT_LLM_ENDPOINT", "AUTOPROFIT_LLM_MODEL", "AUTOPROFIT_LLM_API_KEY")
        checks["model_provider"] = ("configured_not_health_checked"
                                     if all(os.getenv(name, "").strip() for name in remote_fields)
                                     else "unavailable_missing_config")
    elif provider in {"ollama", "llamacpp"}:
        checks["model_provider"] = "configured_not_health_checked"
    else:
        checks["model_provider"] = "invalid_config"
    return JSONResponse(status_code=200 if ready else 503,
                        content={"status": "ready" if ready else "not_ready", "checks": checks})


@app.post("/api/telemetry/pageview", status_code=202)
def api_telemetry_pageview(payload: TelemetryPayload, request: Request):
    if payload.internal_test:
        return {"accepted": False, "status": "internal_test_ignored"}
    session_id = _validate_telemetry_request(request, payload.session_id)
    path = (payload.path or "/")
    path = path.split("?", 1)[0].split("#", 1)[0]
    if not path.startswith("/") or path.startswith("/api/") or len(path) > 200:
        raise HTTPException(status_code=422, detail="Invalid page path")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO telemetry_sessions(session_id, created_at, last_seen_at)
               VALUES (?, ?, ?)
               ON CONFLICT(session_id) DO UPDATE SET last_seen_at=excluded.last_seen_at""",
            (session_id, now, now),
        )
        conn.execute(
            "INSERT INTO telemetry_pageviews(session_id, path, occurred_at) VALUES (?, ?, ?)",
            (session_id, path, now),
        )
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        raise HTTPException(status_code=503, detail="Telemetry storage unavailable")
    finally:
        conn.close()
    return {"accepted": True, "recorded_at": now}


@app.post("/api/telemetry/heartbeat", status_code=202)
def api_telemetry_heartbeat(payload: TelemetryPayload, request: Request):
    if payload.internal_test:
        return {"accepted": False, "status": "internal_test_ignored"}
    session_id = _validate_telemetry_request(request, payload.session_id)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO telemetry_sessions(session_id, created_at, last_seen_at)
               VALUES (?, ?, ?)
               ON CONFLICT(session_id) DO UPDATE SET last_seen_at=excluded.last_seen_at""",
            (session_id, now, now),
        )
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        raise HTTPException(status_code=503, detail="Telemetry storage unavailable")
    finally:
        conn.close()
    return {"accepted": True, "recorded_at": now}


@app.post("/api/public/payment-reports", status_code=202)
def api_public_payment_report(payload: PaymentReportPayload, request: Request):
    """Record a payment claim for manual review without marking it as paid."""
    raise HTTPException(status_code=410, detail="Legacy checkout is retired. Create a consented buyer order and claim through /checkout.html; a reference, QR, or screenshot is not payment proof.")
    origin = request.headers.get("origin")
    if origin:
        origin_parts = urlparse(origin)
        if (origin_parts.scheme not in {"http", "https"}
                or origin_parts.netloc.lower() != request.headers.get("host", "").lower()):
            raise HTTPException(status_code=403, detail="Cross-origin payment reports are not accepted")

    report_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    reference = (payload.reference or "").strip() or None
    email = (payload.customer_email or "").strip().lower() or None
    if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(status_code=422, detail="A valid customer email is required")
    if email and (not reference or len(reference) < 4):
        raise HTTPException(status_code=422, detail="A transaction reference of at least 4 characters is required")

    legacy_slug_aliases = {
        "github-vietqr-crypto-payment-link-maker": "vietqr-crypto-payment-generator",
        "github-defi-stablecoin-apy-yield-optimizer": "defi-staking-yield-compounder",
        "github-papaparse-csv-to-json-converter": "papaparse-csv-to-json-cleaner",
        "github-css-glassmorphism-landing-builder": "css-glassmorphism-card-builder",
    }
    requested_slug = payload.product_slug
    resolved_slug = legacy_slug_aliases.get(requested_slug, requested_slug)
    if resolved_slug.startswith("github-"):
        resolved_slug = resolved_slug[len("github-"):]

    conn = get_connection()
    try:
        product = next((item for item in TOOL_DEFINITIONS if item["slug"] == resolved_slug), None)
        if product is None:
            row = conn.execute(
                "SELECT slug, name, price_usd FROM products WHERE slug = ? AND active = 1",
                (resolved_slug,),
            ).fetchone()
            if row and row["price_usd"] is not None:
                product = {
                    "slug": row["slug"],
                    "name": row["name"] or row["slug"],
                    "price_usd": float(row["price_usd"]),
                    "price_vnd": round(float(row["price_usd"]) * 25500),
                }
        if product is None:
            raise HTTPException(status_code=404, detail="This product is not available for checkout")
        if requires_owner_quote(product):
            raise HTTPException(
                status_code=409,
                detail="This is a free demo. Customization, installation, or licensing requires an owner-reviewed quote after scope and an actual order.",
            )

        conn.execute(
            """INSERT INTO payment_reports
               (id, product_slug, product_name, amount_usd, amount_vnd, payment_method,
                customer_email, reference, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING_REVIEW', ?)""",
            (report_id, product["slug"], product["name"], product["price_usd"], product["price_vnd"],
             payload.payment_method, email, reference, now),
        )
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        raise HTTPException(status_code=503, detail="Payment report storage unavailable")
    finally:
        conn.close()
    return {"accepted": True, "report_id": report_id, "status": "PENDING_REVIEW", "submitted_at": now}


@app.get("/api/admin/payment-reports")
def api_admin_payment_reports(request: Request, limit: int = Query(default=100, ge=1, le=200)):
    if not _is_admin(request):
        raise HTTPException(status_code=403, detail="Admin API key required")
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT id, product_slug, product_name, amount_usd, amount_vnd, payment_method,
                      customer_email, reference, status, created_at, verified_by, verified_at
               FROM payment_reports ORDER BY created_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return {"items": [dict(row) for row in rows]}
    finally:
        conn.close()


@app.post("/api/admin/payment-reports/{report_id}/verify")
def api_admin_verify_payment_report(report_id: str, request: Request, payload: Dict[str, Any] = Body(default={} )):
    if not _is_admin(request):
        raise HTTPException(status_code=403, detail="Admin API key required")
    raise HTTPException(status_code=410, detail="Legacy payment claims cannot create settled revenue. Review and verify a Phase 07 cash claim against the receiving-account statement.")

    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM payment_reports WHERE id = ?", (report_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu thanh toán.")
        report = dict(row)
    finally:
        conn.close()

    if report["status"] == "PAID_VERIFIED":
        return {"status": "PAID_VERIFIED", "already_verified": True}
    if report["status"] != "PENDING_REVIEW":
        raise HTTPException(status_code=409, detail="Yêu cầu này không còn ở trạng thái chờ đối soát.")

    if report["payment_method"] == "BANK_TRANSFER":
        statement_reference = str(payload.get("statement_reference", "")).strip()[:120]
        if len(statement_reference) < 4:
            raise HTTPException(status_code=422, detail="Nhập mã giao dịch trên sao kê ngân hàng.")
        try:
            amount_vnd = int(payload.get("amount_vnd", 0))
        except (TypeError, ValueError):
            raise HTTPException(status_code=422, detail="Số tiền sao kê không hợp lệ.")
        if abs(amount_vnd - int(report["amount_vnd"])) > 1:
            raise HTTPException(status_code=409, detail="Số tiền trên sao kê không khớp yêu cầu thanh toán.")
        tx_reference = statement_reference
        verified_amount_usd = float(report["amount_usd"])
        verified_amount_vnd = amount_vnd
        transaction_method = "BANK_TRANSFER"
    elif report["payment_method"] == "BINANCE_PAY":
        customer_reference = str(report.get("reference") or "").strip()
        if re.fullmatch(r"0x[0-9a-fA-F]{64}", customer_reference):
            tx_reference = customer_reference.lower()
            verified_amount_usd = _verify_bsc_receipt(tx_reference, float(report["amount_usd"]))
            verified_amount_vnd = round(verified_amount_usd * 25500)
            transaction_method = "BSC_USDT_BEP20"
        else:
            tx_reference = str(payload.get("statement_reference", "")).strip()[:120]
            if len(tx_reference) < 4:
                raise HTTPException(status_code=422, detail="Nhập mã giao dịch trên lịch sử Binance Pay sau khi đã đối chiếu.")
            try:
                verified_amount_usd = float(payload.get("amount_usd", 0))
            except (TypeError, ValueError):
                raise HTTPException(status_code=422, detail="Số tiền USD trên lịch sử Binance Pay không hợp lệ.")
            if abs(verified_amount_usd - float(report["amount_usd"])) > 0.01:
                raise HTTPException(status_code=409, detail="Số tiền trên lịch sử Binance Pay không khớp yêu cầu thanh toán.")
            verified_amount_vnd = round(verified_amount_usd * 25500)
            transaction_method = "BINANCE_PAY_MANUAL_REVIEW"
    else:
        raise HTTPException(status_code=409, detail="Phương thức thanh toán chưa được hỗ trợ đối soát.")

    verified_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        latest = conn.execute("SELECT status FROM payment_reports WHERE id=?", (report_id,)).fetchone()
        if not latest:
            raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu thanh toán.")
        if latest["status"] == "PAID_VERIFIED":
            conn.rollback()
            return {"status": "PAID_VERIFIED", "already_verified": True}
        if latest["status"] != "PENDING_REVIEW":
            raise HTTPException(status_code=409, detail="Yêu cầu này không còn ở trạng thái chờ đối soát.")
        if conn.execute("SELECT 1 FROM transactions WHERE lower(tx_hash)=lower(?)", (tx_reference,)).fetchone():
            raise HTTPException(status_code=409, detail="Mã giao dịch đã được ghi nhận.")
        cursor = conn.execute(
            "UPDATE payment_reports SET status='PAID_VERIFIED', verified_by='owner', verified_at=? "
            "WHERE id=? AND status='PENDING_REVIEW'",
            (verified_at, report_id),
        )
        if cursor.rowcount != 1:
            raise HTTPException(status_code=409, detail="Yêu cầu đã được một phiên khác xử lý.")
        conn.execute(
            "INSERT INTO transactions(tx_hash, source, amount_usd, amount_vnd, payment_method, status, created_at) "
            "VALUES(?, ?, ?, ?, ?, 'PAID_VERIFIED', ?)",
            (tx_reference, "payment_report:" + report_id, verified_amount_usd, verified_amount_vnd,
             transaction_method, verified_at),
        )
        conn.commit()
    except HTTPException:
        conn.rollback()
        raise
    except sqlite3.Error:
        conn.rollback()
        raise HTTPException(status_code=503, detail="Không thể cập nhật trạng thái yêu cầu thanh toán.")
    finally:
        conn.close()
    audit_workflow_event("checkout_payment_report_verified", "payment_report", report_id, "owner",
                         {"payment_method": report["payment_method"], "reference": tx_reference})
    return {"status": "PAID_VERIFIED", "amount_usd": verified_amount_usd,
            "product_slug": report["product_slug"], "verified_at": verified_at}


@app.post("/api/public/payment-reports/status")
def api_public_payment_report_status(payload: Dict[str, Any]):
    report_id = str(payload.get("report_id", "")).strip()
    email = str(payload.get("customer_email", "")).strip().lower()
    if not report_id or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(status_code=422, detail="Cần mã yêu cầu và email hợp lệ.")
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, product_slug, status, created_at, verified_at FROM payment_reports "
            "WHERE id=? AND lower(customer_email)=?", (report_id, email)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu khớp với email này.")
        return {"id": row["id"], "product_slug": row["product_slug"], "status": row["status"],
                "created_at": row["created_at"], "verified_at": row["verified_at"],
                "delivery_available": False,
                "message": "Legacy payment reports are retained for history and do not authorize downloads."}
    finally:
        conn.close()


@app.get("/api/dashboard/summary")
def api_dashboard_summary(request: Request, window: str = Query(default="today", pattern="^(realtime|today|7d|30d)$")):
    snapshot = dashboard_summary(window)
    if not _is_admin(request):
        snapshot = copy.deepcopy(snapshot)
        metrics = snapshot.get("metrics", {})
        if "revenue_usd" in metrics:
            metrics["revenue_usd"] = {"value_usd": None, "status": "owner_auth_required"}
    return snapshot


@app.get("/api/dashboard/operations")
def api_dashboard_operations(request: Request):
    if not _is_admin(request):
        raise HTTPException(status_code=403, detail="Owner admin key required over HTTPS")
    return JSONResponse(
        content=dashboard_operations_summary(),
        headers={"Cache-Control": "private, no-store", "Pragma": "no-cache"},
    )


@app.get("/api/dashboard/activity")
def api_dashboard_activity(
    request: Request,
    limit: int = Query(default=25, ge=1, le=100),
    before_id: Optional[int] = Query(default=None, ge=1),
):
    if not _is_admin(request):
        raise HTTPException(status_code=403, detail="Admin API key required over HTTPS")
    return list_activity(limit=limit, before_id=before_id)


@app.get("/api/dashboard/activity/stream")
async def api_dashboard_activity_stream(request: Request, after_id: int = Query(default=0, ge=0)):
    if not _is_admin(request):
        raise HTTPException(status_code=403, detail="Admin API key required over HTTPS")
    source_status = list_activity(limit=1).get("status")
    if source_status not in {"observed", "no_data"}:
        return JSONResponse(
            status_code=503,
            content={"status": source_status, "error": "task_event_store_unavailable"},
            headers={"Cache-Control": "no-store"},
        )
    header_cursor = request.headers.get("last-event-id", "")
    try:
        cursor = max(after_id, int(header_cursor or 0))
    except ValueError:
        cursor = after_id

    async def stream_events():
        nonlocal cursor
        while not await request.is_disconnected():
            batch = events_after(cursor, limit=100)
            if batch:
                for item in batch:
                    cursor = int(item["event_id"])
                    payload = json.dumps(item, ensure_ascii=False, separators=(",", ":"))
                    yield f"id: {cursor}\nevent: activity\ndata: {payload}\n\n"
            else:
                yield ": keep-alive\n\n"
            await asyncio.sleep(1.5)

    return StreamingResponse(
        stream_events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )


@app.get("/api/dashboard/activity/{event_id}")
def api_dashboard_activity_detail(event_id: int, request: Request):
    if not _is_admin(request):
        raise HTTPException(status_code=403, detail="Admin API key required over HTTPS")
    event = task_event_by_id(event_id, include_sensitive=True)
    if event is None:
        raise HTTPException(status_code=404, detail="Activity event not found")
    return event

@app.get("/api/dashboard")
def api_dashboard(request: Request):
    snapshot = dashboard_summary("today")
    is_owner = _is_admin(request)
    if not is_owner:
        snapshot = copy.deepcopy(snapshot)
        if "revenue_usd" in snapshot.get("metrics", {}):
            snapshot["metrics"]["revenue_usd"] = {"value_usd": None, "status": "owner_auth_required"}
    conn = get_connection()
    try:
        workflow_row = conn.execute("SELECT value FROM system_state WHERE key = 'workflow:system'").fetchone()
        workflow_system = json.loads(workflow_row["value"]) if workflow_row else {}
    except (sqlite3.Error, ValueError, TypeError):
        workflow_system = {}
    finally:
        conn.close()
    # Older persisted workflow state could say RUNNING even though this
    # source tree has no connected execution worker.
    if workflow_system.get("system_status") == "RUNNING":
        workflow_system["system_status"] = "IDLE"
    metrics = snapshot.get("metrics", {})
    revenue = metrics.get("revenue_usd", {}).get("value_usd") if is_owner else None
    agents = metrics.get("active_agents", {}).get("value")
    pageviews = metrics.get("pageviews_today", {}).get("value")
    session_count = metrics.get("sessions_today", {}).get("value")
    response = {
        "system": {**SYSTEM_STATE, **workflow_system, "backend_health": "ONLINE" if snapshot.get("status") == "ok" else "DEGRADED"},
        "kpis_real_verified": {
            "verified_revenue_usd": revenue,
            "settled_in_bank_usd": revenue,
            "pending_settlement_usd": None,
            "actual_expenses_usd": None,
            "net_profit_usd": None,
            "paying_customers_count": None,
            "completed_orders_count": None,
            "qualified_opportunities_count": None,
            "conversion_rate_pct": None,
            "api_cost_usd": None,
            "active_agents_count": agents
        },
        "nine_bucket_accounting": {
            "1_verified_revenue_usd": revenue,
            "2_pending_payments_usd": None,
            "3_estimated_revenue_usd": None,
            "4_refunds_usd": None,
            "5_ai_costs_usd": None,
            "6_hosting_costs_usd": None,
            "7_marketplace_fees_usd": None,
            "8_other_expenses_usd": None,
            "9_net_profit_usd": None
        },
        "twelve_bucket_ledger": {
            "1_estimated_revenue_usd": None,
            "2_pending_revenue_usd": None,
            "3_verified_revenue_usd": revenue,
            "4_operating_costs_usd": None,
            "5_refunds_usd": None,
            "6_available_balance_usd": None,
            "7_cryptocurrency_balance_usdt": None,
            "8_token_valuation_usd": None,
            "9_realized_proceeds_usd": None,
            "10_pending_payouts_usd": None,
            "11_confirmed_payouts_usd": None,
            "12_net_profit_usd": None
        },
        "dashboard_18_metrics": {
            "daily_active_leads": None,
            "proposals_delivered": None,
            "conversion_velocity_hours": None,
            "active_affiliate_branches": None,
            "crypto_arbitrage_spread_pct": None,
            "traffic_pageviews_today": pageviews,
            "active_browser_sessions_today": session_count
        },
        "dashboard_data": snapshot,
    }
    # Every dashboard gets lease-backed executor readiness/state. Public users
    # receive no task names, ids, timestamps, diagnostics, or event details.
    from core.agent_runtime import dashboard_agent_registry
    response["agents_registry"] = dashboard_agent_registry(include_details=is_owner)
    if is_owner:
        from core.agent_runtime import runtime_profile
        response["agent_runtime"] = runtime_profile()
    return response

@app.get("/api/pricing/catalog")
def api_pricing_catalog():
    return api_products()

@app.get("/api/tasks")
def api_tasks(request: Request):
    if not _is_admin(request):
        raise HTTPException(status_code=403, detail="Admin API key required over HTTPS")
    items = list_core_tasks()
    availability = list_activity(limit=1).get("status")
    status = "observed" if items else "no_data" if availability == "no_data" else availability
    return {"items": items, "total": len(items) if status in {"observed", "no_data"} else None, "status": status}

@app.get("/api/transactions")
def api_transactions(request: Request):
    if not _is_admin(request):
        raise HTTPException(status_code=403, detail="Admin API key required over HTTPS")
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, source, amount_usd, amount_vnd, payment_method, status, created_at FROM transactions ORDER BY id DESC LIMIT 200"
        ).fetchall()
        return {"items": [dict(row) for row in rows], "total": len(rows), "status": "observed" if rows else "no_data"}
    finally:
        conn.close()

@app.get("/api/wallet/binance-usdt")
def api_wallet(request: Request):
    if not _is_admin(request):
        raise HTTPException(status_code=403, detail="Admin API key required over HTTPS")
    if not (CONFIG.BINANCE_USDT_BEP20 or CONFIG.BSC_USDT_WALLET):
        raise HTTPException(status_code=503, detail="Payment destination is not configured")
    return {
        "wallet_address": CONFIG.BINANCE_USDT_BEP20 or CONFIG.BSC_USDT_WALLET,
        "network": "BNB Smart Chain (BEP20)",
        "status": "configured",
        "receiving_token": "USDT"
    }

@app.get("/api/public/aads-config")
def api_aads_config():
    conn = get_connection()
    try:
        row = conn.execute("SELECT value FROM system_state WHERE key = 'workflow:aads'").fetchone()
        saved = json.loads(row["value"]) if row else {}
    except (sqlite3.Error, ValueError, TypeError):
        saved = {}
    finally:
        conn.close()
    return {
        "top_ad_unit_id": saved.get("top_ad_unit_id", CONFIG.AADS_UNIT_ID_TOP),
        "bottom_ad_unit_id": CONFIG.AADS_UNIT_ID_BOTTOM,
        "monetag_tag": CONFIG.MONETAG_TAG_ID,
        "monetag_zone_id": CONFIG.MONETAG_ZONE_ID,
        "status": "configured_no_verified_telemetry" if any((
            saved.get("top_ad_unit_id", CONFIG.AADS_UNIT_ID_TOP),
            CONFIG.AADS_UNIT_ID_BOTTOM,
            CONFIG.MONETAG_TAG_ID,
        )) else "not_configured"
    }


@app.get("/api/public/aads-live-telemetry")
def api_aads_live_telemetry():
    # No verified ad-network telemetry provider is configured on this backend.
    # Return an explicit state instead of letting the UI mistake a missing route
    # for a network failure or fabricate live earnings.
    return {"status": "not_connected", "source": "no_verified_ad_telemetry_provider"}


@app.get("/api/llm/token-ledger")
def api_llm_token_ledger(limit: int = Query(default=25, ge=1, le=100)):
    """Read real provider usage only; never expose prompts, outputs, or credentials."""
    conn = get_connection()
    try:
        exists = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='llm_usage'").fetchone()
        if not exists:
            return {"status": "not_connected", "source": "no_verified_llm_provider_session",
                    "summary": None, "recent_calls": [], "limit": limit}
        aggregate = conn.execute(
            """SELECT
                 SUM(CASE WHEN status IN ('SUCCESS','FAILURE','PENDING') THEN 1 ELSE 0 END) AS total_requests,
                 SUM(CASE WHEN status='CACHE_HIT' THEN 1 ELSE 0 END) AS cache_hits,
                 SUM(CASE WHEN status='FAILURE' THEN 1 ELSE 0 END) AS failure_count,
                 SUM(CASE WHEN status='DEGRADED' THEN 1 ELSE 0 END) AS degraded_runs,
                 SUM(CASE WHEN status IN ('SUCCESS','FAILURE') AND prompt_tokens IS NULL THEN 1 ELSE 0 END) AS unknown_token_events,
                 SUM(prompt_tokens) AS prompt_tokens,
                 SUM(completion_tokens) AS completion_tokens,
                 AVG(latency_ms) AS average_latency_ms
               FROM llm_usage"""
        ).fetchone()
        rows = conn.execute(
            """SELECT id,task_kind,provider,model,prompt_tokens,completion_tokens,latency_ms,status,
                      failure_code,confidence_estimate,confidence_label,created_at
               FROM llm_usage ORDER BY id DESC LIMIT ?""", (limit,)
        ).fetchall()
        summary = {key: aggregate[key] for key in aggregate.keys()}
        for key in ("total_requests", "cache_hits", "failure_count", "degraded_runs", "unknown_token_events",
                    "prompt_tokens", "completion_tokens"):
            summary[key] = int(summary[key] or 0)
        summary["average_latency_ms"] = round(float(summary["average_latency_ms"] or 0), 1)
        calls = []
        for row in rows:
            prompt = row["prompt_tokens"]
            completion = row["completion_tokens"]
            calls.append({
                "request_id": str(row["id"]), "task_kind": row["task_kind"],
                "provider": row["provider"], "model": row["model"],
                "prompt_tokens": int(prompt) if prompt is not None else None,
                "completion_tokens": int(completion) if completion is not None else None,
                "total_tokens": int(prompt + completion) if prompt is not None and completion is not None else None,
                "latency_ms": int(row["latency_ms"]), "status": row["status"],
                "failure_code": row["failure_code"],
                "confidence_estimate": row["confidence_estimate"],
                "confidence_label": row["confidence_label"],
                "created_at_iso": row["created_at"],
            })
        connected = summary["total_requests"] > 0
        return {"status": "connected" if connected else "not_connected",
                "source": "canonical_llm_usage_ledger", "summary": summary,
                "recent_calls": calls, "limit": limit}
    except sqlite3.Error:
        return {"status": "not_connected", "source": "usage_ledger_unavailable",
                "summary": None, "recent_calls": [], "limit": limit}
    finally:
        conn.close()

# -------------------------------------------------------------
# GITHUB WEB FACTORY APPS ROUTER
# -------------------------------------------------------------

@app.get("/api/github-web-factory/apps")
def api_factory_apps():
    return {
        "items": TOOL_DEFINITIONS,
        "total": len(TOOL_DEFINITIONS)
    }

@app.get("/api/github-web-factory/apps/{slug}/live", response_class=HTMLResponse)
def api_factory_live(slug: str):
    slug = {
        "github-vietqr-crypto-payment-link-maker": "vietqr-crypto-payment-generator",
        "github-defi-stablecoin-apy-yield-optimizer": "defi-staking-yield-compounder",
        "github-papaparse-csv-to-json-converter": "papaparse-csv-to-json-cleaner",
        "github-css-glassmorphism-landing-builder": "css-glassmorphism-card-builder",
    }.get(slug, slug.removeprefix("github-"))
    file_path = APPS_DIR / f"{slug}.html"
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    raise HTTPException(status_code=404, detail="Web app not found")

@app.get("/api/github-web-factory/apps/{slug}/download")
def api_factory_download(slug: str):
    slug = {
        "github-vietqr-crypto-payment-link-maker": "vietqr-crypto-payment-generator",
        "github-defi-stablecoin-apy-yield-optimizer": "defi-staking-yield-compounder",
        "github-papaparse-csv-to-json-converter": "papaparse-csv-to-json-cleaner",
        "github-css-glassmorphism-landing-builder": "css-glassmorphism-card-builder",
    }.get(slug, slug.removeprefix("github-"))
    file_path = APPS_DIR / f"{slug}.html"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Web app file not found")
    raise HTTPException(status_code=410, detail="Direct source downloads are disabled. Paid delivery requires a Phase 07 expiring authorization.")

@app.post("/api/github-web-factory/scan-and-build")
def api_scan_and_build(request: Request, payload: Dict[str, Any] = Body(default={} )):
    if not _is_admin(request):
        raise HTTPException(status_code=403, detail="Cần khóa quản trị hợp lệ.")
    build_all_tools()
    return {
        "status": "REGENERATED",
        "message": f"Đã tạo lại {len(TOOL_DEFINITIONS)} công cụ trong catalog nội bộ. Không quét GitHub và không nhập repository bên ngoài.",
        "count": len(TOOL_DEFINITIONS),
        "external_github_scan": False,
    }

# -------------------------------------------------------------
# STATIC FRONTEND SERVING
# -------------------------------------------------------------

# Mount static frontend
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8450, reload=False)
