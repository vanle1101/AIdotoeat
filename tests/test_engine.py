"""
Test Suite for Zero-Cost Corp Engine
Verifies compliance with the 18 ZERO-COST Rules.
"""
import unittest
import sys
import os
import tempfile
import importlib.util
from pathlib import Path
from unittest import mock

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import POLICY
from core.budget_auditor import BudgetAuditor, BudgetViolationError
from core.roles import list_all_roles, get_role
from core.db import init_db, get_connection
from core.orchestrator import ZeroCostOrchestrator
from modules.qr_vault import VietQRVault
from modules.product_builder import ProductBuilder
import core.config as core_config
import core.db as core_db
import core.orchestrator as orchestrator_module
import modules.product_builder as product_builder_module

class TestZeroCostPolicy(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._temporary = tempfile.TemporaryDirectory(prefix="autoprofit-engine-tests-")
        temp_root = Path(cls._temporary.name)
        core_db.DB_PATH = temp_root / "company.db"
        core_config.OUTPUTS_DIR = temp_root / "outputs"
        core_config.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        orchestrator_module.OUTPUTS_DIR = core_config.OUTPUTS_DIR
        product_builder_module.OUTPUTS_DIR = core_config.OUTPUTS_DIR
        os.environ["AUTOPROFIT_BUDGET_KILL_SWITCH"] = "false"

    @classmethod
    def tearDownClass(cls):
        cls._temporary.cleanup()

    def setUp(self):
        init_db()

    def test_01_hardcap_zero_budget(self):
        """Rule 1 & 8: Budget hardcap must be strictly 0 VND."""
        self.assertEqual(POLICY.HARD_BUDGET_CAP_VND, 0.0)
        self.assertFalse(POLICY.ALLOW_PAID_APIS)
        self.assertFalse(POLICY.ALLOW_CREDIT_CARD_INPUT)
        self.assertFalse(POLICY.ALLOW_AUTO_BILLING)

    def test_02_budget_circuit_breaker(self):
        """Rule 10 & 16: Circuit breaker blocks any attempt to incur financial cost."""
        with self.assertRaises(BudgetViolationError):
            BudgetAuditor.audit_action("Buy API Credit", {"estimated_cost_vnd": 50000})

        with self.assertRaises(BudgetViolationError):
            BudgetAuditor.audit_action("Trial requiring Card", {"requires_card": True})

        with self.assertRaises(BudgetViolationError):
            BudgetAuditor.audit_action("Auto-billing subscription", {"auto_billing": True})

        # Zero cost action must pass cleanly
        passed, msg = BudgetAuditor.audit_action(
            "local.file_generation",
            {"estimated_cost_vnd": 0.0, "provider": "offline_rule_based",
             "operation": ProductBuilder.build_chrome_extension},
        )
        self.assertTrue(passed)

    def test_03_fifty_logical_roles_integrity(self):
        """Rule 13: 50 Logical roles registered with 0 persistent RAM footprint."""
        roles = list_all_roles()
        self.assertEqual(len(roles), 50, f"Expected 50 roles, found {len(roles)}")
        
        departments = set(r.department for r in roles)
        self.assertTrue("Executive" in departments)
        self.assertTrue("Research" in departments)
        self.assertTrue("Engineering" in departments)
        self.assertTrue("Marketing" in departments)
        self.assertTrue("Operations" in departments)

    def test_04_vietqr_generation_zero_cost(self):
        """Rule 4 & 5: Offline VietQR code generator executes at zero cost."""
        qr_url = VietQRVault.generate_vietqr_url("MB", "0123456789", "NGUYEN VAN A", 500000, "Demo payment")
        self.assertIn("img.vietqr.io", qr_url)
        self.assertIn("0123456789", qr_url)
        self.assertIn("amount=500000", qr_url)

    def test_05_end_to_end_venture_run(self):
        """Rules 14 & 15: Run actual value-producing cycle without inter-agent chatter."""
        orchestrator = ZeroCostOrchestrator()
        if importlib.util.find_spec("segno") is None:
            def write_test_placeholder(_content, output_path):
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(b"isolated-test-placeholder")
                return output_path
            with mock.patch.object(VietQRVault, "generate_local_qr_png", side_effect=write_test_placeholder):
                result = orchestrator.run_zero_cost_venture(
                    bank_code="TCB", account_no="190367888888", account_name="NGUYEN TEST OWNER"
                )
        else:
            result = orchestrator.run_zero_cost_venture(
                bank_code="TCB", account_no="190367888888", account_name="NGUYEN TEST OWNER"
            )
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["total_budget_spent_vnd"], 0)
        self.assertTrue(Path(result["deliverable_paths"]["chrome_extension"]).exists())
        self.assertTrue(Path(result["deliverable_paths"]["python_scraper"]).exists())
        self.assertTrue(Path(result["deliverable_paths"]["vietqr_image"]).exists())

if __name__ == "__main__":
    unittest.main()
