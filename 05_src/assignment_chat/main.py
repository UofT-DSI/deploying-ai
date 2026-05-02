from langgraph.graph import StateGraph, MessagesState, START
from langchain.chat_models import init_chat_model
from langgraph.prebuilt.tool_node import ToolNode, tools_condition
from langchain_core.messages import SystemMessage
from dotenv import load_dotenv
import os
from assignment_chat.prompts import return_instructions
from assignment_chat.tools_api import get_joke
from assignment_chat.tools_semantic import semantic_search
from assignment_chat.tools_function import calculate
from utils.logger import get_logger

_logs = get_logger(__name__)
load_dotenv(".env")
load_dotenv(".secrets")

chat_agent = init_chat_model(
    "openai:gpt-4o-mini",
    api_key=os.getenv("OPENAI_API_KEY", "any_value"),
    base_url="https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1",
    default_headers={"x-api-key": os.getenv("API_GATEWAY_KEY")}
)
tools = [get_joke, semantic_search, calculate]
instructions = return_instructions()

def call_model(state: MessagesState):
    # Truncate messages to handle context window limits
    messages = state["messages"]
    if len(messages) > 10:
        messages = messages[-5:]
    
    response = chat_agent.bind_tools(tools).invoke([SystemMessage(content=instructions)] + messages)
    return {"messages": [response]}

def get_graph():
    builder = StateGraph(MessagesState)
    builder.add_node("call_model", call_model)
    builder.add_node("tools", ToolNode(tools))
    builder.add_edge(START, "call_model")
    builder.add_conditional_edges("call_model", tools_condition)
    builder.add_edge("tools", "call_model")
    return builder.compile()
