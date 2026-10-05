import ctypes
from datetime import datetime
import os
from pathlib import Path
from typing import Any, Dict, Optional

from backend.config import BASE_DIR
from backend.services.llm_service import llm_service


class VisionAgent:
    """
    Vision and Visual Intelligence Agent for JARVIS.
    Handles screen capture, webcam perception, active display inspection,
    and multimodal image understanding via Groq/OpenAI or local computer vision.
    """

    def __init__(self):
        self.name = "VisionAgent"
        self.screenshot_dir = BASE_DIR / "artifacts" / "screenshots"
        self.webcam_dir = BASE_DIR / "artifacts" / "webcam"
        self._ensure_dirs()

    def _ensure_dirs(self):
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.webcam_dir.mkdir(parents=True, exist_ok=True)

    def get_screen_resolution(self) -> Dict[str, int]:
        """
        Query system screen dimensions via Windows User32 API.
        """
        try:
            user32 = ctypes.windll.user32
            width = user32.GetSystemMetrics(0)
            height = user32.GetSystemMetrics(1)
            monitors = user32.GetSystemMetrics(80)  # SM_CMONITORS
            return {"width": width, "height": height, "monitors": max(1, monitors)}
        except Exception:
            return {"width": 1920, "height": 1080, "monitors": 1}

    def inspect_screen(self) -> Dict[str, Any]:
        """
        Inspect current display metrics and active foreground window.
        """
        res = self.get_screen_resolution()
        active_window_title = "Unknown"
        hwnd = 0

        try:
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            if hwnd:
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    active_window_title = buff.value
        except Exception as e:
            active_window_title = f"Error reading window: {e}"

        return {
            "success": True,
            "message": f"Display: {res['width']}x{res['height']} ({res['monitors']} monitor(s)) | Active Window: '{active_window_title}'",
            "data": {
                "resolution": f"{res['width']}x{res['height']}",
                "width": res["width"],
                "height": res["height"],
                "monitors": res["monitors"],
                "active_window": active_window_title,
                "hwnd": hwnd
            },
            "error": None
        }

    def take_screenshot(self, save_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Capture the desktop screen and save to image file.
        Gracefully handles inactive/headless display sessions.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if save_path:
            out_path = Path(save_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            out_path = self.screenshot_dir / f"screenshot_{timestamp}.png"

        # Attempt PIL / pyautogui grab
        try:
            from PIL import ImageGrab
            im = ImageGrab.grab()
            im.save(str(out_path))
            return {
                "success": True,
                "message": f"Screenshot captured successfully: {out_path.name}",
                "data": {
                    "path": str(out_path),
                    "filename": out_path.name,
                    "width": im.size[0],
                    "height": im.size[1],
                    "timestamp": timestamp
                },
                "error": None
            }
        except Exception as e:
            # Fallback check for session
            res = self.get_screen_resolution()
            return {
                "success": False,
                "message": f"Screen capture unavailable in current desktop session ({e}).",
                "data": {
                    "resolution": f"{res['width']}x{res['height']}",
                    "attempted_path": str(out_path),
                    "reason": str(e)
                },
                "error": str(e)
            }

    def capture_webcam(self, save_path: Optional[str] = None, camera_index: int = 0) -> Dict[str, Any]:
        """
        Capture a single frame from the system webcam using OpenCV.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if save_path:
            out_path = Path(save_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            out_path = self.webcam_dir / f"webcam_{timestamp}.jpg"

        try:
            import cv2
            cap = cv2.VideoCapture(camera_index)
            if not cap.isOpened():
                return {
                    "success": False,
                    "message": f"Webcam (camera index {camera_index}) is not accessible.",
                    "data": None,
                    "error": "CameraUnavailable"
                }

            ret, frame = cap.read()
            cap.release()

            if not ret or frame is None:
                return {
                    "success": False,
                    "message": "Failed to read frame from webcam.",
                    "data": None,
                    "error": "FrameReadFailed"
                }

            cv2.imwrite(str(out_path), frame)
            h, w = frame.shape[:2]

            return {
                "success": True,
                "message": f"Webcam frame saved to {out_path.name} ({w}x{h}).",
                "data": {
                    "path": str(out_path),
                    "filename": out_path.name,
                    "width": w,
                    "height": h,
                    "camera_index": camera_index,
                    "timestamp": timestamp
                },
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Webcam capture error: {str(e)}",
                "data": None,
                "error": str(e)
            }

    def analyze_image(self, image_path: str, prompt: str = "Describe what you see in this image in detail.") -> Dict[str, Any]:
        """
        Analyze an image using multimodal LLM (online) or OpenCV edge/color metrics (offline).
        """
        p = Path(image_path)
        if not p.is_file():
            return {
                "success": False,
                "message": f"Image file not found: {image_path}",
                "data": None,
                "error": "FileNotFound"
            }

        # Try LLM vision if available
        if llm_service.is_available():
            llm_res = llm_service.analyze_image(str(p), prompt=prompt)
            if llm_res.get("success"):
                return llm_res

        # Fallback to local CV analysis
        try:
            import cv2
            import numpy as np
            from PIL import Image

            with Image.open(str(p)) as img:
                width, height = img.size
                format_name = img.format
                mode = img.mode

            cv_img = cv2.imread(str(p))
            brightness = float(np.mean(cv_img)) if cv_img is not None else 0.0

            summary = (
                f"Image: {p.name} | Format: {format_name} | Size: {width}x{height} | "
                f"Mode: {mode} | Mean Brightness: {brightness:.1f}/255"
            )

            return {
                "success": True,
                "message": summary,
                "data": {
                    "filename": p.name,
                    "path": str(p),
                    "width": width,
                    "height": height,
                    "format": format_name,
                    "mode": mode,
                    "brightness": round(brightness, 2),
                    "note": "Offline computer vision summary. Connect Groq/OpenAI for full semantic understanding."
                },
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Image analysis failed: {str(e)}",
                "data": {"path": str(p)},
                "error": str(e)
            }

    def read_text_from_image(self, image_path: str) -> Dict[str, Any]:
        """
        Extract visible text from an image using multimodal LLM.
        """
        prompt = "Transcribe and extract ALL text visible in this image. Output only the extracted text accurately."
        res = self.analyze_image(image_path, prompt=prompt)
        if res.get("success"):
            return {
                "success": True,
                "message": f"Extracted text: {res.get('message', '')}",
                "data": {"text": res.get("message", ""), "source": image_path},
                "error": None
            }
        return res


vision_agent = VisionAgent()
