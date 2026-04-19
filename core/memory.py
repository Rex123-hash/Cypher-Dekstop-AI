import json
import time
from pathlib import Path
from collections import deque
from typing import Optional

HISTORY_FILE = Path(__file__).parent.parent / "data" / "conversation_history.json"
HISTORY_FILE.parent.mkdir(exist_ok=True)

class ConversationMemory:
    """Manages conversation history with rolling window and persistence."""

    def __init__(self, max_turns: int = 20):
        self.max_turns = max_turns
        self.history: deque = deque(maxlen=max_turns)
        self.session_start = time.time()
        self._load()

    def add(self, role: str, content: str, agent: Optional[str] = None):
        entry = {
            "role": role,
            "content": content,
            "timestamp": time.time(),
            "agent": agent,
        }
        self.history.append(entry)
        self._save()

    def get_context(self, n: int = 10) -> list[dict]:
        """Return last n turns formatted for LLM context."""
        recent = list(self.history)[-n:]
        return [{"role": e["role"], "content": e["content"]} for e in recent]

    def clear(self):
        self.history.clear()
        self._save()

    def _save(self):
        try:
            with open(HISTORY_FILE, "w") as f:
                json.dump(list(self.history), f, indent=2)
        except Exception:
            pass

    def _load(self):
        try:
            if HISTORY_FILE.exists():
                with open(HISTORY_FILE) as f:
                    data = json.load(f)
                    # Only restore from current day
                    cutoff = time.time() - 86400
                    self.history = deque(
                        [e for e in data if e.get("timestamp", 0) > cutoff],
                        maxlen=self.max_turns,
                    )
        except Exception:
            self.history = deque(maxlen=self.max_turns)


# Singleton
memory = ConversationMemory()
