import json

import httpx
import pytest

from app.domain.models import CustomerRequest, Topic, Urgency
from app.services.classifier import OllamaIntentClassifier


@pytest.mark.asyncio
async def test_ollama_classifier_uses_schema_constrained_output() -> None:
    captured: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "message": {
                    "content": json.dumps(
                        {
                            "topic": "order_status",
                            "urgency": 1,
                            "order_number": "ORD-10433",
                            "refund_requested": False,
                            "requested_refund_amount": None,
                            "legal_threat": False,
                        }
                    )
                }
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        intent = await OllamaIntentClassifier(client=client).classify(
            CustomerRequest(message="Where is my ORD-10433 order?")
        )
    finally:
        await client.aclose()

    assert intent.topic is Topic.ORDER_STATUS
    assert intent.urgency is Urgency.LOW
    assert captured["format"] == intent.model_json_schema()
    assert captured["stream"] is False
