from decimal import Decimal

import pytest

from app.domain.models import CustomerRequest, Topic, Urgency
from app.services.classifier import DeterministicIntentClassifier


@pytest.mark.asyncio
async def test_classifier_extracts_assessment_message() -> None:
    classifier = DeterministicIntentClassifier()
    intent = await classifier.classify(
        CustomerRequest(
            message=(
                "My ORD-10432 delivery is late. Refund 799.00 USD today "
                "or I will take legal action."
            )
        )
    )

    assert intent.topic is Topic.REFUND
    assert intent.urgency is Urgency.CRITICAL
    assert intent.order_number == "ORD-10432"
    assert intent.refund_requested is True
    assert intent.requested_refund_amount == Decimal("799.00")
    assert intent.legal_threat is True


@pytest.mark.asyncio
async def test_classifier_returns_low_risk_order_status_intent() -> None:
    classifier = DeterministicIntentClassifier()
    intent = await classifier.classify(
        CustomerRequest(message="Where is my ORD-10433 order?")
    )

    assert intent.topic is Topic.ORDER_STATUS
    assert intent.urgency is Urgency.LOW
    assert intent.order_number == "ORD-10433"
    assert intent.refund_requested is False
    assert intent.legal_threat is False


@pytest.mark.asyncio
async def test_classifier_supports_turkish_signals() -> None:
    classifier = DeterministicIntentClassifier()
    intent = await classifier.classify(
        CustomerRequest(
            message=(
                "ORD-10432 siparişim gelmedi, bugün para iadesi yapın; "
                "yoksa tüketici hakemine gideceğim."
            )
        )
    )

    assert intent.topic is Topic.REFUND
    assert intent.urgency is Urgency.CRITICAL
    assert intent.legal_threat is True
