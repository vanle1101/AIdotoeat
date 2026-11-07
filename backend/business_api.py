"""Authenticated REST and SSE surface for the persistent business engine."""
from __future__ import annotations

import asyncio
import json
from typing import Any, Optional

from fastapi import APIRouter, Body, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

import business_engine as engine
from workflow_api import _require_admin

router = APIRouter()


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RunCreate(StrictModel):
    idempotency_key: Optional[str] = Field(default=None, min_length=1, max_length=180)
    payload: dict[str, Any] = Field(default_factory=dict)


class ApprovalCreate(StrictModel):
    tool_name: str = Field(min_length=1, max_length=100)
    payload: dict[str, Any]
    idempotency_key: Optional[str] = Field(default=None, min_length=1, max_length=180)
    expires_in_seconds: int = Field(default=3600, ge=60, le=259200)


class ApprovalDecision(StrictModel):
    decision: str = Field(pattern="^(APPROVED|REJECTED)$")
    reason: str = Field(default="", max_length=240)


class TaskDecision(StrictModel):
    decision: str = Field(pattern="^(APPROVED|REJECTED)$")


class ToolInvoke(StrictModel):
    payload: dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = True
    approval_id: Optional[str] = Field(default=None, max_length=80)
    idempotency_key: Optional[str] = Field(default=None, min_length=1, max_length=180)


class GrantRequest(StrictModel):
    tool_name: str = Field(min_length=1, max_length=100)
    principal: str = Field(default="owner", min_length=1, max_length=120)


class BooleanControl(StrictModel):
    enabled: bool


def _admin(request: Request) -> None:
    _require_admin(request)


def _task_summary(row: dict[str, Any]) -> dict[str, Any]:
    return {key: row.get(key) for key in (
        "id", "title", "category", "assigned_role_id", "status", "state", "state_version",
        "task_type", "run_id", "trace_id", "attempts", "max_attempts", "available_at",
        "lease_expires_at", "created_at", "updated_at", "started_at", "finished_at", "last_error",
    )}


@router.get("/api/engine/status")
def engine_status(request: Request):
    _admin(request)
    return engine.engine_status()


@router.get("/api/engine/runs")
def engine_runs(request: Request, limit: int = Query(default=100, ge=1, le=500)):
    _admin(request)
    return {"items": engine.list_workflow_runs(limit), "total_status": "observed"}


@router.post("/api/engine/runs", status_code=202)
def engine_create_run(request: Request, body: RunCreate):
    _admin(request)
    try:
        run = engine.start_workflow(idempotency_key=body.idempotency_key, payload=body.payload)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"id": run["id"], "workflow": run["workflow"], "status": run["status"],
            "trace_id": run["trace_id"], "created_at": run["created_at"],
            "worker_enabled": engine.runtime_enabled()}


@router.get("/api/engine/runs/{run_id}")
def engine_run_detail(run_id: str, request: Request):
    _admin(request)
    run = engine.get_workflow_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.post("/api/engine/runs/{run_id}/pause")
def engine_pause_run(run_id: str, request: Request):
    _admin(request)
    if not engine.pause_workflow(run_id):
        raise HTTPException(status_code=409, detail="Run cannot be paused in its current state")
    return {"id": run_id, "status": "PAUSED"}


@router.post("/api/engine/runs/{run_id}/resume")
def engine_resume_run(run_id: str, request: Request):
    _admin(request)
    if not engine.resume_workflow(run_id):
        raise HTTPException(status_code=409, detail="Run is not paused")
    engine.ensure_runtime_started()
    return {"id": run_id, "status": "QUEUED"}


@router.post("/api/engine/runs/{run_id}/cancel")
def engine_cancel_run(run_id: str, request: Request):
    _admin(request)
    if not engine.cancel_workflow(run_id):
        raise HTTPException(status_code=409, detail="Run cannot be cancelled in its current state")
    return {"id": run_id, "status": "CANCELLED"}


@router.get("/api/engine/tasks")
def engine_tasks(request: Request, state: Optional[str] = Query(default=None), limit: int = Query(default=100, ge=1, le=500)):
    _admin(request)
    if state:
        try:
            engine.TaskState(state)
        except ValueError:
            raise HTTPException(status_code=422, detail="Unknown task state")
    items = [_task_summary(row) for row in engine.list_tasks(state=state, limit=limit)]
    return {"items": items, "total": len(items)}


@router.get("/api/engine/tasks/{task_id}/events")
def engine_task_events(task_id: int, request: Request, limit: int = Query(default=100, ge=1, le=500)):
    _admin(request)
    conn = engine.connect()
    try:
        rows = conn.execute("SELECT event_id FROM task_events WHERE task_id=? ORDER BY event_id DESC LIMIT ?",
                            (str(task_id), limit)).fetchall()
    finally:
        conn.close()
    items = []
    for row in reversed(rows):
        items.extend(engine.list_task_events(int(row["event_id"]) - 1, limit=1))
    items = [item for item in items if str(item["task_id"]) == str(task_id)]
    return {"items": items, "total": len(items)}


@router.post("/api/engine/tasks/{task_id}/decision")
def engine_task_decision(task_id: int, request: Request, body: TaskDecision):
    _admin(request)
    try:
        row = engine.decide_task_approval(task_id, body.decision, actor="owner")
    except KeyError:
        raise HTTPException(status_code=404, detail="Task not found")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    if row["state"] == "QUEUED" and row.get("run_id"):
        conn = engine.connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            engine._refresh_run(conn, row["run_id"])
            conn.commit()
        finally:
            conn.close()
    return {"task_id": task_id, "state": row["state"], "state_version": row["state_version"]}


@router.get("/api/engine/queue")
def engine_queue(request: Request, limit: int = Query(default=100, ge=1, le=500)):
    _admin(request)
    items = [_task_summary(row) for state in ("QUEUED", "RUNNING", "RETRY_PENDING", "WAITING_APPROVAL", "BLOCKED")
             for row in engine.list_tasks(state=state, limit=limit)]
    items.sort(key=lambda row: (row.get("available_at") or "", row["id"]))
    return {"items": items[:limit], "total": len(items[:limit]), "status": engine.engine_status()}


@router.get("/api/engine/events")
async def engine_events(request: Request, after_id: int = Query(default=0, ge=0)):
    _admin(request)
    try:
        header_cursor = int(request.headers.get("last-event-id", "0") or 0)
    except ValueError:
        raise HTTPException(status_code=422, detail="Last-Event-ID must be an integer")
    cursor = max(after_id, header_cursor, 0)

    async def stream():
        nonlocal cursor
        while not await request.is_disconnected():
            for item in engine.list_task_events(cursor, limit=100):
                cursor = int(item["event_id"])
                safe = {key: item.get(key) for key in ("event_id", "timestamp", "task_id", "run_id", "event_type", "status", "title", "source", "trace_id", "details")}
                yield f"id: {cursor}\nevent: engine\ndata: {json.dumps(safe,ensure_ascii=False,separators=(',',':'))}\n\n"
            if not engine.list_task_events(cursor, limit=1):
                yield ": keep-alive\n\n"
            await asyncio.sleep(1.0)

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"})


@router.get("/api/engine/audit")
def engine_audit(request: Request, limit: int = Query(default=100, ge=1, le=500)):
    _admin(request)
    return {"items": engine.list_engine_audit(limit), "total": None}


@router.get("/api/engine/dead-letters")
def engine_dead_letters(request: Request, limit: int = Query(default=100, ge=1, le=500)):
    _admin(request)
    conn = engine.connect()
    try:
        rows = conn.execute("SELECT d.task_id,d.reason,d.attempts,d.moved_at,t.title,t.trace_id FROM task_dead_letters d JOIN tasks t ON t.id=d.task_id ORDER BY d.moved_at DESC LIMIT ?",
                            (limit,)).fetchall()
        return {"items": [dict(row) for row in rows], "total": len(rows)}
    finally:
        conn.close()


@router.post("/api/engine/control/pause")
def engine_pause(request: Request):
    _admin(request)
    engine.set_engine_control("paused", True)
    return engine.engine_status()


@router.post("/api/engine/control/resume")
def engine_resume(request: Request):
    _admin(request)
    engine.set_engine_control("paused", False)
    engine.ensure_runtime_started()
    return engine.engine_status()


@router.post("/api/engine/control/shutdown")
def engine_shutdown(request: Request):
    _admin(request)
    engine.set_engine_control("shutdown", True)
    return {**engine.engine_status(), "status": "SHUTDOWN_REQUESTED"}


@router.post("/api/engine/control/kill-switch")
def engine_kill_switch(request: Request, body: BooleanControl):
    _admin(request)
    engine.set_engine_control("kill_switch", body.enabled)
    return engine.engine_status()


@router.get("/api/engine/tools")
def engine_tools(request: Request):
    _admin(request)
    return {"items": engine.tool_registry(), "dry_run_default": True}


@router.post("/api/engine/tools/{tool_name}/approvals", status_code=201)
def engine_request_approval(tool_name: str, request: Request, body: ApprovalCreate):
    _admin(request)
    if body.tool_name != tool_name:
        raise HTTPException(status_code=422, detail="Tool name does not match request path")
    try:
        approval = engine.request_approval(tool_name, "owner", body.payload,
                                           idempotency_key=body.idempotency_key,
                                           expires_in_seconds=body.expires_in_seconds)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {key: approval.get(key) for key in ("id", "tool_name", "permission", "requested_by", "status", "trace_id", "expires_at", "created_at")}


@router.get("/api/engine/approvals")
def engine_approvals(request: Request, limit: int = Query(default=100, ge=1, le=500)):
    _admin(request)
    return {"items": [{key: row.get(key) for key in ("id", "tool_name", "permission", "requested_by", "status", "decision_by", "decision_reason", "expires_at", "created_at", "decided_at", "consumed_at", "trace_id")} for row in engine.list_approvals(limit)],
            "total": None}


@router.post("/api/engine/approvals/{approval_id}/decision")
def engine_decide_approval(approval_id: str, request: Request, body: ApprovalDecision):
    _admin(request)
    try:
        result = engine.decide_approval(approval_id, body.decision, actor="owner", reason=body.reason)
    except KeyError:
        raise HTTPException(status_code=404, detail="Approval not found")
    except TimeoutError:
        raise HTTPException(status_code=409, detail="Approval request expired")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return {key: result.get(key) for key in ("id", "tool_name", "permission", "status", "decision_by", "decided_at", "expires_at")}


@router.post("/api/engine/grants")
def engine_grant(request: Request, body: GrantRequest):
    _admin(request)
    tools = {tool["name"]: tool for tool in engine.tool_registry()}
    tool = tools.get(body.tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    engine.grant_privilege(body.principal, tool["permission"], actor="owner")
    return {"principal": body.principal, "permission": tool["permission"], "status": "GRANTED"}


@router.delete("/api/engine/grants/{principal}/{tool_name}")
def engine_revoke(request: Request, principal: str, tool_name: str):
    _admin(request)
    tools = {tool["name"]: tool for tool in engine.tool_registry()}
    tool = tools.get(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    revoked = engine.revoke_privilege(principal, tool["permission"], actor="owner")
    return {"principal": principal, "permission": tool["permission"], "status": "REVOKED" if revoked else "NOT_GRANTED"}


@router.post("/api/engine/tools/{tool_name}/invoke")
def engine_invoke(tool_name: str, request: Request, body: ToolInvoke):
    _admin(request)
    try:
        result = engine.invoke_tool(tool_name, "owner", body.payload, dry_run=body.dry_run,
                                    approval_id=body.approval_id, idempotency_key=body.idempotency_key)
    except engine.PolicyDenied as exc:
        raise HTTPException(status_code=403, detail=exc.reason_code)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return result
