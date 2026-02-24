from langchain.tools import tool
from fastmcp import FastMCP
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from pydantic import BaseModel, Field
import sqlalchemy as sa
import pandas as pd
from dotenv import load_dotenv
from utils.logger import get_logger
import os
_logs = get_logger(__name__)
load_dotenv()
load_dotenv(".secrets")
 

vector_db_client_url = "http://localhost:8000"
chroma = chromadb.HttpClient(host=vector_db_client_url)

collection = chroma.get_or_create_collection(
    name="disaster_docs",
    embedding_function=OpenAIEmbeddingFunction(
        api_key=os.getenv("OPENAI_API_KEY"),
        model_name="text-embedding-3-small"
    )
)

DATA_FOLDER = r"C:\Users\nancy\Downloads\DSI Certificate\deploying-ai\05_src\documents\hdx_files"

if collection.count() == 0:
    ingest_folder(DATA_FOLDER)


class DisasterRowData(BaseModel):
    """Structured disaster data response from semantic search."""
    source_file: str = Field(..., description="The source Excel file the snippet came from.")
    snippet: str = Field(..., description="A portion of the row text relevant to the user query.")


@tool
def find_disaster_rows(query: str, n_results: int = 3) -> list[DisasterRowData]:
    """Fetches disaster data based on the query. Returns n_results snippets."""
    results = get_context(query, collection, n_results)
    return results



def ingest_folder(folder_path: str):
    """
    Ingest ALL .xlsx/.xls files in folder into Chroma.
    Each row becomes one document.
    """
    files = [
        f for f in os.listdir(folder_path)
        if f.lower().endswith((".xlsx", ".xls"))
    ]
    if not files:
        _logs.warning(f"No Excel files found in: {folder_path}")
        return

    for fname in files:
        full_path = os.path.join(folder_path, fname)
        _logs.info(f"Ingesting: {full_path}")

        df = pd.read_excel(full_path)
        df = df.dropna(how="all")
        if df.empty:
            continue

        docs, ids, metas = [], [], []
        for i, row in df.iterrows():
            parts = []
            for col in df.columns:
                val = row.get(col)
                if pd.isna(val):
                    continue
                parts.append(f"{col}: {val}")
            if not parts:
                continue

            text = " | ".join(parts)
            docs.append(text)
            ids.append(f"{fname}_{i}")
            metas.append({"file": fname})

        if docs:
            collection.upsert(documents=docs, ids=ids, metadatas=metas)


def get_file_from_custom_id(custom_id: str):
    # custom_id is like: "<filename>_<rowindex>"
    # split from the right to avoid underscores inside filename
    return custom_id.rsplit("_", 1)[0]


def get_context_data(query: str, collection: chromadb.api.models.Collection, top_n: int):
    results = collection.query(
        query_texts=[query],
        n_results=top_n,
        include=["documents", "metadatas", "ids"]
    )

    context_data = []
    ids = results.get("ids", [[]])[0]
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]

    for idx, custom_id in enumerate(ids):
        # Prefer metadata, fallback to parsing id
        meta = metas[idx] if idx < len(metas) else {}
        source_file = meta.get("file") if meta else None
        if not source_file:
            source_file = get_file_from_custom_id(custom_id)

        context_data.append({
            "file": source_file,
            "text": docs[idx] if idx < len(docs) else "N/A"
        })

    return context_data


def get_context(query: str, collection: chromadb.api.models.Collection, top_n: int):
    context_data = get_context_data(query, collection, top_n)
    out = []
    if not context_data:
        return out

    for item in context_data:
        rec = DisasterRowData(
            source_file=item.get("file", "N/A"),
            snippet=item.get("text", "N/A")
        )
        out.append(rec)

    return out