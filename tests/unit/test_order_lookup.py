from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.repositories.orders import JsonOrderRepository
from app.tools.order_lookup import OrderLookupInput, OrderLookupTool


@pytest.fixture
def order_lookup_tool() -> OrderLookupTool:
    repository = JsonOrderRepository(
        Path(__file__).parents[2] / "app" / "data" / "orders.json"
    )
    return OrderLookupTool(repository)


@pytest.mark.asyncio
async def test_order_lookup_returns_typed_order(
    order_lookup_tool: OrderLookupTool,
) -> None:
    order = await order_lookup_tool.run(
        OrderLookupInput(order_number="ORD-10432")
    )

    assert order is not None
    assert order.status == "delayed"
    assert order.amount == Decimal("149.99")


@pytest.mark.asyncio
async def test_order_lookup_returns_none_for_unknown_order(
    order_lookup_tool: OrderLookupTool,
) -> None:
    order = await order_lookup_tool.run(
        OrderLookupInput(order_number="ORD-99999")
    )

    assert order is None


def test_order_lookup_rejects_invalid_order_number() -> None:
    with pytest.raises(ValidationError):
        OrderLookupInput(order_number="not-an-order")
