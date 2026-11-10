"""Bounded task-specific agents over the durable SQLite task engine.

The 50 rows in :mod:`core.roles` are logical job titles, not model instances.
Handlers are stateless Python functions/classes invoked one at a time with a
small source-cited handoff. All current implementations are explicit
``LOCAL_RULES``; only callers requesting real-model work reach Phase 02's
local-only LLM gateway.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import threading
import time
import uuid
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from pydantic import BaseModel, ConfigDict, Field

from core.roles import ROLES, LogicalRole
from core.skills import duplicate_csv_export_v1, public_evidence_v1


class AgentReadiness(str, Enum):
    READY = "READY"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"


class AgentStatus(str, Enum):
    READY = "READY"
    BLOCKED = "BLOCKED"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"


class AgentBudget(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    max_cost_minor: int = Field(default=0, ge=0, le=0)
    currency: str = "VND"
    max_wall_seconds: int = Field(default=20, ge=1, le=30)
    max_tool_calls: int = Field(default=0, ge=0, le=0)


class AgentSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    role_id: str
    name: str
    department: str
    handler_id: Optional[str]
    readiness: AgentReadiness
    triggers: tuple[str, ...]
    skills: tuple[str, ...]
    tools: tuple[str, ...]
    preconditions: tuple[str, ...]
    budget: AgentBudget
    max_tokens: int = Field(ge=0, le=1024)
    allowed_side_effects: tuple[str, ...]
    success_metrics: tuple[str, ...]
    output_schema: dict[str, Any]


class AgentOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role_id: str
    status: AgentStatus
    readiness: AgentReadiness
    executor_mode: str
    result: dict[str, Any] = Field(default_factory=dict)
    source_ids: list[str] = Field(default_factory=list, max_length=20)
    metrics: dict[str, Any] = Field(default_factory=dict)
    handoff: Optional[dict[str, Any]] = None


class PublicSource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: str = Field(min_length=1, max_length=120)
    uri: str = Field(min_length=1, max_length=500)
    title: str = Field(min_length=1, max_length=240)
    body: str = Field(default="", max_length=6000)
    license: str = Field(min_length=1, max_length=40)
    state: str = Field(default="unknown", max_length=30)
    claims: dict[str, str] = Field(default_factory=dict, max_length=20)


class AgentWorkflowRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    idempotency_key: str = Field(default_factory=lambda: f"agent:{uuid.uuid4()}", min_length=1, max_length=180)
    source: PublicSource
    additional_sources: list[PublicSource] = Field(default_factory=list, max_length=4)
    estimated_cost_vnd: int = Field(default=0, ge=0, le=1_000_000_000)
    requested_side_effects: list[str] = Field(default_factory=list, max_length=8)
    require_llm: bool = False


@dataclass(frozen=True)
class RuntimeLimits:
    max_depth: int = 1
    max_iterations: int = 16
    max_wall_seconds: int = 120
    max_tool_calls: int = 0
    max_tokens_per_run: int = 1024
    max_context_chars: int = 10_000
    default_active_inference_tasks: int = 1


LIMITS = RuntimeLimits()
_INFERENCE_GATE = threading.BoundedSemaphore(LIMITS.default_active_inference_tasks)
_INFERENCE_STATE_LOCK = threading.Lock()
_ACTIVE_INFERENCE_TASKS = 0


# Reuse small handlers; unsupported network/payment integrations remain explicit.
ROLE_HANDLERS: dict[str, Optional[str]] = {
    "EXEC_ORCHESTRATOR": "ExecutiveScheduler",
    "EXEC_ZERO_BUDGET": "ZeroBudgetGuard",
    "EXEC_RISK_COMPLIANCE": "RiskCompliance",
    "EXEC_QA_DIRECTOR": "QAReviewer",
    "EXEC_OWNER_LIAISON": "Copywriter",
    "MKT_TREND_SCOUT": "OpportunityScout",
    "MKT_GIG_PARSER": "OpportunityScout",
    "MKT_COMPETITOR_ANALYST": "EvidenceVerifier",
    "MKT_PAINPOINT_EXTRACTOR": "OpportunityScout",
    "MKT_AUDIENCE_PROFILER": "NicheScorer",
    "MKT_NICHE_EXPLORER": "NicheScorer",
    "MKT_KEYWORD_RESEARCHER": "SEOResearcher",
    "MKT_OFFER_STRATEGIST": "OfferStrategist",
    "MKT_VALUE_DRAFTER": "Copywriter",
    "MKT_SENTIMENT_ANALYZER": "AnalystOptimizer",
    "DEV_SOLUTION_ARCHITECT": "SolutionArchitect",
    "DEV_PYTHON_ENGINEER": "ProductEngineer",
    "DEV_CHROME_EXT_BUILDER": None,
    "DEV_WEB_STATIC_BUILDER": "ProductEngineer",
    "DEV_SCRAPER_SPECIALIST": None,
    "DEV_SQLITE_ARCHITECT": "SolutionArchitect",
    "DEV_PROMPT_ENGINEER": "Copywriter",
    "DEV_CODE_REVIEWER": "QAReviewer",
    "DEV_SECURITY_LINTER": "RiskCompliance",
    "DEV_TEST_RUNNER": "QAReviewer",
    "DEV_DOCS_WRITER": "Copywriter",
    "DEV_ASSET_PACKAGER": "DeliveryOperator",
    "DEV_TELEGRAM_BOT_CRAFTER": None,
    "DEV_EXCEL_CSV_WIZARD": "ProductEngineer",
    "DEV_DEBUGGER": "QAReviewer",
    "MKT_COPYWRITER": "Copywriter",
    "MKT_HEADLINE_SPECIALIST": "Copywriter",
    "MKT_LANDING_COPY_WRITER": "Copywriter",
    "MKT_SOCIAL_POST_CRAFTER": "Copywriter",
    "MKT_PROMPT_PACK_CREATOR": "Copywriter",
    "MKT_CASE_STUDY_WRITER": "Copywriter",
    "MKT_TUTORIAL_CREATOR": "Copywriter",
    "MKT_DISTRIBUTION_PLANNER": "DistributionPlanner",
    "MKT_EMAIL_OUTREACH_CRAFTER": "CRMOperator",
    "MKT_OBJECTION_KILLER": "OfferStrategist",
    "OPS_PROPOSAL_CRAFTER": "Copywriter",
    "OPS_LEAD_QUALIFIER": "NicheScorer",
    "OPS_VIETQR_ARCHITECT": None,
    "OPS_DELIVERY_DISPATCHER": "DeliveryOperator",
    "OPS_PORTFOLIO_CURATOR": "DeliveryOperator",
    "OPS_CUSTOMER_FOLLOWUP": "CRMOperator",
    "OPS_REVENUE_BOOKKEEPER": "PaymentReconciler",
    "OPS_RESOURCE_OPTIMIZER": "AnalystOptimizer",
    "OPS_WORKFLOW_REFINER": "AnalystOptimizer",
    "OPS_OWNER_GATEWAY": "RiskCompliance",
}

if set(ROLE_HANDLERS) != set(ROLES) or len(ROLE_HANDLERS) != 50:
    raise RuntimeError("agent registry must map the unchanged 50 logical roles exactly once")


_ROLE_SKILLS: dict[str, tuple[str, ...]] = {
    "ExecutiveScheduler": ("sequential-handoff@1",),
    "RiskCompliance": ("public-source-policy@1",),
    "ZeroBudgetGuard": ("zero-cost-policy@1",),
    "OpportunityScout": ("github-issue-scope@1",),
    "EvidenceVerifier": ("public-evidence@1",),
    "NicheScorer": ("bounded-rules-score@1",),
    "OfferStrategist": ("draft-only-offer@1",),
    "SolutionArchitect": ("csv-export-architecture@1",),
    "ProductEngineer": ("duplicate-csv-export@1",),
    "QAReviewer": ("duplicate-csv-contract-tests@1",),
    "Copywriter": ("source-cited-copy@1",),
    "SEOResearcher": ("title-keywords@1",),
    "DistributionPlanner": ("manual-channel-plan@1",),
    "CRMOperator": ("draft-only-crm@1",),
    "PaymentReconciler": ("verified-ledger-read@1",),
    "DeliveryOperator": ("draft-manifest@1",),
    "AnalystOptimizer": ("event-metrics@1",),
}


def _spec(role_id: str, role: LogicalRole, handler_id: Optional[str]) -> AgentSpec:
    ready = handler_id is not None
    local_writes = handler_id == "ProductEngineer"
    token_caps = {"NicheScorer": 384, "Copywriter": 768, "OfferStrategist": 384}
    return AgentSpec(
        role_id=role_id, name=role.name, department=role.department, handler_id=handler_id,
        readiness=AgentReadiness.READY if ready else AgentReadiness.NOT_IMPLEMENTED,
        triggers=("explicit_owner_task", "approved_internal_workflow") if ready else ("explicit_owner_task",),
        skills=_ROLE_SKILLS.get(handler_id or "", ()),
        tools=(() if not ready else ("local.sqlite.read", "local.agent_artifact.write") if local_writes
               else ("local.sqlite.read",)),
        preconditions=("source_cited_input", "zero_cost", "bounded_context", "no_unapproved_external_effect"),
        budget=AgentBudget(max_cost_minor=0, max_wall_seconds=30, max_tool_calls=0),
        max_tokens=token_caps.get(handler_id or "", 256),
        allowed_side_effects=("local.persist_source_cited_draft",) if local_writes else (),
        success_metrics=("typed_output_valid", "task_event_recorded", "zero_unapproved_side_effects"),
        output_schema=AgentOutput.model_json_schema(),
    )


AGENT_REGISTRY: dict[str, AgentSpec] = {
    role_id: _spec(role_id, role, ROLE_HANDLERS[role_id]) for role_id, role in ROLES.items()
}

HANDLER_ROLE_IDS = {
    "ExecutiveScheduler": "EXEC_ORCHESTRATOR",
    "RiskCompliance": "EXEC_RISK_COMPLIANCE",
    "ZeroBudgetGuard": "EXEC_ZERO_BUDGET",
    "OpportunityScout": "MKT_TREND_SCOUT",
    "EvidenceVerifier": "MKT_COMPETITOR_ANALYST",
    "NicheScorer": "MKT_NICHE_EXPLORER",
    "OfferStrategist": "MKT_OFFER_STRATEGIST",
    "SolutionArchitect": "DEV_SOLUTION_ARCHITECT",
    "ProductEngineer": "DEV_PYTHON_ENGINEER",
    "QAReviewer": "EXEC_QA_DIRECTOR",
    "Copywriter": "MKT_COPYWRITER",
    "SEOResearcher": "MKT_KEYWORD_RESEARCHER",
    "DistributionPlanner": "MKT_DISTRIBUTION_PLANNER",
    "CRMOperator": "MKT_EMAIL_OUTREACH_CRAFTER",
    "PaymentReconciler": "OPS_REVENUE_BOOKKEEPER",
    "DeliveryOperator": "OPS_DELIVERY_DISPATCHER",
    "AnalystOptimizer": "OPS_RESOURCE_OPTIMIZER",
}

DEFAULT_PIPELINE = (
    ("EXEC_ORCHESTRATOR", "Prepare bounded sequential agent handoffs"),
    ("EXEC_RISK_COMPLIANCE", "Check public-source permission and side-effect scope"),
    ("EXEC_ZERO_BUDGET", "Verify zero-cash execution limits"),
    ("MKT_TREND_SCOUT", "Extract the public problem and acceptance criteria"),
    ("MKT_COMPETITOR_ANALYST", "Verify cited evidence and check contradictions"),
    ("MKT_NICHE_EXPLORER", "Score evidence strength with deterministic rules"),
    ("MKT_OFFER_STRATEGIST", "Draft a bounded, unpriced offer"),
    ("DEV_SOLUTION_ARCHITECT", "Design a local-only CSV export solution"),
    ("DEV_PYTHON_ENGINEER", "Build a source-cited draft deliverable"),
    ("EXEC_QA_DIRECTOR", "Run bounded contract checks against the draft"),
    ("MKT_COPYWRITER", "Prepare factual, source-cited draft copy"),
    ("MKT_KEYWORD_RESEARCHER", "Extract title terms without claiming search volume"),
    ("MKT_DISTRIBUTION_PLANNER", "Prepare a manual-only distribution plan"),
    ("OPS_DELIVERY_DISPATCHER", "Prepare an owner-reviewed delivery manifest"),
)


class ExecutiveScheduler:
    @staticmethod
    def run(ctx: Mapping[str, Any]) -> dict[str, Any]:
        request = ctx["request"]
        if len(DEFAULT_PIPELINE) > LIMITS.max_iterations:
            return {"status": "BLOCKED", "reason_code": "iteration_limit_exceeded"}
        if request.get("require_llm"):
            try:
                _local_model_router()
            except Exception as exc:
                return {"status": "BLOCKED", "reason_code": getattr(exc, "code", "local_llm_unavailable")}
            if _budget_kill_switch_enabled():
                return {"status": "BLOCKED", "reason_code": "llm_budget_kill_switch_enabled"}
        return {"status": "READY", "workflow": "public_problem_to_tested_draft",
                "step_count": len(DEFAULT_PIPELINE), "max_depth": LIMITS.max_depth,
                "max_iterations": LIMITS.max_iterations, "max_wall_seconds": LIMITS.max_wall_seconds,
                "max_tools": LIMITS.max_tool_calls, "executor_mode": "LOCAL_RULES",
                "require_llm": bool(request.get("require_llm"))}


class RiskCompliance:
    @staticmethod
    def run(ctx: Mapping[str, Any]) -> dict[str, Any]:
        request = ctx["request"]
        sources = [request["source"], *request.get("additional_sources", [])]
        evidence = public_evidence_v1.verify_sources(sources)
        if evidence["status"] != "READY":
            return {"status": "BLOCKED", "reason_code": evidence["reason_code"],
                    "source_validation": {k: v for k, v in evidence.items() if k != "verified_sources"}}
        requested = sorted(set(request.get("requested_side_effects", [])))
        if requested:
            known = {"external.publish", "external.contact", "external.payment", "external.fulfill", "external.purchase"}
            unknown = sorted(set(requested) - known)
            if unknown:
                return {"status": "BLOCKED", "reason_code": "unknown_side_effect_requested",
                        "requested_side_effects": unknown}
            if ctx.get("approval_decision") == "owner_approved":
                return {"status": "BLOCKED", "reason_code": "side_effect_executor_not_implemented",
                        "requested_side_effects": requested, "approved": True,
                        "action_executed": False}
            return {"status": "WAITING_APPROVAL", "reason_code": "owner_approval_required",
                    "requested_side_effects": requested,
                    "handoff": {"target": "owner", "task_decision_required": True,
                                "executor_available": False, "action_executed": False}}
        return {"status": "READY", "source_count": len(sources),
                "policy": "public_read_only_source_snapshot", "external_actions": "disabled"}


class ZeroBudgetGuard:
    @staticmethod
    def run(ctx: Mapping[str, Any]) -> dict[str, Any]:
        request = ctx["request"]
        amount = request.get("estimated_cost_vnd", 0)
        if amount != 0:
            return {"status": "BLOCKED", "reason_code": "nonzero_budget_forbidden",
                    "estimated_cost_vnd": amount}
        if LIMITS.max_tool_calls != 0:
            return {"status": "BLOCKED", "reason_code": "tool_budget_misconfigured"}
        return {"status": "READY", "estimated_cost_vnd": 0,
                "actual_provider_cost_vnd": 0, "inference_requested": bool(request.get("require_llm")),
                "tool_calls_allowed": 0}


class OpportunityScout:
    @staticmethod
    def run(ctx: Mapping[str, Any]) -> dict[str, Any]:
        source = ctx["request"]["source"]
        text = source["body"]
        scope_match = re.search(r"(?im)^\s*Scope\s*:\s*(.+?)(?=\s+Done when\s*:|\n|$)", text)
        done_match = re.search(r"(?im)Done when\s*:\s*(.+?)(?=\n|$)", text)
        scope = scope_match.group(1).strip() if scope_match else source["title"].strip()
        acceptance = done_match.group(1).strip() if done_match else "Owner verifies the requested outcome before use."
        # The source can ask a person to claim/contact the issue. Keep only
        # product acceptance data in downstream handoffs.
        acceptance = re.split(r"(?i)\bplease\s+(?:comment|claim|contact|submit)\b|\bclaim\s+this\s+issue\b",
                              acceptance, maxsplit=1)[0].strip().rstrip(".,;")
        if not acceptance:
            acceptance = "Owner verifies the requested outcome before use."
        return {"status": "READY", "opportunity_id": source["source_id"],
                "title": source["title"], "problem_statement": scope,
                "acceptance_criteria": acceptance, "source_uri": source["uri"],
                "source_license": source["license"], "evidence_status": "UNVERIFIED_UNTIL_EVIDENCE_STEP"}


class EvidenceVerifier:
    @staticmethod
    def run(ctx: Mapping[str, Any]) -> dict[str, Any]:
        request = ctx["request"]
        sources = [request["source"], *request.get("additional_sources", [])]
        verification = public_evidence_v1.verify_sources(sources)
        if verification["status"] != "READY":
            return {"status": "BLOCKED", "reason_code": verification["reason_code"],
                    "conflicting_claims": verification.get("conflicting_claims", [])}
        return {"status": "READY", "verified_sources": verification["verified_quotes"],
                "verified_facts": [f"Public issue asks: {source['title']}" for source in verification["verified_sources"]],
                "contradictions": 0,
                "verification_scope": "canonical_github_url_shape_and_owner_asserted_allowlisted_license"}


class NicheScorer:
    @staticmethod
    def run(ctx: Mapping[str, Any]) -> dict[str, Any]:
        request = ctx["request"]
        opportunity = _prior_result(ctx, "MKT_TREND_SCOUT")
        evidence = _prior_result(ctx, "MKT_COMPETITOR_ANALYST")
        if not opportunity or not evidence:
            return {"status": "BLOCKED", "reason_code": "verified_opportunity_handoff_missing"}
        if request.get("require_llm"):
            try:
                with _inference_slot():
                    from core.llm import LLMGateway
                    gateway = _local_model_router()
                    output = LLMGateway(router=gateway).run(
                        "niche_classification",
                        {"source_id": request["source"]["source_id"],
                         "source_text": f"{opportunity['title']}\n{opportunity['problem_statement']}\n{opportunity['acceptance_criteria']}"},
                        trace_id=str(ctx.get("trace_id") or ""), use_cache=False,
                        max_output_tokens=int(ctx.get("max_tokens", 384)),
                    )
                return {"status": "READY", "mode": "MODEL_INFERENCE",
                        "classification": dict(output.output), "provenance": dict(output.provenance)}
            except Exception as exc:
                return {"status": "BLOCKED", "reason_code": getattr(exc, "code", "llm_inference_unavailable")}
        score = 0
        rationale = []
        if opportunity.get("acceptance_criteria"):
            score += 25
            rationale.append("explicit acceptance criteria")
        if evidence.get("verified_sources"):
            score += 30
            rationale.append("source snapshot provided and citation validated")
        if "csv" in opportunity.get("title", "").lower():
            score += 20
            rationale.append("bounded data-export scope")
        if opportunity.get("source_license") in public_evidence_v1.ALLOWED_LICENSES:
            score += 15
            rationale.append("declared SPDX license is on the allowlist")
        return {"status": "READY", "mode": "LOCAL_RULES", "score": min(score, 100),
                "score_label": "deterministic evidence-strength score; not demand or revenue",
                "rationale": rationale, "source_ids": [request["source"]["source_id"]]}


class OfferStrategist:
    @staticmethod
    def run(ctx: Mapping[str, Any]) -> dict[str, Any]:
        opportunity = _prior_result(ctx, "MKT_TREND_SCOUT")
        evidence = _prior_result(ctx, "MKT_COMPETITOR_ANALYST")
        if not opportunity or not evidence:
            return {"status": "BLOCKED", "reason_code": "verified_opportunity_handoff_missing"}
        return {"status": "READY", "offer_type": "LOCAL_DRAFT_PROTOTYPE",
                "scope": opportunity["problem_statement"],
                "acceptance_criteria": opportunity["acceptance_criteria"],
                "price_vnd": None, "delivery_time": None,
                "verified_facts": evidence["verified_facts"],
                "owner_review_required": True}


class SolutionArchitect:
    @staticmethod
    def run(ctx: Mapping[str, Any]) -> dict[str, Any]:
        opportunity = _prior_result(ctx, "MKT_TREND_SCOUT")
        evidence = _prior_result(ctx, "MKT_COMPETITOR_ANALYST")
        if not opportunity or not evidence or not evidence.get("verified_sources"):
            return {"status": "BLOCKED", "reason_code": "verified_evidence_required"}
        text = f"{opportunity['title']} {opportunity['problem_statement']}".lower()
        if "csv" not in text or "duplicate" not in text:
            return {"status": "NOT_IMPLEMENTED", "reason_code": "draft_template_not_supported"}
        return {"status": "READY", "deliverable_kind": "csv_duplicate_export",
                "skill_version": duplicate_csv_export_v1.SKILL_ID,
                "inputs": ["JSON file with a duplicates array"],
                "outputs": ["UTF-8 CSV columns file_a,file_b,reason"],
                "dependencies": ["Python standard library"], "network": False,
                "acceptance_criteria": opportunity["acceptance_criteria"],
                "source_ids": [ctx["request"]["source"]["source_id"]]}


class ProductEngineer:
    @staticmethod
    def run(ctx: Mapping[str, Any]) -> dict[str, Any]:
        architecture = _prior_result(ctx, "DEV_SOLUTION_ARCHITECT")
        if not architecture or architecture.get("deliverable_kind") != "csv_duplicate_export":
            return {"status": "NOT_IMPLEMENTED", "reason_code": "supported_architecture_required"}
        module_path = Path(duplicate_csv_export_v1.__file__).resolve()
        content = module_path.read_text(encoding="utf-8")
        if len(content.encode("utf-8")) > 20_000:
            return {"status": "BLOCKED", "reason_code": "skill_size_limit_exceeded"}
        from core.agent_runtime import _engine
        saved = _engine().save_agent_artifact(
            run_id=ctx["run_id"], task_id=ctx["task_id"], role_id=ctx["role_id"],
            title="Duplicate pairs CSV exporter draft", artifact_type="PYTHON_SOURCE",
            mime_type="text/x-python", content=content,
            source_ids=[ctx["request"]["source"]["source_id"]], path=ctx.get("db_path"),
        )
        return {"status": "READY", "artifact_id": saved["id"],
                "content_sha256": saved["content_sha256"], "artifact_type": saved["artifact_type"],
                "title": saved["title"], "skill_version": duplicate_csv_export_v1.SKILL_ID,
                "source_ids": saved["source_ids"], "artifact_uri": f"db://agent_artifacts/{saved['id']}"}


class QAReviewer:
    @staticmethod
    def run(ctx: Mapping[str, Any]) -> dict[str, Any]:
        product = _prior_result(ctx, "DEV_PYTHON_ENGINEER")
        if not product or not product.get("artifact_id"):
            return {"status": "BLOCKED", "reason_code": "draft_artifact_missing"}
        from core.agent_runtime import _engine
        artifact = _engine().get_agent_artifact(product["artifact_id"], path=ctx.get("db_path"))
        expected = Path(duplicate_csv_export_v1.__file__).read_text(encoding="utf-8")
        if not artifact or hashlib.sha256(artifact["content"].encode("utf-8")).hexdigest() != product["content_sha256"]:
            return {"status": "BLOCKED", "reason_code": "artifact_hash_mismatch"}
        if artifact["content"] != expected:
            return {"status": "BLOCKED", "reason_code": "artifact_not_from_approved_skill"}
        contract = duplicate_csv_export_v1.run_contract_tests()
        if not contract["passed"]:
            return {"status": "BLOCKED", "reason_code": "draft_contract_tests_failed", "checks": contract["checks"]}
        return {"status": "READY", "artifact_id": artifact["id"], "content_sha256": artifact["content_sha256"],
                "test_status": "PASS", "checks": contract["checks"], "tested_skill": duplicate_csv_export_v1.SKILL_ID}


class Copywriter:
    @staticmethod
    def run(ctx: Mapping[str, Any]) -> dict[str, Any]:
        opportunity = _prior_result(ctx, "MKT_TREND_SCOUT")
        evidence = _prior_result(ctx, "MKT_COMPETITOR_ANALYST")
        if not opportunity or not evidence:
            return {"status": "BLOCKED", "reason_code": "verified_evidence_required"}
        facts = evidence.get("verified_facts", [])
        if ctx["request"].get("require_llm"):
            try:
                with _inference_slot():
                    from core.llm import LLMGateway
                    output = LLMGateway(router=_local_model_router()).run(
                        "proposal_personalization",
                        {"customer_need": opportunity["problem_statement"], "verified_facts": facts},
                        trace_id=str(ctx.get("trace_id") or ""), use_cache=False,
                        max_output_tokens=int(ctx.get("max_tokens", 768)),
                    )
                return {"status": "READY", "mode": "MODEL_INFERENCE", "draft": dict(output.output),
                        "provenance": dict(output.provenance), "publish_allowed": False}
            except Exception as exc:
                return {"status": "BLOCKED", "reason_code": getattr(exc, "code", "llm_inference_unavailable")}
        return {"status": "READY", "mode": "LOCAL_RULES", "title": opportunity["title"],
                "draft": f"Draft prototype: {opportunity['problem_statement']}. Scope and completion checks: {opportunity['acceptance_criteria']}",
                "verified_facts": facts, "source_uri": opportunity["source_uri"],
                "price_vnd": None, "publish_allowed": False, "requires_owner_review": True}


class SEOResearcher:
    @staticmethod
    def run(ctx: Mapping[str, Any]) -> dict[str, Any]:
        source = ctx["request"]["source"]
        words = re.findall(r"[A-Za-z0-9À-ỹ]+", source["title"].lower())
        terms = list(dict.fromkeys(word for word in words if len(word) > 2))[:12]
        return {"status": "READY", "candidate_terms": terms,
                "search_volume": None, "volume_status": "not_measured",
                "source_uri": source["uri"]}


class DistributionPlanner:
    @staticmethod
    def run(ctx: Mapping[str, Any]) -> dict[str, Any]:
        opportunity = _prior_result(ctx, "MKT_TREND_SCOUT")
        if not opportunity:
            return {"status": "BLOCKED", "reason_code": "opportunity_handoff_missing"}
        return {"status": "READY", "channels_for_owner_review": ["project issue tracker", "documentation page"],
                "publication_action": "NONE", "outreach_action": "NONE",
                "requires_owner_approval": True, "claim_was_submitted": False}


class CRMOperator:
    @staticmethod
    def run(ctx: Mapping[str, Any]) -> dict[str, Any]:
        request = ctx["request"]
        if request.get("requested_side_effects"):
            return {"status": "WAITING_APPROVAL", "reason_code": "owner_approval_required",
                    "send_message": False, "handoff": {"target": "owner", "action_executed": False}}
        return {"status": "READY", "message_draft": "No customer contact was provided; no message was drafted or sent.",
                "recipient": None, "send_message": False, "status_label": "DRAFT_ONLY"}


class PaymentReconciler:
    @staticmethod
    def run(ctx: Mapping[str, Any]) -> dict[str, Any]:
        from core.agent_runtime import _engine
        conn = _engine().connect(ctx.get("db_path"))
        try:
            claims = {str(row["status"]): int(row["count"]) for row in conn.execute(
                "SELECT status,COUNT(*) AS count FROM payment_claims GROUP BY status")}
            verified = int(conn.execute("SELECT COUNT(*) FROM verified_transactions").fetchone()[0])
            orphaned = int(conn.execute(
                """SELECT COUNT(*) FROM verified_transactions t
                   WHERE t.source LIKE 'payment_report:%'
                     AND NOT EXISTS (SELECT 1 FROM payment_claims c
                                     WHERE c.id=substr(t.source,16) AND c.status='PAID_VERIFIED')"""
            ).fetchone()[0])
        except Exception as exc:
            return {"status": "BLOCKED", "reason_code": "payment_ledger_unavailable",
                    "error_type": type(exc).__name__, "claims_mutated": False}
        finally:
            conn.close()
        return {"status": "READY", "source": "canonical_verified_transactions",
                "payment_claim_counts_by_status": claims,
                "verified_transaction_count": verified, "orphaned_payment_report_transactions": orphaned,
                "claims_mutated": False,
                "owner_confirmation_substituted": False}


class DeliveryOperator:
    @staticmethod
    def run(ctx: Mapping[str, Any]) -> dict[str, Any]:
        product = _prior_result(ctx, "DEV_PYTHON_ENGINEER")
        qa = _prior_result(ctx, "EXEC_QA_DIRECTOR")
        if not product or not qa or qa.get("test_status") != "PASS":
            return {"status": "BLOCKED", "reason_code": "qa_pass_required_before_delivery"}
        return {"status": "READY", "artifact_id": product["artifact_id"],
                "artifact_uri": product["artifact_uri"], "quality_status": "PASS",
                "delivery_status": "READY_FOR_OWNER_REVIEW", "delivered": False,
                "requires_owner_approval": True}


class AnalystOptimizer:
    @staticmethod
    def run(ctx: Mapping[str, Any]) -> dict[str, Any]:
        previous = ctx.get("prior", {})
        qa = previous.get("EXEC_QA_DIRECTOR", {}).get("result", {})
        score = previous.get("MKT_NICHE_EXPLORER", {}).get("result", {})
        return {"status": "READY", "measured_workflow_steps": len(previous),
                "quality_pass": qa.get("test_status") == "PASS",
                "evidence_score": score.get("score"),
                "success_metrics": "observed_task_events_only",
                "recommendation": "Manual owner review before any external publication or delivery."}


HANDLERS = {
    cls.__name__: cls for cls in (ExecutiveScheduler, RiskCompliance, ZeroBudgetGuard,
        OpportunityScout, EvidenceVerifier, NicheScorer, OfferStrategist, SolutionArchitect,
        ProductEngineer, QAReviewer, Copywriter, SEOResearcher, DistributionPlanner,
        CRMOperator, PaymentReconciler, DeliveryOperator, AnalystOptimizer)
}

_HANDLER_CAPABILITIES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "ProductEngineer": (("local.sqlite.read", "local.agent_artifact.write"),
                         ("local.persist_source_cited_draft",)),
}


def _engine():
    backend_dir = str(Path(__file__).resolve().parent.parent / "backend")
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    import business_engine
    return business_engine


def _budget_kill_switch_enabled() -> bool:
    return os.getenv("AUTOPROFIT_BUDGET_KILL_SWITCH", "true").strip().lower() not in {"0", "false", "no", "off"}


def _local_model_router():
    """Select only an installed loopback model; remote endpoints are never probed."""
    from core.llm import LLMConfig, ModelRouter, ProviderUnavailable
    base = LLMConfig.from_env()
    failures = []
    for provider_name in ("ollama", "llamacpp"):
        router = ModelRouter(config=replace(base, provider=provider_name))
        try:
            router.select(health_check=True)
            return router
        except Exception as exc:
            failures.append(getattr(exc, "code", provider_name + "_unavailable"))
    raise ProviderUnavailable(failures[0] if failures else "local_model_unavailable", "No ready local model is installed")


def _prior_result(ctx: Mapping[str, Any], role_id: str) -> dict[str, Any]:
    item = ctx.get("prior", {}).get(role_id, {})
    result = item.get("result", {}) if isinstance(item, Mapping) else {}
    return result if isinstance(result, dict) else {}


_HANDOFF_DEPENDENCIES: dict[str, tuple[str, ...]] = {
    "MKT_NICHE_EXPLORER": ("MKT_TREND_SCOUT", "MKT_COMPETITOR_ANALYST"),
    "MKT_OFFER_STRATEGIST": ("MKT_TREND_SCOUT", "MKT_COMPETITOR_ANALYST"),
    "DEV_SOLUTION_ARCHITECT": ("MKT_TREND_SCOUT", "MKT_COMPETITOR_ANALYST"),
    "DEV_PYTHON_ENGINEER": ("DEV_SOLUTION_ARCHITECT",),
    "EXEC_QA_DIRECTOR": ("DEV_PYTHON_ENGINEER",),
    "MKT_COPYWRITER": ("MKT_TREND_SCOUT", "MKT_COMPETITOR_ANALYST"),
    "MKT_DISTRIBUTION_PLANNER": ("MKT_TREND_SCOUT",),
    "OPS_DELIVERY_DISPATCHER": ("DEV_PYTHON_ENGINEER", "EXEC_QA_DIRECTOR"),
}


def agent_registry() -> list[dict[str, Any]]:
    return [spec.model_dump(mode="json") for spec in AGENT_REGISTRY.values()]


def runtime_profile() -> dict[str, Any]:
    try:
        from core.llm import hardware_report
        hardware = hardware_report()
    except Exception:
        hardware = {"verified": False, "logical_cpus": None, "available_ram_bytes": None}
    # Agent inference is single-slot by default; this host's low free RAM never raises it.
    cpu_count = hardware.get("logical_cpus")
    ram_available = hardware.get("available_ram_bytes")
    measured_capacity = min(
        max(1, min(4, int(cpu_count or 1) // 2)),
        max(1, min(4, int(ram_available or 0) // (6 * 1024**3))) if ram_available else 1,
    )
    active_cap = max(1, min(LIMITS.default_active_inference_tasks, measured_capacity))
    return {"mode": "LOCAL_RULES", "logical_roles": len(AGENT_REGISTRY),
            "ready_handlers": sum(1 for spec in AGENT_REGISTRY.values() if spec.readiness is AgentReadiness.READY),
            "not_implemented": sum(1 for spec in AGENT_REGISTRY.values() if spec.readiness is AgentReadiness.NOT_IMPLEMENTED),
            "max_active_inference_tasks": active_cap,
            "concurrency_cap_basis": {"logical_cpus": cpu_count, "available_ram_bytes": ram_available,
                                      "measured_capacity": measured_capacity, "default_cap": LIMITS.default_active_inference_tasks},
            "max_workflow_depth": LIMITS.max_depth, "max_iterations": LIMITS.max_iterations,
            "max_wall_seconds": LIMITS.max_wall_seconds, "max_tool_calls": LIMITS.max_tool_calls,
            "actual_inference_tasks_active": _active_inference_count(), "hardware": hardware}


def _run_payload(task: Mapping[str, Any], path: Optional[str | Path] = None) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    engine = _engine()
    conn = engine.connect(path)
    try:
        run = conn.execute("SELECT * FROM agent_runs WHERE id=?", (task["run_id"],)).fetchone()
        if not run:
            raise ValueError("agent_run_missing")
        request = json.loads(run["payload_json"])
        # Carry only the explicit predecessors needed by this handler. This
        # keeps each task context small without losing older dependencies.
        role_id = str(task.get("assigned_role_id") or "")
        dependencies = _HANDOFF_DEPENDENCIES.get(role_id, ())
        if dependencies:
            marks = ",".join("?" for _ in dependencies)
            prior_rows = conn.execute(
                f"SELECT assigned_role_id,result_json FROM tasks WHERE run_id=? AND id<? AND state='DONE' AND assigned_role_id IN ({marks}) ORDER BY id",
                (task["run_id"], task["id"], *dependencies),
            ).fetchall()
        else:
            prior_rows = []
        prior = {}
        for row in reversed(prior_rows):
            try:
                prior[row["assigned_role_id"]] = json.loads(row["result_json"] or "{}")
            except (TypeError, json.JSONDecodeError):
                continue
        return dict(run), request, prior
    finally:
        conn.close()


def _reserved_run_tokens(run_id: str, *, path: Optional[str | Path] = None) -> int:
    conn = _engine().connect(path)
    try:
        rows = conn.execute("SELECT result_json FROM tasks WHERE run_id=? AND state='DONE'", (run_id,)).fetchall()
    finally:
        conn.close()
    reserved = 0
    for row in rows:
        item = _engine()._loads(row["result_json"], {})
        metrics = item.get("metrics", {}) if isinstance(item, dict) else {}
        try:
            reserved += max(0, int(metrics.get("output_budget_reserved", 0)))
        except (TypeError, ValueError):
            continue
    return reserved


def execute_agent_task(task: Mapping[str, Any], *, path: Optional[str | Path] = None) -> dict[str, Any]:
    started = time.monotonic()
    role_id = str(task.get("assigned_role_id") or "")
    spec = AGENT_REGISTRY.get(role_id)
    source_ids = []
    try:
        run, request, prior = _run_payload(task, path)
        source = request.get("source", {})
        source_ids = [str(source.get("source_id", ""))] if source.get("source_id") else []
        conn = _engine().connect(path)
        try:
            total_tasks = int(conn.execute("SELECT COUNT(*) FROM tasks WHERE run_id=?", (task["run_id"],)).fetchone()[0])
        finally:
            conn.close()
        if total_tasks > LIMITS.max_iterations:
            return AgentOutput(role_id=role_id, status=AgentStatus.BLOCKED,
                               readiness=spec.readiness if spec else AgentReadiness.NOT_IMPLEMENTED,
                               executor_mode="LOCAL_RULES", source_ids=source_ids,
                               result={"reason_code": "iteration_limit_exceeded"}).model_dump(mode="json")
        if not spec or not spec.handler_id or spec.readiness is AgentReadiness.NOT_IMPLEMENTED:
            return AgentOutput(role_id=role_id, status=AgentStatus.NOT_IMPLEMENTED,
                               readiness=AgentReadiness.NOT_IMPLEMENTED, executor_mode="LOCAL_RULES",
                               source_ids=source_ids, result={"reason_code": "handler_not_implemented"}).model_dump(mode="json")
        task_payload = json.loads(task.get("payload_json") or "{}")
        if int(task_payload.get("depth", 0)) > LIMITS.max_depth:
            return AgentOutput(role_id=role_id, status=AgentStatus.BLOCKED, readiness=spec.readiness,
                               executor_mode="LOCAL_RULES", source_ids=source_ids,
                               result={"reason_code": "agent_depth_limit_exceeded"}).model_dump(mode="json")
        elapsed_run = (_engine().utc_now() - _engine().parse_time(run["created_at"])).total_seconds()
        if elapsed_run > LIMITS.max_wall_seconds:
            return AgentOutput(role_id=role_id, status=AgentStatus.BLOCKED, readiness=spec.readiness,
                               executor_mode="LOCAL_RULES", source_ids=source_ids,
                               result={"reason_code": "workflow_wall_time_exceeded"}).model_dump(mode="json")
        if int(task.get("timeout_seconds") or spec.budget.max_wall_seconds) > spec.budget.max_wall_seconds:
            return AgentOutput(role_id=role_id, status=AgentStatus.BLOCKED, readiness=spec.readiness,
                               executor_mode="LOCAL_RULES", source_ids=source_ids,
                               result={"reason_code": "agent_step_timeout_limit_exceeded"}).model_dump(mode="json")
        required_tools, required_effects = _HANDLER_CAPABILITIES.get(spec.handler_id, ((), ()))
        if (not set(required_tools).issubset(spec.tools)
                or not set(required_effects).issubset(spec.allowed_side_effects)):
            return AgentOutput(role_id=role_id, status=AgentStatus.BLOCKED, readiness=spec.readiness,
                               executor_mode="LOCAL_RULES", source_ids=source_ids,
                               result={"reason_code": "handler_capability_not_granted"}).model_dump(mode="json")
        max_tokens = spec.max_tokens
        reserve_tokens = 0
        if request.get("require_llm") and spec.handler_id in {"NicheScorer", "Copywriter"}:
            remaining = LIMITS.max_tokens_per_run - _reserved_run_tokens(str(task["run_id"]), path=path)
            if remaining <= 0:
                return AgentOutput(role_id=role_id, status=AgentStatus.BLOCKED, readiness=spec.readiness,
                                   executor_mode="LOCAL_RULES", source_ids=source_ids,
                                   result={"reason_code": "run_token_budget_exhausted"}).model_dump(mode="json")
            reserve_tokens = min(spec.max_tokens, remaining)
            max_tokens = reserve_tokens
        context = {"role_id": role_id, "run_id": task["run_id"], "task_id": int(task["id"]),
                   "request": request, "prior": prior, "db_path": str(path) if path is not None else None,
                   "approval_decision": task.get("last_error"), "trace_id": task.get("trace_id"),
                   "max_tokens": max_tokens}
        if len(json.dumps(context, ensure_ascii=False)) > LIMITS.max_context_chars:
            return AgentOutput(role_id=role_id, status=AgentStatus.BLOCKED, readiness=spec.readiness,
                               executor_mode="LOCAL_RULES", source_ids=source_ids,
                               result={"reason_code": "handoff_context_limit_exceeded"}).model_dump(mode="json")
        handler = HANDLERS[spec.handler_id]
        result = handler.run(context)
        status = AgentStatus(result.get("status", "READY"))
        if status is AgentStatus.READY and role_id == "MKT_COMPETITOR_ANALYST":
            for source in [request["source"], *request.get("additional_sources", [])]:
                facts = [quote["quote"] for quote in result.get("verified_sources", [])
                         if quote["source_id"] == source["source_id"]]
                for fact in facts:
                    _engine().save_agent_memory(
                        run_id=task["run_id"], namespace="public_problem_evidence",
                        source_id=source["source_id"], source_uri=source["uri"],
                        source_sha256=public_evidence_v1.validate_source(source)["sha256"], fact=fact,
                        ttl_days=30, path=path,
                    )
        output = AgentOutput(role_id=role_id, status=status, readiness=spec.readiness,
                             executor_mode=result.get("mode", "LOCAL_RULES"), result=result,
                             source_ids=source_ids,
                             metrics={"duration_ms": int((time.monotonic() - started) * 1000),
                                      "inference_mode": "model" if result.get("mode") == "MODEL_INFERENCE" else "none",
                                      "usage_source": "canonical_llm_usage_ledger" if result.get("mode") == "MODEL_INFERENCE" else "none",
                                      "output_budget_reserved": reserve_tokens if result.get("mode") == "MODEL_INFERENCE" else 0},
                             handoff=result.get("handoff"))
        return output.model_dump(mode="json")
    except Exception as exc:
        return AgentOutput(role_id=role_id, status=AgentStatus.BLOCKED,
                           readiness=spec.readiness if spec else AgentReadiness.NOT_IMPLEMENTED,
                           executor_mode="LOCAL_RULES", source_ids=source_ids,
                           result={"reason_code": "agent_execution_error",
                                   "error_type": type(exc).__name__},
                           metrics={"duration_ms": int((time.monotonic() - started) * 1000)}).model_dump(mode="json")


def start_public_problem_workflow(request: AgentWorkflowRequest | Mapping[str, Any], *,
                                  role_ids: Sequence[str] | None = None,
                                  path: Optional[str | Path] = None) -> dict[str, Any]:
    parsed = request if isinstance(request, AgentWorkflowRequest) else AgentWorkflowRequest.model_validate(request)
    sources = [parsed.source, *parsed.additional_sources]
    if parsed.estimated_cost_vnd != 0:
        raise ValueError("agent workflows reject nonzero cash exposure before enqueue")
    # Validate before creating any task; source body is data and never selects tools.
    for source in sources:
        public_evidence_v1.validate_source(source.model_dump(mode="json"))
    roles = tuple(role_ids or [role for role, _ in DEFAULT_PIPELINE])
    if len(roles) > LIMITS.max_iterations or len(set(roles)) != len(roles):
        raise ValueError("agent pipeline exceeds iteration limit or repeats a role")
    for role_id in roles:
        spec = AGENT_REGISTRY.get(role_id)
        if not spec:
            raise ValueError("unknown logical role id")
        if spec.readiness is AgentReadiness.NOT_IMPLEMENTED:
            raise ValueError(f"role readiness is NOT_IMPLEMENTED: {role_id}")
    if parsed.requested_side_effects and "EXEC_RISK_COMPLIANCE" not in roles:
        raise ValueError("side-effect requests require the RiskCompliance handoff")
    request_data = parsed.model_dump(mode="json")
    steps_by_role = {role: title for role, title in DEFAULT_PIPELINE}
    steps = [{"role_id": role, "title": steps_by_role.get(role, f"Run {role} task-specific handler")} for role in roles]
    input_chars = sum(len(source.title) + len(source.body) for source in sources)
    if input_chars > 6000:
        raise ValueError("combined public source snapshots exceed the workflow input limit")
    return _engine().start_agent_workflow(idempotency_key=parsed.idempotency_key,
                                          payload=request_data, steps=steps, path=path)


def run_public_problem_to_completion(request: AgentWorkflowRequest | Mapping[str, Any], *,
                                     worker_id: str = "phase03-e2e", max_steps: int = LIMITS.max_iterations,
                                     role_ids: Sequence[str] | None = None,
                                     path: Optional[str | Path] = None) -> dict[str, Any]:
    """Run a deterministic local pipeline synchronously for tests/CLI diagnostics."""
    engine = _engine()
    run = start_public_problem_workflow(request, role_ids=role_ids, path=path)
    run_id = str(run["id"])
    start = time.monotonic()
    outcomes = []
    for _ in range(max_steps):
        if time.monotonic() - start > LIMITS.max_wall_seconds:
            raise TimeoutError("agent workflow wall-time budget exceeded")
        outcome = engine.run_worker_once(worker_id, path=path, run_id=run_id)
        if not outcome:
            break
        outcomes.append(outcome)
        current = engine.get_workflow_run(run_id, path=path)
        if not current or current["status"] in {"DONE", "BLOCKED", "FAILED", "WAITING_APPROVAL", "CANCELLED"}:
            break
    result = engine.get_workflow_run(run_id, path=path)
    if not result:
        raise RuntimeError("agent run was not persisted")
    result["execution_outcomes"] = outcomes
    return result


_DASHBOARD_AGENT_MAP = {
    "RESEARCH_AGENT": "MKT_TREND_SCOUT",
    "PRODUCT_AGENT": "DEV_SOLUTION_ARCHITECT",
    "CODING_AGENT": "DEV_PYTHON_ENGINEER",
    "MARKETING_AGENT": "MKT_COPYWRITER",
    "SALES_AGENT": "OPS_LEAD_QUALIFIER",
    "CUSTOMER_SUPPORT_AGENT": "OPS_DELIVERY_DISPATCHER",
    "FINANCE_AGENT": "OPS_REVENUE_BOOKKEEPER",
    "OPTIMIZATION_AGENT": "OPS_RESOURCE_OPTIMIZER",
    "SECURITY_AGENT": "EXEC_RISK_COMPLIANCE",
}


def dashboard_agent_registry(*, path: Optional[str | Path] = None,
                             include_details: bool = False) -> list[dict[str, Any]]:
    """Project persisted executor status into the dashboard's nine cards.

    Public views contain readiness and state only. Task names, timestamps,
    diagnostics, and event details require the authenticated owner view.
    """
    engine = _engine()
    conn = engine.connect(path)
    try:
        output = []
        for alias, role_id in _DASHBOARD_AGENT_MAP.items():
            spec = AGENT_REGISTRY[role_id]
            task = conn.execute("SELECT id,title,state,started_at,finished_at,updated_at,trace_id,last_error,lease_expires_at,result_json FROM tasks WHERE assigned_role_id=? ORDER BY id DESC LIMIT 1", (role_id,)).fetchone()
            count = int(conn.execute("SELECT COUNT(*) FROM tasks WHERE assigned_role_id=?", (role_id,)).fetchone()[0])
            state = task["state"] if task else ("IDLE" if spec.readiness is AgentReadiness.READY else "NOT_IMPLEMENTED")
            lease_live = bool(task and task["lease_expires_at"] and task["lease_expires_at"] > engine.iso())
            if state == "RUNNING" and not lease_live:
                state = "STALE"
            active = state == "RUNNING" and lease_live
            status = {"QUEUED": "THINKING", "RUNNING": "WORKING", "WAITING_APPROVAL": "WAITING_APPROVAL",
                      "BLOCKED": "ERROR", "FAILED": "ERROR", "DONE": "SUCCESS", "RETRY_PENDING": "THINKING"}.get(state, state)
            result = engine._loads(task["result_json"], {}) if task else {}
            runtime_mode = result.get("executor_mode", "LOCAL_RULES") if isinstance(result, dict) else "LOCAL_RULES"
            result_detail = result.get("result", {}) if isinstance(result, dict) else {}
            reason = result_detail.get("reason_code") if isinstance(result_detail, dict) else None
            summary = ((task["last_error"] if task and task["last_error"] else reason or
                        f"Executor ghi nhận trạng thái {state}.") if include_details else
                       f"Task executor: {state}." if task else "Chưa có executor event.")
            entry = {"role": alias, "agent_id": alias, "executor_role_id": role_id,
                     "readiness": spec.readiness.value, "runtime_mode": runtime_mode,
                     "command_status": status, "has_active_flow": active,
                     "current_job": (task["title"] if include_details and task else
                                     f"Task {state.lower()}" if task else
                                     "Sẵn sàng; chưa có task executor." if spec.readiness is AgentReadiness.READY else "NOT_IMPLEMENTED"),
                     "latest_task_id": task["id"] if task and include_details else None,
                     "started_at": task["started_at"] if task and include_details else None,
                     "completed_at": task["finished_at"] if task and include_details else None,
                     "output_summary": summary,
                     "total_tasks_count": count, "total_cost_usd": None,
                     "connected_to_orchestrator": bool(task),
                     "activity_logs": []}
            if task and include_details:
                events = conn.execute("SELECT event_id,timestamp,event_type,status,title,trace_id FROM task_events WHERE task_id=? ORDER BY event_id DESC LIMIT 5", (str(task["id"]),)).fetchall()
                entry["activity_logs"] = [{"id": item["event_id"], "timestamp": item["timestamp"],
                                            "title": item["title"], "status": item["status"],
                                            "evidence": item["event_type"], "trace_id": item["trace_id"]}
                                           for item in events]
            output.append(entry)
        return output
    finally:
        conn.close()


def active_executor_role_ids(*, path: Optional[str | Path] = None) -> set[str]:
    conn = _engine().connect(path)
    try:
        now = _engine().iso()
        rows = conn.execute("SELECT DISTINCT assigned_role_id FROM tasks WHERE state='RUNNING' AND lease_expires_at>?", (now,)).fetchall()
        return {str(row[0]) for row in rows if row[0]}
    finally:
        conn.close()


def agent_role_statuses(*, path: Optional[str | Path] = None) -> dict[str, dict[str, Any]]:
    """Readiness plus latest persisted executor task/event for every logical role."""
    engine = _engine()
    conn = engine.connect(path)
    try:
        now = engine.iso()
        latest: dict[str, Any] = {}
        counts: dict[str, int] = {}
        for row in conn.execute("SELECT assigned_role_id,COUNT(*) AS count FROM tasks GROUP BY assigned_role_id"):
            counts[str(row["assigned_role_id"])] = int(row["count"])
        rows = conn.execute(
            """SELECT t.* FROM tasks t JOIN (
                   SELECT assigned_role_id,MAX(id) AS task_id FROM tasks GROUP BY assigned_role_id
               ) latest ON latest.task_id=t.id"""
        ).fetchall()
        for row in rows:
            latest[str(row["assigned_role_id"])] = dict(row)
        result = {}
        for role_id, spec in AGENT_REGISTRY.items():
            task = latest.get(role_id)
            state = task["state"] if task else ("IDLE" if spec.readiness is AgentReadiness.READY else "NOT_IMPLEMENTED")
            if task and state == "RUNNING" and (not task.get("lease_expires_at") or task["lease_expires_at"] <= now):
                state = "STALE"
            task_result = engine._loads(task.get("result_json"), {}) if task else {}
            result[role_id] = {"role_id": role_id, "readiness": spec.readiness.value,
                               "handler_id": spec.handler_id,
                               "executor_mode": task_result.get("executor_mode", "LOCAL_RULES") if isinstance(task_result, dict) else "LOCAL_RULES",
                               "status": state, "task_count": counts.get(role_id, 0),
                               "latest_task": ({"id": task["id"], "title": task["title"],
                                                "state": state, "updated_at": task["updated_at"],
                                                "trace_id": task["trace_id"],
                                                "last_error": task["last_error"]} if task else None)}
        return result
    finally:
        conn.close()


def _active_inference_count() -> int:
    with _INFERENCE_STATE_LOCK:
        return _ACTIVE_INFERENCE_TASKS


class _InferenceSlot:
    """Keep local inference concurrency measurable and capped at one by default."""
    def __enter__(self):
        global _ACTIVE_INFERENCE_TASKS
        _INFERENCE_GATE.acquire()
        with _INFERENCE_STATE_LOCK:
            _ACTIVE_INFERENCE_TASKS += 1
        return self

    def __exit__(self, *_exc):
        global _ACTIVE_INFERENCE_TASKS
        with _INFERENCE_STATE_LOCK:
            _ACTIVE_INFERENCE_TASKS = max(0, _ACTIVE_INFERENCE_TASKS - 1)
        _INFERENCE_GATE.release()


def _inference_slot():
    return _InferenceSlot()
