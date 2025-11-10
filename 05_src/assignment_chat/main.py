from langgraph.graph import StateGraph, MessagesState, START
from langchain.chat_models import init_chat_model
from langgraph.prebuilt.tool_node import ToolNode, tools_condition
from langchain_core.messages import SystemMessage,  HumanMessage

from dotenv import load_dotenv
import json
import requests
import os
import weather_tool
import fun_facts
from utils.logger import get_logger



chat_agent = init_chat_model("gpt-4o-mini", model_provider="openai")
tools = [weather_tool.get_weather, fun_facts.query_fun_facts]

instructions = "you are an AI assistant with access to the following tools: " \
"" \
"Get weather based on current location. Use the tools when the user asks for weather information. If the user does not ask for weather information, respond normally." \
"Access a database of fun facts about various topics. Use the tools when the user asks for a fun fact about a specific topic. Query for a relevant fun fact to the topics discussed in the conversation. Do not give fun facts not listed in the fun fact database. If the user does not ask for a fun fact, respond normally." \
"" \
"Always respond in a sardonic manner."


def call_model(state: MessagesState):
    """LLM decides whether to call a tool or not"""
    response = chat_agent.bind_tools(tools).invoke( [SystemMessage(content=instructions)] + state["messages"])
    return {
        "messages": [response]
    }

def get_graph() -> StateGraph:
    builder = StateGraph(MessagesState)
    builder.add_node(call_model)
    builder.add_node(ToolNode(tools))
    builder.add_edge(START, "call_model")
    builder.add_conditional_edges(
        "call_model",
        tools_condition,
    )
    builder.add_edge("tools", "call_model")
    graph = builder.compile()
    return graph