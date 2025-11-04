
from fastmcp import FastMCP
from pydantic import BaseModel, Field
from utils.logger import get_logger
from dotenv import load_dotenv
import os

load_dotenv()
_logs = get_logger(__name__)


mcp = FastMCP(
    name="weather_service",
    instructions="""
    This server provides weather forecast for the requested location.
    Respond with structured data including temperature, humidity, and wind speed.
    """
)

class WeatherData(BaseModel):
    """Structured weather data response."""
    temperature: float = Field(..., description="The current temperature in Celsius.")
    humidity: float = Field(..., description="The current humidity level as a percentage.")
    wind_speed: float = Field(..., description="The current wind speed in meters per second.")


@mcp.tool
def weather_service(location: str) -> WeatherData:
    """Fetches weather data for a given location."""
    # Simulated weather data for demonstration purposes
    return WeatherData(temperature=22.5, humidity=60.0, wind_speed=5.5)

if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="localhost", 
        port=3000, 
    )
