
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load course environment settings
SRC_DIR = Path(__file__).resolve().parents[1]

load_dotenv(SRC_DIR / ".env")
load_dotenv(SRC_DIR / ".secrets")

sys.path.insert(0, str(SRC_DIR))

import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import ToolNode, tools_condition

from assignment_chat.prompts import return_instructions
from assignment_chat.services.food_api import get_food_nutrition
from assignment_chat.services.semantic_search import search_knowledge
from assignment_chat.services.workout_calculator import calculate_workout_volume

os.environ["LANGCHAIN_TRACING_V2"] = "false"
# Initialize AI model
chat_agent = ChatOpenAI(
    model="gpt-4o-mini",
    base_url="https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1",
    api_key="any value",
    default_headers={
        "x-api-key": os.getenv("API_GATEWAY_KEY")
    }
)
# Available tools
tools = [
    get_food_nutrition,
    search_knowledge,
    calculate_workout_volume
]

# System instructions
instructions = return_instructions()


# AI node
def call_model(state: MessagesState):
    response = chat_agent.bind_tools(tools).invoke(
        [SystemMessage(content=instructions)] + state["messages"]
    )

    return {"messages": [response]}


# Build LangGraph
def get_graph():
    builder = StateGraph(MessagesState)

    builder.add_node("call_model", call_model)
    builder.add_node("tools", ToolNode(tools))

    builder.add_edge(START, "call_model")

    builder.add_conditional_edges(
        "call_model",
        tools_condition
    )

    builder.add_edge("tools", "call_model")

    return builder.compile()


if __name__ == "__main__":
    graph = get_graph()

    response = graph.invoke({
        "messages": [
            (
                "user",
                 "Calculate my workout volume using the workout calculator: "
                 "4 sets, 12 reps, and 20 kg."
            )
        ]
    })

    for message in response["messages"]:
        print("\n---", message.type, "---")

        if getattr(message, "tool_calls", None):
            print("Tool calls:", message.tool_calls)

        if message.content:
            print(message.content)
