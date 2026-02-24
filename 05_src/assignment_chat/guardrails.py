import re
from typing import Tuple

BANNED_TOPICS = [
    r"\bcat(s)?\b",
    r"\bdog(s)?\b",
    r"\bhoroscope(s)?\b",
    r"\bzodiac\b",
    r"\btaylor\s+swift\b",
]

PROMPT_ATTACK_PATTERNS = [
    r"system prompt",
    r"developer prompt",
    r"reveal .*prompt",
    r"show .*prompt",
    r"ignore (all|the) previous instructions",
    r"override .*instructions",
    r"you are now (not|no longer)",
    r"act as (a|an) system",
]

def check_guardrails(user_msg: str) -> Tuple[bool, str]:
    """Returns (allowed, response_if_blocked)."""
    text = user_msg.lower()

    for pat in BANNED_TOPICS:
        if re.search(pat, text):
            return (False,
                "Request denied pursuant to Policy Appendix 7(b): this office does not process inquiries about "
                "cats/dogs, horoscopes/zodiac signs, or Taylor Swift. Please submit a different topic."
            )

    for pat in PROMPT_ATTACK_PATTERNS:
        if re.search(pat, text):
            return (False,
                "Denied. I can’t reveal or modify system/developer instructions. "
                "Please rephrase your request without referencing internal prompts."
            )

    return (True, "")