from langchain.tools import tool
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from utils.logger import get_logger
import os
import json

_logs = get_logger(__name__)
load_dotenv()
load_dotenv(".secrets")

_GATEWAY_URL = "https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1"
_USE_GATEWAY = os.getenv("USE_GATEWAY", "true").lower() != "false"


def _make_llm(model_id: str):
    if _USE_GATEWAY:
        return init_chat_model(
            model_id,
            base_url=_GATEWAY_URL,
            api_key="any value",
            default_headers={"x-api-key": os.getenv("API_GATEWAY_KEY")},
        )
    return init_chat_model(model_id)

chroma = chromadb.HttpClient(host=os.getenv("CHROMA_URL"))
collection = chroma.get_collection(
    name="pitchfork_reviews",
    embedding_function=OpenAIEmbeddingFunction(
        api_key=os.getenv("OPENAI_API_KEY"),
        model_name="text-embedding-3-small"
    )
)

_rerank_llm = _make_llm("openai:gpt-4o-mini")
_logs.info(f"tools_music: USE_GATEWAY={_USE_GATEWAY}")


class MusicReviewData(BaseModel):
    """Structured music review data response."""
    title: str = Field(..., description="The title of the album.")
    artist: str = Field(..., description="The artist of the album.")
    review: str = Field(..., description="A portion of the album review relevant to the user query.")
    score: float = Field(None, description="The Pitchfork score (0–10). Above 8.0 is a must-listen.")
    year: int | None = None
    genre: str | None = None


def get_context_data(
    query: str,
    collection: chromadb.api.models.Collection,
    top_n: int,
    where_document: dict = None,
    where: dict = None,
) -> list[dict]:
    kwargs = dict(query_texts=[query], n_results=top_n)
    if where_document:
        kwargs["where_document"] = where_document
    if where:
        kwargs["where"] = where
    results = collection.query(**kwargs)
    context_data = []
    for idx in range(len(results["ids"][0])):
        details = dict(results["metadatas"][0][idx])
        details["text"] = results["documents"][0][idx]
        context_data.append(details)
    return context_data


def llm_rerank(context_data: list[dict], query: str, top_k: int = 3) -> list[dict]:
    if not context_data:
        return context_data

    candidates_text = ""
    for i, c in enumerate(context_data):
        snippet = c.get("text", "")[:200].replace("\n", " ")
        candidates_text += (
            f"[{i}] Artist: {c.get('artist', 'N/A')}, "
            f"Album: {c.get('album', 'N/A')}, "
            f"Score: {c.get('score', 'N/A')}, "
            f"Genre: {c.get('genre', 'N/A')}\n"
            f"    Excerpt: {snippet}\n\n"
        )

    rerank_prompt = (
        f"You are ranking album review candidates by how well they answer the user query.\n"
        f"Return ONLY a JSON array of candidate indices ordered from most to least relevant.\n"
        f"Example: [2, 0, 4, 1, 3]\n\n"
        f"Query: {query}\n\n"
        f"Candidates:\n{candidates_text}"
    )

    try:
        response = _rerank_llm.invoke([
            SystemMessage(content="Return only a valid JSON array of integers. No explanation."),
            HumanMessage(content=rerank_prompt),
        ])
        raw = response.content.strip()
        start = raw.find("[")
        end = raw.rfind("]") + 1
        ranked_indices = json.loads(raw[start:end])
        valid = [i for i in ranked_indices if isinstance(i, int) and 0 <= i < len(context_data)]
        seen: set[int] = set()
        deduped = [i for i in valid if not (i in seen or seen.add(i))]
        reranked = [context_data[i] for i in deduped]
        missing = [c for i, c in enumerate(context_data) if i not in seen]
        return (reranked + missing)[:top_k]
    except Exception:
        _logs.warning("llm_rerank: falling back to original order")
        return context_data[:top_k]


def hybrid_rag(
    query: str,
    collection: chromadb.api.models.Collection,
    keyword: str = None,
    where_filter: dict = None,
    top_n_candidates: int = 10,
    top_k_final: int = 3,
) -> list[dict]:
    where_document = {"$contains": keyword} if keyword else None
    candidates = get_context_data(
        query, collection, top_n_candidates,
        where_document=where_document,
        where=where_filter,
    )
    if not candidates:
        _logs.warning("hybrid_rag: no candidates returned for the given filters")
        return []
    return llm_rerank(candidates, query, top_k=top_k_final)


@tool
def recommend_albums(query: str, keyword: str = "", n_results: int = 3) -> list[MusicReviewData]:
    """Fetches music review data using hybrid RAG. keyword optionally filters by text content."""
    results = hybrid_rag(query, collection, keyword=keyword or None, top_k_final=n_results)
    return [
        MusicReviewData(
            title=r.get("album", "N/A"),
            artist=r.get("artist", "N/A"),
            review=r.get("text", "N/A"),
            score=r.get("score", 0.0),
            year=r.get("year"),
            genre=r.get("genre"),
        )
        for r in results
    ]
