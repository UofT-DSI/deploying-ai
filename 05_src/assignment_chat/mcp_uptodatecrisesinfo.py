from fastmcp import FastMCP
import requests

mcp = FastMCP("Web Search MCP Server")


@mcp.tool
def web_search(query: str) -> str:
    """
    Simple web search tool.
    Returns the top result title + URL.
    """
    url = "https://api.duckduckgo.com/"
    params = {
        "q": query,
        "format": "json",
        "no_redirect": 1,
        "no_html": 1
    }

    response = requests.get(url, params=params, timeout=10)
    data = response.json()

    title = data.get("Heading")
    abstract = data.get("AbstractText")
    link = data.get("AbstractURL")

    if not title:
        return "No clear result found."

    return f"{title}\n{abstract}\nSource: {link}"


if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="localhost",
        port=3000,
    )