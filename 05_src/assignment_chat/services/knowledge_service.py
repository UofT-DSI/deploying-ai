import os
import pandas as pd
import chromadb
from openai import OpenAI

from pathlib import Path

SECRETS_PATH = Path(__file__).resolve().parent.parent.parent / ".secrets"

load_dotenv_path = SECRETS_PATH

from dotenv import load_dotenv
load_dotenv(load_dotenv_path)

client = OpenAI()

current_dir = Path(__file__).resolve().parent.parent
csv_path = current_dir / "data" / "travel_knowledge.csv"
db_path = current_dir / "chroma_db"

df = pd.read_csv(csv_path)

chroma_client = chromadb.PersistentClient(path=str(db_path))

collection = chroma_client.get_or_create_collection(name="travel_knowledge")

if collection.count() == 0:
    for index, row in df.iterrows():
        text = f"{row['title']}. {row['category']}. {row['content']}"

        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )

        collection.add(
            ids=[str(index)],
            documents=[text],
            metadatas=[{
                "title": row["title"],
                "category": row["category"]
            }],
            embeddings=[response.data[0].embedding]
        )

def search_knowledge(question):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=question
    )

    results = collection.query(
        query_embeddings=[response.data[0].embedding],
        n_results=3
    )

    documents = results["documents"][0]

    return "\n\n".join(documents)