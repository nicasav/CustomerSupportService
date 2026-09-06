"""Classifier interfaces and the deterministic development implementation."""

import re
from decimal import Decimal
from typing import Protocol

import httpx
from pydantic import ValidationError

from app.domain.models import CustomerRequest, ExtractedIntent, Topic, Urgency
from app.services.prompts import CLASSIFICATION_SYSTEM_PROMPT

ORDER_NUMBER_PATTERN = re.compile(r"\bORD-\d{5}\b", re.IGNORECASE)
AMOUNT_PATTERN = re.compile(
    r"(?P<amount>\d+(?:[.,]\d{1,2})?)\s*(?:₺|TL|TRY|€|EUR|\$|USD)",
    re.IGNORECASE,
)


class IntentClassifier(Protocol):
    async def classify(self, request: CustomerRequest) -> ExtractedIntent:
        """Convert a customer message into validated structured intent."""


class OllamaClassificationError(RuntimeError):
    """Raised when Ollama cannot return valid structured intent."""


class FallbackIntentClassifier:
    """Use a fallback classifier when the primary classifier is unavailable."""

    def __init__(
        self,
        primary: IntentClassifier,
        fallback: IntentClassifier,
    ) -> None:
        self._primary = primary
        self._fallback = fallback

    async def classify(self, request: CustomerRequest) -> ExtractedIntent:
        try:
            return await self._primary.classify(request)
        except OllamaClassificationError:
            return await self._fallback.classify(request)


class OllamaIntentClassifier:
    """Classify messages through Ollama's JSON-schema constrained output."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        model: str = "qwen2.5:3b",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        """Configure the Ollama endpoint, model, and optional HTTP client."""
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._client = client

    async def classify(self, request: CustomerRequest) -> ExtractedIntent:
        """Call Ollama and validate its schema-constrained JSON response."""
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient()
        try:
            response = await client.post(
                f"{self._base_url}/api/chat",
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": CLASSIFICATION_SYSTEM_PROMPT},
                        {"role": "user", "content": request.message},
                    ],
                    "format": ExtractedIntent.model_json_schema(),
                    "stream": False,
                },
                timeout=60.0,
            )
            response.raise_for_status()
            payload = response.json()
            content = payload["message"]["content"]
            return ExtractedIntent.model_validate_json(content)
        except (httpx.HTTPError, KeyError, TypeError, ValueError, ValidationError) as exc:
            raise OllamaClassificationError(
                "Ollama failed to return valid structured intent"
            ) from exc
        finally:
            if owns_client:
                await client.aclose()


class DeterministicIntentClassifier:
    """Extract intent with explicit rules until an LLM adapter is introduced."""

    async def classify(self, request: CustomerRequest) -> ExtractedIntent:
        """Extract intent using local rules without network access."""
        message = request.message
        normalized = message.casefold()

        return ExtractedIntent(
            topic=self._topic_for(normalized),
            urgency=self._urgency_for(normalized),
            order_number=self._order_number_for(message),
            refund_requested=self._contains_any(
                normalized, ("refund", "iade", "para iade", "money back")
            ),
            requested_refund_amount=self._refund_amount_for(normalized),
            legal_threat=self._contains_any(
                normalized,
                (
                    "legal action",
                    "lawsuit",
                    "lawyer",
                    "mahkeme",
                    "avukat",
                    "tüketici hakem",
                    "yasal işlem",
                ),
            ),
        )

    @staticmethod
    def _topic_for(message: str) -> Topic:
        """Map delivery, refund, and status keywords to a topic."""
        if DeterministicIntentClassifier._contains_any(
            message, ("refund", "iade", "para iade", "money back")
        ):
            return Topic.REFUND
        if DeterministicIntentClassifier._contains_any(
            message,
            ("delivery", "shipping", "cargo", "kargo", "gelmedi", "gecik"),
        ):
            return Topic.DELIVERY
        if DeterministicIntentClassifier._contains_any(
            message, ("status", "where is", "durum", "nerede", "takip")
        ):
            return Topic.ORDER_STATUS
        return Topic.OTHER

    @staticmethod
    def _urgency_for(message: str) -> Urgency:
        """Map urgency keywords to the normalized urgency scale."""
        if DeterministicIntentClassifier._contains_any(
            message, ("emergency", "acil", "immediately", "hemen", "right now")
        ):
            return Urgency.EMERGENCY
        if DeterministicIntentClassifier._contains_any(
            message, ("today", "bugün", "critical", "kritik", "asap")
        ):
            return Urgency.CRITICAL
        if DeterministicIntentClassifier._contains_any(
            message, ("urgent", "aciliyet", "soon", "en kısa sürede")
        ):
            return Urgency.HIGH
        if DeterministicIntentClassifier._contains_any(
            message, ("week", "hafta", "late", "geç")
        ):
            return Urgency.MEDIUM
        return Urgency.LOW

    @staticmethod
    def _order_number_for(message: str) -> str | None:
        """Return the first valid order number found in the message."""
        match = ORDER_NUMBER_PATTERN.search(message)
        return match.group(0).upper() if match else None

    @staticmethod
    def _refund_amount_for(message: str) -> Decimal | None:
        """Extract a currency amount when the message requests a refund."""
        if not DeterministicIntentClassifier._contains_any(
            message, ("refund", "iade", "para iade", "money back")
        ):
            return None
        match = AMOUNT_PATTERN.search(message)
        if not match:
            return None
        return Decimal(match.group("amount").replace(",", "."))

    @staticmethod
    def _contains_any(message: str, terms: tuple[str, ...]) -> bool:
        """Return whether any case-normalized term occurs in the message."""
        return any(term in message for term in terms)
