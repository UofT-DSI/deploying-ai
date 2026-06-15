import json
from pathlib import Path
from typing import Literal

from langchain.tools import tool
from deepagents import SubAgent
from pydantic import BaseModel
from utils.logger import get_logger

_logs = get_logger(__name__)

_MAX_FILE_KB = 50
_MAX_FILE_BYTES = _MAX_FILE_KB * 1024

REPO_ROOT = Path(__file__).resolve().parents[2]
_SPEC_PATHS = {
    "assignment_1": REPO_ROOT / "02_activities" / "assignment_1.ipynb",
    "assignment_2": REPO_ROOT / "02_activities" / "assignment_2.md",
}


# ---------------------------------------------------------------------------
# File-reading tools (passed to the reviewer subagent)
# ---------------------------------------------------------------------------

def _read_notebook_as_text(path: Path) -> str:
    """Format a Jupyter notebook as readable plain text."""
    with open(path, encoding="utf-8") as f:
        nb = json.load(f)
    parts = []
    for i, cell in enumerate(nb.get("cells", [])):
        cell_type = cell.get("cell_type", "unknown")
        source = "".join(cell.get("source", []))
        if source.strip():
            parts.append(f"[Cell {i} — {cell_type}]\n{source}")
    return "\n\n".join(parts)


@tool
def read_submission_file(path: str, max_kb: int = _MAX_FILE_KB) -> str:
    """Read a single assignment submission file and return its contents as text.

    Supports .ipynb (Jupyter notebooks are formatted as plain text), .md, .py, and .txt.
    Files exceeding max_kb kilobytes are truncated with a warning.
    """
    file_path = Path(path)
    if not file_path.exists():
        return f"[ERROR] File not found: {path}"

    max_bytes = max_kb * 1024

    try:
        if file_path.suffix == ".ipynb":
            text = _read_notebook_as_text(file_path)
        else:
            text = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"[ERROR] Could not read {path}: {e}"

    encoded = text.encode("utf-8")
    if len(encoded) > max_bytes:
        text = encoded[:max_bytes].decode("utf-8", errors="ignore")
        text += f"\n\n[TRUNCATED — file exceeds {max_kb} KB]"

    return text


@tool
def list_submission_directory(path: str) -> list[str]:
    """List all readable files under a directory path (recursive).

    Excludes __pycache__, .pyc files, and hidden files/directories.
    Returns a sorted list of relative file paths.
    """
    base = Path(path)
    if not base.exists():
        return [f"[ERROR] Directory not found: {path}"]
    if not base.is_dir():
        return [f"[ERROR] Not a directory: {path}"]

    files = []
    for p in sorted(base.rglob("*")):
        if p.is_file() and not any(
            part.startswith(".") or part == "__pycache__"
            for part in p.parts
        ) and p.suffix != ".pyc":
            files.append(str(p.relative_to(base)))
    return files


# ---------------------------------------------------------------------------
# Structured output schema
# ---------------------------------------------------------------------------

class RequirementCheck(BaseModel):
    requirement: str
    status: Literal["complete", "partial", "missing"]
    notes: str


class AssignmentFeedback(BaseModel):
    assignment: Literal["assignment_1", "assignment_2"]
    checks: list[RequirementCheck]
    next_steps: list[str]
    overall: str


# ---------------------------------------------------------------------------
# Reviewer subagent
# ---------------------------------------------------------------------------

_REVIEWER_SYSTEM_PROMPT = f"""You are an assignment reviewer for a Deploying AI course.

You will receive a description of the submission to review (a file path or directory path)
and the assignment name (assignment_1 or assignment_2).

## Review process

1. First, read the official spec:
   - Assignment 1 spec: {_SPEC_PATHS['assignment_1']}
   - Assignment 2 spec: {_SPEC_PATHS['assignment_2']}

2. Then read the student's submission using read_submission_file or list_submission_directory.

3. Check each requirement below and produce an AssignmentFeedback response.

---

## Assignment 1 Requirements

Check each of the following — status is "complete", "partial", or "missing":

R1-1: Pydantic BaseModel with ALL seven required fields: Author, Title, Relevance, Summary, Tone, InputTokens, OutputTokens.
R1-2: A chosen tone that is identifiable and consistent throughout the summary.
R1-3: Five or more assessment questions in the Summarization DeepEval metric.
R1-4: Three G-Eval metrics defined — Coherence/Clarity, Tonality, and Safety — each with five or more evaluation questions.
R1-5: Structured evaluation output for each metric with a Score and a Reason.
R1-6: An enhancement step that re-evaluates the summary after improvement.
R1-7: Written comments throughout the notebook explaining the approach.

---

## Assignment 2 Requirements

R2-1: At least three services: an API call, ChromaDB semantic search, and at least one of (function calling / web search / MCP).
R2-2: A Gradio chat UI with a distinct personality and conversation memory.
R2-3: Guardrails that block responses about cats, dogs, horoscopes, and Taylor Swift.
R2-4: A readme.md that explains the system (personality, services, guardrails).

---

When reviewing Assignment 2, use list_submission_directory first to see all files,
then read_submission_file on each relevant file. Apply the 50 KB cap per file.

Return your review as a structured AssignmentFeedback object."""


reviewer_subagent: SubAgent = {
    "name": "assignment-reviewer",
    "description": (
        "Reviews a student assignment submission against the official spec. "
        "Accepts a file path (Assignment 1) or directory path (Assignment 2)."
    ),
    "system_prompt": _REVIEWER_SYSTEM_PROMPT,
    "tools": [read_submission_file, list_submission_directory],
    "response_format": AssignmentFeedback,
}
