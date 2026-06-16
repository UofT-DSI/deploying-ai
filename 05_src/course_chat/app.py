import asyncio
import uuid
from pathlib import Path

import gradio as gr  # import before filter setup so our filter prepends after gradio's

import warnings
# Suppress Starlette deprecation warning emitted on every HTTP request from gradio/routes.py
warnings.filterwarnings("ignore", message=".*HTTP_422_UNPROCESSABLE_ENTITY.*")

from langgraph.types import Command
from dotenv import load_dotenv

from course_chat.main import get_agent
from course_chat.last_path import load_last_paths, save_last_paths
from course_chat.tools_feedback import FEEDBACK_DIR
from course_chat.tools_mcp import init_mcp, get_mcp_tools, get_background_loop
from course_chat.tool_logger import ToolCallLogger
from utils.logger import get_logger

_logs = get_logger(__name__)
load_dotenv(".secrets")

# Agent is initialized in __main__ (after MCP) or lazily on first chat turn.
agent = None


def _ensure_agent():
    global agent
    if agent is None:
        agent = get_agent()
    return agent


def _agent_invoke(ag, args, config):
    """Invoke the agent, routing through the MCP background loop when present.

    MCP StructuredTools are async-only; running ainvoke in their own loop avoids
    the 'StructuredTool does not support sync invocation' error.
    """
    config_with_callbacks = {**config, "callbacks": list(config.get("callbacks") or []) + [ToolCallLogger()]}
    loop = get_background_loop()
    if loop and loop.is_running():
        return asyncio.run_coroutine_threadsafe(
            ag.ainvoke(args, config_with_callbacks, version="v2"), loop
        ).result()
    return ag.invoke(args, config_with_callbacks, version="v2")


def _format_interrupt_message(interrupt) -> str:
    """Format a HITL interrupt as a readable chat message."""
    try:
        action_requests = interrupt.value.get("action_requests", [])
        if action_requests:
            req = action_requests[0]
            args = req.get("args", {})
            file_path = args.get("file_path", "unknown")
            content = args.get("content", "")
            preview = content[:300] + "\n..." if len(content) > 300 else content
            full_path = FEEDBACK_DIR / Path(file_path).name
            overwrite_note = " **(will overwrite existing file)**" if full_path.exists() else ""
            return (
                f"🔐 **Write permission required{overwrite_note}**\n\n"
                f"Target: `{file_path}`\n\n"
                f"**Content preview:**\n```markdown\n{preview}\n```\n\n"
                f"Reply **yes** to approve or anything else to cancel."
            )
    except Exception as e:
        _logs.warning("Could not format interrupt: %s", e)
    return (
        "🔐 **Write permission required.** "
        "Reply **yes** to approve or anything else to cancel."
    )


def _list_feedback_files() -> str:
    if not FEEDBACK_DIR.exists():
        return "_No feedback files yet._"
    files = sorted(FEEDBACK_DIR.glob("*.md"))
    if not files:
        return "_No feedback files yet._"
    lines = ["**Exported feedback files:**", ""]
    for f in files:
        size_kb = f.stat().st_size / 1024
        lines.append(f"- `{f.name}` ({size_kb:.1f} KB)")
    return "\n".join(lines)


def _path_info_text(a1: str, a2: str) -> str:
    parts = []
    if a1:
        parts.append(f"A1: `{a1}`")
    if a2:
        parts.append(f"A2: `{a2}`")
    if parts:
        return "📁 " + " | ".join(parts)
    return "📁 No assignment paths set — use the **Assignment** tab to configure them."


def _last_message(state, fallback: str) -> str:
    msgs = state.values.get("messages", [])
    return next((m.content for m in reversed(msgs) if getattr(m, "content", None)), fallback)


def _append_turn(history: list, message: str, response: str) -> list:
    return history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": response},
    ]


def _build_user_message(message: str, a1_path: str, a2_path: str) -> str:
    path_lines = []
    if a1_path:
        path_lines.append(f"[Assignment 1 path: {a1_path}]")
    if a2_path:
        path_lines.append(f"[Assignment 2 path: {a2_path}]")
    return "\n".join(path_lines + ["", message]) if path_lines else message


def _handle_interrupt_turn(ag, config: dict, message: str, history: list, thread_id: str) -> tuple:
    approve = message.strip().lower() in ("yes", "y", "approve", "ok", "sure")
    _logs.info("chat_fn: HITL response — approve=%s thread_id=%s", approve, thread_id)
    decision = {"type": "approve"} if approve else {"type": "reject", "message": message}
    try:
        _agent_invoke(ag, Command(resume={"decisions": [decision]}), config)
        state = ag.get_state(config)
    except Exception as exc:
        _logs.error("chat_fn: agent resume failed for thread_id=%s: %s", thread_id, exc)
        return _append_turn(history, message, "Something went wrong during approval. Please try again."), "", False
    new_interrupted = bool(state.interrupts)
    _logs.debug("chat_fn: post-resume state — new_interrupted=%s thread_id=%s", new_interrupted, thread_id)
    response = (
        _format_interrupt_message(state.interrupts[0])
        if new_interrupted
        else _last_message(state, "Done.")
    )
    return _append_turn(history, message, response), "", new_interrupted


def chat_fn(
    message: str,
    history: list,
    thread_id: str,
    is_interrupted: bool,
    a1_path: str,
    a2_path: str,
) -> tuple:
    ag = _ensure_agent()
    config = {"configurable": {"thread_id": thread_id}}

    if is_interrupted:
        return _handle_interrupt_turn(ag, config, message, history, thread_id)

    _logs.info(
        "chat_fn: normal turn — thread_id=%s msg_len=%d a1=%s a2=%s",
        thread_id, len(message), a1_path, a2_path,
    )
    msg_tuples = [(m["role"], m["content"]) for m in history]
    msg_tuples.append(("user", _build_user_message(message, a1_path, a2_path)))

    try:
        _agent_invoke(ag, {"messages": msg_tuples}, config)
        state = ag.get_state(config)
    except Exception as exc:
        _logs.error("chat_fn: agent invocation failed for thread_id=%s: %s", thread_id, exc)
        return _append_turn(history, message, "Something went wrong. Please try again."), "", False

    if state.interrupts:
        _logs.info("chat_fn: interrupt raised mid-turn for thread_id=%s", thread_id)
        response = _format_interrupt_message(state.interrupts[0])
        return _append_turn(history, message, response), "", True

    response = _last_message(state, "No response.")
    _logs.info("chat_fn: normal turn complete — thread_id=%s", thread_id)
    return _append_turn(history, message, response), "", False


def save_paths_fn(a1: str, a2: str) -> tuple:
    a1 = a1.strip()
    a2 = a2.strip()
    save_last_paths(a1, a2)
    return a1, a2, "✅ Paths saved.", _path_info_text(a1, a2)


with gr.Blocks(title="Course Chat") as app:
    thread_id_state = gr.State(value=lambda: str(uuid.uuid4()))
    interrupted_state = gr.State(value=False)
    a1_path_state = gr.State(value=lambda: load_last_paths()[0])
    a2_path_state = gr.State(value=lambda: load_last_paths()[1])

    with gr.Tabs():

        with gr.Tab("💬 Chat"):
            chatbot = gr.Chatbot(label="Course Chat", height=520)
            path_info = gr.Markdown(value=lambda: _path_info_text(*load_last_paths()))
            with gr.Row():
                msg_box = gr.Textbox(
                    placeholder="Ask about course material, request an assignment review, or just chat...",
                    show_label=False,
                    scale=9,
                    autofocus=True,
                )
                send_btn = gr.Button("Send", scale=1, variant="primary")

            chat_inputs = [msg_box, chatbot, thread_id_state, interrupted_state, a1_path_state, a2_path_state]
            chat_outputs = [chatbot, msg_box, interrupted_state]
            msg_box.submit(chat_fn, chat_inputs, chat_outputs)
            send_btn.click(chat_fn, chat_inputs, chat_outputs)

        with gr.Tab("📄 Assignment"):
            gr.Markdown(
                "## Assignment Submission Paths\n\n"
                "Set the paths to your submission files. Paths are saved across restarts."
            )
            gr.Markdown("### Assignment 1")
            a1_path_input = gr.Textbox(
                label="Assignment 1 — notebook file",
                value=lambda: load_last_paths()[0],
                placeholder=r"e.g. C:/Users/you/work/repo/02_activities/assignment_1.ipynb",
            )
            gr.Markdown("### Assignment 2")
            a2_path_input = gr.Textbox(
                label="Assignment 2 — project directory",
                value=lambda: load_last_paths()[1],
                placeholder=r"e.g. C:/Users/you/work/repo/05_src/assignment_chat",
            )
            save_paths_btn = gr.Button("Save Paths", variant="primary")
            path_save_status = gr.Markdown()

            save_paths_btn.click(
                save_paths_fn,
                [a1_path_input, a2_path_input],
                [a1_path_state, a2_path_state, path_save_status, path_info],
            )

        with gr.Tab("📝 Feedback"):
            gr.Markdown(
                "## Exported Feedback\n\n"
                f"Files are written to `{FEEDBACK_DIR}`."
            )
            feedback_display = gr.Markdown(value=_list_feedback_files)
            refresh_btn = gr.Button("🔄 Refresh")
            refresh_btn.click(lambda: _list_feedback_files(), outputs=feedback_display)

if __name__ == "__main__":
    _logs.info("Starting Course Chat App...")
    _logs.info("Initializing MCP tool connections (Docker required)...")
    init_mcp()
    mcp_tools = get_mcp_tools()
    if mcp_tools:
        _logs.info("MCP tools loaded (%d): %s", len(mcp_tools), [t.name for t in mcp_tools])
    else:
        _logs.warning("No MCP tools loaded — Docker may not be running or images not pulled.")
    agent = get_agent(extra_tools=mcp_tools)
    app.launch()
