"""Helpers for short-term conversation memory and destination carry-over."""

from __future__ import annotations

import re


TRAVEL_TO_PATTERN = re.compile(
    r"\b(?:going|travel(?:ing)?|flying|headed)\s+to\s+([A-Za-z][A-Za-z\s\-\.',]{1,60})\b",
    re.IGNORECASE,
)

LOCATION_PATTERN = re.compile(
    r"\b(?:in|for|at|near|visit(?:ing)?|staying in)\s+([A-Za-z][A-Za-z\s\-\.',]{1,60})\b",
    re.IGNORECASE,
)

TRAILING_LOCATION_NOISE = {
    "this",
    "today",
    "tomorrow",
    "tonight",
    "week",
    "weekend",
    "month",
    "year",
    "next",
    "current",
}

MONTH_WORDS = {
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
    "jan",
    "feb",
    "mar",
    "apr",
    "jun",
    "jul",
    "aug",
    "sep",
    "sept",
    "oct",
    "nov",
    "dec",
}

MONTH_PATTERN = (
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|"
    r"nov(?:ember)?|dec(?:ember)?)"
)

TEMPORAL_TAIL_PATTERN = re.compile(
    r"\b(?:in|on|during)\s+(?:this\s+|next\s+)?"
    r"(?:week|weekend|month|year|spring|summer|fall|autumn|winter|"
    + MONTH_PATTERN
    + r")\b.*$",
    re.IGNORECASE,
)


def _clean_location_candidate(raw_candidate: str) -> str | None:
    """Normalize location text extracted from historical user turns."""
    candidate = (raw_candidate or "").strip(" .,!?:;")
    if not candidate:
        return None

    candidate = re.split(
        r"\b(today|tomorrow|tonight|this weekend|weekend|next week|this week)\b",
        candidate,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip(" .,!?:;")
    candidate = TEMPORAL_TAIL_PATTERN.sub("", candidate).strip(" .,!?:;")

    tokens = [piece for piece in candidate.split() if piece]
    while tokens and tokens[-1].lower() in TRAILING_LOCATION_NOISE:
        tokens.pop()

    if not tokens:
        return None

    normalized = " ".join(tokens).strip()
    if normalized.lower() in MONTH_WORDS:
        return None
    return normalized


def sanitize_history(history: list[dict] | None) -> list[dict[str, str]]:
    """Keep only user/assistant text messages in a consistent shape."""
    cleaned: list[dict[str, str]] = []
    for item in history or []:
        role = item.get("role")
        content = item.get("content")
        if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
            cleaned.append({"role": role, "content": content.strip()})
    return cleaned


def build_messages(
    *,
    history: list[dict] | None,
    user_message: str,
    max_turns: int = 8,
) -> list[dict[str, str]]:
    """Construct bounded message context for model calls."""
    cleaned = sanitize_history(history)
    if max_turns > 0:
        cleaned = cleaned[-(max_turns * 2) :]
    cleaned.append({"role": "user", "content": user_message})
    return cleaned


def infer_recent_location(history: list[dict] | None) -> str | None:
    """Find most recent destination mention for follow-up weather prompts."""
    for item in reversed(sanitize_history(history)):
        if item["role"] != "user":
            continue
        text = item["content"]

        for pattern in (TRAVEL_TO_PATTERN, LOCATION_PATTERN):
            match = pattern.search(text)
            if not match:
                continue
            cleaned = _clean_location_candidate(match.group(1))
            if cleaned:
                return cleaned

    return None
