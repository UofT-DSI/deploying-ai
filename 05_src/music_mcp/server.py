from fastmcp import FastMCP
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from pydantic import BaseModel, Field

import sqlalchemy as sa
import pandas as pd

from dotenv import load_dotenv
import ngrok
import os

from utils.logger import get_logger

# Load environment variables and secrets
load_dotenv()
load_dotenv(".secrets")

# Setup Logger
_logs = get_logger(__name__)


MCP_DOMAIN = os.getenv("MCP_DOMAIN")

vector_db_client_url="http://localhost:8000"
chroma = chromadb.HttpClient(host=vector_db_client_url)
collection = chroma.get_collection(name="pitchfork_reviews", 
                                   embedding_function=OpenAIEmbeddingFunction(
                                       api_key = os.getenv("OPENAI_API_KEY"),
                                       model_name="text-embedding-3-small")
                                   )

# Initialize MCP Server
mcp = FastMCP(
    name="music_recommendation_server",
    instructions="""
    This server provides album recommendations based on Pitchfork reviews.
    """
)

class MusicReviewData(BaseModel):
    """Structured music review data response."""
    title: str = Field(..., description="The title of the album.")
    artist: str = Field(..., description="The artist of the album.")
    review: str = Field(..., description="A portion of the album review that is relevant to the user query.")
    year: int = Field(None, description="The release year of the album.")
    score: float = Field(None, description="The Pitchfork score of the album. The score is numeric and its scale is from 0 to 10, with 10 being the highest rating. Any album with a score greater than 8.0 is considered a must-listen; album with a score greater than 6.5 is good.")


@mcp.tool(
        name="recommend_albums",
        description="Recommends albums based on user query by fetching relevant Pitchfork reviews.",


)
def recommend_albums(query: str, n_results: int = 1) -> list[MusicReviewData]:
    """Fetches music review data based on the query. Returns n_results reviews."""
    recommendations = get_context(query, collection, n_results)
    return recommendations


def additional_details(review_id:str):
    _logs.debug(f'Fetching additional details for review ID: {review_id}')
    engine = sa.create_engine(os.getenv("SQL_URL"))
    query = f"""
    SELECT r.reviewid,
		r.title,
		r.artist,
		r.score,
		g.genre
    FROM reviews AS r
    LEFT JOIN genres as g
	    ON r.reviewid = g.reviewid
    WHERE r.reviewid = '{review_id}'
    """
    with engine.connect() as conn:
        result = pd.read_sql(query, conn)
    if not result.empty:
        row = result.iloc[0]
        details = {
            "reviewid": row['reviewid'],
            "album": row['title'],
            "score": row['score'],
            "artist": row['artist']
        }
        return details
    else:
        _logs.warning(f'No details found for review ID: {review_id}')
        return {}
    
def get_reviewid_from_custom_id(custom_id:str):
    return custom_id.split('_')[0]

def get_context_data(query:str, collection:chromadb.api.models.Collection, top_n:int):
    results = collection.query(
        query_texts=[query],
        n_results=top_n
    )
    context_data = []
    for idx, custom_id in enumerate(results['ids'][0]):
        review_id = get_reviewid_from_custom_id(custom_id)
        details = additional_details(review_id)
        details['text'] = results['documents'][0][idx]
        context_data.append(details)
    return context_data

def get_context(query:str, collection:chromadb.api.models.Collection, top_n:int):
    # context_data = get_context_data(query, collection, top_n)
    recommendations = []
    # for item in context_data:
    #     _logs.debug(f'Context item: {item.title} by {item.artist} with score {item.score}.')
    #     # rec = MusicReviewData(
        #     title=item.get('album', 'N/A'),
        #     artist=item.get('artist', 'N/A'),
        #     review=item.get('text', 'N/A'),
        #     year=item.get('year', None),
        #     score=item.get('score', None)
        # )
    rec = MusicReviewData(
        title="Cri Cri",
        artist="Gabilondo Soler",
        review="A great album!",
        year=1945,
        score=8.5
    )
    recommendations.append(rec)
    return recommendations


if __name__ == "__main__":
    listener = ngrok.forward("localhost:3000", authtoken_from_env=True,
                                domain=MCP_DOMAIN)
    _logs.info(f'Ngrok tunnel established at {listener.url()}')
    mcp.run(
        transport="http",
        host="localhost", 
        port=3000, 
    )
