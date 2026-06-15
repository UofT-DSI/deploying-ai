from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.memory import MemorySaver
from deepagents import create_deep_agent, FilesystemPermission
from deepagents.backends import FilesystemBackend
from dotenv import load_dotenv
import os

from course_chat.llm_factory import make_llm
from course_chat.prompts import return_instructions
from course_chat.tools_animals import get_cat_facts, get_dog_facts
from course_chat.tools_horoscope import get_horoscope
from course_chat.tools_music import recommend_albums
from course_chat.tools_course_rag import course_rag_subagent
from course_chat.tools_assignment_reviewer import reviewer_subagent
from course_chat.tools_feedback import FEEDBACK_DIR
from utils.logger import get_logger

_logs = get_logger(__name__)
load_dotenv(".env")
load_dotenv(".secrets")

tools = [get_cat_facts, get_dog_facts, recommend_albums, get_horoscope]

_feedback_permission = FilesystemPermission(
    operations=["write"],
    paths=[str(FEEDBACK_DIR)],
    mode="interrupt",
)


def get_agent(extra_tools: list | None = None) -> CompiledStateGraph:
    use_gateway = os.getenv("USE_GATEWAY", "true").lower() != "false"
    _logs.info("get_agent: USE_GATEWAY=%s", use_gateway)
    llm = make_llm("openai:gpt-4o-mini")
    all_tools = tools + (extra_tools or [])
    return create_deep_agent(
        model=llm,
        tools=all_tools,
        subagents=[course_rag_subagent, reviewer_subagent],
        permissions=[_feedback_permission],
        backend=FilesystemBackend(root_dir=str(FEEDBACK_DIR), virtual_mode=False),
        checkpointer=MemorySaver(),
        system_prompt=return_instructions(),
    )
