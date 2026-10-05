import os
import shutil
import subprocess
from typing import Any, Dict, List, Optional

from backend.config import BASE_DIR
from backend.services.llm_service import llm_service
from backend.tools.terminal_tools import run_command, is_dangerous


class TerminalAgent:
    """
    Dedicated Terminal and Developer Environment Agent for JARVIS.
    Executes commands, inspects processes, detects errors, and diagnoses issues.
    """

    def __init__(self):
        self.name = "TerminalAgent"

    def execute(self, command: str, cwd: Optional[str] = None, allow_dangerous: bool = False) -> Dict[str, Any]:
        """
        Execute developer and system commands with safety checks.
        """
        return run_command(command=command, cwd=cwd, allow_dangerous=allow_dangerous)

    def diagnose_error(self, command: str, error_message: str) -> Dict[str, Any]:
        """
        Analyze command error output and suggest actionable solutions.
        """
        if not error_message:
            return {
                "success": True,
                "message": "No error output to diagnose.",
                "data": None,
                "error": None
            }

        prompt = (
            f"The user attempted to run the command:\n`{command}`\n\n"
            f"It resulted in the following error:\n```\n{error_message}\n```\n\n"
            "Explain in 2-3 concise sentences why this error occurred, and provide the exact command(s) needed to fix it."
        )

        diagnosis = llm_service.generate_chat_response(prompt)

        return {
            "success": True,
            "message": diagnosis,
            "data": {
                "command": command,
                "error": error_message,
                "explanation": diagnosis
            },
            "error": None
        }

    def list_processes(self, filter_name: Optional[str] = None, limit: int = 20) -> Dict[str, Any]:
        """
        List running system processes on Windows.
        """
        try:
            cmd = "tasklist /FO CSV /NH"
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            lines = res.stdout.strip().splitlines()

            processes = []
            for line in lines:
                parts = [p.strip(' "') for p in line.split('","')]
                if len(parts) >= 5:
                    p_name, pid, session, session_num, mem = parts[:5]
                    if filter_name and filter_name.lower() not in p_name.lower():
                        continue
                    processes.append({
                        "name": p_name,
                        "pid": pid,
                        "memory": mem
                    })
                    if len(processes) >= limit:
                        break

            return {
                "success": True,
                "message": f"Retrieved {len(processes)} active processes.",
                "data": processes,
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to list processes: {str(e)}",
                "data": [],
                "error": str(e)
            }

    def inspect_environment(self) -> Dict[str, Any]:
        """
        Inspect developer tooling and runtime environment.
        """
        def get_ver(cmd):
            try:
                r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
                return r.stdout.strip() if r.returncode == 0 else "Not found"
            except Exception:
                return "Not found"

        info = {
            "python": get_ver("python --version"),
            "pip": get_ver("pip --version"),
            "git": get_ver("git --version"),
            "node": get_ver("node --version"),
            "npm": get_ver("npm --version"),
            "virtual_env": os.environ.get("VIRTUAL_ENV", "None"),
            "current_dir": str(BASE_DIR)
        }

        summary = f"Python: {info['python']} | Git: {info['git']} | Venv: {info['virtual_env']}"
        return {
            "success": True,
            "message": summary,
            "data": info,
            "error": None
        }


terminal_agent = TerminalAgent()
