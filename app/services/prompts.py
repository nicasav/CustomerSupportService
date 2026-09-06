"""Prompts used by the structured intent classifier."""

CLASSIFICATION_SYSTEM_PROMPT = """\
You classify customer support messages.
Return only the requested structured fields.
Use urgency 1 for routine, 2 for moderate, 3 for urgent, 4 for critical,
and 5 for emergency.
Extract an order number only when it matches ORD- followed by five digits.
Set legal_threat true for threats of legal action, courts, lawyers, or
consumer arbitration.
"""
