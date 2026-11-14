"""Weather API service for the Assignment 2 sample."""

import requests
from langchain.tools import tool


@tool
def get_weather(city: str) -> str:
    """Get the current temperature and wind speed for a city."""
    places = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                          params={"name": city, "count": 1}, timeout=10)
    places.raise_for_status()
    matches = places.json().get("results") or []
    if not matches:
        return f"Open-Meteo could not find a location named {city}."
    place = matches[0]
    forecast = requests.get("https://api.open-meteo.com/v1/forecast",
                            params={"latitude": place["latitude"], "longitude": place["longitude"],
                                    "current": "temperature_2m,wind_speed_10m"}, timeout=10)
    forecast.raise_for_status()
    current = forecast.json()["current"]
    return (f"Open-Meteo reports {current['temperature_2m']} °C and wind near "
            f"{current['wind_speed_10m']} km/h in {place['name']} right now.")
