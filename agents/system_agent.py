"""
System Agent — full Windows PC control via psutil, subprocess, and PowerShell.
"""
import asyncio
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import psutil

try:
    import screen_brightness_control as sbc
    _SBC = True
except ImportError:
    _SBC = False

try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
    from ctypes import cast, POINTER
    _PYCAW = True
except ImportError:
    _PYCAW = False

try:
    import pyautogui
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

try:
    import pyperclip
    _PYPERCLIP = True
except ImportError:
    _PYPERCLIP = False


def run_ps(command: str, capture: bool = True) -> str:
    """Run a PowerShell command and return output."""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=capture,
        text=True,
        timeout=30,
    )
    return (result.stdout + result.stderr).strip()


def run_cmd(command: str) -> str:
    """Run a CMD command and return output."""
    result = subprocess.run(
        command, shell=True, capture_output=True, text=True, timeout=30
    )
    return (result.stdout + result.stderr).strip()


class SystemAgent:
    name = "system"

    # ── Apps ──────────────────────────────────────────────────────────────────

    async def open_app(self, app_name: str) -> str:
        import shutil
        name = re.sub(r"[^\w\s]", "", app_name).lower().strip()

        # Built-in Windows executables
        builtins = {
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "calc": "calc.exe",
            "paint": "mspaint.exe",
            "task manager": "taskmgr.exe",
            "file explorer": "explorer.exe",
            "explorer": "explorer.exe",
            "edge": "msedge.exe",
            "microsoft edge": "msedge.exe",
            "terminal": "wt.exe",
            "windows terminal": "wt.exe",
            "word": "winword.exe",
            "excel": "excel.exe",
            "powerpoint": "powerpnt.exe",
            "vscode": "code.exe",
            "vs code": "code.exe",
            "cmd": "cmd.exe",
            "powershell": "powershell.exe",
        }

        # Known install paths for common apps
        known_paths = {
            "chrome": [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            ],
            "google chrome": [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            ],
            "firefox": [
                r"C:\Program Files\Mozilla Firefox\firefox.exe",
                r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
            ],
            "discord": [
                os.path.expandvars(r"%LOCALAPPDATA%\Discord\Update.exe --processStart Discord.exe"),
                os.path.expandvars(r"%LOCALAPPDATA%\Discord\app-*\Discord.exe"),
            ],
            "spotify": [
                os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe"),
                os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\Spotify.exe"),
            ],
            "steam": [
                r"C:\Program Files (x86)\Steam\Steam.exe",
                r"C:\Program Files\Steam\Steam.exe",
            ],
            "vlc": [
                r"C:\Program Files\VideoLAN\VLC\vlc.exe",
                r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
            ],
            "obs": [
                r"C:\Program Files\obs-studio\bin\64bit\obs64.exe",
                r"C:\Program Files (x86)\obs-studio\bin\32bit\obs32.exe",
            ],
        }

        # 1. Built-in Windows app
        if name in builtins:
            exe = builtins[name]
            exe_path = shutil.which(exe)
            try:
                subprocess.Popen(exe_path or exe, shell=not exe_path)
                return f"Opened {app_name}."
            except Exception as e:
                return f"Failed to open {app_name}: {e}"

        # 2. shutil.which — finds anything on PATH
        exe_name = name.replace(" ", "") + ".exe"
        found = shutil.which(exe_name) or shutil.which(name)
        if found:
            try:
                subprocess.Popen([found])
                return f"Opened {app_name}."
            except Exception as e:
                return f"Failed to open {app_name}: {e}"

        # 3. Known install paths
        if name in known_paths:
            import glob as _glob
            for path in known_paths[name]:
                matches = _glob.glob(path)
                target = matches[0] if matches else path
                if os.path.exists(target):
                    try:
                        subprocess.Popen([target])
                        return f"Opened {app_name}."
                    except Exception:
                        continue

        # 4. os.startfile — Windows shell open (handles UWP apps, file associations)
        try:
            os.startfile(name)
            return f"Opened {app_name}."
        except Exception:
            pass

        # 5. PowerShell Start-Process last resort
        try:
            run_ps(f"Start-Process '{name}'")
            return f"Opened {app_name}."
        except Exception as e:
            return f"Could not open '{app_name}': {e}"

    async def close_app(self, app_name: str) -> str:
        killed = []
        for proc in psutil.process_iter(["name", "pid"]):
            if app_name.lower() in proc.info["name"].lower():
                proc.kill()
                killed.append(proc.info["name"])
        if killed:
            return f"Closed: {', '.join(set(killed))}"
        return f"No process found matching '{app_name}'."

    async def kill_process(self, identifier: str) -> str:
        """Kill by name or PID."""
        try:
            pid = int(identifier)
            psutil.Process(pid).kill()
            return f"Killed PID {pid}."
        except ValueError:
            return await self.close_app(identifier)

    # ── Monitoring ────────────────────────────────────────────────────────────

    async def get_system_stats(self) -> str:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            gpu_str = f"\nGPU: {gpus[0].name} | Load: {gpus[0].load*100:.1f}% | VRAM: {gpus[0].memoryUsed:.0f}/{gpus[0].memoryTotal:.0f} MB" if gpus else ""
        except Exception:
            gpu_str = ""
        return (
            f"CPU: {cpu}% | RAM: {ram.percent}% ({ram.used//1024**3}GB/{ram.total//1024**3}GB) "
            f"| Disk: {disk.percent}%{gpu_str}"
        )

    async def get_top_processes(self, n: int = 10) -> str:
        procs = []
        for p in psutil.process_iter(["name", "pid", "cpu_percent", "memory_percent"]):
            try:
                procs.append(p.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        procs.sort(key=lambda x: x.get("cpu_percent", 0), reverse=True)
        lines = [f"{'PID':>7} {'CPU%':>6} {'RAM%':>6} {'Name'}" ]
        lines += [
            f"{p['pid']:>7} {p['cpu_percent']:>6.1f} {p['memory_percent']:>6.1f} {p['name']}"
            for p in procs[:n]
        ]
        return "\n".join(lines)

    async def kill_high_cpu(self, threshold: float = 80.0) -> str:
        killed = []
        for p in psutil.process_iter(["name", "pid", "cpu_percent"]):
            try:
                if p.info["cpu_percent"] > threshold and p.info["name"] not in (
                    "System", "Registry", "svchost.exe", "python.exe", "python3.exe"
                ):
                    p.kill()
                    killed.append(f"{p.info['name']} (PID {p.info['pid']})")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        if killed:
            return f"Killed high-CPU processes: {', '.join(killed)}"
        return f"No processes found exceeding {threshold}% CPU."

    # ── Volume & Brightness ───────────────────────────────────────────────────

    async def set_volume(self, level: int) -> str:
        if _PYCAW:
            try:
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = cast(interface, POINTER(IAudioEndpointVolume))
                volume.SetMasterVolumeLevelScalar(max(0.0, min(1.0, level / 100.0)), None)
                return f"Volume set to {level}%."
            except Exception:
                pass
        run_ps(f"$obj = New-Object -ComObject WScript.Shell; $obj.SendKeys([char]174)")
        return f"Volume adjusted to ~{level}% (PowerShell fallback)."

    async def mute_volume(self) -> str:
        run_ps("(New-Object -ComObject WScript.Shell).SendKeys([char]173)")
        return "Audio muted/unmuted."

    async def set_brightness(self, level: int) -> str:
        if _SBC:
            try:
                sbc.set_brightness(level)
                return f"Brightness set to {level}%."
            except Exception as e:
                return f"Brightness control failed: {e}"
        return "Brightness control not available. Install screen-brightness-control."

    # ── Screenshot ────────────────────────────────────────────────────────────

    async def screenshot(self, save_path: Optional[str] = None) -> str:
        if not save_path:
            save_path = str(Path.home() / "Desktop" / f"nexus_screenshot_{int(time.time())}.png")
        if _PYAUTOGUI:
            img = pyautogui.screenshot()
            img.save(save_path)
        else:
            run_ps(f"Add-Type -AssemblyName System.Windows.Forms; $s=[System.Windows.Forms.Screen]::PrimaryScreen; $bmp=New-Object System.Drawing.Bitmap($s.Bounds.Width,$s.Bounds.Height); $g=[System.Drawing.Graphics]::FromImage($bmp); $g.CopyFromScreen(0,0,0,0,$s.Bounds.Size); $bmp.Save('{save_path}')")
        return f"Screenshot saved to: {save_path}"

    # ── Text Input ────────────────────────────────────────────────────────────

    async def type_text(self, text: str) -> str:
        if _PYPERCLIP and _PYAUTOGUI:
            pyperclip.copy(text)
            pyautogui.hotkey("ctrl", "v")
        else:
            run_ps(f"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('{text}')")
        return f"Typed: {text[:50]}{'...' if len(text) > 50 else ''}"

    # ── Power ─────────────────────────────────────────────────────────────────

    async def lock_pc(self) -> str:
        run_cmd("rundll32.exe user32.dll,LockWorkStation")
        return "PC locked."

    async def sleep_pc(self) -> str:
        run_ps("Add-Type -Assembly System.Windows.Forms; [System.Windows.Forms.Application]::SetSuspendState('Suspend', $false, $false)")
        return "PC going to sleep."

    async def restart_pc(self) -> str:
        run_cmd("shutdown /r /t 10")
        return "PC will restart in 10 seconds."

    async def shutdown_pc(self) -> str:
        run_cmd("shutdown /s /t 10")
        return "PC will shut down in 10 seconds."

    async def cancel_shutdown(self) -> str:
        run_cmd("shutdown /a")
        return "Shutdown/restart cancelled."

    # ── PowerShell / CMD ──────────────────────────────────────────────────────

    async def run_powershell(self, command: str) -> str:
        return run_ps(command)

    async def run_cmd_command(self, command: str) -> str:
        return run_cmd(command)

    # ── Handle natural language commands ─────────────────────────────────────

    async def handle(self, command: str) -> str:
        cmd = command.lower().strip()

        if "open" in cmd:
            app = re.sub(r"open\s+", "", cmd).strip()
            return await self.open_app(app)
        if "close" in cmd or "kill" in cmd:
            app = re.sub(r"(close|kill)\s+", "", cmd).strip()
            return await self.close_app(app)
        if "screenshot" in cmd:
            return await self.screenshot()
        if "volume" in cmd:
            nums = re.findall(r"\d+", cmd)
            if nums:
                return await self.set_volume(int(nums[0]))
            if "mute" in cmd:
                return await self.mute_volume()
        if "brightness" in cmd:
            nums = re.findall(r"\d+", cmd)
            if nums:
                return await self.set_brightness(int(nums[0]))
        if "lock" in cmd:
            return await self.lock_pc()
        if "sleep" in cmd:
            return await self.sleep_pc()
        if "restart" in cmd:
            return await self.restart_pc()
        if "shutdown" in cmd or "shut down" in cmd:
            return await self.shutdown_pc()
        if "system stats" in cmd or "system status" in cmd:
            return await self.get_system_stats()
        if "processes" in cmd or "top processes" in cmd:
            return await self.get_top_processes()
        if "kill high cpu" in cmd:
            return await self.kill_high_cpu()
        if cmd.startswith("run powershell") or cmd.startswith("powershell"):
            ps_cmd = re.sub(r"^(run\s+)?powershell\s*", "", cmd).strip()
            return await self.run_powershell(ps_cmd)
        if cmd.startswith("type "):
            text = cmd[5:]
            return await self.type_text(text)

        return f"System agent received: '{command}' — not mapped to a direct action."


system_agent = SystemAgent()
