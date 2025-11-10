from dotenv import load_dotenv
import os
from utils.logger import get_logger
from langchain.chat_models import init_chat_model
import chromadb
import json
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction


if __name__ == "__main__":
    _logs = get_logger(__name__)
    load_dotenv('.secrets')
    CHROMA_DB_DIR = os.getenv('CHROMA_DB_DIR')

    client = chromadb.PersistentClient(path="./chroma_data")
    
    collection = client.get_or_create_collection(
        name="fun_facts"
    )

    file_path = "facts.jsonl"
    documents = []
    ids = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            item = json.loads(line)
            ids.append(str(item["id"]))
            documents.append(item["fact"])
    collection.add(ids=ids, documents=documents)

def query_fun_facts(query: str) -> str:
    """
    Takes a user question, searches ChromaDB, and returns the top matching fun facts.
    """
    try:
        results = collection.query(query_texts=[query], n_results=3)
        docs = results.get("documents", [[]])[0]
        print(docs['id'])
        print("hello")
        if not docs:
            return "No relevant fun facts found."

        return "\n".join(f"- {doc}" for doc in docs)

    except Exception as e:
        return f"Error querying database: {e}"