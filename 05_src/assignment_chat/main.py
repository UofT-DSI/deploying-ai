import os
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv

secrets_path = Path(__file__).resolve().parents[1] / ".secrets"
load_dotenv(secrets_path)
from langchain.chat_models import init_chat_model
from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing_extensions import TypedDict

from prompts import return_instructions
from tools import (
    create_study_quiz,
    get_programming_wisdom,
    search_ai_knowledge,
)

class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


MODEL = os.getenv("MODEL", "gpt-4o-mini")

model = init_chat_model(
    MODEL,
    model_provider="openai",
    temperature=0,
)

tools = [
    get_programming_wisdom,
    search_ai_knowledge,
    create_study_quiz,
]

instructions = return_instructions()


def call_model(state: State):
    model_with_tools = model.bind_tools(tools)

    response = model_with_tools.invoke(
        [SystemMessage(content=instructions)] + state["messages"]
    )

    return {"messages": [response]}


def get_graph():
    builder = StateGraph(State)

    builder.add_node("call_model", call_model)
    builder.add_node("tools", ToolNode(tools))

    builder.add_edge(START, "call_model")

    builder.add_conditional_edges(
        "call_model",
        tools_condition,
    )

    builder.add_edge("tools", "call_model")

    return builder.compile()