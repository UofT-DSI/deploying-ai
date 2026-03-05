from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from app.core.openai_client import get_client
from app.core.guardrails import check_guardrails
from app.core.memory import MemoryStore
from app.services.semantic import SemanticStore
from app.llm_router import ChatRouter
import re

app = FastAPI(title="StudyMate")

oai = get_client()
semantic = SemanticStore("chroma_store", "course_kb", oai)
router = ChatRouter(oai=oai, semantic=semantic)
memory = MemoryStore(max_turns=12)
MEMORY_RE = re.compile(r"^\s*(remember|note|save|store)\b[:\-]?\s*(.*)$", re.IGNORECASE)

class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    user_message = (req.message or "").strip()

    ok, msg = check_guardrails(user_message)
    if not ok:
        return ChatResponse(reply=msg)

    # add user msg
    memory.append(req.session_id, "user", user_message)

    # ✅ MEMORY SHORT-CIRCUIT (no router / no vector store / no LLM)
    m = MEMORY_RE.match(user_message)
    if m:
        extracted_text = (m.group(2) or "").strip()
        if not extracted_text:
            reply = "Sure — what would you like me to remember?"
        else:
            memory.remember(req.session_id, extracted_text)
            reply = f"Noted. I’ll remember: {extracted_text}"

        memory.append(req.session_id, "assistant", reply)
        return ChatResponse(reply=reply)

    # build context for router
    context_messages = memory.get_context_messages(req.session_id)

    # get reply
    reply = router.chat(context_messages)

    # store assistant msg
    memory.append(req.session_id, "assistant", reply)

    return ChatResponse(reply=reply)