"""
OpenRouter client — OpenAI-compatible cloud fallback.
Free-tier models, auto-selected by task type.
Fallback chain: local Ollama first → OpenRouter when local fails or task too complex.
"""
import asyncio
import logging
from typing import Optional

import httpx

import config

logger = logging.getLogger("nexus.openrouter")


class OpenRouterClient:
    BASE_URL = config.OPENROUTER_BASE_URL

    def __init__(self):
        self._key = config.OPENROUTER_API_KEY

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._key}",
            "HTTP-Referer": "https://nexus.local",
            "X-Title": "CIPHER AI Desktop",
            "Content-Type": "application/json",
        }

    def is_configured(self) -> bool:
        return bool(self._key)

    async def chat(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: str = "You are NEXUS, an advanced AI desktop assistant.",
        messages: Optional[list[dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        if not self.is_configured():
            return "OpenRouter API key not set. Add OPENROUTER_API_KEY to your .env file."

        chosen = model or config.OPENROUTER_COMPLEX
        payload_messages = [{"role": "system", "content": system}]
        if messages:
            payload_messages.extend(messages)
        payload_messages.append({"role": "user", "content": prompt})

        payload = {
            "model": chosen,
            "messages": payload_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=90) as client:
                resp = await client.post(
                    f"{self.BASE_URL}/chat/completions",
                    headers=self._headers(),
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenRouter HTTP error {e.response.status_code}: {e.response.text}")
            return f"OpenRouter error: {e.response.status_code}"
        except Exception as e:
            logger.error(f"OpenRouter error: {e}")
            return f"OpenRouter unavailable: {e}"

    async def select_model_for_task(self, task_type: str) -> str:
        """Return best free model for a given task type."""
        mapping = {
            "long_context":  config.OPENROUTER_LONG_CONTEXT,
            "translation":   config.OPENROUTER_LONG_CONTEXT,
            "heavy_reason":  config.OPENROUTER_HEAVY_REASON,
            "reasoning":     config.OPENROUTER_HEAVY_REASON,
            "complex":       config.OPENROUTER_COMPLEX,
            "code":          config.OPENROUTER_COMPLEX,
            "multi_agent":   config.OPENROUTER_MULTI_AGENT,
        }
        return mapping.get(task_type, config.OPENROUTER_COMPLEX)

    async def list_free_models(self) -> list[dict]:
        """Fetch available models from OpenRouter."""
        if not self.is_configured():
            return []
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/models",
                    headers=self._headers(),
                )
                data = resp.json()
                return [m for m in data.get("data", []) if m.get("pricing", {}).get("prompt") == "0"]
        except Exception as e:
            logger.warning(f"Could not fetch OpenRouter model list: {e}")
            return []


# Singleton
openrouter = OpenRouterClient()
