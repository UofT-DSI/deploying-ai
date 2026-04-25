import os
from openai import OpenAI
from dotenv import load_dotenv

def get_client_api():
    load_dotenv()
    load_dotenv(".secrets")
    
    API_GATEWAY_KEY = os.getenv("API_GATEWAY_KEY")
    
    if not API_GATEWAY_KEY:
        raise ValueError("Please set the API_GATEWAY_KEY environment variable in .secrets file.")
    
    client = OpenAI(
        base_url='https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1',
        api_key='any value',
        default_headers={"x-api-key": API_GATEWAY_KEY}
    )
    return client