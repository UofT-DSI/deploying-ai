# LangGraph agent wiring all 3 services together.
# Adapted from course_chat/main.py - same structure throughout:
#   - init_chat_model
#   - MessagesState
#   - call_model node
#   - ToolNode
#   - tools_condition
#   - StateGraph with START -> call_model -> tools -> call_model loop

from langgraph.graph import StateGraph, MessagesState, START
from langchain.chat_models import init_chat_model
from langgraph.prebuilt.tool_node import ToolNode, tools_condition
from langchain_core.messages import SystemMessage
import os

from dotenv import load_dotenv
load_dotenv(".env")
load_dotenv(".secrets")

from assignment_chat.prompts import return_instructions
from assignment_chat.tools_news import get_spaceflight_news
from assignment_chat.tools_rag import search_ai_report
from assignment_chat.tools_converter import convert_currency
from utils.logger import get_logger

_logs = get_logger(__name__)

# All tools available to the agent — same list pattern as course_chat/main.py
tools = [
    get_spaceflight_news,
    search_ai_report,
    convert_currency,
]

# Mirror utils/clients.py gateway logic for init_chat_model
if os.getenv("USE_GATEWAY", "FALSE").upper() == "TRUE":
    chat_agent = init_chat_model(
        "openai:gpt-4o-mini",
        base_url="https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1",
        api_key="any value",
        default_headers={"x-api-key": os.getenv("API_GATEWAY_KEY")},
    )
else:
    chat_agent = init_chat_model("openai:gpt-4o-mini")

instructions = return_instructions()


def call_model(state: MessagesState):
    """LLM decides whether to call a tool or not.
    Identical to call_model() in course_chat/main.py.
    """
    response = chat_agent.bind_tools(tools).invoke(
        [SystemMessage(content=instructions)] + state["messages"]
    )
    return {"messages": [response]}


def get_graph():
    """Build and compile the LangGraph agent.
    Identical structure to get_graph() in course_chat/main.py.
    """
    builder = StateGraph(MessagesState)
    builder.add_node(call_model)
    builder.add_node(ToolNode(tools))
    builder.add_edge(START, "call_model")
    builder.add_conditional_edges("call_model", tools_condition)
    builder.add_edge("tools", "call_model")
    return builder.compile()
