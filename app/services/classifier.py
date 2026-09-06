"""Classifier interfaces and the deterministic development implementation."""

import re
from decimal import Decimal
from typing import Protocol

from app.domain.models import CustomerRequest, ExtractedIntent, Topic, Urgency

ORDER_NUMBER_PATTERN = re.compile(r"\bORD-\d{5}\b", re.IGNORECASE)
AMOUNT_PATTERN = re.compile(
    r"(?P<amount>\d+(?:[.,]\d{1,2})?)\s*(?:₺|TL|TRY|€|EUR|\$|USD)",
    re.IGNORECASE,
)


class IntentClassifier(Protocol):
    async def classify(self, request: CustomerRequest) -> ExtractedIntent:
        """Convert a customer message into validated structured intent."""


class DeterministicIntentClassifier:
    """Extract intent with explicit rules until an LLM adapter is introduced."""

    async def classify(self, request: CustomerRequest) -> ExtractedIntent:
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
        match = ORDER_NUMBER_PATTERN.search(message)
        return match.group(0).upper() if match else None

    @staticmethod
    def _refund_amount_for(message: str) -> Decimal | None:
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
        return any(term in message for term in terms)
