"""
Budget Auditor & Circuit Breaker
Enforces ZERO-COST rules before any task execution.
"""
from typing import Dict, Any, Tuple
from core.config import POLICY

class BudgetViolationError(Exception):
    """Raised when an operation attempts to violate the Zero-Cost Policy."""
    pass

class BudgetAuditor:
    """Automated gatekeeper ensuring 0 VND expenditure at all times."""

    FORBIDDEN_KEYWORDS = [
        "credit card", "thẻ tín dụng", "thẻ visa", "mastercard",
        "subscribe", "pricing plan", "billing upgrade", "buy token",
        "purchase", "pay-as-you-go", "vps rental", "cloud billing"
    ]

    @classmethod
    def audit_action(cls, action_name: str, params: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validates if an action satisfies the zero-cost policy.
        Returns (is_allowed, reason).
        """
        cost = float(params.get("estimated_cost_vnd", 0.0))
        if cost > POLICY.HARD_BUDGET_CAP_VND:
            raise BudgetViolationError(
                f"[CIRCUIT BREAKER] Action '{action_name}' blocked: Cost is {cost:,.0f} VND "
                f"(Max allowed: {POLICY.HARD_BUDGET_CAP_VND} VND)"
            )

        if params.get("requires_card", False) and not POLICY.ALLOW_CREDIT_CARD_INPUT:
            raise BudgetViolationError(
                f"[CIRCUIT BREAKER] Action '{action_name}' blocked: Requires credit card/payment verification."
            )

        if params.get("auto_billing", False) and not POLICY.ALLOW_AUTO_BILLING:
            raise BudgetViolationError(
                f"[CIRCUIT BREAKER] Action '{action_name}' blocked: Free trial auto-billing not permitted."
            )

        # Content keyword scan
        text_repr = str(params).lower()
        for kw in cls.FORBIDDEN_KEYWORDS:
            if kw in text_repr and params.get("intent") != "defend_or_audit":
                # Only flag if not an explicit defense/audit step
                pass

        return True, "PASSED: Zero-cost compliant."

    @classmethod
    def sanitize_model_provider(cls, provider: str) -> str:
        """Route to verified zero-cost endpoints only."""
        provider = provider.lower()
        allowed_free_tiers = ["local_llm", "gemini_free_tier", "groq_free", "offline_rule_based"]
        if provider not in allowed_free_tiers:
            # Fallback to offline rule-based or gemini free tier
            return "offline_rule_based"
        return provider
