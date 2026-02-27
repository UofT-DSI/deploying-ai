# %%
import sys
sys.path.append('../../05_src/')

# %%
import sys, os
sys.path.insert(0, os.path.join(os.getcwd(), "05_src"))

# %%
from utils.logger import get_logger
_logs = get_logger(__name__, log_dir='../../06_logs/')

# %%
_logs.info('This is a log message.')

# %%
import os
os.getenv('LOG_LEVEL')

# %%
import os
print("CWD:", os.getcwd())

# %%
import os
os.environ["API_GATEWAY_KEY"] = "0ZP4RO533EPURJOO2YJQ"
os.environ["API_GATEWAY_BASE_URL"] = "https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1"

# %%
from openai import OpenAI
client = OpenAI(base_url='https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1', 
                api_key='any value',
                default_headers={"x-api-key": os.getenv('API_GATEWAY_KEY')})

response = client.responses.create(
    model = 'gpt-4o-mini',
    input = 'Hello world!'
    
)

print(response.output_text)

# %%
response.model_dump()

# %%
response.output[0].content

# %%
pip install gradio

# %%
pip install requests

# %%
import requests

def get_weather_summary_city(city: str) -> str:
    city = city.strip()

    if not city:
        return "Please provide a city name."

    try:
        # Step 1: Geocoding API (city → lat/lon)
        geo_url = "https://geocoding-api.open-meteo.com/v1/search"
        geo_params = {
            "name": city,
            "count": 1,
            "language": "en",
            "format": "json"
        }

        geo_response = requests.get(geo_url, params=geo_params, timeout=10)
        geo_response.raise_for_status()
        geo_data = geo_response.json()

        results = geo_data.get("results")
        if not results:
            return f"I couldn’t find a city called '{city}'."

        lat = results[0]["latitude"]
        lon = results[0]["longitude"]
        city_name = results[0]["name"]

        # Step 2: Weather API
        weather_url = "https://api.open-meteo.com/v1/forecast"
        weather_params = {
            "latitude": lat,
            "longitude": lon,
            "current_weather": True,
            "timezone": "auto"
        }

        weather_response = requests.get(weather_url, params=weather_params, timeout=10)
        weather_response.raise_for_status()
        weather_data = weather_response.json()

        current = weather_data.get("current_weather", {})
        temp = current.get("temperature")
        wind = current.get("windspeed")

        return f"In {city_name} right now, it’s {temp}°C with winds around {wind} km/h."

    except Exception as e:
        return f"Weather service error: {type(e).__name__}"

# %%
def get_weather_summary(latitude, longitude):
    import requests
    
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current_weather": True,
        "timezone": "auto"
    }

    response = requests.get(url, params=params)
    data = response.json()

    current = data.get("current_weather", {})
    temp = current.get("temperature")
    wind = current.get("windspeed")

    return f"The current temperature is {temp}°C with a wind speed of {wind} km/h."

# %%
RESTRICTED_TOPICS = ["cat", "dog", "zodiac", "horoscope", "taylor swift"]

SYSTEM_PROMPT_KEYWORDS = [
    "system prompt",
    "ignore previous instructions",
    "reveal your instructions",
    "change your personality",
]

def chatbot(message, history):
    msg = (message or "").strip().lower()

    # Guardrail 1: Block system prompt attacks
    for phrase in SYSTEM_PROMPT_KEYWORDS:
        if phrase in msg:
            return "Nice try 😌 but I can’t share or modify my internal instructions."

    # Guardrail 2: Block restricted topics
    for topic in RESTRICTED_TOPICS:
        if topic in msg:
            return "I’m not allowed to discuss that topic. Let’s stick to weather 🌦️"

    # continue normal logic below...

# %%
def chatbot(message, history):
    msg = (message or "").strip()
    if not msg:
        return genz_wrap("Drop a city 👀 Try: weather Paris")

    low = msg.lower()

    if low in {"hey", "hi", "hello"}:
        return genz_wrap("Heyyy 👋 Ask me about any city’s weather 🌦️")

    if low.startswith("weather"):
        city = msg[len("weather"):].strip()
        if not city:
            return genz_wrap("Tell me the city name 😌 Try: weather Tokyo")

        result = get_weather_summary_city(city)
        return genz_wrap(result)

    return genz_wrap("I’m your weather plug 🌦️ Try: weather New York")

# %%
def chatbot(message, history):
    ...

# %%
def get_last_user_message(history):
    """
    Returns the most recent USER message across Gradio history formats.
    Works when history entries are tuples or dicts.
    """
    if not history:
        return None

    # Walk backwards to find a user message
    for item in reversed(history):

        # Format A: tuple/list like (user, bot)
        if isinstance(item, (list, tuple)) and len(item) >= 1:
            user_text = item[0]
            if isinstance(user_text, str) and user_text.strip():
                return user_text

        # Format B: dict like {"role":"user","content":"..."}
        if isinstance(item, dict):
            role = item.get("role")
            content = item.get("content") or item.get("text")
            if role == "user" and isinstance(content, str) and content.strip():
                return content

        # Format C: sometimes a list of message dicts
        if isinstance(item, list):
            for sub in reversed(item):
                if isinstance(sub, dict) and sub.get("role") == "user":
                    content = sub.get("content") or sub.get("text")
                    if isinstance(content, str) and content.strip():
                        return content

    return None

# %%
def genz_wrap(text) -> str:
    if text is None:
        text = "Oops — I got nothing back. Try again."
    return f"yo 😄 frosty here ❄️\n\n{str(text)}"

# %%
def chatbot(message, history):
    try:
        msg = (message or "").strip()
        if not msg:
            return genz_wrap("Drop a city 👀 Try: weather Paris")

        low = msg.lower()

        if low in {"hey", "hi", "hello"}:
            return genz_wrap("Heyyy 👋 Ask me: weather Tokyo")

        if low.startswith("weather"):
            city = msg[len("weather"):].strip()
            if not city:
                return genz_wrap("Tell me the city name 😌 Example: weather Beirut")

            result = get_weather_summary_city(city)

            # ✅ hard guarantee: never return None
            if result is None:
                result = "Weather service returned nothing. Try another city."

            return genz_wrap(result)

        return genz_wrap("I’m a weather bot 🌦️ Try: weather New York")

    except Exception as e:
        # ✅ never crash Gradio
        return genz_wrap(f"Internal error: {type(e).__name__}: {e}")

# %%
import random

GENZ_INTROS = [
    "yo 😄 frosty here ❄️",
    "heyyy bestie 👋",
    "ok weather check time 🌦️",
    "what’s good 👀",
]

GENZ_COLD_REACTIONS = [
    "bundle up fr 🧥",
    "it’s giving Antarctica vibes 🥶",
    "nah that’s actually freezing 😭",
]

GENZ_WARM_REACTIONS = [
    "ok that’s kinda nice tho 😌",
    "we vibing today ✨",
    "lowkey perfect weather",
]

def genz_wrap(text: str) -> str:
    text = str(text) if text else "Something went weird 😭 try again."
    intro = random.choice(GENZ_INTROS)
    return f"{intro}\n\n{text}"

# %%
import gradio as gr

with gr.ChatInterface(fn=chatbot) as demo:
    demo.launch()



