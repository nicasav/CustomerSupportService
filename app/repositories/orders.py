"""Order repository abstractions and the JSON-backed development implementation."""

import json
from pathlib import Path
from typing import Protocol

from pydantic import TypeAdapter

from app.domain.models import Order, OrderNumber, TrackingInfo, TrackingNumber


class OrderRepository(Protocol):
    async def find_by_order_number(self, order_number: str) -> Order | None:
        """Return an order by number, or None when it does not exist."""

    async def find_by_tracking_number(
        self, tracking_number: str
    ) -> TrackingInfo | None:
        """Return tracking information by shipment tracking number."""


class JsonOrderRepository:
    """Load and validate the small JSON order dataset at startup."""

    def __init__(self, data_path: Path) -> None:
        """Read records from ``data_path`` and index them by order number."""
        records = json.loads(data_path.read_text(encoding="utf-8"))
        self._orders = {
            order.order_number: order
            for order in (Order.model_validate(record) for record in records)
        }
        self._tracking = {
            order.tracking_number: TrackingInfo(
                tracking_number=order.tracking_number,
                status=order.status,
            )
            for order in self._orders.values()
        }

    async def find_by_order_number(self, order_number: str) -> Order | None:
        """Validate an order number and return its record when present."""
        validated_number = TypeAdapter(OrderNumber).validate_python(order_number)
        return self._orders.get(validated_number)

    async def find_by_tracking_number(
        self, tracking_number: str
    ) -> TrackingInfo | None:
        """Validate a tracking number and return its shipment status."""
        validated_number = TypeAdapter(TrackingNumber).validate_python(tracking_number)
        return self._tracking.get(validated_number)
