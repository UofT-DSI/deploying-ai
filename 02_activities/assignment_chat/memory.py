# 02_activities/assignment_chat/memory.py
from __future__ import annotations
import os
from typing import List, Tuple

class ShortTermMemory:
    """
    Keeps only the last N (message, reply) pairs. Older ones drop off.
    """
    def __init__(self, max_turns: int = 8):
        self.max_turns = max_turns
        self._pairs: List[Tuple[str, str]] = []
        self._debug = os.getenv("MEMORY_DEBUG", "0") == "1"

    def add(self, user: str, assistant: str):
        self._pairs.append((user or "", assistant or ""))
        # Overflow handling
        dropped = 0
        while len(self._pairs) > self.max_turns:
            self._pairs.pop(0)
            dropped += 1
        if self._debug and dropped:
            print(f"[memory] overflow: dropped {dropped} oldest turn(s); kept last {self.max_turns}.")

    def as_text(self) -> str:
        """
        Returns a compact transcript the model can read.
        """
        lines = []
        for i, (u, a) in enumerate(self._pairs, 1):
            lines.append(f"Turn {i} — User: {u}")
            lines.append(f"Turn {i} — Astra: {a}")
        return "\n".join(lines)

    def stats(self) -> dict:
        return {
            "kept_turns": len(self._pairs),
            "max_turns": self.max_turns,
            "overflow_possible_next": max(0, len(self._pairs) + 1 - self.max_turns),
        }
