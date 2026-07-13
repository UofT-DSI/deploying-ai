import os
from langchain.chat_models import init_chat_model

_GATEWAY_URL = "https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1"


def make_llm(model_id: str):
    if os.getenv("USE_GATEWAY", "true").lower() != "false":
        return init_chat_model(
            model_id,
            base_url=_GATEWAY_URL,
            api_key="any value",
            default_headers={"x-api-key": os.getenv("API_GATEWAY_KEY")},
        )
    return init_chat_model(model_id)
