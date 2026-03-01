import re
from typing import Optional

BLOCKED_TOPICS = [
    r"\bcats?\b",
    r"\bdogs?\b",
    r"\bhoroscope(s)?\b",
    r"\bzodiac\b",
    r"\btaylor\s+swift\b",
]

PROMPT_ATTACK_PATTERNS = [
    r"reveal\s+.*system\s+prompt",
    r"show\s+.*system\s+prompt",
    r"print\s+.*system\s+prompt",
    r"what\s+is\s+your\s+system\s+prompt",
    r"ignore\s+(all|previous)\s+instructions",
    r"overwrite\s+.*system\s+prompt",
    r"change\s+.*system\s+prompt",
    r"developer\s+message",
    r"jailbreak",
]

TOPIC_BLOCK_REPLY = "I can’t help with that topic. Please ask about weather, semantic search, or study planning instead."
PROMPT_BLOCK_REPLY = "I can’t reveal or modify system instructions, but I can still help with weather, semantic search, or study planning."


def evaluate_guardrails(message: str) -> Optional[str]:
    text = (message or "").strip().lower()

    for pattern in BLOCKED_TOPICS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return TOPIC_BLOCK_REPLY

    for pattern in PROMPT_ATTACK_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return PROMPT_BLOCK_REPLY

    return None
