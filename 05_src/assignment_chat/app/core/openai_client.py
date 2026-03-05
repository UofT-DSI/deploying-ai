from __future__ import annotations

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(".secrets")

BASE_URL = "https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1"

def get_client() -> OpenAI:
    gateway_key = os.getenv("API_GATEWAY_KEY")
    if not gateway_key:
        raise RuntimeError("API_GATEWAY_KEY not set. Create .secrets with API_GATEWAY_KEY=XXX at assignment_chat root directory level.")

    return OpenAI(
        base_url=BASE_URL,
        api_key="unused key (but required)",
        default_headers={"x-api-key": gateway_key},
    )