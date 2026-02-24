from typing import Dict, Any, List
from pydantic import BaseModel, Field
from ..llm import get_client

class ProjectPlan(BaseModel):
    goal: str
    milestones: List[str] = Field(min_items=3, max_items=8)
    risks: List[str] = Field(min_items=2, max_items=6)
    next_actions: List[str] = Field(min_items=3, max_items=8)

def create_project_plan(goal: str) -> Dict[str, Any]:
    """
    Function tool: returns a structured plan. This is called by the model (function calling).
    """
    client = get_client()
    dev = (
        "Create a practical project plan in JSON according to the schema. "
        "Avoid banned topics. Be concise and actionable."
    )
    user = f"Goal: {goal}"
    resp = client.responses.parse(
        model="gpt-4o-mini",
        input=[
            {"role": "developer", "content": dev},
            {"role": "user", "content": user},
        ],
        text_format=ProjectPlan,
    )
    plan: ProjectPlan = resp.output_parsed
    return plan.model_dump()

def render_plan(plan: Dict[str, Any]) -> str:
    lines = []
    lines.append(f"**Filed Plan Objective:** {plan['goal']}\n")
    lines.append("**Milestones (scheduled):**")
    for m in plan["milestones"]:
        lines.append(f"- {m}")
    lines.append("\n**Risks (noted):**")
    for r in plan["risks"]:
        lines.append(f"- {r}")
    lines.append("\n**Next Actions (immediate):**")
    for a in plan["next_actions"]:
        lines.append(f"- {a}")
    return "\n".join(lines)