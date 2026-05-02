from langchain.tools import tool
import requests
from utils.logger import get_logger

_logs = get_logger(__name__)

@tool
def get_joke() -> str:
    """Fetches a random joke from a public API and rephrases it naturally (no verbatim return)."""
    try:
        response = requests.get("https://official-joke-api.appspot.com/random_joke", timeout=5).json()
        setup = response.get("setup", "")
        punchline = response.get("punchline", "")
        # Transformed output (not raw API response)
        return f"Here's a galactic chuckle for you: {setup} ... Wait for it ... {punchline} Hope that made your circuits buzz!"
    except Exception as e:
        _logs.error(f"API call failed: {e}")
        return "My comedy database is taking a hyperspace break, try again later!"
