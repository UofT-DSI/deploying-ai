"""The three services exposed to the chat model as tools.

1. get_weather          -> Open-Meteo public API (no key needed)
2. search_destinations  -> hybrid search: metadata filter + semantic ranking in ChromaDB, enriched with pandas
3. estimate_trip_budget -> local function called through function calling
"""
import pandas as pd
import requests

from config import CHROMA_PATH, COLLECTION_NAME, DATA_CSV, embed

# ---------------------------------------------------------------- Service 1: API
GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def _describe(code: int) -> str:
    """Translate Open-Meteo weather codes into words."""
    if code == 0:
        return "clear sky"
    if code in (1, 2, 3):
        return "partly cloudy"
    if code in (45, 48):
        return "fog"
    if 51 <= code <= 57:
        return "drizzle"
    if 61 <= code <= 67:
        return "rain"
    if 71 <= code <= 77:
        return "snow"
    if 80 <= code <= 82:
        return "rain showers"
    if code >= 95:
        return "thunderstorm"
    return "mixed conditions"


def get_weather(city: str, days: int = 3) -> dict:
    """Return current weather and a short forecast as structured data (the LLM turns it into prose)."""
    days = max(1, min(int(days), 7))
    try:
        geo = requests.get(
            GEO_URL, params={"name": city, "count": 1, "language": "en", "format": "json"}, timeout=10
        )
        geo.raise_for_status()
        results = geo.json().get("results")
        if not results:
            return {"error": f"Could not find a place called '{city}'."}
        place = results[0]

        fc = requests.get(
            FORECAST_URL,
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": "temperature_2m,wind_speed_10m,weather_code",
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                "timezone": "auto",
                "forecast_days": days,
            },
            timeout=10,
        )
        fc.raise_for_status()
        data = fc.json()
    except requests.RequestException:
        return {"error": "The weather service is not reachable right now."}

    daily = data["daily"]
    return {
        "place": f"{place['name']}, {place.get('country', '')}".strip(", "),
        "current": {
            "temperature_c": data["current"]["temperature_2m"],
            "wind_kmh": data["current"]["wind_speed_10m"],
            "conditions": _describe(data["current"]["weather_code"]),
        },
        "forecast": [
            {
                "date": daily["time"][i],
                "conditions": _describe(daily["weather_code"][i]),
                "max_c": daily["temperature_2m_max"][i],
                "min_c": daily["temperature_2m_min"][i],
                "rain_chance_pct": daily["precipitation_probability_max"][i],
            }
            for i in range(len(daily["time"]))
        ],
    }


# ------------------------------------------------- Service 2: semantic / hybrid query
_df = None
_collection = None


def _data() -> pd.DataFrame:
    global _df
    if _df is None:
        _df = pd.read_csv(DATA_CSV)
    return _df


def _col():
    global _collection
    if _collection is None:
        import chromadb

        _collection = chromadb.PersistentClient(path=str(CHROMA_PATH)).get_collection(COLLECTION_NAME)
    return _collection


def search_destinations(query: str, region: str | None = None, max_daily_budget: int | None = None, top_k: int = 3) -> dict:
    """Hybrid search: optional structured filters (region, budget) first, then semantic ranking."""
    filters = []
    if region:
        filters.append({"region": region})
    if max_daily_budget:
        filters.append({"daily_budget_usd": {"$lte": int(max_daily_budget)}})
    where = None if not filters else (filters[0] if len(filters) == 1 else {"$and": filters})

    top_k = max(1, min(int(top_k), 5))
    res = _col().query(query_embeddings=embed([query]), n_results=top_k, where=where)

    df = _data().set_index("name")
    matches = []
    for name, dist in zip(res["ids"][0], res["distances"][0]):
        row = df.loc[name]  # enrichment from the CSV
        matches.append(
            {
                "name": name,
                "country": row["country"],
                "region": row["region"],
                "best_season": row["best_season"],
                "daily_budget_usd": int(row["daily_budget_usd"]),
                "description": row["description"],
                "similarity": round(1 - dist, 3),
            }
        )
    if not matches:
        return {"matches": [], "note": "No destinations matched those filters."}
    return {"matches": matches}


# ------------------------------------------------------- Service 3: function calling
STYLE_MULTIPLIER = {"budget": 0.7, "mid-range": 1.0, "luxury": 2.0}


def estimate_trip_budget(destination: str, days: int, travelers: int = 1, style: str = "mid-range") -> dict:
    """Rough on-the-ground cost estimate (excludes flights)."""
    df = _data()
    hit = df[df["name"].str.lower() == destination.strip().lower()]
    if hit.empty:
        hit = df[df["name"].str.lower().str.contains(destination.strip().lower(), regex=False)]
    if hit.empty:
        return {"error": f"'{destination}' is not in my destination list, so I cannot estimate it."}

    days, travelers = max(1, int(days)), max(1, int(travelers))
    mult = STYLE_MULTIPLIER.get(style, 1.0)
    base = int(hit.iloc[0]["daily_budget_usd"])
    per_day = round(base * mult)
    return {
        "destination": hit.iloc[0]["name"],
        "style": style if style in STYLE_MULTIPLIER else "mid-range",
        "days": days,
        "travelers": travelers,
        "per_person_per_day_usd": per_day,
        "total_usd": per_day * days * travelers,
        "note": "Rough estimate for lodging, food and local transport; flights not included.",
    }
