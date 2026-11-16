import requests

def get_weather(city):
    geo_url = "https://geocoding-api.open-meteo.com/v1/search"
    geo_response = requests.get(
        geo_url,
        params={"name": city, "count": 1}
    )

    geo_data = geo_response.json()

    if not geo_data.get("results"):
        return None

    location = geo_data["results"][0]

    weather_url = "https://api.open-meteo.com/v1/forecast"
    weather_response = requests.get(
        weather_url,
        params={
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "current_weather": True
        }
    )

    weather_data = weather_response.json()

    return {
        "city": location["name"],
        "country": location.get("country", ""),
        "temperature": weather_data["current_weather"]["temperature"],
        "wind_speed": weather_data["current_weather"]["windspeed"],
        "weather_code": weather_data["current_weather"]["weathercode"]
    }