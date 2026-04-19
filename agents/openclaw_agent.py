"""
OpenClaw Agent — integrates OpenClaw v2026.4.14 (installed at system level).
Runs as background subprocess; streams stdout live into NEXUS activity log.

Trigger modes:
  "code mode <task>"          → openclaw --task <task>
  "openclaw whatsapp <msg>"   → openclaw --task "open whatsapp web and send message: <msg>"
  "openclaw file <task>"      → openclaw --task <task> --context file
"""
import asyncio
import logging
import re
import subprocess
from typing import AsyncGenerator, Callable, Optional

import config

logger = logging.getLogger("nexus.openclaw")


class OpenClawAgent:
    name = "openclaw"

    def __init__(self):
        self._current_proc: Optional[asyncio.subprocess.Process] = None
        self._output_callback: Optional[Callable[[str], None]] = None

    def set_output_callback(self, cb: Callable[[str], None]):
        """Register a callback to stream OpenClaw output into the UI."""
        self._output_callback = cb

    def _emit(self, line: str):
        logger.debug(f"[OpenClaw] {line}")
        if self._output_callback:
            self._output_callback(f"[OpenClaw] {line}")

    async def _verify_installed(self) -> bool:
        try:
            proc = await asyncio.create_subprocess_exec(
                config.OPENCLAW_PATH, "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=8)
            version_str = stdout.decode().strip()
            self._emit(f"Version: {version_str}")
            return True
        except FileNotFoundError:
            return False
        except Exception as e:
            logger.warning(f"OpenClaw version check failed: {e}")
            return False

    async def run_task(
        self,
        task: str,
        context: Optional[str] = None,
        extra_args: Optional[list[str]] = None,
    ) -> str:
        """
        Launch openclaw as a background subprocess and stream its output.
        Returns the full accumulated output when done.
        """
        cmd = [config.OPENCLAW_PATH, "--task", task]
        if context:
            cmd += ["--context", context]
        if extra_args:
            cmd += extra_args

        self._emit(f"Starting: {' '.join(cmd)}")
        output_lines: list[str] = []

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            self._current_proc = proc

            assert proc.stdout is not None
            async for raw_line in proc.stdout:
                line = raw_line.decode(errors="replace").rstrip()
                output_lines.append(line)
                self._emit(line)

            await proc.wait()
            self._current_proc = None
            result = "\n".join(output_lines)
            return result if result else "OpenClaw task completed."

        except FileNotFoundError:
            msg = (
                "OpenClaw not found on PATH. "
                "Ensure OpenClaw v2026.4.14 is installed and available as 'openclaw'."
            )
            self._emit(msg)
            return msg
        except Exception as e:
            msg = f"OpenClaw error: {e}"
            self._emit(msg)
            return msg

    async def stop(self):
        if self._current_proc:
            self._current_proc.terminate()
            try:
                await asyncio.wait_for(self._current_proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                self._current_proc.kill()
            self._current_proc = None
            self._emit("Process terminated by user.")

    # ── WhatsApp via OpenClaw → Playwright ───────────────────────────────────

    async def whatsapp_send(self, contact: str, message: str) -> str:
        task = f"Open WhatsApp Web and send this message to {contact}: {message}"
        return await self.run_task(task, context="whatsapp")

    # ── Code mode ─────────────────────────────────────────────────────────────

    async def code_task(self, task: str) -> str:
        return await self.run_task(task, context="code")

    # ── File mode ─────────────────────────────────────────────────────────────

    async def file_task(self, task: str) -> str:
        return await self.run_task(task, context="file")

    # ── Handle natural language ───────────────────────────────────────────────

    async def handle(self, command: str) -> str:
        cmd = command.lower().strip()

        # "code mode <task>" pattern
        code_match = re.search(r"code\s+mode\s+(.+)", command, re.IGNORECASE)
        if code_match:
            return await self.code_task(code_match.group(1))

        # "openclaw whatsapp <contact> <message>"
        wa_match = re.search(
            r"(?:openclaw\s+)?whatsapp\s+(\w+)\s+(.+)", command, re.IGNORECASE
        )
        if wa_match:
            return await self.whatsapp_send(wa_match.group(1), wa_match.group(2))

        # "openclaw file <task>"
        file_match = re.search(r"(?:openclaw\s+)?file\s+(.+)", command, re.IGNORECASE)
        if file_match:
            return await self.file_task(file_match.group(1))

        # Generic openclaw invocation
        task = re.sub(r"^openclaw\s*", "", command, flags=re.IGNORECASE).strip()
        return await self.run_task(task)


openclaw_agent = OpenClawAgent()
