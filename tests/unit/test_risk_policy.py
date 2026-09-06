from decimal import Decimal

import pytest

from app.domain.models import ExtractedIntent, Order, RiskLevel, Urgency
from app.domain.risk_policy import assess_risk


def make_intent(**overrides: object) -> ExtractedIntent:
    values: dict[str, object] = {
        "topic": "delivery",
        "urgency": Urgency.LOW,
    }
    values.update(overrides)
    return ExtractedIntent.model_validate(values)


def make_order(amount: str = "149.99") -> Order:
    return Order(
        order_number="ORD-10432",
        customer_number="CUS-1001",
        status="delayed",
        amount=Decimal(amount),
        tracking_number="TRK-10432",
        return_eligible=True,
    )


def test_routine_request_is_low_risk() -> None:
    assessment = assess_risk(make_intent(), make_order())

    assert assessment.level is RiskLevel.LOW
    assert assessment.requires_human_approval is False
    assert assessment.reasons == []


@pytest.mark.parametrize(
    ("intent_overrides", "order", "reason"),
    [
        ({"legal_threat": True}, make_order(), "legal threat"),
        (
            {"urgency": Urgency.CRITICAL},
            make_order(),
            "urgency is critical or emergency",
        ),
        (
            {"refund_requested": True},
            make_order("799.00"),
            "refund amount exceeds 500",
        ),
        (
            {
                "refund_requested": True,
                "requested_refund_amount": Decimal("501"),
            },
            make_order("149.99"),
            "refund amount exceeds 500",
        ),
    ],
)
def test_each_high_risk_rule_requires_approval(
    intent_overrides: dict[str, object],
    order: Order,
    reason: str,
) -> None:
    assessment = assess_risk(make_intent(**intent_overrides), order)

    assert assessment.level is RiskLevel.HIGH
    assert assessment.requires_human_approval is True
    assert reason in assessment.reasons
