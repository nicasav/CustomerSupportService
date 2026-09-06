"""Deterministic LangGraph workflow for customer support requests."""

from datetime import UTC, datetime
from typing import Literal

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from app.domain.models import (
    CustomerRequest,
    WorkflowState,
    WorkflowStatus,
    WorkflowStep,
)
from app.domain.risk_policy import assess_risk
from app.services.classifier import IntentClassifier
from app.tools.order_lookup import OrderLookupInput, OrderLookupTool


def _step(name: str, detail: str) -> WorkflowStep:
    return WorkflowStep(
        name=name,
        detail=detail,
        recorded_at=datetime.now(UTC),
    )


def build_support_graph(
    classifier: IntentClassifier,
    order_lookup: OrderLookupTool,
    checkpointer: BaseCheckpointSaver | None = None,
):
    """Build a compiled graph with its external dependencies injected."""

    async def classify_node(state: WorkflowState) -> dict[str, object]:
        intent = await classifier.classify(
            CustomerRequest(message=state.customer_message)
        )
        return {
            "intent": intent,
            "steps": [
                *state.steps,
                _step(
                    "classify",
                    f"Classified request as {intent.topic.value} with urgency "
                    f"{intent.urgency.name.lower()}",
                )
            ],
        }

    async def lookup_order_node(state: WorkflowState) -> dict[str, object]:
        if state.intent is None or state.intent.order_number is None:
            return {
                "steps": [
                    *state.steps,
                    _step("lookup_order", "No order number was found in the request")
                ]
            }

        order = await order_lookup.run(
            OrderLookupInput(order_number=state.intent.order_number)
        )
        detail = (
            f"Loaded order {order.order_number}"
            if order is not None
            else f"Order {state.intent.order_number} was not found"
        )
        return {
            "order": order,
            "steps": [*state.steps, _step("lookup_order", detail)],
        }

    def assess_risk_node(state: WorkflowState) -> dict[str, object]:
        if state.intent is None:
            raise RuntimeError("Risk assessment requires classified intent")
        risk = assess_risk(state.intent, state.order)
        return {
            "risk": risk,
            "steps": [
                *state.steps,
                _step(
                    "assess_risk",
                    "Human approval required"
                    if risk.requires_human_approval
                    else "Routine request can be answered automatically",
                )
            ],
        }

    def route_after_risk(
        state: WorkflowState,
    ) -> Literal["routine_response", "mark_pending"]:
        if state.risk is None:
            raise RuntimeError("Risk routing requires a risk assessment")
        return (
            "mark_pending"
            if state.risk.requires_human_approval
            else "routine_response"
        )

    def mark_pending_node(state: WorkflowState) -> dict[str, object]:
        return {
            "status": WorkflowStatus.PENDING_APPROVAL,
            "steps": [
                *state.steps,
                _step("await_approval", "Waiting for human approval"),
            ],
        }

    def routine_response_node(state: WorkflowState) -> dict[str, object]:
        order_detail = (
            f" for order {state.order.order_number}"
            if state.order is not None
            else ""
        )
        return {
            "status": WorkflowStatus.COMPLETED,
            "customer_response": (
                f"Thanks for contacting support. We reviewed your request"
                f"{order_detail} and will help with the next steps."
            ),
            "steps": [
                *state.steps,
                _step("routine_response", "Generated automatic response"),
            ],
        }

    def await_approval_node(state: WorkflowState) -> dict[str, object]:
        decision = interrupt(
            {
                "reference": state.reference,
                "message": "Human approval is required",
                "reasons": state.risk.reasons if state.risk else [],
            }
        )
        from app.domain.models import HumanDecision

        human_decision = HumanDecision.model_validate(decision)
        status = (
            WorkflowStatus.COMPLETED
            if human_decision.approved
            else WorkflowStatus.REJECTED
        )
        return {
            "status": status,
            "human_decision": human_decision,
            "customer_response": (
                "Your request was approved and will be processed."
                if human_decision.approved
                else "Your request was not approved."
            ),
            "steps": [
                *state.steps,
                _step(
                    "human_decision",
                    "Approved by support specialist"
                    if human_decision.approved
                    else "Rejected by support specialist",
                ),
            ],
        }

    graph = StateGraph(WorkflowState)
    graph.add_node("classify", classify_node)
    graph.add_node("lookup_order", lookup_order_node)
    graph.add_node("assess_risk", assess_risk_node)
    graph.add_node("mark_pending", mark_pending_node)
    graph.add_node("routine_response", routine_response_node)
    graph.add_node("await_approval", await_approval_node)
    graph.add_edge(START, "classify")
    graph.add_edge("classify", "lookup_order")
    graph.add_edge("lookup_order", "assess_risk")
    graph.add_conditional_edges("assess_risk", route_after_risk)
    graph.add_edge("mark_pending", "await_approval")
    graph.add_edge("routine_response", END)
    graph.add_edge("await_approval", END)
    return graph.compile(checkpointer=checkpointer)
