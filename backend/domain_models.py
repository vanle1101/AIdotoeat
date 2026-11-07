"""Typed records shared by the durable AUTOProfit business engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Optional


class TaskState(str, Enum):
    CREATED = "CREATED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    RETRY_PENDING = "RETRY_PENDING"
    BLOCKED = "BLOCKED"
    DONE = "DONE"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class TaskSpec:
    title: str
    category: str
    assigned_role_id: str = "SYSTEM"
    task_type: str = "internal.noop"
    payload: Mapping[str, Any] = field(default_factory=dict)
    idempotency_key: str = ""
    trace_id: str = ""
    max_attempts: int = 3
    timeout_seconds: int = 300

    def __post_init__(self) -> None:
        if not self.title.strip() or len(self.title) > 240:
            raise ValueError("title must contain 1-240 characters")
        if not self.category.strip() or len(self.category) > 80:
            raise ValueError("category must contain 1-80 characters")
        if not self.task_type.strip() or len(self.task_type) > 120:
            raise ValueError("task_type must contain 1-120 characters")
        if not 1 <= self.max_attempts <= 10:
            raise ValueError("max_attempts must be between 1 and 10")
        if not 1 <= self.timeout_seconds <= 86400:
            raise ValueError("timeout_seconds must be between 1 and 86400")
        if not isinstance(self.payload, Mapping):
            raise ValueError("payload must be an object")


@dataclass(frozen=True)
class TaskRecord:
    id: int
    title: str
    category: str
    assigned_role_id: str
    status: TaskState
    state_version: int
    idempotency_key: str
    trace_id: str
    attempts: int
    max_attempts: int
    lease_owner: Optional[str]
    lease_expires_at: Optional[str]
    available_at: str
    task_type: str
    payload: Mapping[str, Any]
    result: Optional[Mapping[str, Any]]


@dataclass(frozen=True)
class TaskEvent:
    event_id: int
    task_id: str
    event_type: str
    status: str
    title: str
    timestamp: str
    trace_id: str
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Opportunity:
    id: str
    title: str
    source: str
    stage: str
    payload: Mapping[str, Any]


@dataclass(frozen=True)
class Evidence:
    id: str
    opportunity_id: Optional[str]
    evidence_type: str
    source_uri: Optional[str]
    content_hash: Optional[str]
    summary: str
    verified: bool


@dataclass(frozen=True)
class Experiment:
    id: str
    name: str
    hypothesis: str
    status: str
    result: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Customer:
    id: str
    email: Optional[str]
    display_name: Optional[str]
    status: str


@dataclass(frozen=True)
class Lead:
    id: str
    email: Optional[str]
    company: Optional[str]
    source: Optional[str]
    stage: Optional[str]


@dataclass(frozen=True)
class Offer:
    id: str
    product_id: str
    customer_id: Optional[str]
    amount_minor: int
    currency: str
    status: str


@dataclass(frozen=True)
class Product:
    id: str
    slug: str
    name: str
    category: Optional[str]
    price_minor: Optional[int]
    active: bool


@dataclass(frozen=True)
class Asset:
    id: str
    name: str
    asset_type: str
    uri: Optional[str]
    status: str


@dataclass(frozen=True)
class AgentRun:
    id: str
    workflow: str
    status: str
    idempotency_key: str
    trace_id: str
    result: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ApprovalRequest:
    id: str
    tool_name: str
    permission: str
    requested_by: str
    status: str
    expires_at: str
    trace_id: str


@dataclass(frozen=True)
class Order:
    id: str
    customer_id: Optional[str]
    product_id: Optional[str]
    amount_minor: Optional[int]
    currency: str
    status: str
    payload: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PaymentClaim:
    id: str
    product_slug: str
    amount_minor: int
    currency: str
    status: str
    reference: Optional[str]


@dataclass(frozen=True)
class VerifiedTransaction:
    id: int
    transaction_ref: Optional[str]
    source: Optional[str]
    amount_minor: Optional[int]
    currency: str
    status: str


@dataclass(frozen=True)
class Delivery:
    id: str
    order_id: str
    asset_id: Optional[str]
    status: str
    delivered_at: Optional[str]


@dataclass(frozen=True)
class CostExposure:
    id: str
    tool_name: str
    provider: str
    action: str
    estimated_minor: Optional[int]
    currency: str
    status: str
    reason_code: str
    trace_id: str


@dataclass(frozen=True)
class AnalyticsEvent:
    id: str
    event_type: str
    event_name: str
    occurred_at: str
    internal_test: bool
    source: str
