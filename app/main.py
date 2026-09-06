from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app.api.routes import router
from app.core.config import get_settings
from app.orchestration.checkpointer import sqlite_checkpointer
from app.orchestration.graph import build_support_graph
from app.repositories.orders import JsonOrderRepository
from app.services.classifier import (
    DeterministicIntentClassifier,
    IntentClassifier,
    OllamaIntentClassifier,
)
from app.services.ticket_service import TicketService
from app.tools.order_lookup import OrderLookupTool


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Create shared repositories, graph, and checkpoint resources."""
    settings = get_settings()
    data_dir = Path(__file__).parent / "data"
    repository = JsonOrderRepository(data_dir / "orders.json")
    classifier: IntentClassifier
    if settings.llm_provider == "ollama":
        classifier = OllamaIntentClassifier(
            base_url=settings.llm_base_url,
            model=settings.llm_model,
        )
    elif settings.llm_provider == "deterministic":
        classifier = DeterministicIntentClassifier()
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")
    async with sqlite_checkpointer(Path(settings.checkpoint_path)) as saver:
        graph = build_support_graph(
            classifier,
            OrderLookupTool(repository),
            saver,
        )
        application.state.ticket_service = TicketService(graph)
        yield


app = FastAPI(title="Customer Support Service", lifespan=lifespan)
app.include_router(router)
