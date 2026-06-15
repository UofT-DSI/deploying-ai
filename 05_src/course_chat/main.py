from langchain.chat_models import init_chat_model
from langgraph.graph.state import CompiledStateGraph
from deepagents import create_deep_agent
from dotenv import load_dotenv
import os

from course_chat.prompts import return_instructions
from course_chat.tools_animals import get_cat_facts, get_dog_facts
from course_chat.tools_horoscope import get_horoscope
from course_chat.tools_music import recommend_albums
from course_chat.tools_course_rag import course_rag_subagent
from utils.logger import get_logger

_logs = get_logger(__name__)
load_dotenv(".env")
load_dotenv(".secrets")

_GATEWAY_URL = "https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1"
_USE_GATEWAY = os.getenv("USE_GATEWAY", "true").lower() != "false"


def _make_llm(model_id: str):
    if _USE_GATEWAY:
        return init_chat_model(
            model_id,
            base_url=_GATEWAY_URL,
            api_key="any value",
            default_headers={"x-api-key": os.getenv("API_GATEWAY_KEY")},
        )
    return init_chat_model(model_id)


tools = [get_cat_facts, get_dog_facts, recommend_albums, get_horoscope]


def get_agent() -> CompiledStateGraph:
    _logs.info(f"get_agent: USE_GATEWAY={_USE_GATEWAY}")
    llm = _make_llm("openai:gpt-4o-mini")
    return create_deep_agent(
        model=llm,
        tools=tools,
        subagents=[course_rag_subagent],
        system_prompt=return_instructions(),
    )
