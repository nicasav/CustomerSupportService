from pathlib import Path

import pytest

from app.orchestration.checkpointer import sqlite_checkpointer
from app.orchestration.graph import build_support_graph
from app.repositories.orders import JsonOrderRepository
from app.services.classifier import DeterministicIntentClassifier
from app.tools.order_lookup import OrderLookupTool
from app.tools.tracking_lookup import TrackingLookupTool


def dependencies() -> tuple[
    DeterministicIntentClassifier, OrderLookupTool, TrackingLookupTool
]:
    repository = JsonOrderRepository(
        Path(__file__).parents[2] / "app" / "data" / "orders.json"
    )
    return (
        DeterministicIntentClassifier(),
        OrderLookupTool(repository),
        TrackingLookupTool(repository),
    )


@pytest.mark.asyncio
async def test_workflow_state_survives_sqlite_saver_reopen(tmp_path: Path) -> None:
    database_path = tmp_path / "checkpoints.sqlite"
    config = {"configurable": {"thread_id": "persisted-risk-1"}}
    classifier, order_lookup, tracking_lookup = dependencies()

    async with sqlite_checkpointer(database_path) as saver:
        graph = build_support_graph(
            classifier, order_lookup, tracking_lookup, saver
        )
        result = await graph.ainvoke(
            {
                "reference": "persisted-risk-1",
                "customer_message": (
                    "Refund my ORD-10432 today or I will take legal action."
                ),
            },
            config,
        )

        assert result["status"].value == "pending_approval"

    classifier, order_lookup, tracking_lookup = dependencies()
    async with sqlite_checkpointer(database_path) as saver:
        graph = build_support_graph(
            classifier, order_lookup, tracking_lookup, saver
        )
        persisted = await graph.aget_state(config)

        assert persisted.values["reference"] == "persisted-risk-1"
        assert persisted.values["status"].value == "pending_approval"
        assert len(persisted.values["steps"]) == 5
