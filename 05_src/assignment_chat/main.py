from langgraph.graph import StateGraph, MessagesState, START
from langchain.chat_models import init_chat_model
from langgraph.prebuilt.tool_node import ToolNode, tools_condition
from langchain_core.messages import SystemMessage

from dotenv import load_dotenv

from assignment_chat.prompts import return_instructions
from assignment_chat.tools_humanitariancrises import get_humanitarian_needs
from assignment_chat.tools_disastercontext import find_disaster_rows
from fastmcp import MCPClient

from utils.logger import get_logger


_logs = get_logger(__name__)
load_dotenv(".env")
load_dotenv(".secrets")

chat_agent = init_chat_model("openai:gpt-4o-mini")

instructions = return_instructions()

mcp_client = MCPClient("http://localhost:3000")
mcp_tools = mcp_client.tools()

tools = [
    get_humanitarian_needs,   
    find_disaster_rows,       
    *mcp_tools                
]


def call_model(state: MessagesState):
    """LLM decides whether to call a tool or not."""
    response = chat_agent.bind_tools(tools).invoke(
        [SystemMessage(content=instructions)] + state["messages"]
    )
    return {"messages": [response]}


def get_graph():
    builder = StateGraph(MessagesState)
    builder.add_node("call_model", call_model)
    builder.add_node("tools", ToolNode(tools))

    builder.add_edge(START, "call_model")
    builder.add_conditional_edges("call_model", tools_condition)
    builder.add_edge("tools", "call_model")

    return builder.compile()