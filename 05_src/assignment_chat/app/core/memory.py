from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class SessionState:
    messages: List[dict] = field(default_factory=list)  # [{"role": "...","content":"..."}]
    rolling_summary: str = ""

class MemoryStore:
    def __init__(self, max_turns: int = 12):
        self.max_turns = max_turns
        self.sessions: Dict[str, SessionState] = {}

    def get(self, session_id: str) -> SessionState:
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionState()
        return self.sessions[session_id]

    def append(self, session_id: str, role: str, content: str) -> None:
        st = self.get(session_id)
        st.messages.append({"role": role, "content": content})

        # keep last N turns (2 msgs per turn approx)
        if len(st.messages) > self.max_turns * 2:
            st.messages = st.messages[-self.max_turns * 2 :]

    def get_context_messages(self, session_id: str) -> list[dict]:
        st = self.get(session_id)
        msgs = []
        if st.rolling_summary:
            msgs.append({"role": "system", "content": f"Conversation summary so far: {st.rolling_summary}"})
        msgs.extend(st.messages)
        return msgs
    
    def remember(self, session_id: str, fact: str) -> None:
        st = self.get(session_id)
        fact = fact.strip()
        if not fact:
            return
        if st.rolling_summary:
            st.rolling_summary = st.rolling_summary.rstrip() + f" | User note: {fact}"
        else:
            st.rolling_summary = f"User note: {fact}"