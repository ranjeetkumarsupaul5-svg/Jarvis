import os
from pathlib import Path
import shutil
import time


def search_files(folder=".", keyword=""):
    """
    Search for files/folders containing the keyword.
    """
    results = []
    folder = os.path.expanduser(folder)

    if not os.path.exists(folder):
        return {
            "success": False,
            "message": f"Folder not found: {folder}",
            "data": [],
            "error": "FolderNotFound"
        }

    try:
        for root, dirs, files in os.walk(folder):
            # Exclude virtual environments and git from deep searches
            dirs[:] = [d for d in dirs if d not in {".git", ".venv", "envjarvis", "__pycache__", "node_modules"}]

            for name in files:
                if not keyword or keyword.lower() in name.lower():
                    results.append(os.path.join(root, name))

            for name in dirs:
                if keyword and keyword.lower() in name.lower():
                    results.append(os.path.join(root, name))

            if len(results) >= 100:
                break

        return {
            "success": True,
            "message": f"Found {len(results)} matching items.",
            "data": results,
            "error": None
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Search error: {str(e)}",
            "data": [],
            "error": str(e)
        }


def create_folder(path: str):
    """
    Create a new directory folder.
    """
    if not path or not path.strip():
        return {
            "success": False,
            "message": "No folder path provided.",
            "data": None,
            "error": "EmptyPath"
        }

    path = os.path.expanduser(path)

    try:
        os.makedirs(path, exist_ok=True)
        return {
            "success": True,
            "message": f"Folder created successfully: {path}",
            "data": {"path": path},
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Unable to create folder: {str(e)}",
            "data": None,
            "error": str(e)
        }


def create_file(path: str, content: str = ""):
    """
    Create or overwrite a text file.
    """
    if not path or not path.strip():
        return {
            "success": False,
            "message": "No file path provided.",
            "data": None,
            "error": "EmptyPath"
        }

    path = os.path.expanduser(path)

    try:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        with open(path, "w", encoding="utf-8") as file:
            file.write(content)

        return {
            "success": True,
            "message": f"File created successfully: {path}",
            "data": {"path": path, "size_chars": len(content)},
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Unable to create file: {str(e)}",
            "data": None,
            "error": str(e)
        }


def read_file(path: str, max_chars: int = 15000):
    """
    Read text contents from a file.
    """
    if not path or not path.strip():
        return {
            "success": False,
            "message": "No file path provided.",
            "data": None,
            "error": "EmptyPath"
        }

    path = os.path.expanduser(path)

    if not os.path.isfile(path):
        return {
            "success": False,
            "message": f"File not found: {path}",
            "data": None,
            "error": "FileNotFound"
        }

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as file:
            content = file.read(max_chars)

        return {
            "success": True,
            "message": f"Read {len(content)} characters from {path}",
            "data": {"content": content, "path": path},
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Unable to read file: {str(e)}",
            "data": None,
            "error": str(e)
        }


def delete_file(path: str):
    """
    Delete a specified file.
    """
    if not path or not path.strip():
        return {
            "success": False,
            "message": "No file path provided.",
            "data": None,
            "error": "EmptyPath"
        }

    path = os.path.expanduser(path)

    if not os.path.isfile(path):
        return {
            "success": False,
            "message": f"File not found: {path}",
            "data": None,
            "error": "FileNotFound"
        }

    try:
        os.remove(path)
        return {
            "success": True,
            "message": f"File deleted: {path}",
            "data": {"path": path},
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Unable to delete file: {str(e)}",
            "data": None,
            "error": str(e)
        }


def list_folder(path: str = "."):
    """
    List files and folders in a directory.
    """
    path = os.path.expanduser(path)

    if not os.path.isdir(path):
        return {
            "success": False,
            "message": f"Folder not found: {path}",
            "data": [],
            "error": "FolderNotFound"
        }

    try:
        items = os.listdir(path)
        return {
            "success": True,
            "message": f"Folder '{path}' contains {len(items)} items.",
            "data": items,
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Unable to list folder: {str(e)}",
            "data": [],
            "error": str(e)
        }


def get_file_info(path: str):
    """
    Get size and modification metadata for a file or directory.
    """
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        return {
            "success": False,
            "message": f"Path not found: {path}",
            "data": None,
            "error": "NotFound"
        }

    try:
        stat = os.stat(path)
        is_file = os.path.isfile(path)
        info = {
            "path": path,
            "is_file": is_file,
            "is_dir": os.path.isdir(path),
            "size_bytes": stat.st_size if is_file else 0,
            "size_kb": round(stat.st_size / 1024, 2) if is_file else 0,
            "modified": time.ctime(stat.st_mtime)
        }
        return {
            "success": True,
            "message": f"Metadata for {path}",
            "data": info,
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error retrieving info: {str(e)}",
            "data": None,
            "error": str(e)
        }