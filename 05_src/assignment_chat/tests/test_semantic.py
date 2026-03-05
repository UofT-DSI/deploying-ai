from openai import OpenAI
from app.services.semantic import SemanticStore
import os
def test_semantic_search_smoke():
    oai = OpenAI(
    base_url="https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1",
    api_key="unused",
    default_headers={"x-api-key": os.getenv("API_GATEWAY_KEY")},
    )
    store = SemanticStore("chroma_store", "course_docs", oai)
    hits = store.search("What are embeddings?", k=2)
    assert len(hits) <= 2