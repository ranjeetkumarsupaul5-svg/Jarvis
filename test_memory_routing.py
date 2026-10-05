import unittest
from backend.core.brain import brain
from backend.core.router import router
from backend.memory.memory_manager import memory_manager
from backend.services.llm_service import llm_service
from backend.db import get_recent_activities


class TestMemoryRouting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Seed test facts in memory
        memory_manager.add_memory("Ranjeet", key="my name", category="user_fact")
        memory_manager.add_memory("GenAI", key="learning", category="user_fact")
        memory_manager.add_memory("Jarvis OS", key="my current project", category="user_fact")
        memory_manager.add_memory("Python", key="my preferred programming language", category="user_fact")

    def test_personal_name_queries(self):
        """Verify all variations of asking for user's name reach memory and return correct spoken answer."""
        queries = [
            "What is my name?",
            "what is my name",
            "do you remember my name?",
            "can you tell me my name?",
            "do you know my name?",
            "what did I tell you about my name?",
            "tell me what my name is",
            "who am I?",
        ]
        for q in queries:
            res = brain.process_command(q)
            self.assertTrue(res["success"], f"Failed on query: {q}")
            self.assertIn("Ranjeet", res["spoken"], f"Expected 'Ranjeet' in spoken response for query: {q}")
            self.assertNotEqual(res.get("tool"), "search_web", f"Query {q} incorrectly routed to search_web!")

    def test_personal_learning_and_project_queries(self):
        """Verify queries about learning and projects route to memory."""
        res_learn = brain.process_command("What am I learning?")
        self.assertTrue(res_learn["success"])
        self.assertIn("GenAI", res_learn["spoken"])

        res_proj = brain.process_command("What is my current project?")
        self.assertTrue(res_proj["success"])
        self.assertIn("Jarvis OS", res_proj["spoken"])

    def test_personal_listing_queries(self):
        """Verify queries asking what jarvis remembers route to memory listing."""
        queries = [
            "What do you remember about me?",
            "What did I tell you to remember?",
            "What do you remember?",
        ]
        for q in queries:
            res = brain.process_command(q)
            self.assertTrue(res["success"])
            self.assertIn("I remember", res["spoken"])

    def test_activity_log_records_search_memory_not_search_web(self):
        """Verify that 'What is my name?' causes search_memory to be logged in activity logs, not search_web."""
        brain.process_command("What is my name?")
        recent = get_recent_activities(limit=5)
        tools_called = [r.get("tool") for r in recent]
        self.assertIn("search_memory", tools_called)
        self.assertNotIn("search_web", tools_called[:2])

    def test_fallback_router_memory_vs_web(self):
        """Verify the deterministic fallback router correctly distinguishes personal memory from web search."""
        tools = router.get_all_tools()

        # Personal memory questions MUST route to search_memory or recall
        plan_mem1 = llm_service._fallback_rule_router("what is my name?", tools)
        self.assertEqual(plan_mem1.get("tool_name"), "search_memory")

        plan_mem2 = llm_service._fallback_rule_router("do you remember my name?", tools)
        self.assertEqual(plan_mem2.get("tool_name"), "search_memory")

        plan_mem3 = llm_service._fallback_rule_router("what am I learning?", tools)
        self.assertEqual(plan_mem3.get("tool_name"), "search_memory")

        # Genuine web questions MUST route to search_web
        plan_web1 = llm_service._fallback_rule_router("latest AI news", tools)
        self.assertEqual(plan_web1.get("tool_name"), "search_web")

        plan_web2 = llm_service._fallback_rule_router("search the web for Python tutorials", tools)
        self.assertEqual(plan_web2.get("tool_name"), "search_web")

        plan_web3 = llm_service._fallback_rule_router("what is the weather today?", tools)
        self.assertEqual(plan_web3.get("tool_name"), "search_web")


if __name__ == "__main__":
    unittest.main()
