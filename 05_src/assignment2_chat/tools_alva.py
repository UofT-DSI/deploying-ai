from langchain.tools import tool
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from utils.logger import get_logger
import os
from pathlib import Path
_logs = get_logger(__name__)
load_dotenv()
load_dotenv(".secrets")

APP_DIR = Path (__file__).resolve().parent  
DB_PATH = APP_DIR / 'chroma' / 'alva_knowledge'
chroma = chromadb.PersistentClient(path=str(DB_PATH))

collection = chroma.get_or_create_collection(name='alva_workforce_readiness',
                                             embedding_function=OpenAIEmbeddingFunction(
                                                 model_name='text-embedding-3-small',
                                                 api_key='any value',
                                                 api_base=('https://k7uffyg03f.execute-api.'
                                                           'us-east-1.amazonaws.com/prod/openai/v1'),
                                                           default_headers={'x-api-key': os.getenv('API_GATEWAY_KEY')
                                                                            }
                                                                            )
                                                                            )


class AlvaKnowledgeData(BaseModel):
    """Structured music review data response."""
    title: str = Field(..., description='Title of the source document.')
    source: str = Field(..., description='Organization publising the guidance.')
    url: str = Field(..., description='Official source URL, if available.')
    passage: str = Field(..., description='Relevant passage from the knowledge base.')



def search_alva_knowledge(query: str, n_results: int = 3) -> list[AlvaKnowledgeData]:
    """Search indexed AI workforce readinesss documents by semantic similarity."""
    return get_context(query, collection, n_results)


def additional_details(metadata:dict) -> dict:

    """Read the title, publisher, and source link stored with passage."""
    return {
        'title': metadata.get('title',metadata.get('filename', 'untitled')),
        'source': metadata.get('source', 'unknown source '),
        'url': metadata.get('url','')
    }

def get_context_data(query:str, collection:chromadb.api.models.Collection, top_n:int):
    available = collection.count()
    if available == 0:
        return []

    results = collection.query(
        query_texts=[query],
        n_results=min (max (1, top_n), available),
        include=['documents', 'metadatas']
    )
    context_data = []
    for idx, custom_id in enumerate(results['ids'][0]):
        metadata= results ['metadatas'] [0] [idx] or {}
        details = additional_details(metadata)
        details['text'] = results['documents'][0][idx]
        details['chunk_id'] = custom_id
        context_data.append(details)
    return context_data

def get_context(query:str, collection:chromadb.api.models.Collection, top_n:int) -> list[AlvaKnowledgeData]:
    context_data = get_context_data(query, collection, top_n)
    recommendations = []
    if not context_data:
        return recommendations
    for item in context_data:

        rec = AlvaKnowledgeData(
            title=item.get('title', 'untitled'),
            source=item.get('source', 'unknown source'),
            url=item.get('url', ''),
            passage=item.get('text', '')
        )
        recommendations.append(rec)
    return recommendations