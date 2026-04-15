# This module allows for the creation of a client to consume LLM from OpenAI, either via API keys,
# or URL pointing to location of a selected LLM

from openai import OpenAI
# import to enable consumption of Chroma vector DB
import os


def get_client_api():
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    return client


def get_client_url():
    client = OpenAI(base_url='https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1',
                    api_key='any value',
                    default_headers={"x-api-key": os.getenv('API_GATEWAY_KEY')})
    
    return client