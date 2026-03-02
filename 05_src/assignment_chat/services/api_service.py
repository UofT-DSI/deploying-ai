"""Weather service built on Open-Meteo with deterministic parsing + LLM rewrite."""

from __future__ import annotations

import json
import re
import ssl
import time
import urllib.parse
import urllib.error
import urllib.request
from typing import Any

from .llm import create_response
from .memory import infer_recent_location


WEATHER_KEYWORDS = re.compile(
    r"\b("
    r"weather|forecast|temperature|temp|rain|snow|wind|humid|humidity|storm|sunny|cloudy|"
    r"jacket|coat|umbrella|wear"
    r")\b",
    re.IGNORECASE,
)

LOCATION_PATTERN = re.compile(
    r"\b(?:in|for|at|near)\s+([A-Za-z][A-Za-z\s\-\.',]{1,80})\b",
    re.IGNORECASE,
)

TRAVEL_TO_PATTERN = re.compile(
    r"\b(?:going|travel(?:ing)?|flying|headed)\s+to\s+([A-Za-z][A-Za-z\s\-\.',]{1,80})\b",
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

WEATHER_CODE_MAP = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "rime fog",
    51: "light drizzle",
    53: "moderate drizzle",
    55: "dense drizzle",
    61: "slight rain",
    63: "moderate rain",
    65: "heavy rain",
    71: "slight snow",
    73: "moderate snow",
    75: "heavy snow",
    80: "rain showers",
    81: "moderate rain showers",
    82: "heavy rain showers",
    95: "thunderstorm",
}


def is_weather_query(user_text: str) -> bool:
    """Detect weather/packing intent for router-level service selection."""
    return bool(WEATHER_KEYWORDS.search(user_text or ""))


def _clean_location_candidate(raw_candidate: str) -> str | None:
    """Normalize extracted place text and strip trailing temporal fragments."""
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


def _http_get_json(url: str, timeout_s: int = 12) -> dict[str, Any]:
    """Fetch JSON with retries and SSL fallbacks for unstable local network setups."""
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "TripSmith/1.0", "Accept": "application/json"},
        method="GET",
    )

    last_error: Exception | None = None
    contexts = [
        ssl.create_default_context(),
        ssl._create_unverified_context(),  # fallback for strict/legacy TLS environments
    ]

    for attempt in range(3):
        # Retry across SSL contexts to handle local certificate/TLS issues.
        for context in contexts:
            try:
                with urllib.request.urlopen(
                    request,
                    timeout=timeout_s,
                    context=context,
                ) as response:
                    payload = response.read().decode("utf-8", errors="replace")
                return json.loads(payload)
            except (
                urllib.error.URLError,
                urllib.error.HTTPError,
                ssl.SSLError,
                json.JSONDecodeError,
            ) as exc:
                last_error = exc
        time.sleep(0.25 * (attempt + 1))

    # Final fallback keeps the service alive if urllib SSL stack still fails.
    try:
        import requests

        response = requests.get(
            url,
            headers={"User-Agent": "TripSmith/1.0", "Accept": "application/json"},
            timeout=timeout_s,
        )
        response.raise_for_status()
        return response.json()
    except Exception as exc:  # noqa: BLE001
        if last_error is None:
            last_error = exc
        raise RuntimeError(f"Network error while calling weather API: {last_error}") from exc


def _extract_location_hint(user_text: str) -> str | None:
    """Best-effort location extraction from natural travel/weather prompts."""
    text = user_text or ""

    for pattern in (TRAVEL_TO_PATTERN, LOCATION_PATTERN):
        match = pattern.search(text)
        if not match:
            continue
        cleaned = _clean_location_candidate(match.group(1))
        if cleaned:
            return cleaned

    stripped = text.strip()
    if stripped and len(stripped.split()) <= 4 and not is_weather_query(stripped):
        return _clean_location_candidate(stripped)
    return None


def _geocode(place_query: str) -> dict[str, Any]:
    """Resolve free-text place query to coordinates using Open-Meteo geocoding."""
    encoded_query = urllib.parse.quote(place_query.strip())
    url = (
        "https://geocoding-api.open-meteo.com/v1/search"
        f"?name={encoded_query}&count=1&language=en&format=json"
    )
    data = _http_get_json(url)
    results = data.get("results") or []
    if not results:
        raise RuntimeError(
            f"I could not find coordinates for '{place_query}'. Try city plus country."
        )
    return results[0]


def _fetch_forecast(latitude: float, longitude: float, days: int = 3) -> dict[str, Any]:
    """Fetch a compact weather payload suitable for short chat responses."""
    clamped_days = max(1, min(days, 7))
    params = urllib.parse.urlencode(
        {
            "latitude": str(latitude),
            "longitude": str(longitude),
            "timezone": "auto",
            "current_weather": "true",
            "forecast_days": str(clamped_days),
            "daily": ",".join(
                [
                    "weathercode",
                    "temperature_2m_max",
                    "temperature_2m_min",
                    "precipitation_sum",
                    "windspeed_10m_max",
                ]
            ),
        }
    )
    return _http_get_json(f"https://api.open-meteo.com/v1/forecast?{params}")


def _normalize_number(value: Any) -> float | None:
    """Normalize weather numbers for stable formatting and prompt brevity."""
    if value is None:
        return None
    try:
        return round(float(value), 1)
    except (TypeError, ValueError):
        return None


def _condition_from_code(code: Any) -> str:
    """Map Open-Meteo weather code to short human-readable description."""
    try:
        return WEATHER_CODE_MAP.get(int(code), "mixed conditions")
    except (TypeError, ValueError):
        return "mixed conditions"


def _build_weather_facts(place: dict[str, Any], forecast: dict[str, Any]) -> dict[str, Any]:
    """Transform raw API payload into a compact, deterministic fact schema."""
    current = forecast.get("current_weather") or forecast.get("current") or {}
    daily = forecast.get("daily") or {}

    daily_codes = daily.get("weathercode") or daily.get("weather_code") or []
    daily_dates = daily.get("time") or []
    daily_high = daily.get("temperature_2m_max") or []
    daily_low = daily.get("temperature_2m_min") or []
    daily_precip = daily.get("precipitation_sum") or []
    daily_wind = daily.get("windspeed_10m_max") or daily.get("wind_speed_10m_max") or []

    place_bits = [place.get("name", "Unknown location")]
    if place.get("admin1"):
        place_bits.append(place["admin1"])
    if place.get("country"):
        place_bits.append(place["country"])
    place_label = ", ".join([bit for bit in place_bits if bit])

    days: list[dict[str, Any]] = []
    for idx, date in enumerate(daily_dates[:5]):
        days.append(
            {
                "date": date,
                "hi_c": _normalize_number(daily_high[idx] if idx < len(daily_high) else None),
                "lo_c": _normalize_number(daily_low[idx] if idx < len(daily_low) else None),
                "precip_mm": _normalize_number(
                    daily_precip[idx] if idx < len(daily_precip) else None
                ),
                "wind_kmh": _normalize_number(daily_wind[idx] if idx < len(daily_wind) else None),
                "condition": _condition_from_code(
                    daily_codes[idx] if idx < len(daily_codes) else None
                ),
            }
        )

    current_temp = current.get("temperature")
    if current_temp is None:
        current_temp = current.get("temperature_2m")
    current_wind = current.get("windspeed")
    if current_wind is None:
        current_wind = current.get("wind_speed_10m")
    current_code = current.get("weathercode")
    if current_code is None:
        current_code = current.get("weather_code")

    return {
        "place": place_label,
        "timezone": forecast.get("timezone", "local"),
        "current": {
            "temp_c": _normalize_number(current_temp),
            "wind_kmh": _normalize_number(current_wind),
            "condition": _condition_from_code(current_code),
        },
        "daily": days,
    }


def _fallback_weather_text(facts: dict[str, Any]) -> str:
    """Deterministic response used when the rewrite model call is unavailable."""
    current = facts.get("current", {})
    lines = [
        f"Weather for {facts.get('place', 'your destination')} ({facts.get('timezone', 'local')}).",
        (
            "Right now: "
            f"{current.get('temp_c', 'N/A')} C, {current.get('condition', 'mixed conditions')}, "
            f"wind {current.get('wind_kmh', 'N/A')} km/h."
        ),
    ]
    for item in facts.get("daily", [])[:3]:
        lines.append(
            (
                f"{item.get('date')}: {item.get('condition')}, high {item.get('hi_c')} C, "
                f"low {item.get('lo_c')} C, precip {item.get('precip_mm')} mm, "
                f"wind {item.get('wind_kmh')} km/h."
            )
        )
    return "\n".join(lines)


def _rewrite_weather_with_llm(facts: dict[str, Any]) -> str:
    """Rewrite facts in TripSmith tone while prohibiting number invention."""
    instructions = (
        "You are TripSmith, a concise and practical travel consultant.\n"
        "Rewrite the weather facts into plain travel advice.\n"
        "Rules:\n"
        "1) Use only the numbers and facts provided.\n"
        "2) Do not invent temperatures, wind, precipitation, or dates.\n"
        "3) Keep the response under 140 words.\n"
        "4) End with one short packing recommendation."
    )
    response = create_response(
        instructions=instructions,
        input_items=[
            {
                "role": "user",
                "content": "Weather facts JSON:\n" + json.dumps(facts, ensure_ascii=True),
            }
        ],
    )
    return response.output_text.strip()


def handle_weather_query(
    user_text: str,
    *,
    history: list[dict] | None = None,
    default_days: int = 3,
) -> str:
    """End-to-end weather flow: extract place -> geocode -> forecast -> rewrite."""
    location = _extract_location_hint(user_text) or infer_recent_location(history)
    if not location:
        return (
            "I can help with weather planning. Share a location, for example: "
            "`Lisbon, Portugal` or `Tokyo, Japan`."
        )

    try:
        place = _geocode(location)
        forecast = _fetch_forecast(
            latitude=float(place["latitude"]),
            longitude=float(place["longitude"]),
            days=default_days,
        )
        facts = _build_weather_facts(place, forecast)
    except Exception as exc:  # noqa: BLE001
        return f"I could not fetch weather data right now: {exc}"

    try:
        return _rewrite_weather_with_llm(facts)
    except Exception:  # noqa: BLE001
        return _fallback_weather_text(facts)
