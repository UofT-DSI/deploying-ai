import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="gradio")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="starlette")

import uuid
from pathlib import Path

import gradio as gr
from langgraph.types import Command
from dotenv import load_dotenv

from course_chat.main import get_agent
from course_chat.last_path import load_last_path, save_last_path
from course_chat.tools_feedback import FEEDBACK_DIR
from utils.logger import get_logger

_logs = get_logger(__name__)
load_dotenv(".secrets")

agent = get_agent()


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
        _logs.warning(f"Could not format interrupt: {e}")
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


def chat_fn(
    message: str,
    history: list,
    thread_id: str,
    is_interrupted: bool,
    assignment_path: str,
) -> tuple:
    config = {"configurable": {"thread_id": thread_id}}

    if is_interrupted:
        approve = message.strip().lower() in ("yes", "y", "approve", "ok", "sure")
        decision = (
            {"type": "approve"}
            if approve
            else {"type": "reject", "message": message}
        )
        agent.invoke(Command(resume={"decisions": [decision]}), config, version="v2")
        state = agent.get_state(config)
        new_interrupted = bool(state.interrupts)
        if new_interrupted:
            response = _format_interrupt_message(state.interrupts[0])
        else:
            msgs = state.values.get("messages", [])
            response = next(
                (m.content for m in reversed(msgs) if getattr(m, "content", None)),
                "Done.",
            )
        history = history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": response},
        ]
        return history, "", new_interrupted

    # Normal turn — build message list for the agent
    msg_tuples = [(m["role"], m["content"]) for m in history]
    user_text = f"[Assignment path: {assignment_path}]\n\n{message}" if assignment_path else message
    msg_tuples.append(("user", user_text))

    agent.invoke({"messages": msg_tuples}, config, version="v2")
    state = agent.get_state(config)

    if state.interrupts:
        response = _format_interrupt_message(state.interrupts[0])
        history = history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": response},
        ]
        return history, "", True

    msgs = state.values.get("messages", [])
    response = next(
        (m.content for m in reversed(msgs) if getattr(m, "content", None)),
        "No response.",
    )
    history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": response},
    ]
    return history, "", False


def save_path_fn(path: str, current_path_state: str) -> tuple:
    path = path.strip()
    if path:
        save_last_path(path)
        status = f"✅ Path saved: `{path}`"
    else:
        status = "⚠️ Enter a file or directory path first."
        path = current_path_state
    return path, status


with gr.Blocks(title="Course Chat") as app:
    thread_id_state = gr.State(value=lambda: str(uuid.uuid4()))
    interrupted_state = gr.State(value=False)
    assignment_path_state = gr.State(value=load_last_path)

    with gr.Tabs():

        with gr.Tab("💬 Chat"):
            chatbot = gr.Chatbot(label="Course Chat", height=520)
            path_info = gr.Markdown(
                value=lambda: (
                    f"📁 Assignment path: `{load_last_path()}`"
                    if load_last_path()
                    else "📁 No assignment path set — use the **Assignment** tab to set one."
                )
            )
            with gr.Row():
                msg_box = gr.Textbox(
                    placeholder="Ask about course material, request an assignment review, or just chat...",
                    show_label=False,
                    scale=9,
                    autofocus=True,
                )
                send_btn = gr.Button("Send", scale=1, variant="primary")

            chat_inputs = [msg_box, chatbot, thread_id_state, interrupted_state, assignment_path_state]
            chat_outputs = [chatbot, msg_box, interrupted_state]
            msg_box.submit(chat_fn, chat_inputs, chat_outputs)
            send_btn.click(chat_fn, chat_inputs, chat_outputs)

        with gr.Tab("📄 Assignment"):
            gr.Markdown(
                "## Assignment Submission Path\n\n"
                "Set the path to your submission file (Assignment 1) or directory (Assignment 2). "
                "The path is saved across restarts."
            )
            assignment_path_input = gr.Textbox(
                label="File or directory path",
                value=load_last_path,
                placeholder="e.g. C:/Users/you/work/repo/02_activities/assignment_1.ipynb",
            )
            save_path_btn = gr.Button("Save Path", variant="primary")
            path_save_status = gr.Markdown()

            save_path_btn.click(
                save_path_fn,
                [assignment_path_input, assignment_path_state],
                [assignment_path_state, path_save_status],
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
    app.launch()
