import fnmatch
import os
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional

from backend.config import BASE_DIR
from backend.services.llm_service import llm_service
from backend.tools.file_tools import read_file, create_file, delete_file, list_folder


class FileAgent:
    """
    Dedicated File System Agent for JARVIS.
    Handles file searches by pattern, content search, copying, moving,
    renaming, and AI-assisted document summarization.
    """

    def __init__(self):
        self.name = "FileAgent"

    def find_by_extension(self, extension: str, root_dir: str = ".") -> Dict[str, Any]:
        """
        Find all files with a given extension (e.g., '.py', '.txt', '.json').
        """
        ext = extension.strip().lower()
        if not ext.startswith("."):
            ext = "." + ext

        target_dir = os.path.expanduser(root_dir)
        matches = []

        try:
            for root, dirs, files in os.walk(target_dir):
                dirs[:] = [d for d in dirs if d not in {".git", ".venv", "envjarvis", "__pycache__", "node_modules"}]
                for f in files:
                    if f.lower().endswith(ext):
                        matches.append(os.path.join(root, f))
                if len(matches) >= 50:
                    break

            return {
                "success": True,
                "message": f"Found {len(matches)} files with extension '{ext}'.",
                "data": matches,
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"File search error: {str(e)}",
                "data": [],
                "error": str(e)
            }

    def search_content(self, keyword: str, root_dir: str = ".", max_matches: int = 20) -> Dict[str, Any]:
        """
        Search for text or code inside files.
        """
        if not keyword or not keyword.strip():
            return {"success": False, "message": "No search keyword provided.", "data": [], "error": "EmptyKeyword"}

        target_dir = os.path.expanduser(root_dir)
        results = []
        valid_extensions = {".py", ".txt", ".md", ".json", ".html", ".css", ".js", ".env", ".csv", ".xml"}

        try:
            for root, dirs, files in os.walk(target_dir):
                dirs[:] = [d for d in dirs if d not in {".git", ".venv", "envjarvis", "__pycache__", "node_modules"}]
                for file_name in files:
                    ext = os.path.splitext(file_name)[1].lower()
                    if ext in valid_extensions:
                        file_path = os.path.join(root, file_name)
                        try:
                            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                                for line_num, line in enumerate(f, 1):
                                    if keyword.lower() in line.lower():
                                        results.append({
                                            "file": file_path,
                                            "line": line_num,
                                            "snippet": line.strip()[:120]
                                        })
                                        if len(results) >= max_matches:
                                            break
                        except Exception:
                            continue
                if len(results) >= max_matches:
                    break

            return {
                "success": True,
                "message": f"Found {len(results)} matches for '{keyword}'.",
                "data": results,
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Content search failed: {str(e)}",
                "data": [],
                "error": str(e)
            }

    def copy_file(self, src: str, dest: str) -> Dict[str, Any]:
        """
        Copy a file to another location.
        """
        try:
            src_path = os.path.expanduser(src)
            dest_path = os.path.expanduser(dest)

            if not os.path.isfile(src_path):
                return {"success": False, "message": f"Source file does not exist: {src}", "data": None, "error": "FileNotFound"}

            os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
            shutil.copy2(src_path, dest_path)

            return {
                "success": True,
                "message": f"Copied '{src}' to '{dest}' successfully.",
                "data": {"src": src, "dest": dest},
                "error": None
            }
        except Exception as e:
            return {"success": False, "message": f"Copy failed: {str(e)}", "data": None, "error": str(e)}

    def move_file(self, src: str, dest: str) -> Dict[str, Any]:
        """
        Move or rename a file to another location.
        """
        try:
            src_path = os.path.expanduser(src)
            dest_path = os.path.expanduser(dest)

            if not os.path.exists(src_path):
                return {"success": False, "message": f"Source does not exist: {src}", "data": None, "error": "NotFound"}

            os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
            shutil.move(src_path, dest_path)

            return {
                "success": True,
                "message": f"Moved '{src}' to '{dest}' successfully.",
                "data": {"src": src, "dest": dest},
                "error": None
            }
        except Exception as e:
            return {"success": False, "message": f"Move failed: {str(e)}", "data": None, "error": str(e)}

    def summarize_document(self, path: str) -> Dict[str, Any]:
        """
        Read a text document, code file, or report and provide an executive summary.
        """
        res = read_file(path, max_chars=8000)
        if not res["success"]:
            return res

        content = res["data"]["content"]
        prompt = (
            f"Please read the following document content from '{path}' and provide a clear, "
            f"concise executive summary (3-4 bullet points highlighting key points, structure, and findings):\n\n"
            f"```\n{content}\n```"
        )

        summary = llm_service.generate_chat_response(prompt)

        return {
            "success": True,
            "message": summary,
            "data": {
                "path": path,
                "summary": summary,
                "char_count": len(content)
            },
            "error": None
        }


file_agent = FileAgent()
