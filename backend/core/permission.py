from typing import Optional


PROTECTED_TOOLS = {
    "delete_file",
    "execute_command",
    "run_terminal_command",
    "run_command",
    "shutdown_system",
    "restart_system",
    "change_system_setting",
}


# Stores one pending dangerous action.
_pending_action = None


def requires_confirmation(tool_name: str) -> bool:
    return tool_name in PROTECTED_TOOLS


def build_confirmation_message(
    tool_name: str,
    args: Optional[object] = None
) -> str:

    if tool_name == "delete_file":
        return "Sir, this action will delete a file permanently. Should I proceed?"

    if tool_name in {"execute_command", "run_terminal_command"}:
        return "Sir, this will execute a terminal command on your computer. Should I proceed?"

    if tool_name == "shutdown_system":
        return "Sir, this will shut down the computer. Should I proceed?"

    if tool_name == "restart_system":
        return "Sir, this will restart the computer. Should I proceed?"

    if tool_name == "change_system_setting":
        return "Sir, this will change a system setting. Should I proceed?"

    if tool_name in {"execute_command", "run_terminal_command", "run_command"}:
        return "Sir, this will execute a terminal command on your computer. Should I proceed?"

    return "Sir, this action requires your confirmation. Should I proceed?"


def set_pending_action(tool_name: str, args: tuple, kwargs: dict):
    global _pending_action

    _pending_action = {
        "tool": tool_name,
        "args": args,
        "kwargs": kwargs,
    }


def get_pending_action():
    return _pending_action


def clear_pending_action():
    global _pending_action
    _pending_action = None


def is_confirmation(text: str) -> bool:
    if not text:
        return False

    return text.lower().strip() in {
        "yes",
        "yes please",
        "yeah",
        "yep",
        "ok",
        "okay",
        "sure",
        "proceed",
        "do it",
        "go ahead",
        "confirm",
        "haan",
        "ha",
        "kar do",
        "karo",
    }


def is_rejection(text: str) -> bool:
    if not text:
        return False

    return text.lower().strip() in {
        "no",
        "nope",
        "cancel",
        "cancel it",
        "don't",
        "do not",
        "stop",
        "never mind",
        "nahi",
        "mat karo",
        "cancel karo",
    }