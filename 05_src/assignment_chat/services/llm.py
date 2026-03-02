"""Shared OpenAI client and response helper for all TripSmith services."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT.parent / ".env")
load_dotenv(PROJECT_ROOT.parent / ".secrets")
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / ".secrets")


DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
DEFAULT_GATEWAY_BASE_URL = (
    "https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1"
)


def _build_client() -> OpenAI:
    """Initialize client with course gateway first, then standard OpenAI fallback."""
    gateway_key = (os.getenv("API_GATEWAY_KEY") or "").strip()
    gateway_base_url = (
        os.getenv("API_GATEWAY_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
        or DEFAULT_GATEWAY_BASE_URL
    )

    if gateway_key:
        # Course environment uses an API Gateway that expects x-api-key header.
        return OpenAI(
            api_key="not-used-with-api-gateway",
            base_url=gateway_base_url,
            default_headers={"x-api-key": gateway_key},
        )

    openai_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if openai_key:
        return OpenAI(api_key=openai_key)

    raise ValueError(
        "Missing API credentials. Set API_GATEWAY_KEY (course gateway) "
        "or OPENAI_API_KEY."
    )


_client = _build_client()


def get_client() -> OpenAI:
    """Return singleton client reused across all services."""
    return _client


def get_model() -> str:
    """Resolve model from env with assignment-friendly default."""
    return os.getenv("OPENAI_MODEL", DEFAULT_MODEL)


def create_response(
    *,
    instructions: str,
    input_items: list[Any],
    tools: list[dict[str, Any]] | None = None,
) -> Any:
    """Thin wrapper around Responses API to keep call sites consistent."""
    kwargs: dict[str, Any] = {
        "model": get_model(),
        "instructions": instructions,
        "input": input_items,
    }
    if tools is not None:
        kwargs["tools"] = tools
    return _client.responses.create(**kwargs)
