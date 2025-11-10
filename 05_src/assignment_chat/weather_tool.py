from dotenv import load_dotenv
import os
from utils.logger import get_logger
import requests
import gradio as gr
from langchain.chat_models import init_chat_model

_logs = get_logger(__name__)

load_dotenv('.secrets')
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')

def get_weather(Location: str):
    """Get the current weather for a given location"""
    url = f"http://api.weatherstack.com/current?access_key={WEATHER_API_KEY}&query={Location}"
    response = requests.get(url)
    data = response.json()
    temperature = data['current']['temperature']
    weather_descriptions = data['current']['weather_descriptions'][0]
    return f"The current temperature in {Location} is {temperature}°C with {weather_descriptions}."