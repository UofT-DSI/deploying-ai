"""
Utilities for the feedback export flow.

The actual file write is handled by the FilesystemBackend write tool (provided
by create_deep_agent) and is gated by FilesystemPermission(mode="interrupt").
This module provides path helpers and a markdown formatter used by the parent agent.
"""
from datetime import datetime
from pathlib import Path
from utils.logger import get_logger

from course_chat.tools_assignment_reviewer import AssignmentFeedback, RequirementCheck

_logs = get_logger(__name__)

FEEDBACK_DIR: Path = Path(__file__).resolve().parent / "feedback"
try:
    FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
except OSError as exc:
    _logs.error("tools_feedback: could not create FEEDBACK_DIR %s: %s", FEEDBACK_DIR, exc)
    raise

STATUS_ICONS = {"complete": "✅", "partial": "⚠️", "missing": "❌"}


def timestamped_feedback_path(assignment_number: int) -> Path:
    """Return a timestamped path for an assignment feedback file.

    Pattern: FEEDBACK_DIR/feedback_assignment_{1|2}_{YYYY-MM-DDTHHMMSS}.md
    Example: feedback_assignment_1_2026-06-14T215337.md

    Colons are omitted from the time portion — they are illegal in Windows filenames.
    """
    ts = datetime.now().strftime("%Y-%m-%dT%H%M%S")
    name = f"feedback_assignment_{assignment_number}_{ts}.md"
    path = FEEDBACK_DIR / name
    _logs.debug("timestamped_feedback_path: %s", path)
    return path


def format_feedback_as_markdown(feedback: AssignmentFeedback) -> str:
    """Render an AssignmentFeedback Pydantic object as a markdown document."""
    _logs.debug(
        "format_feedback_as_markdown: assignment=%s checks=%d",
        feedback.assignment,
        len(feedback.checks),
    )
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
