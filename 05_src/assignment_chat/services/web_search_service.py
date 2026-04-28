"""
Service 3: Web Search Service
Uses OpenAI's web_search tool (function calling) to retrieve
recent academic news and research developments.
"""

import json


WEB_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "Search the web for recent academic news, research findings, "
            "or current developments on a given topic."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to look up on the web."
                }
            },
            "required": ["query"]
        }
    }
}


def web_search_service(user_query: str, client) -> str:
    """
    Uses OpenAI function calling with a web_search tool definition.
    The model generates a focused academic search query, which is then
    used to perform a real web search via requests and return a summary.

    Since the UofT gateway may not support the Responses API web_search tool,
    we simulate the agentic pattern: ask the model to generate a refined
    search query, then fetch results from a public search API.
    """
    import requests

    try:
        # Step 1: Ask the model to generate a refined academic search query
        query_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a search query optimizer for academic research. "
                        "Given a user question, produce a concise, precise web search query "
                        "(max 10 words) optimized for finding recent academic or scientific "
                        "news. Return ONLY the query string, nothing else."
                    )
                },
                {"role": "user", "content": user_query}
            ],
            max_tokens=30,
            temperature=0.3
        )

        search_query = query_response.choices[0].message.content.strip().strip('"')

        # Step 2: Use DuckDuckGo Instant Answer API (free, no key required)
        ddg_url = "https://api.duckduckgo.com/"
        params = {
            "q": search_query,
            "format": "json",
            "no_redirect": "1",
            "no_html": "1",
            "skip_disambig": "1"
        }
        ddg_response = requests.get(ddg_url, params=params, timeout=10)
        ddg_response.raise_for_status()
        ddg_data = ddg_response.json()

        # Extract useful content from DuckDuckGo response
        results = []

        # Abstract (main answer)
        abstract = ddg_data.get("Abstract", "").strip()
        abstract_source = ddg_data.get("AbstractSource", "")
        if abstract:
            results.append(f"Overview ({abstract_source}): {abstract}")

        # Related topics
        related = ddg_data.get("RelatedTopics", [])[:3]
        for topic in related:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append(f"• {topic['Text']}")

        # Answer (if direct answer exists)
        answer = ddg_data.get("Answer", "").strip()
        if answer:
            results.append(f"Direct Answer: {answer}")

        if not results:
            # Fallback: return the refined query so the assistant knows what was searched
            return (
                f"Web search performed for: '{search_query}'. "
                f"No structured results returned. The assistant will respond based on "
                f"its training knowledge for this topic."
            )

        output = f"Web search query: '{search_query}'\n\n"
        output += "\n".join(results)
        return output

    except Exception as e:
        return f"Web search encountered an error: {str(e)}"
