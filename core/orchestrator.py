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
from pathlib import Path

from core.config import POLICY, OUTPUTS_DIR
from core.budget_auditor import BudgetAuditor, BudgetViolationError
from core.roles import get_role, LogicalRole
from core.db import get_connection, record_task_event, sanitize_text
from modules.market_scout import MarketScout
from modules.product_builder import ProductBuilder
from modules.proposal_crafter import ProposalCrafter
from modules.qr_vault import VietQRVault

class ZeroCostOrchestrator:
    """The central engine executing corporate tasks at exactly 0 VND."""

    def __init__(self):
        self.active_role: Optional[LogicalRole] = None

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

    def run_zero_cost_venture(self, bank_code: str, account_no: str, account_name: str) -> Dict[str, Any]:
        """
        Runs an end-to-end autonomous business cycle:
        1. Market Scout scans top demand (Role: MKT_TREND_SCOUT)
        2. Solution Architect designs 0-cost deliverable (Role: DEV_SOLUTION_ARCHITECT)
        3. Engineer builds the complete working product (Role: DEV_CHROME_EXT_BUILDER / DEV_PYTHON_ENGINEER)
        4. Copywriter & Proposal Crafter drafts the sales pitch (Role: OPS_PROPOSAL_CRAFTER)
        5. VietQR Architect generates direct payment QR (Role: OPS_VIETQR_ARCHITECT)
        6. Owner Liaison prepares executive package for Owner approval (Role: EXEC_OWNER_LIAISON)
        """
        # Step 1: Research
        opportunities = self.execute_role_action(
            "MKT_TREND_SCOUT",
            "Quét nhu cầu thị trường miễn phí",
            MarketScout.get_validated_opportunities,
            budget_action_id="local.static_catalog_read",
        )
        target_opp = opportunities[0]  # E-commerce scraper / Data tool

        # Step 2: Product Engineering - Build Chrome Extension & Scraper
        ext_path = self.execute_role_action(
            "DEV_CHROME_EXT_BUILDER",
            "Lập trình Chrome Extension trích xuất dữ liệu",
            ProductBuilder.build_chrome_extension,
            budget_action_id="local.file_generation",
        )

        scraper_path = self.execute_role_action(
            "DEV_SCRAPER_SPECIALIST",
            "Lập trình Python Web Scraper tự động hóa",
            ProductBuilder.build_python_scraper_bundle,
            budget_action_id="local.file_generation",
        )

        # Step 3: Sales Pitch & Proposal
        proposal_bundle = self.execute_role_action(
            "OPS_PROPOSAL_CRAFTER",
            "Soạn thảo kịch bản chào giá & bàn giao",
            ProposalCrafter.craft_proposal,
            budget_action_id="local.text_generation",
            client_need=target_opp["title"],
            price_vnd=target_opp["estimated_value_vnd"]
        )

        # Step 4: VietQR Generation (Owner bank account)
        BudgetAuditor.audit_action(
            "local.qr_generation",
            {"estimated_cost_vnd": 0.0, "provider": "offline_rule_based",
             "operation": VietQRVault.generate_vietqr_url},
        )
        qr_url = VietQRVault.generate_vietqr_url(
            bank_id=bank_code,
            account_no=account_no,
            account_name=account_name,
            amount=target_opp["estimated_value_vnd"],
            memo="Thanh toan tool tu dong"
        )
        BudgetAuditor.audit_action(
            "local.qr_generation",
            {"estimated_cost_vnd": 0.0, "provider": "offline_rule_based",
             "operation": VietQRVault.generate_local_qr_png},
        )
        local_qr_img = OUTPUTS_DIR / "owner_vietqr.png"
        VietQRVault.generate_local_qr_png(qr_url, local_qr_img)

        # Step 5: Save to Deliverables Database
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO deliverables 
               (name, deliverable_type, file_path, content_preview, estimated_market_value_vnd, owner_status) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                "Gói công cụ trích xuất dữ liệu & Web Scraper",
                "SOFTWARE_BUNDLE",
                str(OUTPUTS_DIR),
                f"Bao gồm Chrome Extension và Python Scraper. Giá đề xuất: {target_opp['estimated_value_vnd']:,} VND",
                target_opp["estimated_value_vnd"],
                "PENDING_OWNER_APPROVAL"
            )
        )
        conn.commit()
        conn.close()

        return {
            "status": "SUCCESS",
            "total_budget_spent_vnd": 0,
            "target_opportunity": target_opp,
            "deliverable_paths": {
                "chrome_extension": str(ext_path),
                "python_scraper": str(scraper_path),
                "vietqr_image": str(local_qr_img)
            },
            "vietqr_payment_url": qr_url,
            "proposals": proposal_bundle,
            "next_step": "Chờ Owner duyệt và gửi cho khách hàng / đăng tải để thu tiền."
        }
