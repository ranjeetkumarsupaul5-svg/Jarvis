import inspect
import time
from typing import Any, Callable, Dict, List, Optional
from backend.tools.system_monitor import get_system_monitor
from backend.tools.weather_tools import get_weather
from backend.tools.location_tools import get_location
from backend.agents.vision_agent import vision_agent as vision_agent_instance
from backend.core.permission import (
    requires_confirmation,
    build_confirmation_message
)


def format_tool_result(success: bool, message: str, data: Any = None, error: Optional[str] = None) -> Dict[str, Any]:
    """
    Standardized tool response schema across JARVIS AI OS.
    """
    return {
        "success": bool(success),
        "message": str(message),
        "data": data,
        "error": str(error) if error else None
    }


class ToolRouter:
    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}

    def register(
        self,
        name: str,
        function: Callable,
        description: str = "",
        category: str = "general",
        parameters: Optional[Dict[str, Any]] = None,
        requires_confirmation: bool = False
    ):
        """
        Register a tool with metadata.
        """
        if parameters is None:
            try:
                sig = inspect.signature(function)
                parameters = {
                    param: str(param_obj.annotation) if param_obj.annotation != inspect.Parameter.empty else "any"
                    for param, param_obj in sig.parameters.items()
                }
            except Exception:
                parameters = {}

        self._tools[name] = {
            "name": name,
            "function": function,
            "description": description or (function.__doc__.strip() if function.__doc__ else name),
            "category": category,
            "parameters": parameters,
            "requires_confirmation": requires_confirmation
        }

    def execute(self, name: str, *args, _confirmed: bool = False, **kwargs) -> Dict[str, Any]:
        """
        Execute a tool safely, returning a structured result.
        """
        start_time = time.time()

        if name not in self._tools:
            return format_tool_result(
                success=False,
                message=f"Tool '{name}' is not available.",
                data=None,
                error="ToolNotFound"
            )

        tool_meta = self._tools[name]
        func = tool_meta["function"]

        # Security / Permission Check
        if requires_confirmation(name) and not _confirmed:
            from backend.core.permission import set_pending_action

            set_pending_action(
                tool_name=name,
                args=args,
                kwargs=kwargs
            )

            return format_tool_result(
                success=False,
                message=build_confirmation_message(name, args),
                data={
                    "requires_confirmation": True,
                    "tool": name,
                    "args": args,
                    "kwargs": kwargs
                },
                error="ConfirmationRequired"
            )

        try:
            raw_result = func(*args, **kwargs)
            elapsed = round(time.time() - start_time, 3)

            # If tool returned structured dict, ensure standard keys
            if isinstance(raw_result, dict) and "success" in raw_result:
                result = {
                    "success": bool(raw_result.get("success", True)),
                    "message": str(raw_result.get("message", "")),
                    "data": raw_result.get("data", None),
                    "error": raw_result.get("error", None)
                }
            elif isinstance(raw_result, list):
                # List-returning tools (e.g. search_memory, recall, list_memories)
                # must pass through directly so callers can index with [0], [1], etc.
                try:
                    from backend.db import log_activity
                    log_activity(
                        command=f"{name}({args}, {kwargs})" if args or kwargs else name,
                        intent=tool_meta.get("category", "memory"),
                        tool=name,
                        status="SUCCESS",
                        result=f"Retrieved {len(raw_result)} items",
                        execution_time=elapsed
                    )
                except Exception:
                    pass
                return raw_result
            else:
                # Wrap unstructured result
                result = format_tool_result(
                    success=True,
                    message=str(raw_result),
                    data=raw_result
                )

            # Log to DB
            try:
                from backend.db import log_activity
                status_str = "SUCCESS" if result["success"] else "FAILED"
                log_activity(
                    command=f"{name}({args}, {kwargs})" if args or kwargs else name,
                    intent=tool_meta.get("category", "general"),
                    tool=name,
                    status=status_str,
                    result=result["message"],
                    execution_time=elapsed
                )
            except Exception:
                pass

            return result

        except Exception as e:
            elapsed = round(time.time() - start_time, 3)
            err_msg = str(e)
            result = format_tool_result(
                success=False,
                message=f"Error while running {name}: {err_msg}",
                data=None,
                error=err_msg
            )
            try:
                from backend.db import log_activity
                log_activity(
                    command=f"{name}({args}, {kwargs})" if args or kwargs else name,
                    intent=tool_meta.get("category", "general"),
                    tool=name,
                    status="ERROR",
                    result=err_msg,
                    execution_time=elapsed
                )
            except Exception:
                pass

            return result
    def has_tool(self, name: str) -> bool:
        return name in self._tools

    def list_tools(self) -> List[str]:
        return list(self._tools.keys())

    def get_tool_info(self, name: str) -> Optional[Dict[str, Any]]:
        if name in self._tools:
            item = dict(self._tools[name])
            item.pop("function", None)
            return item
        return None

    def get_all_tools(self) -> Dict[str, Dict[str, Any]]:
        clean_tools = {}
        for k, v in self._tools.items():
            item = dict(v)
            item.pop("function", None)
            clean_tools[k] = item
        return clean_tools


router = ToolRouter()


def register_default_tools():
    """
    Auto-registers all built-in system, file, terminal, and web tools.
    """
    try:
        from backend.tools import system_tools, file_tools, terminal_tools, web_tools

        # System Tools
        router.register(
            "open_application", system_tools.open_application,
            description="Open a desktop application by name or shortcut",
            category="system"
        )
        router.register(
            "get_system_info", system_tools.get_system_info,
            description="Get OS, CPU, RAM, and hardware metrics",
            category="system"
        )
        router.register(
            "take_screenshot", system_tools.take_screenshot,
            description="Capture the desktop screen and save to disk",
            category="system"
        )
        router.register(
            "get_screen_size", system_tools.get_screen_size,
            description="Get current screen width and height",
            category="system"
        )
        router.register(
            "minimize_all_windows", system_tools.minimize_all_windows,
            description="Minimize all desktop windows",
            category="system"
        )
        router.register(
            "control_volume", system_tools.control_volume,
            description="Control master sound volume (up, down, mute, unmute)",
            category="system"
        )
        router.register(
            "get_battery_status", system_tools.get_battery_status,
            description="Get device battery percentage and power status",
            category="system"
        )
        router.register(
            "lock_workstation", system_tools.lock_workstation,
            description="Lock the computer workstation",
            category="system",
            requires_confirmation=True
        )
        router.register(
            "get_active_window", system_tools.get_active_window,
            description="Get title of currently focused active window",
            category="system"
        )

        router.register(
            "get_system_monitor",
            lambda _args=None: get_system_monitor(),
            description="Get live CPU, memory, disk, battery and uptime information",
            category="system"
        )
        router.register(
            "get_weather",
            lambda args=None: get_weather((args or {}).get("location", "")),
            description="Get current weather for a location",
            category="weather"
        )

        router.register(
            "get_location",
            lambda _args=None: get_location(),
            description="Get approximate current location using IP geolocation",
            category="location"
        )

             # Vision Tools
        router.register(
            "capture_webcam",
            vision_agent_instance.capture_webcam,
            description="Capture a single frame from the webcam",
            category="vision"
        )

        router.register(
            "detect_faces",
            vision_agent_instance.detect_faces,
            description="Detect faces in a webcam frame using OpenCV",
            category="vision"
        )

        router.register(
            "analyze_image",
            vision_agent_instance.analyze_image,
            description="Analyze an image using the vision system",
            category="vision"
        )

        router.register(
            "read_text_from_image",
            vision_agent_instance.read_text_from_image,
            description="Read text from an image",
            category="vision"
        )

        # File Tools & File Agent
        router.register(
            "search_files", file_tools.search_files,
            description="Search files and directories matching a keyword",
            category="files"
        )
        router.register(
            "create_folder", file_tools.create_folder,
            description="Create a directory path",
            category="files"
        )
        router.register(
            "create_file", file_tools.create_file,
            description="Create or overwrite a file with text content",
            category="files"
        )
        router.register(
            "read_file", file_tools.read_file,
            description="Read the contents of a file",
            category="files"
        )
        router.register(
            "delete_file", file_tools.delete_file,
            description="Delete a specified file",
            category="files",
            requires_confirmation=True
        )
        router.register(
            "list_folder", file_tools.list_folder,
            description="List items inside a directory",
            category="files"
        )
        router.register(
            "get_file_info", file_tools.get_file_info,
            description="Get file metadata, size, and modification date",
            category="files"
        )

        from backend.agents.file_agent import file_agent
        router.register(
            "find_by_extension", file_agent.find_by_extension,
            description="Find files by extension (e.g. .py, .txt, .pdf)",
            category="files"
        )
        router.register(
            "search_content", file_agent.search_content,
            description="Search for specific code or text within files",
            category="files"
        )
        router.register(
            "copy_file", file_agent.copy_file,
            description="Copy a file from source to destination",
            category="files"
        )
        router.register(
            "move_file", file_agent.move_file,
            description="Move or rename a file",
            category="files"
        )
        router.register(
            "summarize_document", file_agent.summarize_document,
            description="Read and summarize a document or source file",
            category="files"
        )

        # Terminal Tools & Terminal Agent
        router.register(
            "run_command", terminal_tools.run_command,
            description="Safely execute a shell/terminal command",
            category="terminal"
        )
        router.register(
            "is_dangerous", terminal_tools.is_dangerous,
            description="Check if a terminal command is destructive",
            category="terminal"
        )

        from backend.agents.terminal_agent import terminal_agent
        router.register(
            "diagnose_error", terminal_agent.diagnose_error,
            description="Diagnose a terminal command error and suggest fixes",
            category="terminal"
        )
        router.register(
            "list_processes", terminal_agent.list_processes,
            description="List active system processes",
            category="terminal"
        )
        router.register(
            "inspect_environment", terminal_agent.inspect_environment,
            description="Inspect dev tools (Python, Git, Node, Venv)",
            category="terminal"
        )

        # Web Tools
        router.register(
            "search_web", web_tools.search_web,
            description="Search the web for real-time information",
            category="web"
        )
        router.register(
            "fetch_web_page", web_tools.fetch_web_page,
            description="Fetch and extract text content from a web URL",
            category="web"
        )

        # Memory Tools
        from backend.memory.memory_manager import memory_manager
        router.register(
            "remember", memory_manager.remember,
            description="Remember a user preference, project detail, or important fact",
            category="memory"
        )
        router.register(
            "recall", memory_manager.recall,
            description="Recall stored facts, preferences, or project details",
            category="memory"
        )
        router.register(
            "forget", memory_manager.forget,
            description="Forget a specific piece of stored memory",
            category="memory"
        )
        router.register(
            "add_memory", memory_manager.add_memory,
            description="Store a new fact, preference, or piece of knowledge in persistent memory",
            category="memory"
        )
        router.register(
            "search_memory", memory_manager.search_memory,
            description="Search persistent memory for stored facts and preferences",
            category="memory"
        )
        router.register(
            "delete_memory", memory_manager.delete_memory,
            description="Delete a stored memory item by id, key, or query",
            category="memory"
        )
        router.register(
            "list_memories", memory_manager.list_memories,
            description="List stored memories ordered by importance and recency",
            category="memory"
        )
        router.register(
            "update_memory", memory_manager.update_memory,
            description="Update an existing stored memory item",
            category="memory"
        )

        # Automation / Scheduler
        from backend.automation.scheduler import scheduler

        router.register(
            "add_reminder",
            scheduler.add_reminder,
            description="Schedule a reminder for a specific future date and time",
            category="automation"
        )

        router.register(
            "list_reminders",
            scheduler.list_tasks,
            description="List all scheduled reminders",
            category="automation"
        )

        router.register(
            "cancel_reminder",
            scheduler.cancel_task,
            description="Cancel a scheduled reminder by task ID",
            category="automation"
        )

        # Coding Agent Tools
        from backend.agents.coding_agent import coding_agent
        router.register(
            "inspect_repo", coding_agent.inspect_repo,
            description="Inspect codebase layout, architecture, and git branch",
            category="coding"
        )
        router.register(
            "git_status", coding_agent.git_status,
            description="Check git status for modified or untracked files",
            category="coding"
        )
        router.register(
            "git_diff", coding_agent.git_diff,
            description="Inspect unstaged git diff changes",
            category="coding"
        )
        router.register(
            "git_log", coding_agent.git_log,
            description="View recent git commit history",
            category="coding"
        )
        router.register(
            "create_commit", coding_agent.create_commit,
            description="Create a git commit with changes (requires confirmation)",
            category="coding"
        )
        router.register(
            "run_tests", coding_agent.run_tests,
            description="Run automated tests and return results",
            category="coding"
        )

        # Vision Agent Tools
        from backend.agents.vision_agent import vision_agent
        router.register(
            "inspect_screen", vision_agent.inspect_screen,
            description="Inspect display metrics and active foreground window",
            category="vision"
        )
        router.register(
            "take_screenshot", vision_agent.take_screenshot,
            description="Capture desktop screenshot and save to disk",
            category="vision"
        )
        router.register(
            "capture_webcam", vision_agent.capture_webcam,
            description="Capture single camera frame from webcam",
            category="vision"
        )
        router.register(
            "analyze_image", vision_agent.analyze_image,
            description="Analyze image contents using multimodal AI or computer vision",
            category="vision"
        )
        router.register(
            "read_text_from_image", vision_agent.read_text_from_image,
            description="Extract text from an image using AI vision",
            category="vision"
        )

        # Browser Agent Tools
        from backend.agents.browser_agent import browser_agent
        router.register(
            "open_url", browser_agent.open_url,
            description="Open any URL in system default browser",
            category="browser"
        )
        router.register(
            "search_and_open", browser_agent.search_and_open,
            description="Search query on Google/YouTube/DuckDuckGo and open browser",
            category="browser"
        )
        router.register(
            "scrape_and_summarize", browser_agent.scrape_and_summarize,
            description="Scrape clean text from a webpage and generate summary",
            category="browser"
        )
        router.register(
            "extract_links", browser_agent.extract_links,
            description="Extract hyperlinks from a webpage",
            category="browser"
        )
        router.register(
            "open_media", browser_agent.open_media,
            description="Search and play media on YouTube or Spotify",
            category="browser"
        )
    except Exception as e:
        print(f"Warning during default tool registration: {e}")


# Initialize registration
register_default_tools()
