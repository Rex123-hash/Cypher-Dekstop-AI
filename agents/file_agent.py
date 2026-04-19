"""
File Agent — full filesystem access using deepseek-r1:8b for intelligent operations.
"""
import asyncio
import os
import re
import shutil
import time
from pathlib import Path
from typing import Optional

from core.brain import brain


class FileAgent:
    name = "file"

    async def search_files(
        self, query: str, directory: str = "C:\\", extensions: list[str] = None
    ) -> str:
        results = []
        search_dir = Path(directory)
        if not search_dir.exists():
            return f"Directory {directory} not found."

        pattern = query.lower()
        exts = [e.lower() if e.startswith(".") else f".{e.lower()}" for e in (extensions or [])]

        try:
            for root, dirs, files in os.walk(search_dir):
                # Skip system dirs
                dirs[:] = [
                    d for d in dirs
                    if d not in {"Windows", "System32", "$Recycle.Bin", "WinSxS"}
                ]
                for file in files:
                    if pattern in file.lower():
                        if not exts or Path(file).suffix.lower() in exts:
                            results.append(str(Path(root) / file))
                            if len(results) >= 50:
                                break
                if len(results) >= 50:
                    break
        except PermissionError:
            pass

        if results:
            return f"Found {len(results)} file(s):\n" + "\n".join(results[:50])
        return f"No files found matching '{query}'."

    async def read_file(self, path: str) -> str:
        try:
            p = Path(path)
            if not p.exists():
                return f"File not found: {path}"
            if p.stat().st_size > 1_000_000:
                return f"File too large to read ({p.stat().st_size // 1024}KB). Use a text editor."
            return p.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return f"Error reading file: {e}"

    async def write_file(self, path: str, content: str) -> str:
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return f"File written: {path}"
        except Exception as e:
            return f"Error writing file: {e}"

    async def delete_file(self, path: str) -> str:
        try:
            p = Path(path)
            if p.is_dir():
                shutil.rmtree(p)
                return f"Directory deleted: {path}"
            elif p.exists():
                p.unlink()
                return f"File deleted: {path}"
            return f"Not found: {path}"
        except Exception as e:
            return f"Error deleting: {e}"

    async def move_file(self, src: str, dst: str) -> str:
        try:
            shutil.move(src, dst)
            return f"Moved: {src} → {dst}"
        except Exception as e:
            return f"Error moving file: {e}"

    async def copy_file(self, src: str, dst: str) -> str:
        try:
            if Path(src).is_dir():
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
            return f"Copied: {src} → {dst}"
        except Exception as e:
            return f"Error copying file: {e}"

    async def rename_file(self, path: str, new_name: str) -> str:
        try:
            p = Path(path)
            new_path = p.parent / new_name
            p.rename(new_path)
            return f"Renamed to: {new_path}"
        except Exception as e:
            return f"Error renaming: {e}"

    async def list_directory(self, path: str = ".") -> str:
        try:
            p = Path(path)
            if not p.exists():
                return f"Directory not found: {path}"
            items = list(p.iterdir())
            dirs = sorted([i for i in items if i.is_dir()], key=lambda x: x.name)
            files = sorted([i for i in items if i.is_file()], key=lambda x: x.name)
            lines = [f"[DIR]  {d.name}" for d in dirs[:50]]
            lines += [f"[FILE] {f.name} ({f.stat().st_size:,} bytes)" for f in files[:50]]
            return f"Contents of {p.resolve()}:\n" + "\n".join(lines) if lines else "Empty directory."
        except Exception as e:
            return f"Error listing directory: {e}"

    async def get_disk_usage(self, path: str = "C:\\") -> str:
        try:
            import shutil as _shutil
            total, used, free = _shutil.disk_usage(path)
            return (
                f"Disk {path}: Total={total//1024**3}GB | "
                f"Used={used//1024**3}GB | Free={free//1024**3}GB "
                f"({100*used//total}% used)"
            )
        except Exception as e:
            return f"Error getting disk usage: {e}"

    async def ai_analyze_path(self, path: str, question: str) -> str:
        """Use deepseek-r1 to analyze file contents intelligently."""
        content = await self.read_file(path)
        if content.startswith("Error") or content.startswith("File not found"):
            return content
        prompt = f"Analyze this file content and answer: {question}\n\nFile: {path}\nContent:\n{content[:4000]}"
        return await brain.reason(prompt)

    async def handle(self, command: str) -> str:
        cmd = command.lower().strip()

        if "list" in cmd or "show files" in cmd:
            path_match = re.search(r'(?:in|at|of|directory|folder)\s+([A-Za-z]:[\\\/][^\s]+|[^\s]+)', command)
            path = path_match.group(1) if path_match else "."
            return await self.list_directory(path)

        if "search" in cmd or "find" in cmd:
            query = re.sub(r"(search|find)\s+(for\s+)?", "", cmd).strip()
            dir_match = re.search(r'in\s+([A-Za-z]:[\\\/]\S+)', command)
            directory = dir_match.group(1) if dir_match else "C:\\"
            return await self.search_files(query, directory)

        if "open" in cmd:
            path = re.sub(r"open\s+", "", command, flags=re.IGNORECASE).strip()
            try:
                os.startfile(path)
                return f"Opened: {path}"
            except Exception as e:
                return f"Could not open {path}: {e}"

        if "read" in cmd:
            path = re.sub(r"read\s+", "", command).strip()
            return await self.read_file(path)

        if "delete" in cmd or "remove" in cmd:
            path = re.sub(r"(delete|remove)\s+", "", command).strip()
            return await self.delete_file(path)

        if "disk usage" in cmd or "disk space" in cmd:
            return await self.get_disk_usage()

        # Fall through to AI reasoning for complex file tasks
        return await brain.reason(f"File operation requested: {command}. Describe what should be done step by step.")


file_agent = FileAgent()
