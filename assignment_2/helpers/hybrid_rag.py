import sys
sys.path.append('../../05_src/')


from pydantic import BaseModel, Field
from typing import List, Dict
from dotenv import load_dotenv
from langchain.tools import tool
from sklearn.feature_extraction.text import TfidfVectorizer
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

import os
import requests
import json
import pandas as pd
import chromadb
from pathlib import Path


ENV_DIR = Path(__file__).resolve().parents[2] / "05_src"  # adjust levels as needed
load_dotenv(ENV_DIR / ".env")
load_dotenv(ENV_DIR / ".secrets")

COLLECTION_NAME = "product_list"
CHROMA_URL = os.getenv("CHROMA_URL")
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL')




USE_GATEWAY = os.getenv("USE_GATEWAY", "False").lower() == "true"

if USE_GATEWAY:
    embedding_function = OpenAIEmbeddingFunction(
        api_key="any value",
        api_base="https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1",
        api_type="openai",
        model_name=EMBEDDING_MODEL,
        default_headers={
            "x-api-key": os.getenv("API_GATEWAY_KEY")
        }
    )
else:
    embedding_function = OpenAIEmbeddingFunction(
        api_key=os.getenv("OPENAI_API_KEY"),
        model_name=EMBEDDING_MODEL
    )


def get_keywords(user_prompts: List[str]) -> str:

    vectorizer=TfidfVectorizer(stop_words='english')

    tfidf_matrix = vectorizer.fit_transform(user_prompts)
    feature_names=vectorizer.get_feature_names_out()
    target_row=tfidf_matrix.toarray()[-1]

    keywords = pd.Series(target_row, index=feature_names).sort_values(ascending=False)

    first_keyword = keywords.reset_index().iat[0, 0]  if len(keywords) > 1 else ""

    return first_keyword


def get_context_data(query: str, history: List[str]=[], top_n: int=1):
    chroma = chromadb.HttpClient(host=CHROMA_URL)

    query_history = history if len(history) > 1 else []
    kwargs = dict(query_texts=[query], n_results=top_n)

    full_user_history = query_history + [query]

    print(full_user_history, query)

    keyword = get_keywords(full_user_history) if len(full_user_history) > 1 else ""

    if keyword:
        kwargs['where_document'] = {"$contain": keyword}

    collection = chroma.get_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_function
    )
    results = collection.query(**kwargs)
    context_data = []

    for idx in range(len(results['ids'][0])):
        details = dict(results['metadatas'][0][idx])
        details["product_id"] = results['ids'][0][idx]
        details['content'] = results['documents'][0][idx]
        context_data.append(details)

    return context_data



def generate_prompt(query: str, context_data: Dict):

    context = context_data[0]
    prompt = ("Given a query, provide a detailed response using the context from relevant the list of product from the government of canada statistics." 
              "Each product has an id that reference a statistic conducted by the government of Canada."
              "With the tools available, use the product id and the graph title to fetch the data from the website api and create a graph with the statistics. \n\n")
    prompt += f'<query>{query}</query>\n\n'
    prompt += '<context>\n'
    prompt += f"- Product ID: {context.get('product_id', 'N/A')}\n"
    prompt += f"- Graph Title: {context.get('content', 'N/A')}\n"
    prompt += '</context>\n\n'

    prompt += '\nBased on the context and nothing else, provide a detailed response to the query.'
    return prompt



def generate_augmented_prompt(query: str) -> str:
    context_data = get_context_data(query)
    prompt = generate_prompt(query, context_data)

    return prompt


    """
    response = client.responses.create(
        model=MODEL,
        instructions='You are a helpful assistant that provides information based on Pitchfork reviews.',
        input=[{'role': 'user', 'content': prompt}],
        max_output_tokens=500,
        temperature=1.0
    )
    return response.output_text
    """

generate_augmented_prompt("What about the type of people who reach out to the police?")