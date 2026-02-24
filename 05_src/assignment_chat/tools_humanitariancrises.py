from langchain.tools import tool
import requests
import json
from utils.logger import get_logger

_logs = get_logger(__name__)

BASE = "https://hapi.humdata.org/api/v2"

APP_IDENTIFIER = "YXNzaWdubWVudF9jaGF0OnlvdXIucmVhbC5lbWFpbEBkb21haW4uY29t"

HEADERS = {"X-HDX-HAPI-APP-IDENTIFIER": APP_IDENTIFIER}


@tool
def get_humanitarian_needs(country: str, start_date: str, end_date: str, limit: int = 500) -> str:
    """
    An API call to a humanitarian crises monitoring service is made.
    The API call is to https://hapi.humdata.org/api/v2.
    Returns a short summary of humanitarian needs by country

    start_date and end_date must be in YYYY-MM-DD format.
    """
    _logs.debug(f"Getting humanitarian needs for {country} from {start_date} to {end_date}")
    response = get_needs_from_service(country, limit)
    summary = get_needs_from_response(country, start_date, end_date, response)
    _logs.debug(f"Humanitarian needs result: {summary}")
    return summary


def get_needs_from_service(country: str, limit: int):
    url = f"{BASE}/affected-people/humanitarian-needs"
    params = {
        "location_name": country,
        "limit": limit
    }
    response = requests.get(url, headers=HEADERS, params=params, timeout=20)
    return response


def get_needs_from_response(country: str, start_date: str, end_date: str, response: requests.Response) -> str:
    resp_dict = json.loads(response.text)
    rows = resp_dict.get("data", [])

    if not rows:
        return f"No humanitarian needs data found for {country}."

    # Filter locally by reference period (simple string compare works for YYYY-MM-DD)
    filtered = []
    for item in rows:
        s = (item.get("reference_period_start") or "")[:10]
        e = (item.get("reference_period_end") or "")[:10]
        if not s or not e:
            continue
        if s >= start_date and e <= end_date:
            filtered.append(item)

    if not filtered:
        return (
            f"No rows matched the period {start_date} to {end_date} for {country} "
            f"(fetched {len(rows)} rows; you may need a larger limit or different dates)."
        )

    total_population = sum(item.get("population", 0) for item in filtered)

    summary = (
        f"Humanitarian needs summary for {country}:\n"
        f"- Period: {start_date} to {end_date}\n"
        f"- Total people targeted: {total_population:,}\n"
        f"- Records used: {len(filtered)} (from {len(rows)} fetched)"
    )

    return summary