from langchain.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from utils.logger import get_logger
import os
import json

from course_agents.llm_factory import make_llm
from course_agents.chroma_utils import parse_chroma_results

_logs = get_logger(__name__)
load_dotenv()
load_dotenv(".secrets")

_collection: chromadb.api.models.Collection
_rerank_llm = None


def _init_music_tools() -> None:
    global _collection, _rerank_llm
    try:
        chroma = chromadb.HttpClient(host=os.getenv("CHROMA_URL"))
        _collection = chroma.get_collection(
            name="pitchfork_reviews",
            embedding_function=OpenAIEmbeddingFunction(
                api_key=os.getenv("OPENAI_API_KEY"),
                model_name="text-embedding-3-small",
            ),
        )
        _rerank_llm = make_llm("openai:gpt-4o-mini")
        _logs.info("tools_music: initialized successfully")
    except Exception as exc:
        _logs.error("tools_music: initialization failed — music tool unavailable: %s", exc)


_init_music_tools()


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
    items = parse_chroma_results(results)
    for item in items:
        item["text"] = item.pop("document")
    return items


def _format_candidates(context_data: list[dict]) -> str:
    lines = []
    for i, c in enumerate(context_data):
        snippet = c.get("text", "")[:200].replace("\n", " ")
        lines.append(
            f"[{i}] Artist: {c.get('artist', 'N/A')}, "
            f"Album: {c.get('album', 'N/A')}, "
            f"Score: {c.get('score', 'N/A')}, "
            f"Genre: {c.get('genre', 'N/A')}\n"
            f"    Excerpt: {snippet}"
        )
    return "\n\n".join(lines)


def _parse_rank_indices(raw: str, n_candidates: int) -> list[int]:
    start = raw.find("[")
    end = raw.rfind("]") + 1
    indices = json.loads(raw[start:end])
    valid = [i for i in indices if isinstance(i, int) and 0 <= i < n_candidates]
    seen: set[int] = set()
    return [i for i in valid if not (i in seen or seen.add(i))]


def llm_rerank(context_data: list[dict], query: str, top_k: int = 3) -> list[dict]:
    if not context_data:
        return context_data
    if _rerank_llm is None:
        _logs.warning("llm_rerank: LLM not initialized, skipping rerank")
        return context_data[:top_k]

    try:
        response = _rerank_llm.invoke([
            SystemMessage(content="Return only a valid JSON array of integers. No explanation."),
            HumanMessage(content=(
                "You are ranking album review candidates by how well they answer the user query.\n"
                "Return ONLY a JSON array of candidate indices ordered from most to least relevant.\n"
                f"Example: [2, 0, 4, 1, 3]\n\nQuery: {query}\n\nCandidates:\n{_format_candidates(context_data)}"
            )),
        ])
        ranked = _parse_rank_indices(response.content.strip(), len(context_data))
        seen_set = set(ranked)
        trailing = [c for i, c in enumerate(context_data) if i not in seen_set]
        return ([context_data[i] for i in ranked] + trailing)[:top_k]
    except Exception as exc:
        _logs.warning("llm_rerank: reranking failed (%s), falling back to original order", exc)
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
    _logs.info("recommend_albums: query=%r keyword=%r n_results=%d", query, keyword, n_results)
    if _collection is None:
        _logs.error("recommend_albums: collection not initialized — is ChromaDB running?")
        return []
    results = hybrid_rag(query, _collection, keyword=keyword or None, top_k_final=n_results)
    _logs.info("recommend_albums: returning %d results", len(results))
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
