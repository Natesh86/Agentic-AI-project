"""
SoloBiz AI - Human-in-the-Loop (HITL) Escalation Matrix
Evaluates whether a business event requires human intervention (Level 1, 2, or 3).
"""
from typing import Tuple, List, Optional, Dict, Any
from core.state import SoloBizInboundEvent, Classification, OrderState
from config import (
    MAX_AUTONOMOUS_ORDER_VALUE,
    SENTIMENT_CRITICAL_THRESHOLD,
    MIN_CONFIDENCE_THRESHOLD,
    HITL_LEGAL_KEYWORDS
)
from core.guardrails import scan_legal_risk_keywords


def evaluate_escalation(
    event: SoloBizInboundEvent,
    classification: Classification,
    order_state: Optional[OrderState] = None,
    sentiment_score: Optional[float] = None,
    injection_detected: bool = False,
    is_procurement_po: bool = False,
    is_social_post: bool = False
) -> Tuple[bool, int, str, str, List[str]]:
    """
    Evaluates the event and proposed actions against the HITL Governance Matrix.

    Returns:
        (hitl_required: bool,
         level: int (1 = Autonomous, 2 = Digest/Batch Review, 3 = Immediate Phone/Alert),
         trigger_type: str,
         summary: str,
         actions_held: List[str])
    """
    message_text = event.message_payload.message_text

    # --- LEVEL 3: Immediate Zero-Latency Escalations ---

    # 1. Prompt Injection or Adversarial Payload Detected
    if injection_detected:
        return (
            True, 3, "ADVERSARIAL_INJECTION_DETECTED",
            "Suspicious input attempting to override system behavior or manipulate commercial rules.",
            ["BLOCK_AUTOMATED_TOOL_EXECUTION", "SEND_SAFE_FALLBACK_REPLY"]
        )

    # 2. Legal / Regulatory Threat or Fraud Accusation
    legal_keywords = scan_legal_risk_keywords(message_text)
    if legal_keywords:
        return (
            True, 3, "LEGAL_REGULATORY_THREAT",
            f"Customer message contains sensitive escalation terms: {', '.join(legal_keywords)}. Risk of legal/regulatory exposure.",
            ["FREEZE_AUTOMATED_REPLIES", "ALERT_OWNER_IMMEDIATELY"]
        )

    # 3. High-Stakes Financial Order (Value >= Threshold or Bulk Custom)
    if order_state and order_state.total_quote >= MAX_AUTONOMOUS_ORDER_VALUE:
        return (
            True, 3, "HIGH_VALUE_ORDER_EXCEEDS_THRESHOLD",
            f"Order total ₹{order_state.total_quote:,.2f} exceeds autonomous ceiling (₹{MAX_AUTONOMOUS_ORDER_VALUE:,.2f}). Requires workshop capacity confirmation.",
            ["HOLD_ORDER_CONFIRMATION", "REQUIRE_OWNER_CAPACITY_SIGN_OFF"]
        )

    if classification.intent == "BULK_CUSTOM_ORDER":
        return (
            True, 3, "BULK_CUSTOM_ORDER_ESCALATION",
            "High-volume or custom-branded corporate order requires workshop schedule and labor verification.",
            ["HOLD_DELIVERY_COMMITMENT", "REQUIRE_OWNER_QUOTE_APPROVAL"]
        )

    # 4. Ambiguous Payment Verification (Blurred UPI Screenshot / Unverified UTR)
    if event.event_type == "PAYMENT_STATUS_CHANGE" or "paise bhej diye" in message_text.lower() or "payment" in message_text.lower():
        # Check if transaction ID is missing or ambiguous
        if "screenshot" in message_text.lower() or "upi" in message_text.lower():
            if not any(char.isdigit() for char in message_text) or len([c for c in message_text if c.isdigit()]) < 10:
                return (
                    True, 3, "AMBIGUOUS_PAYMENT_VERIFICATION",
                    "Payment claimed via screenshot or informal text without verifiable 12-digit bank UTR.",
                    ["HOLD_ORDER_RELEASE", "REQUIRE_OWNER_PAYMENT_CHECK"]
                )

    # 5. Severe Hostile Sentiment / Harassment (Sentiment < 0.35)
    if sentiment_score is not None and sentiment_score < SENTIMENT_CRITICAL_THRESHOLD:
        return (
            True, 3, "CRITICAL_NEGATIVE_SENTIMENT",
            f"Sentiment polarity score ({sentiment_score:.2f}) indicates severe customer distress or hostility.",
            ["PAUSE_BOT_RESPONSES", "DIVERT_TO_OWNER_HANDOFF"]
        )

    # --- LEVEL 2: Batch Review / Daily Digest Escalations ---

    # 6. Supplier Purchase Order (> ₹0) - 100% Mandatory Gated
    if is_procurement_po:
        return (
            True, 2, "SUPPLIER_PURCHASE_ORDER_OUTLAY",
            "Any supplier replenishment order spending business capital requires explicit owner review.",
            ["HOLD_SUPPLIER_PO_DISPATCH"]
        )

    # 7. Social Media Post / Photo Upload - 100% Mandatory Pre-Publication Approval
    if is_social_post or event.event_type in ["PHOTO_UPLOAD", "SCHEDULED_CAMPAIGN"]:
        # Also check third-party face consent if photo attached
        photo_ref = event.photo_ref
        if photo_ref and not photo_ref.consent_verified:
            return (
                True, 2, "UNVERIFIED_PHOTO_CONSENT",
                "Customer photo upload contains unverified third-party assets; requires explicit written consent before posting.",
                ["BLOCK_SOCIAL_PUBLISHING", "QUEUE_CONSENT_VERIFICATION"]
            )
        return (
            True, 2, "PRE_PUBLICATION_SOCIAL_APPROVAL",
            "All social media captions and media assets require owner preview before live publishing.",
            ["QUEUE_FOR_OWNER_APPROVAL"]
        )

    # 8. Low Model Confidence Score (< 0.85)
    if classification.confidence_score < MIN_CONFIDENCE_THRESHOLD:
        return (
            True, 2, "LOW_MODEL_CONFIDENCE",
            f"Classification confidence ({classification.confidence_score:.2f}) below quality threshold ({MIN_CONFIDENCE_THRESHOLD}).",
            ["QUEUE_PROPOSED_DRAFT_FOR_REVIEW"]
        )

    # --- LEVEL 1: Autonomous Execution ---
    return (
        False, 1, "AUTONOMOUS_STANDARD_FLOW",
        "Standard low-risk event within autonomous commercial guardrails.",
        []
    )
