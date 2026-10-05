import sys
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from backend.command import getSystemMetrics, getActivityLogs, getMemoryItems, runAgentAction, takeAllCommands


class TestPhase5(unittest.TestCase):
    def test_system_metrics_endpoint(self):
        metrics = getSystemMetrics()
        self.assertTrue(metrics["success"])
        self.assertIn("system", metrics)
        self.assertIn("ram", metrics["system"])
        self.assertIn("active_window", metrics)

    def test_activity_logs_endpoint(self):
        res = getActivityLogs(limit=5)
        self.assertTrue(res["success"])
        self.assertIsInstance(res["logs"], list)

    def test_memory_items_endpoint(self):
        res = getMemoryItems()
        self.assertTrue(res["success"])
        self.assertIsInstance(res["memories"], list)

    def test_run_agent_action_endpoint(self):
        res = runAgentAction("system", "inspect_screen")
        self.assertTrue(res["success"])
        self.assertIn("resolution", res["data"])

    def test_take_all_commands_offline_text(self):
        # Must execute cleanly without Eel or GUI attached
        try:
            takeAllCommands("remember my current project is Jarvis OS")
            # Verify memory was recorded
            m = getMemoryItems()
            found = any("Jarvis OS" in mem.get("value", "") for mem in m["memories"])
            self.assertTrue(found, "Memory preference should be stored via takeAllCommands")
        except Exception as e:
            self.fail(f"takeAllCommands raised unexpected exception: {e}")


if __name__ == "__main__":
    unittest.main()
