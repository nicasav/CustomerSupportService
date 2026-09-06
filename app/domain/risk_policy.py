from decimal import Decimal

from app.domain.models import (
    ExtractedIntent,
    Order,
    RiskAssessment,
    RiskLevel,
    Urgency,
)

HIGH_VALUE_THRESHOLD = Decimal("500")


def assess_risk(
    intent: ExtractedIntent,
    order: Order | None = None,
) -> RiskAssessment:
    """Assess whether a request needs human approval.

    A request is high risk when it contains a legal threat, has critical or
    emergency urgency, or requests a refund above the configured threshold.
    """
    reasons: list[str] = []

    if intent.legal_threat:
        reasons.append("legal threat")

    if intent.urgency >= Urgency.CRITICAL:
        reasons.append("urgency is critical or emergency")

    refund_amount = intent.requested_refund_amount
    if refund_amount is None and intent.refund_requested and order is not None:
        refund_amount = order.amount
    if (
        intent.refund_requested
        and refund_amount is not None
        and refund_amount > HIGH_VALUE_THRESHOLD
    ):
        reasons.append("refund amount exceeds 500")

    if reasons:
        return RiskAssessment(
            level=RiskLevel.HIGH,
            requires_human_approval=True,
            reasons=reasons,
        )

    return RiskAssessment(
        level=RiskLevel.LOW,
        requires_human_approval=False,
    )
