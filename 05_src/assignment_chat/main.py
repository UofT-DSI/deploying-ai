"""Assignment 2 graph: allowed tools and a topic gate before model dispatch."""

import re

from assignment_chat.prompts import return_instructions
from assignment_chat.tools_conversion import convert_units
from assignment_chat.tools_course_search import search_course_materials
from assignment_chat.tools_weather import get_weather
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

RESTRICTED = re.compile(
    r"\b(?:cats?|dogs?|kitt(?:y|ies)|pupp(?:y|ies)|canines?|felines?|"
    r"horoscopes?|zodiac|star\s+signs?|astrolog(?:y|ical)|aries|taurus|gemini|cancer|leo|virgo|"
    r"libra|scorpio|sagittarius|capricorn|aquarius|pisces|taylor\s+swift)\b",
    re.IGNORECASE,
)
REFUSAL = "I can't help with that topic. Ask me about course material, weather, or unit conversions."


def restricted_request(state: MessagesState) -> bool:
    latest = next((message for message in reversed(state["messages"]) if isinstance(message, HumanMessage)), None)
    return latest is not None and bool(RESTRICTED.search(str(latest.content)))


def get_graph():
    tools = [get_weather, search_course_materials, convert_units]
    model = init_chat_model("openai:gpt-4o-mini")
    instructions = return_instructions()

    def call_model(state: MessagesState):
        response = model.bind_tools(tools).invoke([SystemMessage(content=instructions)] + state["messages"])
        return {"messages": [response]}

    def refuse(state: MessagesState):
        return {"messages": [AIMessage(content=REFUSAL)]}

    builder = StateGraph(MessagesState)
    builder.add_node("call_model", call_model)
    builder.add_node("refuse", refuse)
    builder.add_node("tools", ToolNode(tools))
    builder.add_conditional_edges(START, lambda state: "refuse" if restricted_request(state) else "call_model")
    builder.add_edge("refuse", END)
    builder.add_conditional_edges("call_model", tools_condition)
    builder.add_edge("tools", "call_model")
    return builder.compile()
