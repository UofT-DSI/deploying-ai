from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List

import requests


WIKI_UA = (
    "StudyMateAssignmentBot/1.0 (educational project; contact: student@example.com) "
    "PythonRequests"
)

ACTION_API = "https://en.wikipedia.org/w/api.php"


def _clean_query(q: str) -> str:
    q = (q or "").strip()
    # remove trailing punctuation that hurts search
    q = re.sub(r"[?!.]+$", "", q)
    return q


@dataclass
class WikiResult:
    title: str
    url: str
    extract: str


class WebSearchWikipediaTool:
    name = "web_search"
    description = "Search Wikipedia and return top results with short extracts."
    json_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query for Wikipedia"},
            "k": {"type": "integer", "default": 3, "minimum": 1, "maximum": 5},
        },
        "required": ["query"],
    }
    def run(self, args: Dict[str, Any], ctx: Any = None) -> Dict[str, Any]:
        query = _clean_query(str(args.get("query", "")))
        k = int(args.get("k", 3))

        if not query:
            return {"results": []}

        # MediaWiki Action API is much more reliable than /rest.php for bots
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "utf8": 1,
            "srlimit": k,
        }

        headers = {"User-Agent": WIKI_UA}

        r = requests.get(ACTION_API, params=params, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()

        search_hits = (data.get("query", {}) or {}).get("search", []) or []

        results: List[WikiResult] = []
        for hit in search_hits:
            title = hit.get("title", "")
            pageid = hit.get("pageid")

            # get extract for each page (short intro)
            extract = ""
            if pageid is not None:
                r2 = requests.get(
                    ACTION_API,
                    params={
                        "action": "query",
                        "prop": "extracts",
                        "exintro": 1,
                        "explaintext": 1,
                        "pageids": pageid,
                        "format": "json",
                        "utf8": 1,
                    },
                    headers=headers,
                    timeout=15,
                )
                r2.raise_for_status()
                d2 = r2.json()
                pages = (d2.get("query", {}) or {}).get("pages", {}) or {}
                page = pages.get(str(pageid), {}) or {}
                extract = (page.get("extract") or "").strip()

            url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}" if title else ""
            results.append(WikiResult(title=title, url=url, extract=extract))

        return {
            "results": [{"title": x.title, "url": x.url, "extract": x.extract} for x in results]
        }