import pytest
from app.services.weather_api import get_weather_for_city

def test_weather_smoke():
    w = get_weather_for_city("Toronto")
    assert w.lat != 0
    assert w.lon != 0
    assert w.timezone