"""HTTPS owner endpoints for the read-only weekly optimization agent."""
from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from database import get_connection
from core.optimization_agent import decide_optimization_proposal, run_weekly_optimization
from workflow_api import _require_admin

router = APIRouter()


@router.post("/api/optimization/admin/run")
def optimization_run(request: Request):
    _require_admin(request)
    try:
        return run_weekly_optimization()
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="Optimization metrics are unavailable.") from exc


@router.get("/api/optimization/admin/proposals")
def optimization_proposals(request: Request):
    _require_admin(request)
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id,run_id,status,target_stage,hypothesis,proposed_change,stop_criteria,baseline_json,owner_decision,owner_decided_at,created_at,updated_at "
            "FROM optimization_proposals ORDER BY created_at DESC LIMIT 100"
        ).fetchall()
        return {"items": [dict(row) for row in rows], "total": len(rows), "public_change_applied": False}
    finally:
        conn.close()


@router.post("/api/optimization/admin/proposals/{proposal_id}/decision")
def optimization_decision(proposal_id: str, request: Request, payload: dict[str, Any]):
    _require_admin(request)
    if payload.get("decision") == "activate_manual" and payload.get("owner_attests_live_change") is not True:
        raise HTTPException(status_code=422, detail="Owner attestation that the reviewed manual change is active is required.")
    try:
        return decide_optimization_proposal(proposal_id, str(payload.get("decision", "")))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Optimization proposal not found.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail="Optimization proposal is not in the expected state or decision.") from exc
