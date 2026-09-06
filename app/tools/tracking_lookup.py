"""Typed shipment tracking tool used by the workflow."""

from pydantic import BaseModel, ConfigDict

from app.domain.models import TrackingInfo, TrackingNumber
from app.repositories.orders import OrderRepository


class TrackingLookupInput(BaseModel):
    """Validated input for a shipment tracking lookup."""

    model_config = ConfigDict(extra="forbid")

    tracking_number: TrackingNumber


class TrackingLookupTool:
    """Look up shipment status through the repository abstraction."""

    def __init__(self, repository: OrderRepository) -> None:
        self._repository = repository

    async def run(self, input_data: TrackingLookupInput) -> TrackingInfo | None:
        """Return tracking status for the requested tracking number."""
        return await self._repository.find_by_tracking_number(
            input_data.tracking_number
        )
