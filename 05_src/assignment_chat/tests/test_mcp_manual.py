
"""Test ArXiv MCP server connection and tool discovery."""

import asyncio

from assignment_chat.services.arxiv_mcp_service import (
    get_arxiv_tools,
)


async def main():
    print("Connecting to ArXiv MCP server...")

    tools = await get_arxiv_tools()

    print(f"Discovered {len(tools)} MCP tools:\n")

    for tool in tools:
        print(f"- {tool.name}")
        print(f"  {tool.description[:120]}\n")


if __name__ == "__main__":
    asyncio.run(main())
