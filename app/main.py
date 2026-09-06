from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app.api.routes import router
from app.orchestration.checkpointer import sqlite_checkpointer
from app.orchestration.graph import build_support_graph
from app.repositories.orders import JsonOrderRepository
from app.services.classifier import DeterministicIntentClassifier
from app.services.ticket_service import TicketService
from app.tools.order_lookup import OrderLookupTool


@asynccontextmanager
async def lifespan(application: FastAPI):
    data_dir = Path(__file__).parent / "data"
    repository = JsonOrderRepository(data_dir / "orders.json")
    async with sqlite_checkpointer(data_dir / "workflow.sqlite") as saver:
        graph = build_support_graph(
            DeterministicIntentClassifier(),
            OrderLookupTool(repository),
            saver,
        )
        application.state.ticket_service = TicketService(graph)
        yield


app = FastAPI(title="Customer Support Service", lifespan=lifespan)
app.include_router(router)
