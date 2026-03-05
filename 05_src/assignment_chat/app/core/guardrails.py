from __future__ import annotations

import re

# Restricted topics (must refuse)
RESTRICTED = [
    r"\bcats?\b",
    r"\bdogs?\b",
    r"\bhoroscopes?\b",
    r"\bzodiac\b",
    r"\btaylor\s+swift\b",
]

# Prompt injection / system prompt exfiltration (must refuse)
# IMPORTANT: keep these specific. Avoid generic phrases like "tell me".
PROMPT_ATTACK = [
    r"\bsystem\s+prompt\b",
    r"\bdeveloper\s+message\b",
    r"\binternal\s+instructions\b",
    r"\breveal\b.*\b(system|developer)\b",
    r"\bshow\b.*\b(system|developer)\b",
    r"\bprint\b.*\b(system|developer)\b",
    r"\bignore\b.*\b(instructions|previous)\b",
    r"\boverride\b.*\b(instructions|system)\b",
    r"\bjailbreak\b",
    r"\bprompt\s+injection\b",
]

# Allow safe memory/recall phrasing to pass without false positives
MEMORY_OR_RECALL = re.compile(
    r"^\s*(remember|note|save|store)\b|"
    r"\bwhat\s+did\s+i\s+(tell|say)\s+you\b|"
    r"\bwhat\s+did\s+i\s+mention\b|"
    r"\bwhat\s+did\s+i\s+ask\b|"
    r"\bdo\s+you\s+remember\b",
    re.IGNORECASE,
)

def check_guardrails(user_text: str) -> tuple[bool, str]:
    text = (user_text or "").strip()
    low = text.lower()

    # 1) Block prompt attacks (specific patterns only)
    for pat in PROMPT_ATTACK:
        if re.search(pat, low):
            return (
                False,
                "I can’t share or modify system/developer instructions. "
                "Tell me what you’re trying to do and I’ll help safely."
            )

    # 2) Allow memory/recall phrasing (prevents accidental blocks)
    if MEMORY_OR_RECALL.search(text):
        return (True, "")

    # 3) Block restricted topics
    for pat in RESTRICTED:
        if re.search(pat, low):
            return (False, "Sorry — I can’t help with that topic.")

    return (True, "")