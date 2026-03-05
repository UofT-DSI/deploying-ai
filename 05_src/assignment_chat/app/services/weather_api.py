from __future__ import annotations

import requests
from dataclasses import dataclass

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


@dataclass
class WeatherSummary:
    name: str
    country: str
    lat: float
    lon: float
    timezone: str
    temp_c: float | None
    wind_kph: float | None
    daily_max_c: float | None
    daily_min_c: float | None
    precip_prob_max: float | None


def _first(result: list[dict]) -> dict | None:
    return result[0] if result else None


def get_weather_for_city(city: str) -> WeatherSummary:
    # 1) geocode city -> lat/lon
    geo = requests.get(
        GEOCODE_URL,
        params={"name": city, "count": 1, "language": "en", "format": "json"},
        timeout=15,
    )
    geo.raise_for_status()
    g = geo.json()
    loc = _first(g.get("results", []))
    if not loc:
        raise ValueError(f"Could not find a location for '{city}'.")

    lat, lon = float(loc["latitude"]), float(loc["longitude"])
    name = str(loc.get("name", city))
    country = str(loc.get("country", ""))
    tz = str(loc.get("timezone", "auto"))

    # 2) forecast
    forecast = requests.get(
        FORECAST_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,wind_speed_10m",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "timezone": "auto",
        },
        timeout=15,
    )
    forecast.raise_for_status()
    f = forecast.json()

    current = f.get("current", {}) or {}
    daily = f.get("daily", {}) or {}

    # Use today's daily values (index 0)
    def _idx0(arr):
        return arr[0] if isinstance(arr, list) and arr else None

    return WeatherSummary(
        name=name,
        country=country,
        lat=lat,
        lon=lon,
        timezone=str(f.get("timezone", tz)),
        temp_c=current.get("temperature_2m"),
        wind_kph=current.get("wind_speed_10m"),
        daily_max_c=_idx0(daily.get("temperature_2m_max")),
        daily_min_c=_idx0(daily.get("temperature_2m_min")),
        precip_prob_max=_idx0(daily.get("precipitation_probability_max")),
    )