from langgraph.graph import StateGraph, MessagesState, START
from langchain.chat_models import init_chat_model
from langgraph.prebuilt.tool_node import ToolNode, tools_condition
from langchain_core.messages import SystemMessage,  HumanMessage

from dotenv import load_dotenv
import os
from openai import OpenAI

from assignment_chat.prompts import return_instructions
from assignment_chat.tool_get_sailing_weather import get_sailing_weather
from assignment_chat.tool_search_caribbean_tale import search_caribbean_tale

from utils.logger import get_logger
_logs = get_logger(__name__)

load_dotenv(".env")
load_dotenv(".secrets")

chat_agent = OpenAI(base_url='https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1', 
                default_headers={"x-api-key": os.getenv('API_GATEWAY_KEY')})

chat_agent = init_chat_model(
    "openai:gpt-4o-mini",
    base_url='https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1',
    api_key="any value",
    default_headers={"x-api-key": os.getenv('API_GATEWAY_KEY')}
)

tools = [get_sailing_weather, search_caribbean_tale]

instructions = return_instructions()



# @traceable(run_type="llm")
def call_model(state: MessagesState):
    """LLM decides whether to call a tool or not"""
    response = chat_agent.bind_tools(tools).invoke( [SystemMessage(content=instructions)] + state["messages"])
    return {
        "messages": [response]
    }

def get_graph():
    
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

