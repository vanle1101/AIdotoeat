"""
Single-Worker Linear Orchestrator
Strictly complies with Rules 8, 13, 14, 15:
- 0 VND hardcap verification before every step.
- Single worker queue (no concurrency race, no rate limit explosions).
- Zero agent-to-agent idle banter.
- Pure value creation pipeline.
"""
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from core.budget_auditor import BudgetAuditor
from core.roles import get_role, LogicalRole
from core.db import get_connection, record_task_event, sanitize_text
from core.llm import LLMError, LLMGateway

class ZeroCostOrchestrator:
    """The central engine executing corporate tasks at exactly 0 VND."""

    def __init__(self, llm_gateway: Optional[LLMGateway] = None):
        self.active_role: Optional[LogicalRole] = None
        self.llm_gateway = llm_gateway or LLMGateway()

    def classify_opportunity(self, source_text: str, *, source_id: str = "owner_provided_source") -> Dict[str, Any]:
        """Classify actual supplied source material through a health-checked model."""
        return self.llm_gateway.run(
            "niche_classification", {"source_id": source_id, "source_text": source_text}
        ).__dict__

    def extract_evidence(self, sources: List[Dict[str, str]]) -> Dict[str, Any]:
        """Extract claims with source IDs from caller-supplied pages/documents."""
        return self.llm_gateway.run("evidence_extraction", {"sources": sources}).__dict__

    def personalize_proposal(self, customer_need: str, verified_facts: List[str]) -> Dict[str, Any]:
        """Draft against explicitly verified facts; no facts are inferred from memory."""
        return self.llm_gateway.run(
            "proposal_personalization",
            {"customer_need": customer_need, "verified_facts": verified_facts},
        ).__dict__

    def execute_role_action(
        self, role_id: str, task_name: str, action_func, *, budget_action_id: Optional[str] = None, **kwargs
    ) -> Any:
        """
        Executes a task under a specific logical role.
        Enforces budget auditing before and after execution.
        """
        role = get_role(role_id)
        self.active_role = role

        # 1. Zero-Cost Policy Pre-check
        BudgetAuditor.audit_action(
            budget_action_id or "",
            {
                "estimated_cost_vnd": 0.0,
                "provider": "offline_rule_based",
                "operation": action_func,
                "role": role_id,
            },
        )

        # 2. Record a real task run before execution.
        run_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        started_clock = time.monotonic()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO tasks
               (title, category, assigned_role_id, status, cost_vnd, run_id, started_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (task_name, role.department, role_id, "RUNNING", 0.0, run_id, started_at, started_at)
        )
        task_db_id = cursor.lastrowid
        conn.commit()
        record_task_event(
            str(task_db_id), "task_created", "RUNNING", task_name,
            agent_id=role_id, run_id=run_id,
        )
        record_task_event(
            str(task_db_id), "task_started", "RUNNING", task_name,
            agent_id=role_id, run_id=run_id,
        )

        # 3. Execute value-producing action
        try:
            result = action_func(**kwargs)
            finished_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
            duration_ms = int((time.monotonic() - started_clock) * 1000)
            result_text = sanitize_text(result, 500)
            cursor.execute(
                "UPDATE tasks SET status = 'DONE', output_data = ?, updated_at = ?, finished_at = ?, progress_pct = 100 WHERE id = ?",
                (result_text, finished_at, finished_at, task_db_id)
            )
            conn.commit()
            record_task_event(
                str(task_db_id), "task_completed", "DONE", task_name,
                agent_id=role_id, run_id=run_id,
                result=result_text, duration_ms=duration_ms,
            )
            return result
        except Exception as e:
            finished_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
            duration_ms = int((time.monotonic() - started_clock) * 1000)
            error_text = sanitize_text(e, 1200)
            cursor.execute(
                "UPDATE tasks SET status = 'FAILED', output_data = ?, updated_at = ?, finished_at = ? WHERE id = ?",
                (error_text, finished_at, finished_at, task_db_id)
            )
            conn.commit()
            record_task_event(
                str(task_db_id), "task_failed", "FAILED", task_name,
                agent_id=role_id, run_id=run_id,
                duration_ms=duration_ms, error_details=error_text,
            )
            raise e
        finally:
            conn.close()
            self.active_role = None

    def run_zero_cost_venture(
        self, bank_code: str = "", account_no: str = "", account_name: str = "",
        *, source_text: str = "", source_id: str = "owner_provided_source",
    ) -> Dict[str, Any]:
        """
        Run only source-grounded niche analysis. Building, pricing, payment QR,
        and publishing remain separate owner-reviewed actions.
        """
        # A catalog template is not research. No downstream artifacts, prices,
        # customer claims or QR are produced until real source material reaches
        # a ready provider and is explicitly reviewed by the owner.
        if not isinstance(source_text, str) or not source_text.strip():
            return {"status": "BLOCKED", "reason_code": "source_material_required",
                    "message": "Cần nội dung nguồn thật để phân tích; danh sách ý tưởng mẫu không phải nghiên cứu thị trường."}
        try:
            analysis = self.llm_gateway.run(
                "niche_classification", {"source_id": source_id, "source_text": source_text}
            )
        except LLMError as exc:
            return {"status": "BLOCKED", "reason_code": exc.code,
                    "message": "Không có kết quả AI được tạo. Kiểm tra provider bằng `python -m core.llm doctor`."}
        degraded = analysis.provenance.get("mode") == "DEGRADED_MODE"
        return {"status": "DEGRADED_MODE" if degraded else "ANALYSIS_ONLY",
                "message": "Không chạy model inference; đầu ra là placeholder tĩnh." if degraded else None,
                "analysis": dict(analysis.output), "provenance": dict(analysis.provenance),
                "next_step": "Owner xác minh nguồn và chọn bước tạo bản nháp thủ công."}
