from langchain.tools import tool
import json
import requests
from utils.logger import get_logger

_logs = get_logger(__name__)


def _fetch_facts(url: str, params: dict, extractor) -> str:
    _logs.debug("_fetch_facts: GET %s params=%s", url, params)
    try:
        response = requests.get(url, params=params, timeout=10)
        _logs.debug("_fetch_facts: HTTP %d from %s", response.status_code, url)
        response.raise_for_status()
        resp_dict = json.loads(response.text)
    except requests.RequestException as exc:
        _logs.error("_fetch_facts: request failed for %s: %s", url, exc)
        return f"Could not retrieve facts (network error: {exc})."
    except json.JSONDecodeError as exc:
        _logs.error("_fetch_facts: JSON parse failed for %s: %s", url, exc)
        return "Could not parse facts response."
    facts_list = resp_dict.get("data", [])
    _logs.debug("_fetch_facts: received %d facts from %s", len(facts_list), url)
    return "\n".join(f"{i + 1}. {extractor(fact)}\n" for i, fact in enumerate(facts_list))


@tool
def get_cat_facts(n: int = 1) -> str:
    """Returns n cat facts from the Meowfacts API."""
    return _fetch_facts(
        "https://meowfacts.herokuapp.com/",
        {"count": n},
        lambda fact: fact,
    )


@tool
def get_dog_facts(n: int = 1) -> str:
    """Returns n dog facts from the Dog API."""
    return _fetch_facts(
        "http://dogapi.dog/api/v2/facts",
        {"limit": n},
        lambda fact: fact.get("attributes", {}).get("body", ""),
    )
