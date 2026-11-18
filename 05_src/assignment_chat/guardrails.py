import re

# Simple assignment-level input guardrails; not a complete injection defense.
RESTRICTED = [r"\bcats?\b", r"\bdogs?\b", r"\bhoroscopes?\b",
              r"\bzodiac\b", r"\bastrolog(?:y|ical)\b",
              r"\btaylor\s+swift\b",
              r"\b(aries|taurus|gemini|cancer|leo|virgo|libra|scorpio|sagittarius|capricorn|aquarius|pisces)\b"]
PROMPT_ATTACK = [r"\bsystem\s+prompt\b", r"\bdeveloper\s+(?:prompt|instructions?)\b",
                 r"\b(?:reveal|show|print|repeat|change|modify|override)\b.{0,50}\b(?:instructions?|prompt)\b",
                 r"\bignore\b.{0,40}\b(?:previous|prior|system)\b"]

def blocked_request(message: str) -> bool:
    return any(re.search(pattern, message, re.IGNORECASE) for pattern in RESTRICTED + PROMPT_ATTACK)
