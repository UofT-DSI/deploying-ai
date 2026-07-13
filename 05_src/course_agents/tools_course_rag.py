from langchain.tools import tool
from deepagents import SubAgent
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from dotenv import load_dotenv
from utils.logger import get_logger
import os

from course_agents.chroma_utils import parse_chroma_results

_logs = get_logger(__name__)
load_dotenv()
load_dotenv(".secrets")

_COLLECTION_NAME = "course_material"


def _get_collection() -> chromadb.api.models.Collection:
    chroma = chromadb.HttpClient(host=os.getenv("CHROMA_URL", "localhost"))
    return chroma.get_collection(
        name=_COLLECTION_NAME,
        embedding_function=OpenAIEmbeddingFunction(
            api_key=os.getenv("OPENAI_API_KEY"),
            model_name="text-embedding-3-small",
        ),
    )


@tool
def query_course_material(query: str, n_results: int = 5) -> list[dict]:
    """Searches the course material index for content relevant to the query.
    Returns a list of {source, type, title, content} dicts.
    Use this for questions about course notebooks, slides, or assignment descriptions."""
    _logs.debug("query_course_material: query=%r n_results=%d", query, n_results)
    try:
        collection = _get_collection()
    except Exception as e:
        _logs.error("course_material collection unavailable: %s", e)
        return [{"error": "Course material not indexed. Run index_course_material.py first."}]

    results = collection.query(query_texts=[query], n_results=n_results)
    chunks = [
        {
            "source": item.get("source", "unknown"),
            "type": item.get("type", "unknown"),
            "title": item.get("title", "unknown"),
            "content": item["document"],
        }
        for item in parse_chroma_results(results)
    ]
    _logs.debug("query_course_material: %d results for '%s'", len(chunks), query)
    return chunks


_SYSTEM_PROMPT = """You are a course content retrieval assistant for a Deploying AI course.

When you receive a question:
1. Call query_course_material with the user's question as the query.
2. Review the returned excerpts and identify the most relevant ones.
3. Format your answer with source attribution for each excerpt.

Attribution format: cite as (source: <file_path>, section: <title>).

If the results do not contain relevant information, say so clearly — do not hallucinate content."""


course_rag_subagent: SubAgent = {
    "name": "course-rag",
    "description": (
        "Retrieves relevant excerpts from indexed course material: "
        "lab notebooks, markdown slides, and assignment descriptions."
    ),
    "system_prompt": _SYSTEM_PROMPT,
    "tools": [query_course_material],
}
