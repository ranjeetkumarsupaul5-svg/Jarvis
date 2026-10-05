import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
FRONTEND_DIR = BASE_DIR / "frontend"
AUDIO_DIR = FRONTEND_DIR / "assets" / "audio"
START_SOUND_PATH = AUDIO_DIR / "start_sound.mp3"
DB_PATH = BASE_DIR / "jarvis.db"
SCREENSHOTS_DIR = BASE_DIR / "screenshots"


def load_env(env_path=None):
    """
    Lightweight, zero-dependency .env loader.
    """
    if env_path is None:
        env_path = BASE_DIR / ".env"
    else:
        env_path = Path(env_path)

    if not env_path.is_file():
        return

    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("\"' ")
                if key and key not in os.environ:
                    os.environ[key] = val
    except Exception as e:
        print(f"Warning: Failed to load .env file: {e}")


# Load environment variables
load_env()

# Core Configuration
ASSISTANT_NAME = os.getenv("ASSISTANT_NAME", "jarvis").strip().lower()
USER_NAME = os.getenv("USER_NAME", "Ranjeet").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
DEFAULT_LLM_MODEL = os.getenv("DEFAULT_LLM_MODEL", "llama-3.3-70b-versatile").strip()
HOST = os.getenv("JARVIS_HOST", "127.0.0.1")
PORT = int(os.getenv("JARVIS_PORT", "8000"))