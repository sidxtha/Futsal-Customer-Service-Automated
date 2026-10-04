"""Deterministic guardrails. The LLM suggests; these rules decide."""
import re
from .classifier import Classification

ALWAYS_HUMAN_CATEGORIES = {"refund", "complaint", "account"}

# Only these categories may get an automatic reply. Anything involving money,
# bookings or accounts stays with a human (or, later, with explicit tool calls).
AUTO_ANSWER_CATEGORIES = {"venue_info"}

# Categories where we may look up the customer's own payment/booking records (read-only).
INVESTIGATE_CATEGORIES = {"payment"}

# Cheap tripwire, NOT a real defence: easy to bypass, so never rely on it alone.
# A false positive only costs one human review.
INJECTION_PATTERNS = re.compile(
    r"ignore\s+(all\s+|any\s+)?(previous|prior|above)\s+(instructions?|prompts?)"
    r"|you\s+are\s+now\s+(in|an?)\s"
    r"|(admin|developer|debug)\s+mode"
    r"|(^|\n)\s*system\s*:"
    r"|reveal\s+(your|the)\s+(system\s+)?prompt",
    re.IGNORECASE,
)


def looks_like_injection(message: str) -> bool:
    return bool(message) and bool(INJECTION_PATTERNS.search(message))


def apply_rules(c: Classification, message: str = "") -> tuple[Classification, list[str]]:
    reasons = []
    if c.category in ALWAYS_HUMAN_CATEGORIES and not c.requires_human:
        reasons.append(f"category '{c.category}' always needs a human")
    if c.priority == "urgent" and not c.requires_human:
        reasons.append("urgent priority always needs a human")
    if looks_like_injection(message) and not c.requires_human:
        reasons.append("message contains instruction-like text aimed at the AI")
    if reasons:
        c = c.model_copy(update={"requires_human": True})
    return c, reasons


def can_auto_answer(c: Classification) -> bool:
    """Call on the classification AFTER apply_rules, so overrides are respected."""
    return (
        c.category in AUTO_ANSWER_CATEGORIES
        and c.priority == "low"
        and not c.requires_human
    )


def can_investigate(c: Classification, message: str) -> bool:
    """Read-only record lookup for payment problems. Never for injection-looking messages."""
    return c.category in INVESTIGATE_CATEGORIES and not looks_like_injection(message)