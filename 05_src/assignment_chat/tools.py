import os
from pathlib import Path

import chromadb
import requests
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from dotenv import load_dotenv
from langchain.tools import tool


load_dotenv("../.secrets")

KNOWLEDGE_BASE = [
    {
        "id": "rag",
        "text": (
            "Retrieval-Augmented Generation, or RAG, combines a language model "
            "with information retrieved from an external knowledge source. "
            "The retrieved context helps the model answer with information that "
            "is more relevant and grounded."
        ),
    },
    {
        "id": "embeddings",
        "text": (
            "Embeddings are numerical vector representations of text or other data. "
            "Items with similar meanings are positioned near one another in vector "
            "space, enabling semantic similarity searches."
        ),
    },
    {
        "id": "semantic-search",
        "text": (
            "Semantic search compares the meaning of a query with the meaning of "
            "stored documents. Unlike keyword search, it can retrieve relevant "
            "content even when the exact words are different."
        ),
    },
    {
        "id": "langgraph",
        "text": (
            "LangGraph is a framework for building stateful AI workflows as graphs. "
            "Nodes perform tasks, edges control workflow transitions, and state "
            "stores information such as conversation messages."
        ),
    },
    {
        "id": "function-calling",
        "text": (
            "Function calling allows a language model to select and request an "
            "external function or tool. The application executes the function and "
            "returns its result to the model for use in the final response."
        ),
    },
    {
        "id": "prompt-engineering",
        "text": (
            "Prompt engineering is the practice of designing instructions and "
            "context that guide a language model toward useful, accurate, and "
            "consistent outputs."
        ),
    },
]

chroma_path = Path(__file__).parent / "chroma_data"

chroma_client = chromadb.PersistentClient(path=str(chroma_path))

embedding_function = OpenAIEmbeddingFunction(
    api_key=os.getenv("OPENAI_API_KEY"),
    model_name="text-embedding-3-small",
)

collection = chroma_client.get_or_create_collection(
    name="ai_concepts",
    embedding_function=embedding_function,
)

if collection.count() == 0:
    collection.add(
        ids=[item["id"] for item in KNOWLEDGE_BASE],
        documents=[item["text"] for item in KNOWLEDGE_BASE],
    )


@tool
def get_programming_wisdom() -> str:
    """
    Retrieves a short software development message from the Github Zen API.
    Use this when the user requests a programming quote or motivation.
    """
    response = requests.get(
        "https://api.github.com/zen",
        timeout=10,
    )
    response.raise_for_status()
    return response.text


@tool
def search_ai_knowledge(query: str) -> str:
    """
    Searches the AI concepts knowledge base using semantic similarity.
    Use this for questions about AI, RAG, embeddings, LangGraph,
    semantic search, function calling, or prompt engineering.
    """
    results = collection.query(
        query_texts=[query],
        n_results=2,
    )

    documents = results.get("documents", [[]])[0]

    if not documents:
        return "No relevant information was found in the AI knowledge base."

    return "\n\n".join(documents)


@tool
def create_study_quiz(topic: str, number_of_questions: int = 3) -> str:
    """
    Requests a short study quiz about an AI topic.
    Use this when the user asks to practise, review, or take a quiz.
    """
    number_of_questions = max(1, min(number_of_questions, 5))

    return (
        f"Create a {number_of_questions}-question quiz about {topic}. "
        "Ask one question at a time, wait for the user's answer, "
        "then provide feedback before continuing."
    )
