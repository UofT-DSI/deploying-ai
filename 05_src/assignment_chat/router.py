# router.py — detects intent and dispatches to the correct service

import re
from guardrails.policy import check_message

# --- Intent detection keywords ---
BANK_HOLIDAY_KEYWORDS = [
    "bank holiday", "public holiday", "bank holidays",
    "holiday in", "holidays in", "holiday between", "holidays between",
]

MITRE_KEYWORDS = [
    "mitre", "technique", "attack technique", "ttp", "ttps",
    "tactic", "exfiltration", "discovery", "t1", "t10", "t11", "t12", "t13",
    "what technique", "which technique", "how do attackers",
]

# Strong signals that indicate a pasted alert (not a general cybersecurity question)
ALERT_KEYWORDS = [
    "alert:", "severity:", "source: microsoft", "source: defender",
    "defender for endpoint", "defender for office", "microsoft sentinel",
    "high severity", "medium severity", "low severity",
    "triage", "ioc", "incident id",
]


def detect_intent(user_input: str) -> str:
    """
    Returns one of: 'blocked', 'bank_holiday', 'mitre_search', 'soc_triage', 'chat'
    """
    # 1 — Guardrails first
    block_response = check_message(user_input)
    if block_response:
        return "blocked"

    lowered = user_input.lower()

    # 2 — Bank holiday intent
    if any(kw in lowered for kw in BANK_HOLIDAY_KEYWORDS):
        return "bank_holiday"

    # 3 — SOC triage intent (checked before MITRE to catch pasted alerts first)
    if any(kw in lowered for kw in ALERT_KEYWORDS):
        return "soc_triage"

    # 4 — MITRE search intent
    if any(kw in lowered for kw in MITRE_KEYWORDS):
        return "mitre_search"

    # 5 — Default: normal conversation
    return "chat"


def extract_date_range(user_input: str):
    """
    Try to extract start_date and end_date from the user message.
    Returns (start, end) as strings in YYYY-MM-DD, or (None, None).
    """
    dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", user_input)
    if len(dates) >= 2:
        return dates[0], dates[1]
    return None, None


def extract_region(user_input: str) -> str:
    """Extract a region name from the user message."""
    lowered = user_input.lower()
    if "scotland" in lowered:
        return "scotland"
    if "northern ireland" in lowered or " ni " in lowered:
        return "northern ireland"
    if "wales" in lowered:
        return "wales"
    return "england"  # default
