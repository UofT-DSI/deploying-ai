"""Function-calling service for structured planning tasks."""

from __future__ import annotations

import json
import re
from typing import Any

from .llm import create_response
from .memory import build_messages


TOOLS_QUERY_PATTERN = re.compile(
    r"\b(budget|itinerary|plan|packing|pack|checklist|split|allocate|cost)\b",
    re.IGNORECASE,
)


def is_tools_query(user_text: str) -> bool:
    """Detect prompts likely to benefit from structured planning tools."""
    return bool(TOOLS_QUERY_PATTERN.search(user_text or ""))


def budget_planner(
    destination: str,
    total_budget_usd: float,
    days: int,
    travelers: int = 1,
    style: str = "midrange",
) -> dict[str, Any]:
    """Return a practical category split for trip budget planning."""
    style_key = (style or "midrange").strip().lower()
    splits = {
        "budget": {"lodging": 0.3, "food": 0.25, "local_transport": 0.2, "activities": 0.15, "buffer": 0.1},
        "midrange": {"lodging": 0.4, "food": 0.25, "local_transport": 0.15, "activities": 0.15, "buffer": 0.05},
        "comfort": {"lodging": 0.5, "food": 0.25, "local_transport": 0.1, "activities": 0.1, "buffer": 0.05},
    }
    split = splits.get(style_key, splits["midrange"])

    budget = max(float(total_budget_usd), 0.0)
    day_count = max(int(days), 1)
    party_size = max(int(travelers), 1)

    allocations = {
        category: round(budget * ratio, 2) for category, ratio in split.items()
    }
    return {
        "destination": destination,
        "travel_style": style_key,
        "days": day_count,
        "travelers": party_size,
        "total_budget_usd": round(budget, 2),
        "per_day_usd": round(budget / day_count, 2),
        "per_person_per_day_usd": round(budget / (day_count * party_size), 2),
        "allocations_usd": allocations,
    }


def itinerary_generator(
    destination: str,
    days: int,
    interests: str = "landmarks, food, neighborhoods",
    pace: str = "balanced",
) -> dict[str, Any]:
    """Generate a lightweight day-by-day itinerary scaffold."""
    day_count = max(int(days), 1)
    themes = [piece.strip() for piece in interests.split(",") if piece.strip()]
    if not themes:
        themes = ["sightseeing", "food", "culture"]

    pace_key = pace.strip().lower() if pace else "balanced"
    pace_note = {
        "slow": "Keep one major activity and one flexible block.",
        "balanced": "Plan two anchor activities with breaks.",
        "fast": "Plan three anchor activities with efficient transit.",
    }.get(pace_key, "Plan two anchor activities with breaks.")

    day_plans: list[dict[str, Any]] = []
    for day in range(1, day_count + 1):
        theme = themes[(day - 1) % len(themes)]
        day_plans.append(
            {
                "day": day,
                "theme": theme,
                "morning": f"{theme.title()} focus near a central area in {destination}.",
                "afternoon": f"Second activity tied to {theme} with a lunch break.",
                "evening": "Low-effort evening option and transit plan back to lodging.",
            }
        )

    return {
        "destination": destination,
        "days": day_count,
        "pace": pace_key,
        "pace_guidance": pace_note,
        "plan": day_plans,
    }


def packing_list_generator(
    destination: str,
    trip_days: int,
    weather_summary: str = "",
    activities: str = "",
) -> dict[str, Any]:
    """Build a packing checklist from trip length, weather, and activities."""
    days = max(int(trip_days), 1)
    wx = (weather_summary or "").lower()
    acts = (activities or "").lower()

    clothing = ["3-5 tops", "2 bottoms", "sleepwear", "underwear/socks", "comfortable walking shoes"]
    essentials = ["passport/ID", "cards + some cash", "phone charger", "medications", "toiletries"]
    extras: list[str] = []

    if "rain" in wx or "shower" in wx:
        extras.append("compact umbrella or rain shell")
    if any(token in wx for token in ["cold", "chilly", "snow", "wind"]):
        extras.append("insulating layer and weatherproof outer layer")
    if any(token in acts for token in ["hike", "trail", "outdoor"]):
        extras.append("daypack and trail-friendly footwear")
    if "beach" in acts or "swim" in acts:
        extras.append("swimwear and quick-dry towel")

    return {
        "destination": destination,
        "trip_days": days,
        "recommended_items": {
            "clothing": clothing,
            "essentials": essentials,
            "extras": extras or ["none specific beyond standard travel items"],
        },
    }


TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "budget_planner",
        "description": "Split a trip budget into practical categories and per-day figures.",
        "parameters": {
            "type": "object",
            "properties": {
                "destination": {"type": "string"},
                "total_budget_usd": {"type": "number"},
                "days": {"type": "integer"},
                "travelers": {"type": "integer", "default": 1},
                "style": {"type": "string", "description": "budget, midrange, or comfort"},
            },
            "required": ["destination", "total_budget_usd", "days"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "itinerary_generator",
        "description": "Generate a day-by-day travel plan template.",
        "parameters": {
            "type": "object",
            "properties": {
                "destination": {"type": "string"},
                "days": {"type": "integer"},
                "interests": {"type": "string"},
                "pace": {"type": "string", "description": "slow, balanced, or fast"},
            },
            "required": ["destination", "days"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "packing_list_generator",
        "description": "Generate a practical packing list based on trip details.",
        "parameters": {
            "type": "object",
            "properties": {
                "destination": {"type": "string"},
                "trip_days": {"type": "integer"},
                "weather_summary": {"type": "string"},
                "activities": {"type": "string"},
            },
            "required": ["destination", "trip_days"],
            "additionalProperties": False,
        },
    },
]


def _execute_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Dispatch tool calls from model output to local Python functions."""
    if name == "budget_planner":
        return budget_planner(**args)
    if name == "itinerary_generator":
        return itinerary_generator(**args)
    if name == "packing_list_generator":
        return packing_list_generator(**args)
    return {"error": f"Unknown tool: {name}"}


def _parse_arguments(raw_arguments: str) -> dict[str, Any]:
    """Parse tool arguments emitted by the model into a dict payload."""
    if not raw_arguments:
        return {}
    parsed = json.loads(raw_arguments)
    return parsed if isinstance(parsed, dict) else {}


def handle_tools_query(user_text: str, *, history: list[dict] | None = None) -> str:
    """Run function-calling loop until model returns final text response."""
    instructions = (
        "You are TripSmith, a concise travel consultant.\n"
        "Use function tools when useful for calculations or structured planning.\n"
        "After tools run, provide a direct answer with clear numbers and assumptions."
    )
    conversation: list[Any] = build_messages(history=history, user_message=user_text, max_turns=8)

    try:
        response = create_response(
            instructions=instructions,
            input_items=conversation,
            tools=TOOLS,
        )
    except Exception as exc:  # noqa: BLE001
        return f"I could not run planning tools right now: {exc}"

    for _ in range(4):
        # The model can emit one or more tool calls per turn.
        function_calls = [item for item in response.output if item.type == "function_call"]
        if not function_calls:
            text = response.output_text.strip()
            if text:
                return text
            return "I could not generate a planning response for that request."

        conversation.extend(response.output)
        for call in function_calls:
            try:
                args = _parse_arguments(call.arguments)
                result = _execute_tool(call.name, args)
            except Exception as exc:  # noqa: BLE001
                result = {"error": str(exc), "tool": call.name}

            conversation.append(
                {
                    # Return tool result in responses API expected shape.
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps(result, ensure_ascii=True),
                }
            )

        response = create_response(
            instructions=instructions,
            input_items=conversation,
            tools=TOOLS,
        )

    return "I hit a tool-calling limit while planning. Please try a simpler request."
