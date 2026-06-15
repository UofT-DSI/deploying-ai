from langchain.tools import tool
import requests
import json
from utils.logger import get_logger

_logs = get_logger(__name__)


@tool
def get_horoscope(sign: str, date: str = "TODAY") -> str:
    """
    An API call to a horoscope service is made.
    The API call is to https://horoscope-app-api.vercel.app/api/v1/get-horoscope/daily
    and takes two parameters sign and date.
    Accepted values for sign are: Aries, Taurus, Gemini, Cancer, Leo, Virgo, Libra, Scorpio, Sagittarius, Capricorn, Aquarius, Pisces
    Accepted values for date are: Date in format (YYYY-MM-DD) OR "TODAY" OR "TOMORROW" OR "YESTERDAY".
    """
    _logs.debug("get_horoscope: sign=%s date=%s", sign, date)
    try:
        response = get_horoscope_from_service(sign, date)
        horoscope = get_horoscope_from_response(sign, response)
    except requests.RequestException as exc:
        _logs.error("get_horoscope: request failed for sign=%s: %s", sign, exc)
        return f"Could not retrieve horoscope for {sign} (network error)."
    _logs.debug("get_horoscope: result for sign=%s: %s", sign, horoscope[:80])
    return horoscope


def get_horoscope_from_service(sign: str, day: str) -> requests.Response:
    url = "https://horoscope-app-api.vercel.app/api/v1/get-horoscope/daily"
    params = {"sign": sign.capitalize(), "day": day.upper()}
    _logs.debug("get_horoscope_from_service: GET %s params=%s", url, params)
    response = requests.get(url, params=params, timeout=10)
    _logs.debug("get_horoscope_from_service: HTTP %d", response.status_code)
    if not response.ok:
        _logs.warning(
            "get_horoscope_from_service: non-OK status %d for sign=%s day=%s",
            response.status_code, sign, day,
        )
    return response


def get_horoscope_from_response(sign: str, response: requests.Response) -> str:
    try:
        resp_dict = json.loads(response.text)
    except json.JSONDecodeError as exc:
        _logs.error("get_horoscope_from_response: JSON parse failed for sign=%s: %s", sign, exc)
        return f"Could not parse horoscope response for {sign}."
    data = resp_dict.get("data") or {}
    horoscope_data = data.get("horoscope_data", "No horoscope found.")
    date = data.get("date", "No date found.")
    return f"Horoscope for {sign.capitalize()} on {date}: {horoscope_data}"
