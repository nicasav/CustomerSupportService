"""Typed order lookup tool used by the workflow."""

from pydantic import BaseModel, ConfigDict

from app.domain.models import Order, OrderNumber
from app.repositories.orders import OrderRepository


class OrderLookupInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_number: OrderNumber


class OrderLookupTool:
    """Look up order details through the repository abstraction."""

    def __init__(self, repository: OrderRepository) -> None:
        """Store the repository used for order searches."""
        self._repository = repository

    async def run(self, input_data: OrderLookupInput) -> Order | None:
        """Return the order matching the validated order number."""
        return await self._repository.find_by_order_number(input_data.order_number)
