from __future__ import annotations

import json
from datetime import datetime
import re
from typing import Any

import requests
from openai import OpenAI

from .config import MODEL_NAME, get_openai_client_kwargs, get_weatherstack_api_key, has_openai_access
from .semantic_service import answer_from_course_materials


def _normalize_city_query(city: str) -> str:
    cleaned = (city or "").strip()
    cleaned = re.sub(r"^\s*(in|at|for)\s+", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+(today|tomorrow|now|right now|currently)\s*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned)
    known_aliases = {
        "halifax": "Halifax, Nova Scotia, Canada",
        "novascotia": "Halifax, Canada",
        "nova scotia": "Halifax, Canada",
    }
    key = cleaned.lower().replace(" ", "")
    if key in known_aliases:
        return known_aliases[key]
    return cleaned.strip(" ,")


def _extract_city(user_text: str) -> str:
    text = (user_text or "").strip()
    if not text:
        return ""

    tail_pattern = re.search(
        r"\b(?:in|for|at)\s+([a-zA-Z][a-zA-Z\s\.'-]*[a-zA-Z])\s*(?:today|tomorrow|now|currently)?\s*$",
        text,
        flags=re.IGNORECASE,
    )
    if tail_pattern:
        return _normalize_city_query(tail_pattern.group(1))

    text = re.sub(r"^\s*/?(weather|forecast)\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(next\s+\d+\s*day[s]?)\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(weather|forecast|today|tomorrow|now|currently|be|will)\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip(" ,")
    return _normalize_city_query(text)


def _parse_forecast_request(user_text: str) -> tuple[int, bool]:
    text = (user_text or "").lower()
    if not text:
        return 0, False

    days_match = re.search(r"\b(?:next\s+)?(\d{1,2})\s*day[s]?\b", text)
    if days_match:
        days = max(1, min(int(days_match.group(1)), 7))
        return days, False

    if "tomorrow" in text:
        return 2, True

    if "forecast" in text:
        return 3, False

    return 0, False


def _weatherstack_summary(city: str) -> str:
    weatherstack_key = get_weatherstack_api_key()
    if not weatherstack_key:
        return ""

    response = requests.get(
        "http://api.weatherstack.com/current",
        params={
            "access_key": weatherstack_key,
            "query": city,
            "units": "m",
        },
        timeout=20,
    )

    if response.status_code != 200:
        return ""

    payload = response.json()
    if payload.get("success") is False:
        return ""

    location = payload.get("location", {})
    current = payload.get("current", {})
    if not location or not current:
        return ""

    city_name = location.get("name", city)
    region = location.get("region", "")
    country = location.get("country", "")
    temperature = current.get("temperature", "?")
    humidity = current.get("humidity", "?")
    wind_speed = current.get("wind_speed", "?")
    description = ", ".join(current.get("weather_descriptions", [])) or "current conditions"

    place = ", ".join(part for part in [city_name, region, country] if part)
    return (
        f"Current weather in {place}: {description.lower()}, about {temperature}°C, "
        f"humidity near {humidity}%, and wind around {wind_speed} km/h."
    )


def _weatherstack_forecast(city: str, forecast_days: int, tomorrow_only: bool = False) -> str:
    weatherstack_key = get_weatherstack_api_key()
    if not weatherstack_key:
        return ""

    response = requests.get(
        "http://api.weatherstack.com/forecast",
        params={
            "access_key": weatherstack_key,
            "query": city,
            "forecast_days": max(1, min(forecast_days, 7)),
            "units": "m",
        },
        timeout=20,
    )
    if response.status_code != 200:
        return ""

    payload = response.json()
    if payload.get("success") is False:
        return ""

    location = payload.get("location", {})
    forecast = payload.get("forecast", {})
    if not location or not forecast:
        return ""

    place = ", ".join(
        part for part in [location.get("name", city), location.get("region", ""), location.get("country", "")] if part
    )
    dates = sorted(forecast.keys())
    if not dates:
        return ""

    if tomorrow_only:
        idx = 1 if len(dates) > 1 else 0
        date_key = dates[idx]
        day = forecast.get(date_key, {})
        hourly = day.get("hourly", [])
        desc = ""
        if hourly and isinstance(hourly, list):
            mid = hourly[min(len(hourly) // 2, len(hourly) - 1)]
            descriptions = mid.get("weather_descriptions", []) if isinstance(mid, dict) else []
            desc = ", ".join(descriptions).lower() if descriptions else ""
        description_text = f"{desc}, " if desc else ""
        return (
            f"Tomorrow's forecast for {place}: {description_text}"
            f"low {day.get('mintemp', '?')}°C, high {day.get('maxtemp', '?')}°C, "
            f"average {day.get('avgtemp', '?')}°C."
        )

    lines = []
    for date_key in dates:
        day = forecast.get(date_key, {})
        pretty_date = date_key
        try:
            pretty_date = datetime.strptime(date_key, "%Y-%m-%d").strftime("%a %b %d")
        except Exception:
            pass
        lines.append(
            f"- {pretty_date}: low {day.get('mintemp', '?')}°C, high {day.get('maxtemp', '?')}°C, avg {day.get('avgtemp', '?')}°C"
        )
    return f"{len(lines)}-day forecast for {place}:\n" + "\n".join(lines)


def _open_meteo_summary(city: str) -> str:
    geo_url = "https://geocoding-api.open-meteo.com/v1/search"
    geo_response = requests.get(geo_url, params={"name": city, "count": 1}, timeout=20)
    if geo_response.status_code != 200:
        return "Weather lookup failed during geocoding step."

    geo = geo_response.json().get("results") or []
    if not geo:
        return f"I couldn’t find coordinates for '{city}'."

    place = geo[0]
    latitude = place.get("latitude")
    longitude = place.get("longitude")
    country = place.get("country", "")

    weather_url = "https://api.open-meteo.com/v1/forecast"
    weather_response = requests.get(
        weather_url,
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m",
        },
        timeout=20,
    )

    if weather_response.status_code != 200:
        return "Weather lookup failed during forecast step."

    current = weather_response.json().get("current", {})
    temp = current.get("temperature_2m", "?")
    humidity = current.get("relative_humidity_2m", "?")
    wind = current.get("wind_speed_10m", "?")

    return (
        f"Current weather in {place.get('name', city)}, {country}: "
        f"about {temp}°C, humidity near {humidity}%, and wind around {wind} km/h."
    )


def _open_meteo_forecast(city: str, forecast_days: int, tomorrow_only: bool = False) -> str:
    geo_url = "https://geocoding-api.open-meteo.com/v1/search"
    geo_response = requests.get(geo_url, params={"name": city, "count": 1}, timeout=20)
    if geo_response.status_code != 200:
        return ""

    geo = geo_response.json().get("results") or []
    if not geo:
        return ""

    place = geo[0]
    latitude = place.get("latitude")
    longitude = place.get("longitude")
    location_name = ", ".join(part for part in [place.get("name", city), place.get("admin1", ""), place.get("country", "")] if part)

    weather_url = "https://api.open-meteo.com/v1/forecast"
    response = requests.get(
        weather_url,
        params={
            "latitude": latitude,
            "longitude": longitude,
            "daily": "temperature_2m_max,temperature_2m_min",
            "forecast_days": max(1, min(forecast_days, 7)),
            "timezone": "auto",
        },
        timeout=20,
    )
    if response.status_code != 200:
        return ""

    daily = response.json().get("daily", {})
    dates = daily.get("time", [])
    max_temps = daily.get("temperature_2m_max", [])
    min_temps = daily.get("temperature_2m_min", [])
    if not dates:
        return ""

    if tomorrow_only:
        idx = 1 if len(dates) > 1 else 0
        return (
            f"Tomorrow's forecast for {location_name}: "
            f"low {min_temps[idx]}°C, high {max_temps[idx]}°C."
        )

    lines = []
    for date_key, min_temp, max_temp in zip(dates, min_temps, max_temps):
        pretty_date = date_key
        try:
            pretty_date = datetime.strptime(date_key, "%Y-%m-%d").strftime("%a %b %d")
        except Exception:
            pass
        lines.append(f"- {pretty_date}: low {min_temp}°C, high {max_temp}°C")

    return f"{len(lines)}-day forecast for {location_name}:\n" + "\n".join(lines)


def weather_api_summary(user_text: str) -> str:
    city = _extract_city(user_text)
    if not city:
        return "Usage: /weather <city name>"

    forecast_days, tomorrow_only = _parse_forecast_request(user_text)
    if forecast_days > 0:
        forecast_reply = _weatherstack_forecast(city, forecast_days=forecast_days, tomorrow_only=tomorrow_only)
        if forecast_reply:
            return forecast_reply
        open_meteo_forecast_reply = _open_meteo_forecast(city, forecast_days=forecast_days, tomorrow_only=tomorrow_only)
        if open_meteo_forecast_reply:
            return open_meteo_forecast_reply

    weatherstack_reply = _weatherstack_summary(city)
    if weatherstack_reply:
        return weatherstack_reply

    fallback = _open_meteo_summary(city)
    if fallback.startswith("I couldn’t find coordinates"):
        return (
            f"I couldn’t find weather data for '{city}'. Try '/weather Halifax' or '/weather Nova Scotia'."
        )
    return fallback


def semantic_course_qa(question: str) -> str:
    if not question.strip():
        return "Usage: /search <question about labs or slides>"
    return answer_from_course_materials(question)


def _create_study_plan(topic: str, days: int, minutes_per_day: int) -> dict[str, Any]:
    bounded_days = max(1, min(int(days), 21))
    bounded_minutes = max(15, min(int(minutes_per_day), 240))

    tasks = []
    for day in range(1, bounded_days + 1):
        if day == 1:
            tasks.append(f"Day {day}: baseline review and key concepts for {topic}")
        elif day == bounded_days:
            tasks.append(f"Day {day}: final recap, mini mock test, and weak-point review")
        else:
            tasks.append(f"Day {day}: focused practice + one implementation exercise")

    return {
        "topic": topic,
        "days": bounded_days,
        "minutes_per_day": bounded_minutes,
        "daily_tasks": tasks,
    }


def _estimate_quiz_count(available_minutes: int, question_difficulty: str) -> dict[str, Any]:
    minutes = max(10, min(int(available_minutes), 300))
    difficulty = (question_difficulty or "medium").lower()

    pace = {"easy": 1.5, "medium": 2.0, "hard": 3.0}.get(difficulty, 2.0)
    count = max(3, int(minutes / pace))

    return {
        "difficulty": difficulty,
        "recommended_questions": count,
        "estimated_minutes": minutes,
    }


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_study_plan",
            "description": "Create a practical study plan for a topic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string"},
                    "days": {"type": "integer"},
                    "minutes_per_day": {"type": "integer"},
                },
                "required": ["topic", "days", "minutes_per_day"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "estimate_quiz_count",
            "description": "Estimate how many practice questions can fit in a study session.",
            "parameters": {
                "type": "object",
                "properties": {
                    "available_minutes": {"type": "integer"},
                    "question_difficulty": {"type": "string"},
                },
                "required": ["available_minutes", "question_difficulty"],
            },
        },
    },
]


def planning_tool_service(user_request: str) -> str:
    if not has_openai_access():
        return "OpenAI access is required for the planning tool service."

    client = OpenAI(**get_openai_client_kwargs())

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": "You are a concise study planning assistant."},
        {"role": "user", "content": user_request},
    ]

    try:
        first = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )
    except Exception:
        fallback = _create_study_plan(topic="Deploying AI", days=7, minutes_per_day=45)
        lines = "\n".join(f"- {item}" for item in fallback["daily_tasks"])
        return (
            "I couldn’t reach the tool-calling model service, so here is a local fallback plan:\n"
            f"{lines}"
        )

    assistant_message = first.choices[0].message
    if not assistant_message.tool_calls:
        return assistant_message.content or "I can help create a study plan if you provide your goal."

    tool_call = assistant_message.tool_calls[0]
    name = tool_call.function.name
    arguments = json.loads(tool_call.function.arguments or "{}")

    if name == "create_study_plan":
        tool_output = _create_study_plan(
            topic=arguments.get("topic", "Deploying AI"),
            days=arguments.get("days", 7),
            minutes_per_day=arguments.get("minutes_per_day", 45),
        )
    elif name == "estimate_quiz_count":
        tool_output = _estimate_quiz_count(
            available_minutes=arguments.get("available_minutes", 45),
            question_difficulty=arguments.get("question_difficulty", "medium"),
        )
    else:
        tool_output = {"error": "Unknown tool requested."}

    messages.append(assistant_message.model_dump(exclude_none=True))
    messages.append(
        {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps(tool_output),
        }
    )

    try:
        final = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
        )
        return final.choices[0].message.content or "Plan created."
    except Exception:
        if name == "create_study_plan":
            tasks = tool_output.get("daily_tasks", []) if isinstance(tool_output, dict) else []
            task_lines = "\n".join(f"- {item}" for item in tasks)
            return "Plan generated (fallback response):\n" + task_lines
        return "I generated the estimate, but couldn’t reach the model to phrase the final response."
