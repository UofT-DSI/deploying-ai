# Service 1: Spaceflight News API
# Adapted from course_chat/tools_horoscope.py - same 3-part structure:
#   1. @tool function (called by LangGraph)
#   2. private API call function
#   3. private response parser
# API docs: https://spaceflightnewsapi.net/

from langchain.tools import tool
import requests
import json
from utils.logger import get_logger

_logs = get_logger(__name__)

API_BASE = "https://api.spaceflightnewsapi.net/v4"


@tool
def get_spaceflight_news(topic: str = "AI", limit: int = 3) -> str:
    """
    Fetches the latest spaceflight news articles from the Spaceflight News API.
    No API key required.
    Use this tool when the user asks about space, rockets, NASA, SpaceX, satellites,
    launches, or any spaceflight-related news.
    topic: a keyword to search for (e.g. 'NASA', 'SpaceX', 'Mars', 'AI', 'satellite').
    limit: number of articles to return (1-5, default 3).
    """
    _logs.debug(f"Getting spaceflight news for topic='{topic}', limit={limit}")
    response = _get_news_from_service(topic, limit)
    result = _parse_news_response(response)
    _logs.debug(f"News result: {result}")
    return result


def _get_news_from_service(topic: str, limit: int) -> requests.Response:
    url = f"{API_BASE}/articles/"
    params = {
        "search": topic,
        "limit": min(limit, 5),
        "ordering": "-published_at",
    }
    response = requests.get(url, params=params)
    return response


def _parse_news_response(response: requests.Response) -> str:
    resp_dict = json.loads(response.text)
    articles = resp_dict.get("results", [])

    if not articles:
        return "No spaceflight news articles found for that topic."

    lines = []
    for i, article in enumerate(articles, start=1):
        title       = article.get("title", "No title")
        summary     = article.get("summary", "No summary available.")
        published   = article.get("published_at", "Unknown date")[:10]  # YYYY-MM-DD
        news_site   = article.get("news_site", "Unknown source")
        url         = article.get("url", "")

        lines.append(
            f"[Article {i}] {title}\n"
            f"  Source: {news_site} | Published: {published}\n"
            f"  Summary: {summary}\n"
            f"  URL: {url}"
        )

    return "\n\n".join(lines)
