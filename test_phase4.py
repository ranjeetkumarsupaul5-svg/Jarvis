import sys
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from backend.core.router import router
from backend.agents.coding_agent import coding_agent
from backend.agents.vision_agent import vision_agent
from backend.agents.browser_agent import browser_agent


class TestPhase4(unittest.TestCase):
    def test_router_has_phase4_tools(self):
        registered = router.list_tools()
        expected = [
            "inspect_repo", "git_status", "git_diff", "git_log", "create_commit", "run_tests",
            "inspect_screen", "take_screenshot", "capture_webcam", "analyze_image", "read_text_from_image",
            "open_url", "search_and_open", "scrape_and_summarize", "extract_links", "open_media"
        ]
        for tool in expected:
            self.assertIn(tool, registered, f"Tool {tool} must be registered in router")

    def test_coding_agent_inspect_repo(self):
        res = coding_agent.inspect_repo()
        self.assertTrue(res["success"])
        self.assertIn("Python", res["data"]["project_types"])
        self.assertGreater(res["data"]["file_count"], 10)

    def test_coding_agent_git_status_and_log(self):
        res_status = coding_agent.git_status()
        self.assertTrue(res_status["success"])
        res_log = coding_agent.git_log(limit=3)
        self.assertTrue(res_log["success"])

    def test_coding_agent_commit_confirmation_guard(self):
        res = coding_agent.create_commit("test commit", allow_commit=False)
        self.assertFalse(res["success"])
        self.assertEqual(res["error"], "ConfirmationRequired")

    def test_vision_agent_inspect_screen(self):
        res = vision_agent.inspect_screen()
        self.assertTrue(res["success"])
        self.assertIn("resolution", res["data"])
        self.assertGreater(res["data"]["width"], 0)

    def test_vision_agent_webcam_and_analysis(self):
        # Test webcam frame capture
        res_cam = vision_agent.capture_webcam()
        if res_cam["success"]:
            img_path = res_cam["data"]["path"]
            self.assertTrue(Path(img_path).exists())
            # Test image analysis on captured frame
            res_analysis = vision_agent.analyze_image(img_path)
            self.assertTrue(res_analysis["success"])
        else:
            # Webcam might be absent or busy in certain environments
            self.assertIn("error", res_cam)

    def test_vision_agent_screenshot_graceful_handling(self):
        # Must return structured schema whether desktop is interactive or headless
        res = vision_agent.take_screenshot()
        self.assertIn("success", res)
        self.assertIn("message", res)
        self.assertIn("data", res)

    def test_browser_agent_url_normalization_and_search(self):
        norm = browser_agent._normalize_url("example.com")
        self.assertEqual(norm, "https://example.com")
        norm_https = browser_agent._normalize_url("https://google.com")
        self.assertEqual(norm_https, "https://google.com")

    def test_browser_agent_scrape_and_summarize(self):
        # Test scraping with a fast, reliable page (e.g. example.com)
        res = browser_agent.scrape_and_summarize("https://example.com")
        self.assertTrue(res["success"])
        self.assertIn("Example Domain", res["data"]["title"])


if __name__ == "__main__":
    unittest.main()
