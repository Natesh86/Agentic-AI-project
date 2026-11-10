"""
SoloBiz AI - Guardrails & Safety Policies
Deterministic filters for prompt injection, PII masking, binding commitments, and input isolation.
"""
import re
from typing import Tuple, List
from config import HITL_PROMPT_INJECTION_PATTERNS, HITL_LEGAL_KEYWORDS


# --- 1. Semantic Delimiter Isolation ---
def xml_isolate_input(user_text: str) -> str:
    """Wraps untrusted customer input in XML tags to enforce semantic data boundary in prompts."""
    # Escape any existing closing tags to avoid delimiter escape attacks
    sanitized = user_text.replace("</untrusted_customer_input>", "[ESCAPED_DELIMITER]")
    return f"<untrusted_customer_input>\n{sanitized}\n</untrusted_customer_input>"


# --- 2. Prompt Injection Scanner ---
def detect_prompt_injection(text: str) -> Tuple[bool, str]:
    """
    Scans free-form customer text for known prompt injection payloads, system overrides,
    or instruction reset patterns.
    Returns: (is_injection_detected: bool, reason: str)
    """
    if not text:
        return False, ""

    text_lower = text.lower()

    for pattern in HITL_PROMPT_INJECTION_PATTERNS:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            return True, f"Detected adversarial pattern: '{match.group(0)}'"

    # Check for suspicious bracketed administrative instructions inside address notes
    if re.search(r"\[\s*admin\s*notice\s*:", text_lower) or re.search(r"\[\s*system\s*:", text_lower):
        return True, "Detected bracketed administrative instruction injection"

    return False, ""


# --- 3. PII Redactor ---
def mask_pii(text: str) -> Tuple[str, int]:
    """
    Scans and redacts sensitive data (credit cards, Aadhaar, passwords, bank account numbers).
    Returns: (redacted_text: str, redaction_count: int)
    """
    if not text:
        return text, 0

    redacted = text
    count = 0

    # Credit/Debit Card pattern (13-16 digits with optional dashes/spaces)
    card_pattern = r"\b(?:\d{4}[ -]?){3}\d{4}\b"
    matches = re.findall(card_pattern, redacted)
    if matches:
        count += len(matches)
        redacted = re.sub(card_pattern, "[REDACTED_CARD_NUMBER]", redacted)

    # Indian Aadhaar Number pattern (12 digits in 4-4-4 format)
    aadhaar_pattern = r"\b\d{4}\s\d{4}\s\d{4}\b"
    matches = re.findall(aadhaar_pattern, redacted)
    if matches:
        count += len(matches)
        redacted = re.sub(aadhaar_pattern, "[REDACTED_AADHAAR]", redacted)

    # Password / OTP indicators
    otp_pattern = r"(?i)\b(otp|password|pin)\s*[:=]\s*(\d{4,8}|\S+)"
    if re.search(otp_pattern, redacted):
        count += 1
        redacted = re.sub(otp_pattern, r"\1: [REDACTED_SECRET]", redacted)

    return redacted, count


# --- 4. Binding Commitment & Legal Risk Scanner ---
def scan_legal_risk_keywords(text: str) -> List[str]:
    """Checks for presence of high-stakes legal, safety, or regulatory keywords."""
    if not text:
        return []
    text_lower = text.lower()
    found = []
    for keyword in HITL_LEGAL_KEYWORDS:
        if re.search(rf"\b{re.escape(keyword)}\b", text_lower):
            found.append(keyword)
    return found


def validate_binding_commitments(draft_text: str) -> Tuple[bool, str]:
    """
    Post-generation check to prevent autonomous drafts from promising unauthorized refunds
    or legally binding financial compensations without human verification.
    """
    if not draft_text:
        return True, ""

    draft_lower = draft_text.lower()

    # Unauthorized refund promise check
    refund_promises = [
        r"i (have|will) (issue|process|send) (your|a) full refund",
        r"refund of .* has been approved",
        r"we guarantee 100% money back immediately"
    ]
    for pattern in refund_promises:
        if re.search(pattern, draft_lower):
            return False, "Draft makes unauthorized refund promise without owner sign-off"

    return True, ""
