"""Fail-closed budget gate for explicitly audited local operations."""
from __future__ import annotations

import math
from typing import Any, Dict, Tuple

from core.config import POLICY


class BudgetViolationError(Exception):
    """Raised when an operation is unknown, unverified, or exceeds policy."""


class BudgetAuditor:
    """Allow only registered local actions with an explicitly zero estimate.

    The registry is the cost/provider authority. A caller's ``0`` estimate by
    itself is not proof that an arbitrary action or provider is free.
    """

    VERIFIED_ZERO_COST_ACTIONS = {
        "local.llm_inference": {
            "core.llm.LLMGateway.run",
        },
        "local.text_generation": {
            "modules.proposal_crafter.ProposalCrafter.craft_proposal",
        },
        "local.file_generation": {
            "modules.product_builder.ProductBuilder.build_chrome_extension",
            "modules.product_builder.ProductBuilder.build_python_scraper_bundle",
        },
        "local.qr_generation": {
            "modules.qr_vault.VietQRVault.generate_vietqr_url",
            "modules.qr_vault.VietQRVault.generate_local_qr_png",
        },
        "local.static_catalog_read": {
            "modules.market_scout.MarketScout.get_validated_opportunities",
        },
    }

    @classmethod
    def audit_action(cls, action_name: str, params: Dict[str, Any]) -> Tuple[bool, str]:
        if POLICY.kill_switch_enabled():
            raise BudgetViolationError("[CIRCUIT BREAKER] Budget kill switch is enabled; action blocked.")

        approved_operations = cls.VERIFIED_ZERO_COST_ACTIONS.get(action_name)
        if approved_operations is None:
            raise BudgetViolationError(f"[CIRCUIT BREAKER] Unknown or unverified action '{action_name}' blocked.")

        operation = params.get("operation")
        operation_module = getattr(operation, "__module__", "")
        operation_name = getattr(operation, "__qualname__", "")
        operation_identity = f"{operation_module}.{operation_name}" if operation_module and operation_name else ""
        if operation_identity not in approved_operations:
            raise BudgetViolationError(f"[CIRCUIT BREAKER] Operation for '{action_name}' is not registered.")

        provider = params.get("provider")
        if provider != POLICY.VERIFIED_LOCAL_PROVIDER:
            raise BudgetViolationError(
                f"[CIRCUIT BREAKER] Provider for '{action_name}' is missing or unverified."
            )

        # The registry, not the caller, is the authority for a known local
        # action's cost. A caller may omit an estimate; if it supplies one, it
        # must agree with the registry's fixed zero-cost policy.
        if "estimated_cost_vnd" in params:
            try:
                cost = float(params["estimated_cost_vnd"])
            except (TypeError, ValueError, OverflowError):
                raise BudgetViolationError(f"[CIRCUIT BREAKER] Cost estimate for '{action_name}' is invalid.")
            if not math.isfinite(cost) or cost != 0.0:
                raise BudgetViolationError(f"[CIRCUIT BREAKER] Cost for '{action_name}' is not verified within budget.")

        if params.get("requires_card") or params.get("auto_billing") or params.get("paid_exposure"):
            raise BudgetViolationError(f"[CIRCUIT BREAKER] Paid exposure detected for '{action_name}'.")

        return True, "PASSED: registered local action with verified zero-cost provider."

    @classmethod
    def sanitize_model_provider(cls, provider: str) -> str:
        """Reject providers without a verified zero-cost guarantee."""
        if provider != POLICY.VERIFIED_LOCAL_PROVIDER:
            raise BudgetViolationError("[CIRCUIT BREAKER] Provider is not verified as zero-cost.")
        return provider

    @classmethod
    def audit_llm_inference(
        cls,
        *,
        provider_name: str,
        operation,
        zero_billing_verified: bool = False,
        request_quota: int | None = None,
    ) -> Tuple[bool, str]:
        """Allow preinstalled local inference or a strictly attested no-bill endpoint.

        An owner configuration attestation is necessary but is not independent
        verification of a provider's terms. The external call is still refused
        unless its quota and no-payment-method assertions are configured.
        """
        if POLICY.kill_switch_enabled():
            raise BudgetViolationError("[CIRCUIT BREAKER] Budget kill switch is enabled; inference blocked.")
        identity = f"{getattr(operation, '__module__', '')}.{getattr(operation, '__qualname__', '')}"
        if identity != "core.llm.LLMGateway.run":
            raise BudgetViolationError("[CIRCUIT BREAKER] LLM call is not registered.")
        if provider_name in {"ollama_local", "llamacpp_local"}:
            return True, "PASSED: already-installed local inference; no provider billing path."
        if provider_name == "degraded_template":
            return True, "DEGRADED_MODE: deterministic template; no model inference."
        if provider_name == "openai_compatible":
            if not zero_billing_verified:
                raise BudgetViolationError("[CIRCUIT BREAKER] Remote billing terms and payment exposure are unverified.")
            if not isinstance(request_quota, int) or isinstance(request_quota, bool) or not 1 <= request_quota <= 1000:
                raise BudgetViolationError("[CIRCUIT BREAKER] Explicit bounded remote request quota is required.")
            return True, "PASSED: owner-attested zero-billing endpoint with bounded quota; terms are not independently verified."
        raise BudgetViolationError("[CIRCUIT BREAKER] Unknown or unverified model provider.")
