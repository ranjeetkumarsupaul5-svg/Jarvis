import os
import subprocess
from typing import Optional
from backend.config import BASE_DIR

# Commands that should require explicit confirmation
DANGEROUS_COMMANDS = [
    "del ",
    "erase ",
    "rmdir ",
    "rd ",
    "format ",
    "shutdown",
    "restart",
    "taskkill",
    "diskpart",
    "rm -rf",
    "mkfs",
    "git reset --hard",
    "git clean -fd",
    "git push --force",
    "drop table",
    "drop database",
]


def is_dangerous(command: str) -> bool:
    """
    Check whether a command can make destructive system or file changes.
    """
    if not command:
        return False

    command_lower = command.lower().strip()
    for dangerous in DANGEROUS_COMMANDS:
        if dangerous in command_lower:
            return True

    return False


def run_command(command: str, cwd: Optional[str] = None, timeout: int = 30, allow_dangerous: bool = False):
    """
    Execute a terminal command safely and capture output.
    """
    if not command or not command.strip():
        return {
            "success": False,
            "message": "No command provided.",
            "data": None,
            "error": "EmptyCommand"
        }

    command = command.strip()
    working_dir = str(cwd) if cwd else str(BASE_DIR)

    # Do not execute destructive commands automatically
    if is_dangerous(command) and not allow_dangerous:
        return {
            "success": False,
            "message": "This command requires explicit user confirmation before execution.",
            "data": {"command": command, "is_dangerous": True},
            "error": "ConfirmationRequired"
        }

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=working_dir
        )

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        success = (result.returncode == 0)

        summary = stdout if stdout else (stderr if stderr else "Command executed with no output.")

        return {
            "success": success,
            "message": summary,
            "data": {
                "command": command,
                "stdout": stdout,
                "stderr": stderr,
                "returncode": result.returncode,
                "cwd": working_dir
            },
            "error": stderr if not success else None
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "message": f"Command timed out after {timeout} seconds.",
            "data": {"command": command, "timeout": timeout},
            "error": "TimeoutExpired"
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Unable to execute command: {str(e)}",
            "data": {"command": command},
            "error": str(e)
        }