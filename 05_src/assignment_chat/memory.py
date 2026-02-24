from dataclasses import dataclass, field
from typing import List, Dict
from .llm import get_client

@dataclass
class MemoryManager:
    """
    Simple short-term memory:
    - stores recent messages
    - keeps a running summary when the chat gets too long
    """
    messages: List[Dict[str, str]] = field(default_factory=list)
    summary: str = ""

    max_chars: int = 12000

    def add(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})

    def _chars(self) -> int:
        return sum(len(m["content"]) for m in self.messages) + len(self.summary)

    def maybe_summarize(self) -> None:
        if self._chars() <= self.max_chars:
            return

        cut = max(2, len(self.messages) // 2)
        old = self.messages[:cut]
        self.messages = self.messages[cut:]

        client = get_client()
        dev = (
            "You are a memory compression system. Summarize the conversation so far into a short, factual record "
            "of user preferences, decisions, and unresolved tasks. No fluff. 8-12 bullet points max."
        )
        user = "Conversation to summarize:\n" + "\n".join(
            [f'{m["role"]}: {m["content"]}' for m in old]
        )

        resp = client.responses.create(
            model="gpt-4o-mini",
            input=[
                {"role": "developer", "content": dev},
                {"role": "user", "content": user},
            ],
        )

        new_summary = resp.output[0].content[0].text.strip()
        if self.summary:
            self.summary = (self.summary.strip() + "\n" + new_summary).strip()
        else:
            self.summary = new_summary