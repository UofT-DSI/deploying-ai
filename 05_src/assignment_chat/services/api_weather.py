import requests
from typing import Dict, Any
from ..llm import get_client

def _geocode_city(city: str) -> Dict[str, Any]:
    url = "https://geocoding-api.open-meteo.com/v1/search"
    r = requests.get(url, params={"name": city, "count": 1, "language": "en", "format": "json"}, timeout=20)
    r.raise_for_status()
    data = r.json()
    if not data.get("results"):
        return {}
    return data["results"][0]

def get_weather(city: str) -> str:
    geo = _geocode_city(city)
    if not geo:
        return f"Regretfully, the location '{city}' could not be found in the registry."

    lat, lon = geo["latitude"], geo["longitude"]

    url = "https://api.open-meteo.com/v1/forecast"
    r = requests.get(
        url,
        params={
            "latitude": lat,
            "longitude": lon,
            "current_weather": True,
            "timezone": "auto",
        },
        timeout=20,
    )
    r.raise_for_status()
    wx = r.json().get("current_weather", {})

    client = get_client()
    dev = "Rewrite weather API output into a friendly, bureaucratic status memo. Do not output raw JSON."
    user = f"City: {geo.get('name')}, {geo.get('country')} | Current weather payload: {wx}"
    resp = client.responses.create(
        model="gpt-4o-mini",
        input=[
            {"role": "developer", "content": dev},
            {"role": "user", "content": user},
        ],
    )
    return resp.output[0].content[0].text