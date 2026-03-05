from openai import OpenAI
from app.services.semantic import SemanticStore
from app.llm_router import ChatRouter
import os

def test_router_nonempty():
    oai = OpenAI(
    base_url="https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1",
    api_key="unused",
    default_headers={"x-api-key": os.getenv("API_GATEWAY_KEY")},
    )
    store = SemanticStore("chroma_store", "course_docs", oai)
    r = ChatRouter(oai, store)
    out = r.chat("Calculate 12*(3+1)")
    assert out