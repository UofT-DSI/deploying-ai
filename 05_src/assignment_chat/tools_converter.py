# Service 3: Currency Conversion via Function Calling + External API
# Adapted from course_chat/tools_animals.py - same @tool decorator pattern.
# Uses the free Open Exchange Rates API (no API key required for latest rates).
# API docs: https://www.exchangerate-api.com/docs/free

from langchain.tools import tool
import requests
import json
from utils.logger import get_logger

_logs = get_logger(__name__)

API_BASE = "https://open.er-api.com/v6/latest"


@tool
def convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
    """
    Converts an amount from one currency to another using live exchange rates.
    Calls the Open Exchange Rates API (no API key required).
    from_currency and to_currency must be ISO 4217 currency codes, e.g. USD, EUR, CAD, GBP, JPY.
    Example: convert_currency(100, 'USD', 'EUR') -> live conversion result.
    """
    _logs.debug(f"Converting {amount} {from_currency} -> {to_currency}")
    response = _get_rates_from_service(from_currency.upper())
    result = _parse_conversion_response(amount, from_currency.upper(), to_currency.upper(), response)
    _logs.debug(f"Conversion result: {result}")
    return result


def _get_rates_from_service(base_currency: str) -> requests.Response:
    url = f"{API_BASE}/{base_currency}"
    response = requests.get(url)
    return response


def _parse_conversion_response(
    amount: float,
    from_currency: str,
    to_currency: str,
    response: requests.Response,
) -> str:
    resp_dict = json.loads(response.text)

    if resp_dict.get("result") != "success":
        return f"Could not retrieve exchange rates for {from_currency}. Please check the currency code."

    rates = resp_dict.get("rates", {})
    rate = rates.get(to_currency)

    if rate is None:
        return f"Currency code '{to_currency}' not found. Use standard ISO 4217 codes (e.g. USD, EUR, CAD)."

    converted = amount * rate
    last_updated = resp_dict.get("time_last_update_utc", "unknown")

    return (
        f"{amount:,.2f} {from_currency} = {converted:,.2f} {to_currency}\n"
        f"  Exchange rate: 1 {from_currency} = {rate:.6f} {to_currency}\n"
        f"  Rates last updated: {last_updated}"
    )
