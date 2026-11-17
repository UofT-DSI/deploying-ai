
"""ResearchMate AI - LangGraph with ArXiv MCP integration."""

import re

from langchain.chat_models import init_chat_model
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
)
from langgraph.graph import (
    END,
    START,
    MessagesState,
    StateGraph,
)
from langgraph.prebuilt import ToolNode, tools_condition

from assignment_chat.prompts import return_instructions
from assignment_chat.tools_openalex import search_papers
from assignment_chat.tools_research_search import (
    search_research_papers,
)
from assignment_chat.services.arxiv_mcp_service import (
    get_arxiv_tools,
)


RESTRICTED = re.compile(
    r"\b(?:cats?|dogs?|kitt(?:y|ies)|pupp(?:y|ies)|"
    r"canines?|felines?|horoscopes?|zodiac|"
    r"astrolog(?:y|ical)|aries|taurus|gemini|"
    r"cancer|leo|virgo|libra|scorpio|sagittarius|"
    r"capricorn|aquarius|pisces|taylor\s+swift)\b",
    re.IGNORECASE,
)

REFUSAL = (
    "I can't help with that topic. "
    "Ask me about academic research or scholarly papers."
)


def restricted_request(state: MessagesState) -> bool:
    """Check the latest user request against restricted topics."""

    latest = next(
        (
            message
            for message in reversed(state["messages"])
            if isinstance(message, HumanMessage)
        ),
        None,
    )

    return (
        latest is not None
        and bool(RESTRICTED.search(str(latest.content)))
    )


async def get_graph():
    """Build LangGraph with local tools and discovered MCP tools."""

    local_tools = [
        search_papers,
        search_research_papers,
    ]

    # Discover tools from the external MCP server.
    mcp_tools = await get_arxiv_tools()

    tools = local_tools + mcp_tools

    print("Registered ResearchMate tools:")
    for research_tool in tools:
        print(f"  - {research_tool.name}")

    model = init_chat_model("openai:gpt-4o-mini")
    model_with_tools = model.bind_tools(tools)

    instructions = return_instructions()

    async def call_model(state: MessagesState):
        response = await model_with_tools.ainvoke(
            [
                SystemMessage(content=instructions)
            ] + state["messages"]
        )

        return {"messages": [response]}

    def refuse(state: MessagesState):
        return {
            "messages": [
                AIMessage(content=REFUSAL)
            ]
        }

    builder = StateGraph(MessagesState)

    builder.add_node("call_model", call_model)
    builder.add_node("refuse", refuse)
    builder.add_node(
        "tools",
        ToolNode(tools, handle_tool_errors=True),
    )

    builder.add_conditional_edges(
        START,
        lambda state: (
            "refuse"
            if restricted_request(state)
            else "call_model"
        ),
    )

    builder.add_edge("refuse", END)

    builder.add_conditional_edges(
        "call_model",
        tools_condition,
    )

    builder.add_edge("tools", "call_model")

    return builder.compile()
