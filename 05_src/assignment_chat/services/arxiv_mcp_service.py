
"""ArXiv MCP client configuration and tool discovery."""

import shutil

from langchain_mcp_adapters.client import (
    MultiServerMCPClient,
)


def create_arxiv_client() -> MultiServerMCPClient:
    """Configure the local ArXiv MCP server."""

    uvx_path = shutil.which("uvx")

    if not uvx_path:
        raise RuntimeError(
            "uvx executable not found. "
            "Verify uv is installed and available on PATH."
        )

    return MultiServerMCPClient(
        {
            "arxiv": {
                "transport": "stdio",
                "command": uvx_path,
                "args": ["arxiv-mcp-server"],
            }
        },
        tool_name_prefix=True,
    )


async def get_arxiv_tools():
    """Discover ArXiv tools exposed by the MCP server."""

    client = create_arxiv_client()

    tools = await client.get_tools(
        server_name="arxiv"
    )

    if not tools:
        raise RuntimeError(
            "ArXiv MCP server returned no tools."
        )

    return tools
