"""Tool (function calling) schemas and a safe dispatcher."""
import json

from config import logger
from services import estimate_trip_budget, get_weather, search_destinations

REGIONS = ["Europe", "Asia", "Africa", "North America", "South America", "Oceania", "Middle East"]

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather and a short forecast for a city (live data).",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name, e.g. 'Lisbon'"},
                    "days": {"type": "integer", "description": "Forecast days, 1-7", "default": 3},
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_destinations",
            "description": "Find travel destinations that match a free-text description of what the traveller wants "
            "(semantic search). Optionally filter by region and maximum daily budget in USD.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What the traveller is looking for"},
                    "region": {"type": "string", "enum": REGIONS},
                    "max_daily_budget": {"type": "integer", "description": "Max daily budget per person, USD"},
                    "top_k": {"type": "integer", "default": 3},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "estimate_trip_budget",
            "description": "Estimate the on-the-ground cost of a trip to one of the known destinations (no flights).",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {"type": "string"},
                    "days": {"type": "integer"},
                    "travelers": {"type": "integer", "default": 1},
                    "style": {"type": "string", "enum": ["budget", "mid-range", "luxury"]},
                },
                "required": ["destination", "days"],
            },
        },
    },
]

_REGISTRY = {
    "get_weather": get_weather,
    "search_destinations": search_destinations,
    "estimate_trip_budget": estimate_trip_budget,
}


def dispatch(name: str, arguments: str) -> dict:
    """Run a tool requested by the model. Only whitelisted functions can be called."""
    fn = _REGISTRY.get(name)
    if fn is None:
        return {"error": "Unknown tool."}
    try:
        return fn(**json.loads(arguments or "{}"))
    except Exception:
        logger.exception("Tool %s failed", name)
        return {"error": "That tool failed. Tell the user you could not fetch this information."}
