"""Weekly metric-only optimizer: one proposal at a time, never auto-publishes."""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import business_engine

MIN_PERIOD_VISITS = 10
MIN_ACTIVE_TEST_VISITS = 20
FUNNEL = (
    ("landing_view", "consented landing views"),
    ("demo_start", "demo starts"),
    ("contact_submit", "opted-in inquiries"),
    ("qualified_inquiry", "qualified inquiries"),
    ("proposal_sent", "owner-attested proposals sent"),
    ("customer_reply", "customer replies"),
    ("accepted_quote", "accepted quotes"),
    ("verified_payment", "verified orders"),
)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _metric_snapshot(conn: sqlite3.Connection, start: datetime, end: datetime) -> dict[str, Any]:
    start_text = business_engine.iso(start)
    end_text = business_engine.iso(end)
    events: dict[str, int] = {name: 0 for name, _ in FUNNEL}
    try:
        rows = conn.execute(
            "SELECT event_name,COUNT(*) AS count FROM gtm_analytics_events "
            "WHERE internal_test=0 AND occurred_at>=? AND occurred_at<? GROUP BY event_name",
            (start_text, end_text),
        ).fetchall()
        events.update({str(row["event_name"]): int(row["count"]) for row in rows if row["event_name"] in events})
    except sqlite3.Error:
        pass
    verified_orders = 0
    net_by_currency: dict[str, int] = {}
    if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='cash_transactions'").fetchone():
        rows = conn.execute(
            "SELECT t.currency,COUNT(DISTINCT t.order_id) AS orders,SUM(t.amount_minor) AS amount "
            "FROM cash_transactions t JOIN cash_orders o ON o.id=t.order_id "
            "WHERE COALESCE(o.is_test,0)=0 AND t.verified_at>=? AND t.verified_at<? GROUP BY t.currency",
            (start_text, end_text),
        ).fetchall()
        verified_orders = sum(int(row["orders"] or 0) for row in rows)
        net_by_currency = {str(row["currency"]): int(row["amount"] or 0) for row in rows}
        adjustment_rows = conn.execute(
            "SELECT a.currency,a.adjustment_type,SUM(a.amount_minor) AS amount "
            "FROM cash_adjustments a JOIN cash_orders o ON o.id=a.order_id "
            "WHERE COALESCE(o.is_test,0)=0 AND a.occurred_at>=? AND a.occurred_at<? "
            "GROUP BY a.currency,a.adjustment_type",
            (start_text, end_text),
        ).fetchall()
        for row in adjustment_rows:
            direction = 1 if row["adjustment_type"] == "CHARGEBACK_REVERSAL" else -1
            currency = str(row["currency"])
            net_by_currency[currency] = net_by_currency.get(currency, 0) + direction * int(row["amount"] or 0)
    events["verified_payment"] = verified_orders
    return {
        "window_start": start_text,
        "window_end_exclusive": end_text,
        "source": "consented_gtm_analytics_and_non_test_verified_cash_ledger",
        "event_counts": events,
        "verified_net_cash_by_currency_minor": dict(sorted(net_by_currency.items())),
        "test_orders_excluded": True,
        "unique_people_claimed": False,
    }


def _proposal_for(snapshot: dict[str, Any]) -> tuple[str, str] | None:
    counts = snapshot["event_counts"]
    if counts.get("landing_view", 0) < MIN_PERIOD_VISITS:
        return None
    measured = [(key, label, counts.get(key, 0)) for key, label in FUNNEL]
    gaps = []
    for (left_key, left_label, left_count), (right_key, right_label, right_count) in zip(measured, measured[1:]):
        if left_count >= MIN_PERIOD_VISITS:
            gaps.append((right_count / left_count, right_key, left_label, right_label))
    if not gaps:
        return None
    _ratio, target, previous, next_stage = min(gaps, key=lambda item: (item[0], item[1]))
    return target, f"Test one clearer next-step message after {previous}; measure whether more visitors complete {next_stage}. Keep layout, offer, and channel unchanged."


def run_weekly_optimization(*, path: Optional[Path | str] = None,
                             now: Optional[datetime] = None,
                             force: bool = False) -> dict[str, Any]:
    """Snapshot two completed weeks and save at most one owner-reviewed hypothesis."""
    business_engine.ensure_schema(path)
    safety_conn = business_engine.connect(path)
    try:
        controls = {row["key"]: row["value"] for row in safety_conn.execute("SELECT key,value FROM engine_control")}
        if business_engine._kill_switch_enabled(safety_conn, controls):
            return {"status": "blocked", "reason_code": "kill_switch_enabled",
                    "public_change_applied": False}
    finally:
        safety_conn.close()
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    end = current.replace(hour=0, minute=0, second=0, microsecond=0)
    start = end - timedelta(days=7)
    baseline_start = start - timedelta(days=7)
    run_key = f"{baseline_start.date().isoformat()}:{end.date().isoformat()}"
    conn = business_engine.connect(path)
    try:
        existing = conn.execute("SELECT * FROM optimization_runs WHERE run_key=?", (run_key,)).fetchone()
        if existing:
            proposal = conn.execute("SELECT id,status,target_stage FROM optimization_proposals WHERE run_id=?", (existing["id"],)).fetchone()
            return {"status": "already_ran", "run_id": existing["id"], "run_status": existing["status"],
                    "proposal": dict(proposal) if proposal else None, "public_change_applied": False}

        baseline = _metric_snapshot(conn, baseline_start, start)
        latest = _metric_snapshot(conn, start, end)
        active = conn.execute(
            "SELECT * FROM optimization_proposals WHERE active_slot=1 ORDER BY created_at LIMIT 1"
        ).fetchone()
        status = "INSUFFICIENT_BASELINE"
        stop_recommended = False
        proposal_id: str | None = None

        if active and active["status"] == "ACTIVE_MANUAL":
            old = json.loads(active["baseline_json"])
            visits = int(latest["event_counts"].get("landing_view", 0))
            old_visits = int(old.get("event_counts", {}).get("landing_view", 0))
            old_conversions = int(old.get("event_counts", {}).get("qualified_inquiry", 0))
            new_conversions = int(latest["event_counts"].get("qualified_inquiry", 0))
            if visits >= MIN_ACTIVE_TEST_VISITS and old_visits >= MIN_PERIOD_VISITS:
                old_rate = old_conversions / old_visits
                new_rate = new_conversions / visits
                if new_rate < old_rate * 0.8:
                    conn.execute("UPDATE optimization_proposals SET status='STOP_RECOMMENDED',updated_at=? WHERE id=?",
                                 (business_engine.iso(current), active["id"]))
                    status = "STOP_RECOMMENDED"
                    stop_recommended = True
                else:
                    status = "NO_CHANGE_PROPOSED"
            run_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO optimization_runs(id,run_key,window_start,window_end,baseline_json,current_json,status,created_at) VALUES(?,?,?,?,?,?,?,?)",
                (run_id, run_key, business_engine.iso(baseline_start), business_engine.iso(end), _json(baseline), _json(latest), status, business_engine.iso(current)),
            )
            conn.commit()
            return {"status": status.lower(), "run_id": run_id,
                    "proposal": {"id": active["id"], "status": "STOP_RECOMMENDED" if stop_recommended else active["status"]},
                    "public_change_applied": False}

        proposal_exists = active is not None
        visits = int(latest["event_counts"].get("landing_view", 0))
        baseline_visits = int(baseline["event_counts"].get("landing_view", 0))
        if visits >= MIN_PERIOD_VISITS and baseline_visits >= MIN_PERIOD_VISITS and not proposal_exists:
            candidate = _proposal_for(latest)
            if candidate:
                target_stage, hypothesis = candidate
                run_id = str(uuid.uuid4())
                status = "PROPOSAL_CREATED"
                conn.execute(
                    "INSERT INTO optimization_runs(id,run_key,window_start,window_end,baseline_json,current_json,status,created_at) VALUES(?,?,?,?,?,?,?,?)",
                    (run_id, run_key, business_engine.iso(baseline_start), business_engine.iso(end), _json(baseline), _json(latest), status, business_engine.iso(current)),
                )
                proposal_id = str(uuid.uuid4())
                conn.execute(
                    """INSERT INTO optimization_proposals
                       (id,run_id,status,active_slot,target_stage,hypothesis,proposed_change,stop_criteria,baseline_json,created_at,updated_at)
                       VALUES(?,?,'AWAITING_APPROVAL',1,?,?,?,?,?,?,?)""",
                    (proposal_id, run_id, target_stage, hypothesis,
                     "Change one text element only; public edits require owner approval and manual deployment.",
                     "After at least 20 consented views, recommend stopping if qualified inquiries per view fall at least 20% below this saved baseline.",
                     _json(latest), business_engine.iso(current), business_engine.iso(current)),
                )
            else:
                status = "NO_CHANGE_PROPOSED"
                run_id = str(uuid.uuid4())
                conn.execute(
                    "INSERT INTO optimization_runs(id,run_key,window_start,window_end,baseline_json,current_json,status,created_at) VALUES(?,?,?,?,?,?,?,?)",
                    (run_id, run_key, business_engine.iso(baseline_start), business_engine.iso(end), _json(baseline), _json(latest), status, business_engine.iso(current)),
                )
        else:
            run_id = str(uuid.uuid4())
            status = "NO_CHANGE_PROPOSED" if proposal_exists else "INSUFFICIENT_BASELINE"
            conn.execute(
                "INSERT INTO optimization_runs(id,run_key,window_start,window_end,baseline_json,current_json,status,created_at) VALUES(?,?,?,?,?,?,?,?)",
                (run_id, run_key, business_engine.iso(baseline_start), business_engine.iso(end), _json(baseline), _json(latest), status, business_engine.iso(current)),
            )
        conn.commit()
        return {"status": status.lower(), "run_id": run_id,
                "proposal": ({"id": proposal_id, "status": "AWAITING_APPROVAL"} if proposal_id else None),
                "public_change_applied": False,
                "baseline_window": [baseline["window_start"], baseline["window_end_exclusive"]],
                "measurement_window": [latest["window_start"], latest["window_end_exclusive"]]}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def decide_optimization_proposal(proposal_id: str, decision: str, *, path: Optional[Path | str] = None,
                                 now: Optional[datetime] = None) -> dict[str, Any]:
    transitions = {
        "approve": ("AWAITING_APPROVAL", "APPROVED_FOR_MANUAL_CHANGE"),
        "activate_manual": ("APPROVED_FOR_MANUAL_CHANGE", "ACTIVE_MANUAL"),
        "reject": ("AWAITING_APPROVAL", "REJECTED"),
        "stop": ("STOP_RECOMMENDED", "STOPPED"),
        "complete": ("ACTIVE_MANUAL", "COMPLETED"),
    }
    if decision not in transitions:
        raise ValueError("unsupported optimization decision")
    current_state, next_state = transitions[decision]
    business_engine.ensure_schema(path)
    conn = business_engine.connect(path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM optimization_proposals WHERE id=?", (proposal_id,)).fetchone()
        if not row:
            raise KeyError("optimization proposal not found")
        if row["status"] != current_state:
            raise ValueError("optimization proposal is not in the expected review state")
        now_text = business_engine.iso(now or datetime.now(timezone.utc))
        slot = None if next_state in {"REJECTED", "STOPPED", "COMPLETED"} else row["active_slot"]
        conn.execute("UPDATE optimization_proposals SET status=?,active_slot=?,owner_decision=?,owner_decided_at=?,updated_at=? WHERE id=?",
                     (next_state, slot, decision, now_text, now_text, proposal_id))
        conn.commit()
        return {"id": proposal_id, "status": next_state, "public_change_applied": False}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Read real first-party metrics and propose at most one weekly optimization hypothesis.")
    parser.add_argument("--force", action="store_true", help="ignore the seven-day cadence guard; the same completed window remains idempotent")
    args = parser.parse_args()
    result = run_weekly_optimization(force=args.force)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
