"""Typed contracts shared by the workflow, tools, and HTTP layer."""

from datetime import datetime
from decimal import Decimal
from enum import IntEnum, StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


OrderNumber = Annotated[str, Field(pattern=r"^ORD-\d{5}$")]
Reference = Annotated[str, Field(min_length=1, max_length=100)]


class Topic(StrEnum):
    """Supported customer-support request categories."""

    DELIVERY = "delivery"
    REFUND = "refund"
    ORDER_STATUS = "order_status"
    OTHER = "other"


class WorkflowStatus(StrEnum):
    """Lifecycle states persisted for a support workflow."""

    RUNNING = "running"
    PENDING_APPROVAL = "pending_approval"
    COMPLETED = "completed"
    REJECTED = "rejected"


class Urgency(IntEnum):
    """Normalized urgency scale consumed by the risk policy."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    EMERGENCY = 5


class RiskLevel(StrEnum):
    """Risk result used to select automatic or human handling."""

    LOW = "low"
    HIGH = "high"


class CustomerRequest(BaseModel):
    """Validated customer message at the application boundary."""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=5_000)


class ExtractedIntent(BaseModel):
    """Structured classifier output trusted by downstream nodes."""

    model_config = ConfigDict(extra="forbid")

    topic: Topic
    urgency: Urgency
    order_number: OrderNumber | None = None
    refund_requested: bool = False
    requested_refund_amount: Decimal | None = Field(default=None, ge=0)
    legal_threat: bool = False


class Order(BaseModel):
    """Mock order record available to the order lookup tool."""

    model_config = ConfigDict(extra="forbid")

    order_number: OrderNumber
    customer_number: str = Field(min_length=1)
    status: str = Field(min_length=1)
    amount: Decimal = Field(ge=0)
    tracking_number: str = Field(min_length=1)
    return_eligible: bool


class RiskAssessment(BaseModel):
    """Risk decision and human-approval reasons for a request."""

    model_config = ConfigDict(extra="forbid")

    level: RiskLevel
    requires_human_approval: bool
    reasons: list[str] = Field(default_factory=list)


class WorkflowStep(BaseModel):
    """Auditable event recorded during workflow execution."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    detail: str = Field(min_length=1)
    recorded_at: datetime


class HumanDecision(BaseModel):
    """Decision supplied when a human approval interrupt is resumed."""

    model_config = ConfigDict(extra="forbid")

    approved: bool
    note: str | None = Field(default=None, max_length=1_000)


class WorkflowState(BaseModel):
    """Complete state snapshot passed between LangGraph nodes."""

    model_config = ConfigDict(extra="forbid")

    reference: Reference
    customer_message: str = Field(min_length=1, max_length=5_000)
    status: WorkflowStatus = WorkflowStatus.RUNNING
    intent: ExtractedIntent | None = None
    order: Order | None = None
    risk: RiskAssessment | None = None
    human_decision: HumanDecision | None = None
    customer_response: str | None = None
    steps: list[WorkflowStep] = Field(default_factory=list)
