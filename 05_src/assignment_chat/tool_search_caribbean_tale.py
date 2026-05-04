from langchain.tools import tool
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from dotenv import load_dotenv
import os

load_dotenv(".env")
load_dotenv(".secrets")

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "chroma_data")
COLLECTION_NAME = "caribbean_tales"

embedding_fn = OpenAIEmbeddingFunction(
    api_key="any value",
    api_base='https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1',
    model_name="text-embedding-3-small",
    default_headers={"x-api-key": os.getenv('API_GATEWAY_KEY')}
)

chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = chroma_client.get_collection(
    name=COLLECTION_NAME,
    embedding_function=embedding_fn
)


@tool
def search_caribbean_tale(user_query: str) -> str:
    """
    Searches the Caribbean pirate database (chromaDB- table: caribbean_tale) for semantic match for user query. 
    Returns the most relevant tale entry about pirates,
    ships, islands, sea myths, cursed treasures, and Caribbean history.
    Use this when the user asks about any pirate or Caribbean topic.
    """
    tale_result = collection.query(query_texts=[user_query], n_results=1)

    # show output when no story found
    if not tale_result["documents"] or not tale_result["documents"][0]:
        return "No relevant story/tale found in the archives."

    # Get the first (and only) result
    story = tale_result["documents"][0][0]
    
    category = "unknown"
    if tale_result["metadatas"] and tale_result["metadatas"][0]:
        category = tale_result["metadatas"][0][0].get("category", "unknown")

    # Return story with category
    return f"[{category}] {story}"
