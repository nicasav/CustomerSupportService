from pathlib import Path

import pytest
from pydantic import ValidationError

from app.repositories.orders import JsonOrderRepository
from app.tools.tracking_lookup import TrackingLookupInput, TrackingLookupTool


@pytest.fixture
def tracking_tool() -> TrackingLookupTool:
    repository = JsonOrderRepository(
        Path(__file__).parents[2] / "app" / "data" / "orders.json"
    )
    return TrackingLookupTool(repository)


@pytest.mark.asyncio
async def test_tracking_lookup_returns_shipment_status(tracking_tool) -> None:
    result = await tracking_tool.run(
        TrackingLookupInput(tracking_number="TRK-10433")
    )

    assert result is not None
    assert result.status == "delivered"


def test_tracking_lookup_rejects_invalid_number() -> None:
    with pytest.raises(ValidationError):
        TrackingLookupInput(tracking_number="not-a-tracking-number")
