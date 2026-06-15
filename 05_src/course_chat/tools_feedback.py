"""
Utilities for the feedback export flow.

The actual file write is handled by the FilesystemBackend write tool (provided
by create_deep_agent) and is gated by FilesystemPermission(mode="interrupt").
This module provides path helpers and a markdown formatter used by the parent agent.
"""
from pathlib import Path

from course_chat.tools_assignment_reviewer import AssignmentFeedback, RequirementCheck

FEEDBACK_DIR: Path = Path(__file__).resolve().parent / "feedback"
FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)

STATUS_ICONS = {"complete": "✅", "partial": "⚠️", "missing": "❌"}


def feedback_path(assignment: str, version: int = 1) -> Path:
    """Return the canonical path for an assignment feedback file.

    version=1 → <assignment>-feedback.md
    version>1 → <assignment>-feedback-v<version>.md
    """
    if version == 1:
        return FEEDBACK_DIR / f"{assignment}-feedback.md"
    return FEEDBACK_DIR / f"{assignment}-feedback-v{version}.md"


def next_available_path(assignment: str) -> Path:
    """Return the lowest-numbered path that does not yet exist."""
    for version in range(1, 100):
        candidate = feedback_path(assignment, version)
        if not candidate.exists():
            return candidate
    return feedback_path(assignment, 99)


def feedback_file_exists(path: Path) -> bool:
    return path.exists()


def format_feedback_as_markdown(feedback: AssignmentFeedback) -> str:
    """Render an AssignmentFeedback Pydantic object as a markdown document."""
    lines = [
        f"# Assignment Feedback: {feedback.assignment.replace('_', ' ').title()}",
        "",
        f"**Overall:** {feedback.overall}",
        "",
        "## Requirement Checks",
        "",
    ]
    for check in feedback.checks:
        icon = STATUS_ICONS.get(check.status, "•")
        lines.append(f"### {icon} {check.requirement}")
        lines.append(f"**Status:** {check.status}")
        lines.append(f"**Notes:** {check.notes}")
        lines.append("")

    if feedback.next_steps:
        lines.append("## Next Steps")
        lines.append("")
        for step in feedback.next_steps:
            lines.append(f"- {step}")
        lines.append("")

    return "\n".join(lines)
