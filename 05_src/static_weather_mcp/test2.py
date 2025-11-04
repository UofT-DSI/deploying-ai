import asyncio
from fastmcp import Client
from dotenv import load_dotenv
import os

from utils.logger import get_logger
_logs = get_logger(__name__)


load_dotenv()

mcp_url = os.getenv("MCP_URL")
# HTTP server
client = Client(mcp_url)


async def main():
    async with client:
        # Basic server interaction
        await client.ping()
        
        # List available operations
        tools = await client.list_tools()
        _logs.info(f'Available tools: {tools}')
        resources = await client.list_resources()
        _logs.info(f'Available resources: {resources}')
        prompts = await client.list_prompts()
        _logs.info(f'Available prompts: {prompts}')

        # Execute operations
        result = await client.call_tool("weather_service", {"location": "Toronto"})
        _logs.info(result)

asyncio.run(main())