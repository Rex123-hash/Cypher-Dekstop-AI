"""
Security Agent — malware scanning, threat detection, process monitoring via Windows Defender.
"""
import asyncio
import subprocess
import psutil
import re
from pathlib import Path
from datetime import datetime


def run_ps(command: str) -> str:
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True, text=True, timeout=60,
    )
    return (result.stdout + result.stderr).strip()


SUSPICIOUS_PORTS = {4444, 1337, 31337, 6666, 6667, 6668, 1080, 9050}
SUSPICIOUS_NAMES = {
    "mimikatz", "meterpreter", "nc.exe", "ncat", "netcat",
    "psexec", "lazagne", "pwdump",
}


class SecurityAgent:
    name = "security"

    async def quick_scan(self, path: str = "C:\\Users") -> str:
        """Run Windows Defender quick scan on a path."""
        result = run_ps(
            f'Start-MpScan -ScanType QuickScan -ScanPath "{path}"; '
            f'Get-MpThreatDetection | Select-Object -First 10 | '
            f'Format-List ThreatName, ActionSuccess, InitialDetectionTime, Resources'
        )
        return result if result else "No threats detected by Windows Defender."

    async def full_scan(self) -> str:
        """Start a full Windows Defender scan (runs in background)."""
        run_ps("Start-MpScan -ScanType FullScan")
        return "Full scan started in background. Check Windows Security for results."

    async def get_threats(self) -> str:
        """Get current detected threats."""
        result = run_ps(
            "Get-MpThreat | Select-Object ThreatName, SeverityID, CategoryID, "
            "IsActive | Format-Table -AutoSize"
        )
        return result if result else "No active threats detected."

    async def get_threat_history(self) -> str:
        result = run_ps(
            "Get-MpThreatDetection | Select-Object ThreatName, ActionSuccess, "
            "InitialDetectionTime | Format-Table -AutoSize"
        )
        return result if result else "No threat history found."

    async def update_defender(self) -> str:
        result = run_ps("Update-MpSignature")
        return "Windows Defender signatures updated." if not result else result

    async def check_firewall(self) -> str:
        result = run_ps(
            "Get-NetFirewallProfile | Select-Object Name, Enabled | Format-Table"
        )
        return result

    async def get_open_ports(self) -> str:
        result = run_ps(
            "Get-NetTCPConnection -State Listen | "
            "Select-Object LocalPort, OwningProcess | "
            "Sort-Object LocalPort | Format-Table -AutoSize"
        )
        return result if result else "No open ports found."

    async def check_suspicious_processes(self) -> str:
        """Scan running processes for known suspicious names and behaviors."""
        alerts = []
        for proc in psutil.process_iter(["name", "pid", "exe", "connections"]):
            try:
                name = proc.info["name"].lower()
                if any(s in name for s in SUSPICIOUS_NAMES):
                    alerts.append(f"SUSPICIOUS PROCESS: {proc.info['name']} (PID {proc.info['pid']})")

                # Check for suspicious network connections
                try:
                    for conn in proc.connections():
                        if conn.raddr and conn.raddr.port in SUSPICIOUS_PORTS:
                            alerts.append(
                                f"SUSPICIOUS CONNECTION: {proc.info['name']} (PID {proc.info['pid']}) "
                                f"→ port {conn.raddr.port}"
                            )
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    pass
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        if alerts:
            return "⚠️ SECURITY ALERTS:\n" + "\n".join(alerts)
        return "No suspicious processes detected."

    async def get_startup_items(self) -> str:
        result = run_ps(
            "Get-CimInstance Win32_StartupCommand | "
            "Select-Object Name, Command, Location | Format-Table -AutoSize"
        )
        return result if result else "No startup items found."

    async def get_recent_events(self) -> str:
        """Get recent Windows Security event log entries."""
        result = run_ps(
            "Get-EventLog -LogName Security -Newest 20 -EntryType FailureAudit,SuccessAudit "
            "2>$null | Select-Object TimeGenerated, EntryType, Message | Format-List"
        )
        return result[:3000] if result else "No recent security events found."

    async def kill_suspicious(self) -> str:
        """Kill processes matching known suspicious names."""
        killed = []
        for proc in psutil.process_iter(["name", "pid"]):
            try:
                if any(s in proc.info["name"].lower() for s in SUSPICIOUS_NAMES):
                    proc.kill()
                    killed.append(f"{proc.info['name']} (PID {proc.info['pid']})")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return f"Killed suspicious processes: {', '.join(killed)}" if killed else "No suspicious processes to kill."

    async def full_security_report(self) -> str:
        tasks = [
            self.get_threats(),
            self.check_suspicious_processes(),
            self.check_firewall(),
        ]
        results = await asyncio.gather(*tasks)
        return (
            f"=== NEXUS SECURITY REPORT [{datetime.now().strftime('%Y-%m-%d %H:%M')}] ===\n\n"
            f"THREATS:\n{results[0]}\n\n"
            f"SUSPICIOUS PROCESSES:\n{results[1]}\n\n"
            f"FIREWALL:\n{results[2]}"
        )

    async def handle(self, command: str) -> str:
        cmd = command.lower()
        if "quick scan" in cmd or "scan" in cmd and "quick" in cmd:
            return await self.quick_scan()
        if "full scan" in cmd:
            return await self.full_scan()
        if "threats" in cmd or "threat history" in cmd:
            return await self.get_threats()
        if "firewall" in cmd:
            return await self.check_firewall()
        if "ports" in cmd or "open ports" in cmd:
            return await self.get_open_ports()
        if "suspicious" in cmd:
            return await self.check_suspicious_processes()
        if "startup" in cmd:
            return await self.get_startup_items()
        if "security report" in cmd or "security status" in cmd:
            return await self.full_security_report()
        if "update defender" in cmd or "update antivirus" in cmd:
            return await self.update_defender()
        return await self.full_security_report()


security_agent = SecurityAgent()
