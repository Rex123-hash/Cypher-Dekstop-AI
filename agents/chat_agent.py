"""
Chat Agent — conversational AI using qwen3:8b via Ollama.
"""
from core.brain import brain
from core.memory import memory


class ChatAgent:
    name = "chat"

    async def respond(self, message: str) -> str:
        context = memory.get_context(10)
        response = await brain.chat(message, context)
        memory.add("user", message, agent="chat")
        memory.add("assistant", response, agent="chat")
        return response

    async def handle(self, command: str) -> str:
        return await self.respond(command)


chat_agent = ChatAgent()
