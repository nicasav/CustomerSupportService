import pytest

from app.domain.models import CustomerRequest, Topic
from app.services.classifier import (
    FallbackIntentClassifier,
    OllamaClassificationError,
)


class FailingClassifier:
    async def classify(self, request: CustomerRequest):
        raise OllamaClassificationError("model unavailable")


class StubClassifier:
    async def classify(self, request: CustomerRequest):
        from app.domain.models import ExtractedIntent

        return ExtractedIntent(topic=Topic.DELIVERY, urgency=1)


@pytest.mark.asyncio
async def test_classifier_falls_back_when_ollama_fails() -> None:
    classifier = FallbackIntentClassifier(FailingClassifier(), StubClassifier())

    result = await classifier.classify(CustomerRequest(message="delivery help"))

    assert result.topic is Topic.DELIVERY
