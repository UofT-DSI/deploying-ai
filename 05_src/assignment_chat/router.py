from typing import Optional
from pydantic import BaseModel, Field
from .llm import get_client
from .services.api_weather import get_weather
from .services.semantic_search import semantic_answer
from .services.project_planner import create_project_plan, render_plan

class RouteDecision(BaseModel):
    route: str = Field(description="One of: weather, semantic, plan, chat")

    city: Optional[str] = None
    query: Optional[str] = None
    goal: Optional[str] = None

ROUTER_DEV = """
You are a routing controller for a chat assistant.
Select the best route for the user's request:

- weather: user asks about weather in a city/location
- semantic: user asks factual questions about AI deployment concepts; answer via semantic search
- plan: user asks to make a plan/roadmap/checklist for a project
- chat: general conversation or unclear requests

Return ONLY valid structured output matching the schema.
"""

def route(user_msg: str) -> str:
    client = get_client()

    resp = client.responses.parse(
        model="gpt-4o-mini",
        input=[
            {"role": "developer", "content": ROUTER_DEV},
            {"role": "user", "content": user_msg},
        ],
        text_format=RouteDecision,
    )

    decision: RouteDecision = resp.output_parsed
    r = (decision.route or "").strip().lower()

    if r == "weather":
        city = (decision.city or "").strip() or user_msg
        return get_weather(city)

    if r == "semantic":
        q = (decision.query or "").strip() or user_msg
        return semantic_answer(q)

    if r == "plan":
        goal = (decision.goal or "").strip() or user_msg
        plan = create_project_plan(goal)
        return render_plan(plan)

    return ""