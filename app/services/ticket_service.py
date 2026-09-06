"""Application service bridging HTTP requests and the workflow graph."""

from uuid import uuid4

from langgraph.types import Command

from app.api.schemas import (
    DecisionRequest,
    FinalResponse,
    PendingResponse,
    RequestCreate,
    RequestResponse,
)
from app.domain.models import CustomerRequest, HumanDecision, WorkflowState, WorkflowStatus


class InvalidReferenceError(Exception):
    """Raised when a request reference has no persisted workflow state."""


class AlreadyResolvedError(Exception):
    """Raised when a completed workflow is resumed again."""


class TicketService:
    """Translate API operations into graph invocations and typed responses."""

    def __init__(self, graph) -> None:
        """Store the compiled graph used for all ticket operations."""
        self._graph = graph

    async def start(self, request: RequestCreate) -> RequestResponse:
        """Create a reference, run a workflow, and map its first result."""
        reference = str(uuid4())
        config = {"configurable": {"thread_id": reference}}
        result = await self._graph.ainvoke(
            {
                "reference": reference,
                "customer_message": CustomerRequest(
                    message=request.message
                ).message,
            },
            config,
        )
        state = WorkflowState.model_validate(
            {key: value for key, value in result.items() if key != "__interrupt__"}
        )
        if state.status is WorkflowStatus.PENDING_APPROVAL:
            return PendingResponse(
                status="pending_approval",
                reference=reference,
                reasons=state.risk.reasons if state.risk else [],
                steps=state.steps,
            )
        return self._final_response(state)

    async def resume(
        self, reference: str, decision: DecisionRequest
    ) -> FinalResponse:
        """Resume a checkpointed workflow with a validated human decision."""
        config = {"configurable": {"thread_id": reference}}
        current = await self._graph.aget_state(config)
        if not current.values:
            raise InvalidReferenceError(reference)
        state = WorkflowState.model_validate(current.values)
        if state.status is not WorkflowStatus.PENDING_APPROVAL:
            raise AlreadyResolvedError(reference)

        result = await self._graph.ainvoke(
            Command(
                resume=HumanDecision(
                    approved=decision.approved,
                    note=decision.note,
                ).model_dump(mode="json")
            ),
            config,
        )
        return self._final_response(WorkflowState.model_validate(result))

    @staticmethod
    def _final_response(state: WorkflowState) -> FinalResponse:
        """Convert a completed workflow state into the public response DTO."""
        if state.status not in {
            WorkflowStatus.COMPLETED,
            WorkflowStatus.REJECTED,
        } or state.customer_response is None:
            raise RuntimeError("Workflow did not produce a final response")
        return FinalResponse(
            status=state.status.value,
            reference=state.reference,
            customer_response=state.customer_response,
            steps=state.steps,
        )
