import os
from pathlib import Path
import subprocess
from typing import Any, Dict, List, Optional

from backend.config import BASE_DIR
from backend.services.llm_service import llm_service


class CodingAgent:
    """
    Dedicated Software Engineering and Git Assistant for JARVIS.
    Understands project structures, diagnoses bugs, runs tests, and manages Git workflows safely.
    """

    def __init__(self):
        self.name = "CodingAgent"

    def inspect_repo(self, repo_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze codebase architecture, file layout, and project dependencies.
        """
        target = Path(repo_path) if repo_path else BASE_DIR

        if not target.is_dir():
            return {
                "success": False,
                "message": f"Directory not found: {target}",
                "data": None,
                "error": "DirectoryNotFound"
            }

        files_list = []
        project_types = set()

        for item in target.rglob("*"):
            # Exclude virtual environments and git from tree
            if any(part in {".git", ".venv", "envjarvis", "__pycache__", "node_modules"} for part in item.parts):
                continue
            if item.is_file():
                rel = item.relative_to(target).as_posix()
                files_list.append(rel)
                if item.suffix == ".py":
                    project_types.add("Python")
                elif item.name in ["package.json", "node_modules"]:
                    project_types.add("Node.js/JavaScript")
                elif item.suffix in [".html", ".css", ".js"]:
                    project_types.add("Web/Frontend")
                elif item.name in ["Dockerfile", "docker-compose.yml"]:
                    project_types.add("Docker")

        # Get current git branch if available
        branch = "Unknown"
        try:
            r = subprocess.run("git rev-parse --abbrev-ref HEAD", shell=True, capture_output=True, text=True, cwd=str(target), timeout=5)
            if r.returncode == 0:
                branch = r.stdout.strip()
        except Exception:
            pass

        summary = (
            f"Codebase: {target.name} | Types: {', '.join(project_types) or 'General'} | "
            f"Branch: {branch} | Tracked Files: {len(files_list)}"
        )

        return {
            "success": True,
            "message": summary,
            "data": {
                "name": target.name,
                "path": str(target),
                "branch": branch,
                "project_types": list(project_types),
                "file_count": len(files_list),
                "files_sample": files_list[:30]
            },
            "error": None
        }

    def git_status(self, repo_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Check working tree status (uncommitted changes, untracked files).
        """
        target = str(repo_path) if repo_path else str(BASE_DIR)
        try:
            r = subprocess.run("git status --short", shell=True, capture_output=True, text=True, cwd=target, timeout=10)
            output = r.stdout.strip()
            lines = output.splitlines() if output else []
            msg = f"{len(lines)} modified/untracked files." if lines else "Working tree clean. No changes."

            return {
                "success": (r.returncode == 0),
                "message": msg,
                "data": {"status_lines": lines, "raw": output},
                "error": r.stderr.strip() if r.returncode != 0 else None
            }
        except Exception as e:
            return {"success": False, "message": f"Git status error: {str(e)}", "data": None, "error": str(e)}

    def git_diff(self, repo_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Show changes in the working directory compared to HEAD.
        """
        target = str(repo_path) if repo_path else str(BASE_DIR)
        try:
            r = subprocess.run("git diff", shell=True, capture_output=True, text=True, cwd=target, timeout=10)
            diff_text = r.stdout.strip()
            return {
                "success": (r.returncode == 0),
                "message": f"Diff length: {len(diff_text)} characters." if diff_text else "No unstaged changes.",
                "data": {"diff": diff_text[:5000]},
                "error": r.stderr.strip() if r.returncode != 0 else None
            }
        except Exception as e:
            return {"success": False, "message": f"Git diff error: {str(e)}", "data": None, "error": str(e)}

    def git_log(self, limit: int = 5, repo_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Show recent commit history.
        """
        target = str(repo_path) if repo_path else str(BASE_DIR)
        try:
            r = subprocess.run(f"git log -n {limit} --oneline", shell=True, capture_output=True, text=True, cwd=target, timeout=10)
            commits = r.stdout.strip().splitlines() if r.stdout.strip() else []
            return {
                "success": (r.returncode == 0),
                "message": f"Recent {len(commits)} commits retrieved.",
                "data": {"commits": commits},
                "error": r.stderr.strip() if r.returncode != 0 else None
            }
        except Exception as e:
            return {"success": False, "message": f"Git log error: {str(e)}", "data": None, "error": str(e)}

    def create_commit(self, message: str, allow_commit: bool = False, repo_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Stage all changes and create a commit. Requires user confirmation.
        """
        if not allow_commit:
            return {
                "success": False,
                "message": f"Commit requires user confirmation. Message proposed: '{message}'",
                "data": {"message": message, "requires_confirmation": True},
                "error": "ConfirmationRequired"
            }

        target = str(repo_path) if repo_path else str(BASE_DIR)
        try:
            subprocess.run("git add -A", shell=True, check=True, cwd=target, timeout=10)
            r = subprocess.run(f'git commit -m "{message}"', shell=True, capture_output=True, text=True, cwd=target, timeout=15)
            return {
                "success": (r.returncode == 0),
                "message": r.stdout.strip() if r.returncode == 0 else f"Commit failed: {r.stderr.strip()}",
                "data": {"output": r.stdout.strip()},
                "error": r.stderr.strip() if r.returncode != 0 else None
            }
        except Exception as e:
            return {"success": False, "message": f"Commit failed: {str(e)}", "data": None, "error": str(e)}

    def run_tests(self, test_script: str = "test_router.py") -> Dict[str, Any]:
        """
        Execute test suite and parse success/failure.
        """
        python_exe = str(BASE_DIR / "envjarvis" / "Scripts" / "python.exe")
        if not os.path.exists(python_exe):
            python_exe = "python"

        cmd = f'"{python_exe}" {test_script}'
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=str(BASE_DIR), timeout=30)
            success = (r.returncode == 0)
            return {
                "success": success,
                "message": f"Tests {'passed' if success else 'failed'}: {test_script}",
                "data": {
                    "test_script": test_script,
                    "returncode": r.returncode,
                    "stdout": r.stdout.strip(),
                    "stderr": r.stderr.strip()
                },
                "error": r.stderr.strip() if not success else None
            }
        except Exception as e:
            return {"success": False, "message": f"Test run error: {str(e)}", "data": None, "error": str(e)}


coding_agent = CodingAgent()
