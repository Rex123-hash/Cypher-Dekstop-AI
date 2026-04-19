"""
AI Brain — unified async interface for all models.

Routing logic:
  fast/chat/web  → OpenRouter gemma-4-31b (primary) → gpt-oss-120b → nemotron (fallback chain)
  code/system    → qwen2.5-coder:7b LOCAL ONLY (deterministic, no internet needed)
  file scanning  → deepseek-r1:8b LOCAL ONLY (privacy, no data leaves machine)
"""
import asyncio
import json
import httpx
from typing import Optional

import config
from core.memory import memory
from core.openrouter import openrouter

_CIPHER_SYSTEM = (
    "You are CIPHER, an advanced AI desktop assistant for Windows 11. "
    "Be concise, precise, and direct. You have full PC control capabilities. "
    "Never say you can't access the internet — answer from your knowledge. "
    "Measured, confident, slightly cold tone. No filler phrases."
)

_OPENROUTER_CHAIN = [
    config.OPENROUTER_HEAVY_REASON,   # google/gemma-4-31b — primary
    config.OPENROUTER_COMPLEX,        # openai/gpt-oss-120b — secondary
    config.OPENROUTER_MULTI_AGENT,    # nvidia/nemotron-3-super — fallback
]


def _failed(result: str) -> bool:
    return result.startswith(("OpenRouter error", "OpenRouter unavailable", "All models"))


class OllamaClient:
    def __init__(self, base_url: str = config.OLLAMA_BASE_URL):
        self.base_url = base_url

    async def chat(self, model: str, messages: list[dict], system: str = "") -> str:
        payload: dict = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"num_ctx": 4096, "temperature": 0.7},
        }
        if system:
            payload["system"] = system
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            return resp.json()["message"]["content"]

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=4) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                return r.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=6) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                return [m["name"] for m in r.json().get("models", [])]
        except Exception:
            return []


class Brain:
    """Routes every request to the most appropriate model."""

    def __init__(self):
        self.ollama = OllamaClient()

    # ── OpenRouter primary (conversation + reasoning) ─────────────────────────

    async def fast(self, prompt: str) -> str:
        """OpenRouter chain — instant single-turn reply."""
        for model in _OPENROUTER_CHAIN:
            result = await openrouter.chat(prompt, model=model, system=_CIPHER_SYSTEM)
            if not _failed(result):
                return result
        try:
            return await self.ollama.chat(
                config.FAST_MODEL, [{"role": "user", "content": prompt}], system=_CIPHER_SYSTEM
            )
        except Exception as e:
            return f"All models unavailable: {e}"

    async def chat(self, prompt: str, context: Optional[list] = None) -> str:
        """OpenRouter chain — multi-turn conversation with memory."""
        msgs = list(context if context is not None else memory.get_context(8))
        for model in _OPENROUTER_CHAIN:
            result = await openrouter.chat(prompt, model=model, system=_CIPHER_SYSTEM, messages=msgs)
            if not _failed(result):
                return result
        try:
            msgs.append({"role": "user", "content": prompt})
            return await self.ollama.chat(config.CHAT_MODEL, msgs, system=_CIPHER_SYSTEM)
        except Exception as e:
            return f"All models unavailable: {e}"

    async def web_search(self, prompt: str) -> str:
        """OpenRouter chain — knowledge and web queries."""
        for model in _OPENROUTER_CHAIN:
            result = await openrouter.chat(prompt, model=model, system=_CIPHER_SYSTEM)
            if not _failed(result):
                return result
        return "Could not reach any AI model. Check your OpenRouter API key."

    # ── Local Ollama (code + file privacy) ───────────────────────────────────

    async def code(self, prompt: str) -> str:
        """qwen2.5-coder:7b LOCAL — system commands and code execution."""
        system = (
            "You are NEXUS code engine. Write clean, working code. "
            "Return ONLY runnable code unless asked to explain."
        )
        try:
            return await self.ollama.chat(
                config.CODER_MODEL, [{"role": "user", "content": prompt}], system=system
            )
        except Exception:
            return await openrouter.chat(prompt, model=config.OPENROUTER_COMPLEX, system=system)

    async def reason(self, prompt: str, context: Optional[list] = None) -> str:
        """deepseek-r1:8b LOCAL ONLY — file scanning, privacy-sensitive analysis."""
        system = (
            "You are NEXUS reasoning engine. Think step-by-step. "
            "Provide structured, accurate, thorough analysis."
        )
        msgs = list(context or [])
        msgs.append({"role": "user", "content": prompt})
        try:
            return await self.ollama.chat(config.REASONING_MODEL, msgs, system=system)
        except Exception as e:
            return f"Local reasoning model unavailable: {e}"

    # ── OpenRouter explicit cloud models ──────────────────────────────────────

    async def heavy_reason(self, prompt: str) -> str:
        return await openrouter.chat(prompt, model=config.OPENROUTER_HEAVY_REASON, system=_CIPHER_SYSTEM)

    async def complex_task(self, prompt: str) -> str:
        return await openrouter.chat(prompt, model=config.OPENROUTER_COMPLEX, system=_CIPHER_SYSTEM)

    async def multi_agent(self, prompt: str) -> str:
        return await openrouter.chat(prompt, model=config.OPENROUTER_MULTI_AGENT, system=_CIPHER_SYSTEM)

    # ── Smart auto-router ─────────────────────────────────────────────────────

    async def smart(self, prompt: str) -> str:
        """
        Auto-route:
          Code/system    → qwen2.5-coder local
          File analysis  → deepseek-r1 local (privacy)
          Everything else→ OpenRouter gemma-4-31b chain
        """
        lower = prompt.lower()

        if any(kw in lower for kw in ["write code", "python script", "def ", "class ", "import ", "#!/"]):
            return await self.code(prompt)

        if any(kw in lower for kw in ["scan file", "read file", "analyze file", "file content"]):
            return await self.reason(prompt)

        return await self.chat(prompt)

    async def is_ollama_running(self) -> bool:
        return await self.ollama.is_available()

    async def available_models(self) -> list[str]:
        return await self.ollama.list_models()


# Singleton
brain = Brain()
