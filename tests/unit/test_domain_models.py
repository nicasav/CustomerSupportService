from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.domain.models import ExtractedIntent, Order, Urgency


def test_extracted_intent_accepts_structured_order_request() -> None:
    intent = ExtractedIntent(
        topic="delivery",
        urgency=4,
        order_number="ORD-10432",
        refund_requested=True,
        requested_refund_amount=Decimal("149.99"),
        legal_threat=True,
    )

    assert intent.order_number == "ORD-10432"
    assert intent.urgency is Urgency.CRITICAL
    assert intent.legal_threat is True


def test_order_number_must_match_expected_format() -> None:
    with pytest.raises(ValidationError):
        Order(
            order_number="10432",
            customer_number="CUS-1001",
            status="delayed",
            amount=Decimal("149.99"),
            tracking_number="TRK-10432",
            return_eligible=True,
        )
