"""
Code Agent — uses qwen2.5-coder:7b for code generation, and optionally Codex CLI.
"""
import asyncio
import subprocess
from pathlib import Path
from core.brain import brain


class CodeAgent:
    name = "code"

    async def generate(self, task: str, language: str = "python") -> str:
        prompt = (
            f"Write {language} code for: {task}\n"
            f"Requirements:\n"
            f"- Clean, working, production-quality code\n"
            f"- Include necessary imports\n"
            f"- Add brief inline comments for non-obvious parts\n"
            f"- Handle errors appropriately\n"
            f"Return ONLY the code."
        )
        return await brain.code(prompt)

    async def explain_code(self, code: str) -> str:
        return await brain.reason(
            f"Explain this code clearly, covering what it does, how it works, "
            f"and any important considerations:\n\n{code}"
        )

    async def debug_code(self, code: str, error: str = "") -> str:
        prompt = f"Debug this code"
        if error:
            prompt += f". Error: {error}"
        prompt += f":\n\n{code}\n\nProvide the fixed version with explanation."
        return await brain.code(prompt)

    async def refactor_code(self, code: str) -> str:
        return await brain.code(
            f"Refactor this code for better readability, performance, and best practices:\n\n{code}"
        )

    async def run_codex(self, prompt: str, working_dir: str = ".") -> str:
        """Invoke Codex CLI if available."""
        try:
            result = subprocess.run(
                ["codex", prompt],
                capture_output=True,
                text=True,
                cwd=working_dir,
                timeout=120,
            )
            return result.stdout + result.stderr
        except FileNotFoundError:
            return "Codex CLI not found. Falling back to local code model."
        except Exception as e:
            return f"Codex CLI error: {e}"

    async def write_and_run(self, code: str, filename: str = "nexus_temp.py") -> str:
        """Write code to a temp file and run it."""
        tmp = Path("E:/NEXUS/tmp") / filename
        tmp.parent.mkdir(exist_ok=True)
        tmp.write_text(code, encoding="utf-8")
        try:
            result = subprocess.run(
                ["python", str(tmp)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            output = result.stdout + result.stderr
            return f"Output:\n{output}" if output else "Code ran with no output."
        except subprocess.TimeoutExpired:
            return "Code execution timed out after 30 seconds."
        except Exception as e:
            return f"Execution error: {e}"

    async def handle(self, command: str) -> str:
        cmd = command.lower().strip()

        if "write" in cmd or "create" in cmd or "generate" in cmd or "code" in cmd:
            task = command
            for prefix in ["write code for", "create code for", "generate code for",
                           "write a", "create a", "generate a", "write", "create", "generate"]:
                task = task.replace(prefix, "").strip()
            return await self.generate(task)

        if "explain" in cmd:
            code = command.replace("explain", "").strip()
            return await self.explain_code(code)

        if "debug" in cmd:
            code = command.replace("debug", "").strip()
            return await self.debug_code(code)

        if "refactor" in cmd:
            code = command.replace("refactor", "").strip()
            return await self.refactor_code(code)

        return await self.generate(command)


code_agent = CodeAgent()
