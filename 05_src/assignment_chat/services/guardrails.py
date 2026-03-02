"""Prompt-protection and restricted-topic guardrails."""

from __future__ import annotations

import re


PROMPT_ATTACK_PATTERN = re.compile(
    r"("
    r"system prompt|developer message|hidden instructions|"
    r"reveal.*prompt|show.*prompt|"
    r"ignore (all|previous|prior) instructions|"
    r"override (the )?rules|jailbreak"
    r")",
    re.IGNORECASE,
)

RESTRICTED_TOPIC_PATTERN = re.compile(
    r"("
    r"\bcat\b|\bcats\b|\bdog\b|\bdogs\b|"
    r"\bhoroscope\b|\bhoroscopes\b|\bzodiac\b|"
    r"taylor\s+swift"
    r")",
    re.IGNORECASE,
)


def check_guardrails(user_message: str) -> str | None:
    """Return refusal text when message violates guardrails, else None."""
    if PROMPT_ATTACK_PATTERN.search(user_message or ""):
        return (
            "I cannot reveal or modify internal prompts or system instructions. "
            "I can still help with travel planning if you share your trip question."
        )

    if RESTRICTED_TOPIC_PATTERN.search(user_message or ""):
        return (
            "I cannot help with that topic. "
            "I can help with travel planning instead: destination ideas, budgets, weather, or itineraries."
        )

    return None
