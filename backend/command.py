import os
import threading
import time
from typing import Any, Dict, Optional

import pyttsx3
import speech_recognition as sr
import eel

from backend.core.brain import jarvis_brain
from backend.db import get_recent_activities, get_db_connection


def safe_eel(func_name: str, *args, **kwargs):
    """
    Safely invoke Eel JavaScript callbacks without crashing if frontend is disconnected.
    Accepts function name as string to avoid AttributeError when Eel is not running.
    """
    try:
        fn = getattr(eel, func_name, None)
        if callable(fn):
            fn(*args, **kwargs)
    except Exception:
        # Frontend not initialized or client disconnected
        pass


class VoiceEngine:
    """
    Thread-safe Singleton Text-to-Speech Engine for JARVIS.
    Manages SAPI5 speech synthesis without COM deadlocks.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(VoiceEngine, cls).__new__(cls)
                    cls._instance._init_engine()
        return cls._instance

    def _init_engine(self):
        self.engine = None
        self.speech_lock = threading.Lock()
        try:
            self.engine = pyttsx3.init('sapi5')
            voices = self.engine.getProperty('voices')
            if voices:
                self.engine.setProperty('voice', voices[0].id)
            self.engine.setProperty('rate', 174)
            self.engine.setProperty('volume', 1.0)
        except Exception as e:
            print(f"Warning: pyttsx3 initialization failed: {e}")
            self.engine = None

    def speak(self, text: str):
        if not text:
            return

        text = str(text).strip()
        print(f"JARVIS: {text}")

        # Update Eel UI display
        safe_eel("DisplayMessage", text)

        with self.speech_lock:
            if self.engine is not None:
                try:
                    self.engine.say(text)
                    self.engine.runAndWait()
                except Exception as e:
                    print(f"Speech synthesis error: {e}")
                    try:
                        self._init_engine()
                    except Exception:
                        pass
            else:
                time.sleep(0.05 * len(text.split()))

        # Update Eel UI receiver transcript
        safe_eel("receiverText", text)


# Singleton voice engine instance
voice_engine = VoiceEngine()


def speak(text):
    """
    Global speak function compatible with legacy calls.
    """
    voice_engine.speak(text)


def takecommand() -> Optional[str]:
    """
    Listen to user speech input via microphone using Google Speech Recognition.
    Fixes the echo bug by not speaking user input back.
    """
    r = sr.Recognizer()
    query = None

    try:
        with sr.Microphone() as source:
            print("Listening...")
            safe_eel("DisplayMessage", "I'm listening...")
            r.pause_threshold = 1.0
            r.adjust_for_ambient_noise(source, duration=0.8)
            audio = r.listen(source, timeout=8, phrase_time_limit=10)

        print("Recognizing speech...")
        safe_eel("DisplayMessage", "Recognizing...")
        query = r.recognize_google(audio, language='en-US')
        print(f"User said: {query}\n")
        safe_eel("DisplayMessage", query)

        # Removed speak(query) echo bug here!

    except sr.WaitTimeoutError:
        print("Microphone listen timed out.")
        return None
    except sr.UnknownValueError:
        print("Could not understand audio.")
        return None
    except Exception as e:
        print(f"Voice recognition error: {e}")
        return None

    return query.lower() if query else None


@eel.expose
def takeAllCommands(message=None):
    """
    Central command processor exposed to Eel frontend.
    Handles voice or text queries and executes through JarvisBrain.
    """
    if message is None:
        query = takecommand()
        if not query:
            safe_eel("ShowHood")
            return
        safe_eel("senderText", query)
    else:
        query = str(message).strip()
        print(f"Text command received: {query}")
        safe_eel("senderText", query)

    if not query:
        speak("No command was detected.")
        safe_eel("ShowHood")
        return

    try:
        # Check for legacy WhatsApp contacts workflow
        if any(trigger in query for trigger in ["send message to", "whatsapp call to", "video call to"]):
            from backend.feature import findContact, whatsApp
            flag = ""
            Phone, name = findContact(query)
            if Phone != 0:
                if "send message" in query:
                    flag = 'message'
                    speak(f"What message would you like to send to {name}?")
                    msg_query = takecommand()
                    if msg_query:
                        whatsApp(Phone, msg_query, flag, name)
                elif "call" in query:
                    flag = 'call'
                    whatsApp(Phone, query, flag, name)
                else:
                    flag = 'video call'
                    whatsApp(Phone, query, flag, name)
                safe_eel("ShowHood")
                return

        # Core intelligence routing via JarvisBrain
        result = jarvis_brain.process_command(query) or {}

        text_response = (
            result.get("message")
            or result.get("text_response")
            or "Command executed."
        )

        speech_response = (
            result.get("spoken")
            or result.get("speech_response")
            or text_response
        )

        # Send only one response to the Eel UI.
        # UI displays the normal message; spoken is reserved for TTS.
        print("SENDING TO UI:", result)
        safe_eel("showAssistantResponse", {
            "message": text_response
        })
        print("UI RESPONSE SENT:", text_response)

        # Speak response aloud
        speak(speech_response)

        # Return result to JavaScript callback
        return None

    except Exception as e:
        print(f"Error processing command '{query}': {e}")
        error_msg = f"I encountered an error executing that request: {str(e)}"
        safe_eel("receiverText", error_msg)
        speak("Sorry, an error occurred while processing your request.")

    safe_eel("ShowHood")


# =====================================================================
# Futuristic AI OS Eel API Endpoints
# Exposing live backend telemetry and tools to the frontend
# =====================================================================

@eel.expose
def getSystemMetrics():
    """
    Exposes live system health (RAM, CPU, active window, battery, network) to frontend dashboard.
    """
    from backend.tools.system_tools import get_system_info, get_active_window, get_battery_status
    info = get_system_info()
    win = get_active_window()
    battery = get_battery_status()

    # Quick network check
    is_online = True
    try:
        import socket
        socket.create_connection(("8.8.8.8", 53), timeout=1.5).close()
    except Exception:
        is_online = False

    return {
        "success": True,
        "system": info.get("data", {}),
        "active_window": win.get("data", {}).get("title", "Desktop"),
        "battery": battery.get("data", {}),
        "network": {"online": is_online, "status": "CONNECTED" if is_online else "OFFLINE"},
        "timestamp": time.strftime("%H:%M:%S")
    }


@eel.expose
def getActivityLogs(limit=25):
    """
    Exposes live activity logs from SQLite database to the frontend terminal console.
    """
    try:
        logs = get_recent_activities(limit=limit)
        return {"success": True, "logs": logs}
    except Exception as e:
        return {"success": False, "error": str(e), "logs": []}


@eel.expose
def getMemoryItems():
    """
    Exposes persistent user memories to frontend memory viewer.
    """
    from backend.memory.memory_manager import memory_manager
    items = memory_manager.recall()
    return {"success": True, "memories": items}


@eel.expose
def saveMemoryItem(key: str, value: str, category: str = "user_fact"):
    """
    Save or update a memory item.
    """
    from backend.memory.memory_manager import memory_manager
    return memory_manager.remember(category=category, key=key, value=value)


@eel.expose
def deleteMemoryItem(key: str):
    """
    Forget a specific memory key.
    """
    from backend.memory.memory_manager import memory_manager
    return memory_manager.forget(key)


@eel.expose
def getFileList(folder: Optional[str] = None):
    """
    List contents of a directory.
    """
    from backend.tools.file_tools import list_folder
    return list_folder(folder or ".")


@eel.expose
def readFileContent(filepath: str):
    """
    Read contents of a file safely.
    """
    from backend.tools.file_tools import read_file
    return read_file(filepath)


@eel.expose
def searchFiles(folder: Optional[str] = None, keyword: str = ""):
    """
    Search files matching keyword and format data for UI consumption.
    """
    if keyword == "" and folder:
        keyword = folder
        folder = "."
    from backend.tools.file_tools import search_files
    raw = search_files(folder or ".", keyword or "")
    if isinstance(raw, dict) and raw.get("success"):
        matches = []
        for p in raw.get("data", []):
            try:
                matches.append({
                    "name": os.path.basename(p),
                    "path": p,
                    "extension": os.path.splitext(p)[1] or "file",
                    "size": os.path.getsize(p) if os.path.isfile(p) else 0
                })
            except Exception:
                matches.append({
                    "name": os.path.basename(p),
                    "path": p,
                    "extension": "file",
                    "size": 0
                })
        return {
            "success": True,
            "message": raw.get("message"),
            "data": {"matches": matches}
        }
    return raw


@eel.expose
def createFileOrFolder(target_type: str, path: str, content: str = ""):
    """
    Create a file or folder.
    """
    from backend.tools.file_tools import create_file, create_folder
    if target_type == "folder":
        return create_folder(path)
    return create_file(path, content)


@eel.expose
def runTerminalCommand(command: str, allow_dangerous: bool = False):
    """
    Execute terminal command with safety checks.
    """
    from backend.tools.terminal_tools import run_command
    return run_command(command, allow_dangerous=allow_dangerous)


@eel.expose
def getProcessList():
    """
    List active system processes.
    """
    from backend.agents.terminal_agent import terminal_agent
    return terminal_agent.list_processes()


@eel.expose
def getGitTelemetry():
    """
    Fetch comprehensive Git status, diff, branch, and commit log.
    """
    from backend.agents.coding_agent import coding_agent
    repo_info = coding_agent.inspect_repo()
    status_info = coding_agent.git_status()
    diff_info = coding_agent.git_diff()
    log_info = coding_agent.git_log(limit=8)
    return {
        "success": True,
        "repo": repo_info.get("data", {}),
        "status": status_info.get("data", {}),
        "diff": diff_info.get("data", {}),
        "logs": log_info.get("data", {}).get("commits", [])
    }


@eel.expose
def executeGitCommit(message: str, allow_commit: bool = False):
    """
    Create a git commit with changes.
    """
    from backend.agents.coding_agent import coding_agent
    return coding_agent.create_commit(message, allow_commit=allow_commit)


@eel.expose
def runTestSuite(test_script: str = "test_router.py"):
    """
    Run automated tests.
    """
    from backend.agents.coding_agent import coding_agent
    return coding_agent.run_tests(test_script)


@eel.expose
def getVisionTelemetry():
    """
    Display resolution, active window, and recent screenshot thumbnails.
    """
    from backend.agents.vision_agent import vision_agent
    from backend.config import BASE_DIR
    screen_info = vision_agent.inspect_screen()

    screenshot_dir = BASE_DIR / "artifacts" / "screenshots"
    shots = []
    if screenshot_dir.exists():
        shots = [p.name for p in sorted(screenshot_dir.glob("*.png"), key=lambda x: x.stat().st_mtime, reverse=True)[:8]]

    webcam_dir = BASE_DIR / "artifacts" / "webcam"
    cams = []
    if webcam_dir.exists():
        cams = [p.name for p in sorted(webcam_dir.glob("*.jpg"), key=lambda x: x.stat().st_mtime, reverse=True)[:8]]

    return {
        "success": True,
        "screen": screen_info.get("data", {}),
        "screenshots": shots,
        "webcam_frames": cams
    }


@eel.expose
def captureScreenNow():
    """
    Capture screen snapshot.
    """
    from backend.agents.vision_agent import vision_agent
    return vision_agent.take_screenshot()


@eel.expose
def captureWebcamNow():
    """
    Capture frame from webcam.
    """
    from backend.agents.vision_agent import vision_agent
    return vision_agent.capture_webcam()


@eel.expose
def analyzeImageNow(image_path: str, prompt: str = "Describe what you see in this image in detail."):
    """
    Multimodal image analysis or computer vision.
    """
    from backend.agents.vision_agent import vision_agent
    return vision_agent.analyze_image(image_path, prompt=prompt)


@eel.expose
def searchWebBrowser(query: str, engine: str = "google"):
    """
    Launch search in browser.
    """
    from backend.agents.browser_agent import browser_agent
    return browser_agent.search_and_open(query, engine)


@eel.expose
def scrapeWebPage(url: str):
    """
    Scrape and summarize webpage.
    """
    from backend.agents.browser_agent import browser_agent
    return browser_agent.scrape_and_summarize(url)


@eel.expose
def getAutomationsList():
    """
    List configured automations and active scheduled triggers.
    """
    from backend.db import get_automations
    return {
        "success": True,
        "automations": get_automations(),
        "active_triggers": [
            {"name": "System Telemetry Monitor", "interval": "3.5s", "status": "ACTIVE"},
            {"name": "Hotword Wake-Word Standby", "interval": "Continuous", "status": "ACTIVE"}
        ]
    }


@eel.expose
def createAutomationTask(name: str, trigger_type: str, command: str, interval_sec: int = 0):
    """
    Save automation task.
    """
    from backend.db import add_automation
    res = add_automation(name, trigger_type, command, interval_sec)
    return {"success": res, "message": f"Automation '{name}' saved." if res else "Failed to save automation."}


@eel.expose
def toggleAutomationTask(automation_id: int):
    """
    Toggle automation active/disabled state.
    """
    from backend.db import toggle_automation
    status = toggle_automation(automation_id)
    return {"success": status is not None, "new_status": status}


@eel.expose
def getAiConfig():
    """
    Retrieve AI configuration and API statuses.
    """
    from backend.services.llm_service import llm_service
    from backend.config import GROQ_API_KEY
    has_groq = bool(GROQ_API_KEY or os.getenv("GROQ_API_KEY"))
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_porcupine = bool(os.getenv("PORCUPINE_ACCESS_KEY"))

    return {
        "success": True,
        "provider": llm_service.provider,
        "model": llm_service.model,
        "has_groq": has_groq,
        "has_openai": has_openai,
        "has_porcupine": has_porcupine,
        "voice_rate": 174,
        "is_online": llm_service.is_available()
    }


@eel.expose
def setVoiceSettings(rate: int, voice_idx: int = 0):
    """
    Calibrate voice settings.
    """
    global voice_engine
    if voice_engine.engine is not None:
        try:
            voice_engine.engine.setProperty('rate', int(rate))
            voices = voice_engine.engine.getProperty('voices')
            if 0 <= voice_idx < len(voices):
                voice_engine.engine.setProperty('voice', voices[voice_idx].id)
        except Exception:
            pass
    speak("Voice parameters calibrated.")
    return {"success": True, "rate": rate}


@eel.expose
def runAiToolAction(tool_type: str, prompt: str, context: Optional[str] = None):
    """
    Directly run AI tools: chat, summarize, code, research.
    """
    from backend.services.llm_service import llm_service
    if tool_type == "summarize":
        system = "You are JARVIS. Summarize the following document or text with extreme clarity and structured bullet points."
        resp = llm_service.generate_chat_response(prompt, system_prompt=system)
    elif tool_type == "code":
        system = "You are JARVIS Senior Code Architect. Generate, debug, or refactor the requested code with robust error handling and explanations."
        resp = llm_service.generate_chat_response(prompt, system_prompt=system)
    elif tool_type == "research":
        system = "You are JARVIS Deep Research Intelligence. Synthesize findings, outline key insights, risks, and next steps."
        resp = llm_service.generate_chat_response(prompt, system_prompt=system)
    else:
        resp = llm_service.generate_chat_response(prompt)

    return {"success": True, "response": resp}


@eel.expose
def runAgentAction(agent_name: str, action: str, params: Optional[Dict[str, Any]] = None):
    """
    Directly triggers an agent action from the UI dashboard.
    """
    params = params or {}
    from backend.core.router import router

    tool_name = action
    if not router.has_tool(tool_name):
        return {"success": False, "message": f"Action '{action}' not recognized.", "data": None}

    return router.execute(tool_name, **params)