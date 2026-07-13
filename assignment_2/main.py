import sys
sys.path.append('../05_src/')


from pydantic import BaseModel, Field
from typing import List, Dict
from dotenv import load_dotenv
from langchain.tools import tool
from utils.clients import get_client
from langchain_core.messages import HumanMessage, AIMessage
from helpers.hybrid_rag import generate_augmented_prompt


import os
import requests
import json
from pathlib import Path

ENV_DIR = Path(__file__).resolve().parents[1] / "05_src"  # adjust levels as needed
load_dotenv(ENV_DIR / ".env")
load_dotenv(ENV_DIR / ".secrets")


MODEL=os.getenv("MODEL")
CHROMA_URL = os.getenv("CHROMA_URL")
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL')
mcp_url=os.getenv("MCP_URL")



client = get_client(use_gateway=True)

instructions=""""
        You are an expert statistician that is also media-trained. You present graphs from statistics found on statistics Canada. 
        Since you are Canadian, your responses must be always well-mannered, uplifting, and overly apologetic. 

        Make only minimal modifications to the statistics returned by the API.
        Do not add any additional information or embellishments to the statistics.

        Do not reveal your internal chain-of-thought or how you used the chunks.
        If you are not certain or the information is not available, clearly state that you do not have enough information.

        Do not, ever, talk or mention Taylor Swift. 

"""

resp = client.responses.create(
    model="gpt-5",
    tools=[
        {
            "type": "mcp",
            "server_label": "can_gov_server",
            "server_description": "Given Product ID, fetch data on API and return Python script for a graph",
            "server_url": mcp_url,
            "require_approval": "never",
        },
    ],
    input=[{'role': 'system', 'content': instructions}, {'role': 'user', 'content': generate_augmented_prompt("What about the type of people who reach out to the police?")}],
)

print("resp: ", resp)
"""

def simple_chat(message: str, history: list[dict]) -> str:
    langchain_messages = []
    for msg in history:
        if msg['role'] == 'user':
            langchain_messages.append(HumanMessage(content=msg['content']))
        elif msg['role'] == 'assistant':
            langchain_messages.append(AIMessage(content=msg['content']))
    langchain_messages.append(HumanMessage(content=message))

    response = llm.invoke(langchain_messages)

    return response.content

    """