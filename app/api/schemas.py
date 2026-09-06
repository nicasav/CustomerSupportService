"""HTTP-boundary request and response models."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models import WorkflowStep


class RequestCreate(BaseModel):
    """Payload accepted when a customer submits a new message."""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=5_000)


class DecisionRequest(BaseModel):
    """Approval or rejection submitted by a support specialist."""

    model_config = ConfigDict(extra="forbid")

    approved: bool
    note: str | None = Field(default=None, max_length=1_000)


class PendingResponse(BaseModel):
    """Response returned when a workflow is waiting for human approval."""

    status: Literal["pending_approval"]
    reference: str
    reasons: list[str]
    steps: list[WorkflowStep]


class FinalResponse(BaseModel):
    """Response returned after a workflow has completed or been rejected."""

    status: Literal["completed", "rejected"]
    reference: str
    customer_response: str
    steps: list[WorkflowStep]


RequestResponse = PendingResponse | FinalResponse
