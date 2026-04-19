"""
Orchestrator — intelligently routes every command to the right agent.
Keyword heuristics first, then LLM classification for ambiguous input.
"""
import re
from typing import Callable

from core.brain import brain
from core.memory import memory


# Keyword routing table — ordered by specificity (most specific first)
ROUTE_MAP = [
    # WhatsApp
    (r"\b(whatsapp|send.*to|message\s+\w+.*)\b", "whatsapp"),
    # Security
    (r"\b(scan|malware|virus|threat|defender|firewall|suspicious|security report|security status)\b", "security"),
    # System power/control
    (r"\b(lock|sleep|restart|shutdown|shut down|volume|brightness|mute|screenshot|type text|open app|close app|kill process|system stats|top processes)\b", "system"),
    # File operations
    (r"\b(file|folder|directory|search files|find files|read file|delete file|move|copy|rename|disk space|disk usage)\b", "file"),
    # Code
    (r"\b(code|script|program|function|class|debug|refactor|write.*code|generate.*code|python|javascript|powershell script)\b", "code"),
    # Web / internet
    (r"\b(search online|google|latest news|what is.*happening|current|today|weather|news about|look up)\b", "web"),
    # System (open/close apps)
    (r"\b(open|close|launch|start|kill)\s+\w+", "system"),
]


class Orchestrator:
    def __init__(self):
        self._agents: dict[str, object] = {}

    def register(self, agent):
        self._agents[agent.name] = agent

    def _keyword_route(self, command: str) -> str | None:
        cmd = command.lower()
        for pattern, agent_name in ROUTE_MAP:
            if re.search(pattern, cmd):
                return agent_name
        return None

    async def _llm_route(self, command: str) -> str:
        """Fall back to LLM classification when keywords don't match."""
        prompt = (
            f"Classify this user command into EXACTLY ONE category. "
            f"Categories: chat, file, system, security, web, code, whatsapp\n"
            f"Command: {command}\n"
            f"Reply with ONLY the category name, nothing else."
        )
        result = await brain.chat(prompt, context=[])
        result = result.strip().lower()
        valid = {"chat", "file", "system", "security", "web", "code", "whatsapp"}
        return result if result in valid else "chat"

    async def cancel(self):
        """Cancel any running agent task."""
        pass  # extend per-agent cancellation here if needed

    async def handle(self, command: str) -> str:
        _, response = await self.route(command)
        return response

    async def route(self, command: str) -> tuple[str, str]:
        """Returns (agent_name, response)."""
        agent_name = self._keyword_route(command) or await self._llm_route(command)
        agent = self._agents.get(agent_name)

        if not agent:
            return "chat", f"Agent '{agent_name}' not loaded."

        try:
            response = await agent.handle(command)
        except Exception as e:
            response = f"Error in {agent_name} agent: {e}"

        memory.add("user", command, agent=agent_name)
        memory.add("assistant", response, agent=agent_name)
        return agent_name, response


# Singleton
orchestrator = Orchestrator()
