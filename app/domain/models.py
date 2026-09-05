"""Typed contracts shared by the workflow, tools, and HTTP layer."""

from datetime import datetime
from decimal import Decimal
from enum import IntEnum, StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


OrderNumber = Annotated[str, Field(pattern=r"^ORD-\d{5}$")]
Reference = Annotated[str, Field(min_length=1, max_length=100)]


class Topic(StrEnum):
    DELIVERY = "delivery"
    REFUND = "refund"
    ORDER_STATUS = "order_status"
    OTHER = "other"


class WorkflowStatus(StrEnum):
    RUNNING = "running"
    PENDING_APPROVAL = "pending_approval"
    COMPLETED = "completed"
    REJECTED = "rejected"


class Urgency(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    EMERGENCY = 5


class CustomerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=5_000)


class ExtractedIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: Topic
    urgency: int = Field(ge=1, le=5)
    order_number: OrderNumber | None = None
    refund_requested: bool = False
    requested_refund_amount: Decimal | None = Field(default=None, ge=0)
    legal_threat: bool = False


class Order(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_number: OrderNumber
    customer_number: str = Field(min_length=1)
    status: str = Field(min_length=1)
    amount: Decimal = Field(ge=0)
    tracking_number: str = Field(min_length=1)
    return_eligible: bool


class RiskAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requires_human_approval: bool
    reasons: list[str] = Field(default_factory=list)


class WorkflowStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    detail: str = Field(min_length=1)
    recorded_at: datetime


class HumanDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approved: bool
    note: str | None = Field(default=None, max_length=1_000)


class WorkflowState(BaseModel):
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
