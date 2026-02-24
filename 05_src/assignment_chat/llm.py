import os
from openai import OpenAI

BASE_URL = "https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1"

def get_client() -> OpenAI:
    return OpenAI(
        api_key=os.getenv("OPENAI_API_KEY", "DUMMY_KEY"),

        default_headers={"x-api-key": os.getenv("API_GATEWAY_KEY", "")},

        base_url=BASE_URL,
    )