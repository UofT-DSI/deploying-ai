from langchain.tools import tool
import requests
import json


@tool
def get_sailing_weather(latitude: float = 18.2, longitude: float = -66.5) -> str:
    """
    Fetches current weather and marine conditions for a Caribbean location.
    Default coordinates are for the Caribbean Sea near Puerto Rico.
    Returns temperature, wind speed, wind direction, and wave height
    useful for assessing sailing conditions.
    Latitude and longitude should be for Caribbean locations roughly between
    latitudes 10-25 N and longitudes 60-90 W.
    """
    weather_url = "https://api.open-meteo.com/v1/forecast"
    weather_params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,wind_speed_10m,wind_direction_10m,weather_code",
        "wind_speed_unit": "kn",
        "timezone": "America/Puerto_Rico"
    }

    result = {}

    try:
        weather_resp = requests.get(weather_url, params=weather_params, timeout=10)
        weather_data = weather_resp.json()
        current = weather_data.get("current", {})
        result["temperature_celsius"] = current.get("temperature_2m", "unknown")
        result["wind_speed_knots"] = current.get("wind_speed_10m", "unknown")
        result["wind_direction_degrees"] = current.get("wind_direction_10m", "unknown")
        result["weather_code"] = current.get("weather_code", "unknown")
    except Exception as e:
        result["weather_error"] = str(e)

    # The Open-Meteo API returns a weather_code as an integer (e.g., 0, 61, 95)
    # The below dictionary maps these codes to human-readable descriptions (required to return a meaningful description)
    # Note: these codes are defined here: https://www.nodc.noaa.gov/archive/arc0021/0002199/1.1/data/0-data/HTML/WMO-CODE/WMO4677.HTM
    weather_codes = {
    0: "Clear sky", 
    1: "Mainly clear", 
    2: "Partly cloudy", 
    3: "Overcast",
    45: "Foggy", 
    48: "Depositing rime fog",
    51: "Light drizzle", 
    53: "Moderate drizzle", 
    55: "Dense drizzle",
    61: "Slight rain", 
    63: "Moderate rain", 
    65: "Heavy rain",
    71: "Slight snow", 
    73: "Moderate snow", 
    75: "Heavy snow",
    80: "Slight rain showers", 
    81: "Moderate rain showers", 
    82: "Violent rain showers",
    95: "Thunderstorm", 
    96: "Thunderstorm with slight hail", 
    99: "Thunderstorm with heavy hail"
    }

    # This makes it easier for the LLM to rephrase the weather in pirate terms like 
    # "Slight rain be falling, mate — nothing the Black Pearl can't handle!"

    code = result.get("weather_code", -1)
    result["weather_description"] = weather_codes.get(code, "Unknown conditions")

    result["location"] = {"latitude": latitude, "longitude": longitude}

    return json.dumps(result)
