# services/bank_holidays_service.py — Service 1: UK Bank Holidays API

import requests
from datetime import date
from typing import Optional

# --- Constants ---
BANK_HOLIDAYS_URL = "https://www.gov.uk/bank-holidays.json"

REGION_MAP = {
    "england": "england-and-wales",
    "england and wales": "england-and-wales",
    "england & wales": "england-and-wales",
    "wales": "england-and-wales",
    "scotland": "scotland",
    "northern ireland": "northern-ireland",
    "ni": "northern-ireland",
}

# --- In-memory cache (fetch once per session) ---
_cache = None


def _fetch_data() -> dict:
    """Fetch and cache the full bank holidays JSON from gov.uk."""
    global _cache
    if _cache is None:
        response = requests.get(BANK_HOLIDAYS_URL, timeout=10)
        response.raise_for_status()
        _cache = response.json()
    return _cache


def normalize_region(region_input: str) -> Optional[str]:
    """
    Convert a user-friendly region name to the API key.
    Returns None if the region is not recognised.
    """
    return REGION_MAP.get(region_input.lower().strip(), None)


def get_holidays_in_range(region_input: str, start_str: str, end_str: str) -> dict:
    """
    Return all bank holidays for a region between start_str and end_str.

    Args:
        region_input: friendly name e.g. "Scotland"
        start_str:    start date as YYYY-MM-DD
        end_str:      end date   as YYYY-MM-DD

    Returns a structured dict — the LLM formats the final response.
    Possible keys:
        "error"    -> something went wrong (bad dates, unknown region, API failure)
        "prompt"   -> we need more info from the user (missing region)
        "holidays" -> list of matching holidays (may be empty with a "message" key)
    """

    # --- Validate region ---
    if not region_input or region_input.strip() == "":
        return {
            "prompt": "Which region would you like? Please choose one of: England & Wales, Scotland, or Northern Ireland."
        }

    region_key = normalize_region(region_input)
    if region_key is None:
        return {
            "prompt": (
                f"I didn't recognise '{region_input}' as a valid region. "
                "Please choose one of: England & Wales, Scotland, or Northern Ireland."
            )
        }

    # --- Validate dates ---
    try:
        start = date.fromisoformat(start_str)
        end = date.fromisoformat(end_str)
    except (ValueError, TypeError):
        return {"error": "Invalid date format. Please use YYYY-MM-DD (e.g. 2026-03-01)."}

    # Auto-swap reversed dates
    if start > end:
        start, end = end, start

    # --- Fetch & filter ---
    try:
        data = _fetch_data()
    except requests.RequestException as e:
        return {"error": f"Could not reach the bank holidays API: {e}"}

    if region_key not in data:
        return {"error": f"Region '{region_key}' was not found in the API response."}

    events = data[region_key].get("events", [])

    holidays = [
        {
            "title": e["title"],
            "date": e["date"],
            "notes": e.get("notes", ""),
        }
        for e in events
        if start <= date.fromisoformat(e["date"]) <= end
    ]

    # --- No results ---
    if not holidays:
        return {
            "message": (
                f"There are no bank holidays in {region_input.title()} "
                f"between {start_str} and {end_str}."
            ),
            "holidays": [],
        }

    return {
        "region": region_key,
        "start": str(start),
        "end": str(end),
        "count": len(holidays),
        "holidays": holidays,
    }