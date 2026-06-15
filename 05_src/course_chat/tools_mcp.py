"""
MCP tool loader using MultiServerMCPClient with Docker stdio transport.

All four MCP servers are launched as Docker subprocesses via the MCP client.
GitHub is optional — omitted gracefully if GITHUB_PERSONAL_ACCESS_TOKEN is unset.

Usage (call from app.py __main__ before launching Gradio):
    init_mcp()           # blocks until all connections are established
    tools = get_mcp_tools()
    agent = get_agent(extra_tools=tools)
"""
import asyncio
import os
import subprocess
import threading
from typing import Any

from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from utils.logger import get_logger

load_dotenv()
load_dotenv(".secrets")

_logs = get_logger(__name__)

_mcp_client: MultiServerMCPClient | None = None
_mcp_tools: list = []
_background_loop: asyncio.AbstractEventLoop | None = None


def _docker_available() -> bool:
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _build_connections() -> dict[str, Any]:
    connections: dict[str, Any] = {
        "playwright": {
            "command": "docker",
            "args": ["run", "-i", "--rm", "--init", "mcr.microsoft.com/playwright/mcp"],
            "transport": "stdio",
        },
        "duckduckgo": {
            "command": "docker",
            "args": ["run", "-i", "--rm", "mcp/duckduckgo"],
            "transport": "stdio",
        },
        "wikipedia": {
            "command": "docker",
            "args": ["run", "-i", "--rm", "mcp/wikipedia-mcp"],
            "transport": "stdio",
        },
    }

    github_token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    if github_token:
        connections["github"] = {
            "command": "docker",
            "args": [
                "run", "-i", "--rm",
                "-e", f"GITHUB_PERSONAL_ACCESS_TOKEN={github_token}",
                "ghcr.io/github/github-mcp-server",
            ],
            "transport": "stdio",
        }
        _logs.info("GitHub MCP: token found — GitHub tools will be loaded")
    else:
        _logs.warning(
            "GITHUB_PERSONAL_ACCESS_TOKEN not set — GitHub MCP tools will not be loaded. "
            "See docs/plans/2026-06-14-003-feat-course-chat-enhancements-plan.md for instructions."
        )

    return connections


async def _init_client_async() -> None:
    global _mcp_client, _mcp_tools
    connections = _build_connections()
    client = MultiServerMCPClient(connections)
    await client.__aenter__()
    _mcp_client = client
    _mcp_tools = await client.get_tools()
    _logs.info(f"MCP tools loaded: {[t.name for t in _mcp_tools]}")


def _run_loop_forever(loop: asyncio.AbstractEventLoop) -> None:
    asyncio.set_event_loop(loop)
    loop.run_forever()


def init_mcp(timeout: float = 60.0) -> None:
    """Initialize MCP connections in a background event loop thread.

    Blocks until all configured MCP servers respond (or raises TimeoutError).
    Must be called before get_mcp_tools().
    """
    global _background_loop

    if not _docker_available():
        _logs.error(
            "Docker is not available or not running. MCP tools will not be loaded. "
            "Install and start Docker, then restart the app."
        )
        return

    _background_loop = asyncio.new_event_loop()
    thread = threading.Thread(
        target=_run_loop_forever,
        args=(_background_loop,),
        daemon=True,
        name="mcp-event-loop",
    )
    thread.start()

    future = asyncio.run_coroutine_threadsafe(_init_client_async(), _background_loop)
    try:
        future.result(timeout=timeout)
    except TimeoutError:
        _logs.error(f"MCP initialization timed out after {timeout}s. Check that Docker images are pulled.")
    except Exception as e:
        _logs.error(f"MCP initialization failed: {e}")


def get_mcp_tools() -> list:
    """Return the list of LangChain BaseTool objects loaded from MCP servers."""
    return _mcp_tools
