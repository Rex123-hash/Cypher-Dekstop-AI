"""
Web Agent — OpenRouter cloud models for knowledge queries + wttr.in for weather (no API key needed).
"""
import httpx
from core.brain import brain


class WebAgent:
    name = "web"

    async def search(self, query: str) -> str:
        prompt = (
            f"Provide a comprehensive, accurate answer to: {query}\n"
            f"Include relevant facts and be concise but complete."
        )
        return await brain.web_search(prompt)

    async def explain(self, topic: str) -> str:
        return await brain.web_search(f"Explain in detail: {topic}")

    async def latest_news(self, topic: str) -> str:
        return await brain.web_search(
            f"What are the latest developments about: {topic}? Focus on recent information."
        )

    async def weather(self, location: str = "") -> str:
        loc = location.strip().replace(" ", "+") or "auto"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(
                    f"https://wttr.in/{loc}?format=3",
                    headers={"User-Agent": "curl/7.0"},
                )
                if r.status_code == 200:
                    return r.text.strip()
                return f"Weather service returned {r.status_code}."
        except Exception as e:
            return f"Weather unavailable: {e}"

    async def handle(self, command: str) -> str:
        cmd = command.lower().strip()

        if "weather" in cmd:
            loc = (
                cmd.replace("weather", "")
                   .replace("what's the", "")
                   .replace("what is the", "")
                   .replace("in", "")
                   .strip()
            )
            return await self.weather(loc)

        if "latest" in cmd or "news" in cmd:
            topic = cmd.replace("latest", "").replace("news", "").replace("about", "").strip()
            return await self.latest_news(topic)

        if "explain" in cmd:
            topic = cmd.replace("explain", "").strip()
            return await self.explain(topic)

        return await self.search(command)


web_agent = WebAgent()
