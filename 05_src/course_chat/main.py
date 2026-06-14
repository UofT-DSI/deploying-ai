from langchain.chat_models import init_chat_model
from langgraph.graph.state import CompiledStateGraph
from deepagents import create_deep_agent
from dotenv import load_dotenv
import os

from course_chat.prompts import return_instructions
from course_chat.tools_animals import get_cat_facts, get_dog_facts
from course_chat.tools_horoscope import get_horoscope
from course_chat.tools_music import recommend_albums
from utils.logger import get_logger

_logs = get_logger(__name__)
load_dotenv(".env")
load_dotenv(".secrets")

_GATEWAY_URL = "https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1"

tools = [get_cat_facts, get_dog_facts, recommend_albums, get_horoscope]


def get_agent() -> CompiledStateGraph:
    llm = init_chat_model(
        "openai:gpt-4o-mini",
        base_url=_GATEWAY_URL,
        api_key="any value",
        default_headers={"x-api-key": os.getenv("API_GATEWAY_KEY")},
    )
    return create_deep_agent(model=llm, tools=tools, system_prompt=return_instructions())
