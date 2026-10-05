import sys
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from backend.memory.memory_manager import memory_manager
from backend.core.brain import brain
from backend.core.router import router


class TestMemorySystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Clean up any leftover test data
        memory_manager.delete_memory(key="test_unit_key")
        memory_manager.delete_memory(query="Ranjeet")
        memory_manager.delete_memory(query="GenAI")

    def test_01_add_and_get_memory(self):
        """Test adding memory and retrieving it by ID."""
        res = memory_manager.add_memory(
            fact="Python is my favorite language",
            category="preference",
            importance=3,
            user_id="user_1",
            key="test_unit_key"
        )
        self.assertTrue(res["success"])
        self.assertIn("data", res)
        mem = res["data"]
        self.assertEqual(mem["key"], "test_unit_key")
        self.assertEqual(mem["category"], "preference")
        self.assertEqual(mem["importance"], 3)
        self.assertEqual(mem["user_id"], "user_1")
        self.assertIn("memory_id", mem)
        self.assertIn("created_at", mem)

        # Retrieve by memory_id
        fetched = memory_manager.get_memory(mem["memory_id"])
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["memory_id"], mem["memory_id"])
        self.assertEqual(fetched["value"], "Python is my favorite language")

    def test_02_update_memory(self):
        """Test updating an existing memory record."""
        # Find the test memory
        matches = memory_manager.search_memory("test_unit_key")
        self.assertTrue(len(matches) > 0)
        mem_id = matches[0]["memory_id"]

        # Update importance and fact
        up_res = memory_manager.update_memory(
            memory_id=mem_id,
            fact="Python 3.12 is my absolute favorite language",
            importance=5
        )
        self.assertTrue(up_res["success"])
        self.assertEqual(up_res["data"]["importance"], 5)
        self.assertIn("Python 3.12", up_res["data"]["value"])

    def test_03_search_and_list_memory(self):
        """Test keyword search and listing with filters."""
        # Search exact
        results = memory_manager.search_memory("favorite language")
        self.assertTrue(len(results) > 0)
        self.assertIn("Python", results[0]["value"])

        # List memories with category filter
        cat_memories = memory_manager.list_memories(category="preference")
        self.assertTrue(len(cat_memories) > 0)
        self.assertTrue(all(m["category"] == "preference" for m in cat_memories))

    def test_04_delete_memory(self):
        """Test deleting memory by key."""
        del_res = memory_manager.delete_memory(key="test_unit_key")
        self.assertTrue(del_res["success"])

        # Verify it no longer exists
        matches = memory_manager.search_memory("test_unit_key")
        self.assertEqual(len(matches), 0)

    def test_05_natural_commands_flow(self):
        """
        Test the complete natural commands flow required:
        1. Remember that my name is Ranjeet.
        2. Remember that I am learning GenAI.
        3. What is my name?
        4. What am I learning?
        5. Forget that my name is Ranjeet.
        """
        # Step 1: Remember that my name is Ranjeet.
        cmd1 = "Remember that my name is Ranjeet."
        res1 = brain.process_command(cmd1)
        self.assertTrue(res1["success"])
        self.assertIn("Ranjeet", res1["spoken"])
        self.assertEqual(res1["tool"], "remember")

        # Step 2: Remember that I am learning GenAI.
        cmd2 = "Remember that I am learning GenAI."
        res2 = brain.process_command(cmd2)
        self.assertTrue(res2["success"])
        self.assertIn("GenAI", res2["spoken"])
        self.assertEqual(res2["tool"], "remember")

        # Step 3: What is my name?
        cmd3 = "What is my name?"
        res3 = brain.process_command(cmd3)
        self.assertTrue(res3["success"])
        self.assertIn("Ranjeet", res3["spoken"])
        self.assertEqual(res3["tool"], "recall")

        # Step 4: What am I learning?
        cmd4 = "What am I learning?"
        res4 = brain.process_command(cmd4)
        self.assertTrue(res4["success"])
        self.assertIn("GenAI", res4["spoken"])
        self.assertEqual(res4["tool"], "recall")

        # Step 5: Forget that my name is Ranjeet.
        cmd5 = "Forget that my name is Ranjeet."
        res5 = brain.process_command(cmd5)
        self.assertTrue(res5["success"])
        self.assertIn("forgotten", res5["spoken"].lower())
        self.assertEqual(res5["tool"], "forget")

        # Step 6: Verify name is now forgotten
        res6 = brain.process_command("What is my name?")
        self.assertNotIn("Ranjeet", res6["spoken"])
        self.assertIn("do not have", res6["spoken"].lower())

        # Clean up learning memory
        brain.process_command("Forget that I am learning GenAI.")

    def test_06_casual_conversation_not_stored_in_memory(self):
        """Verify that normal conversations do NOT pollute long-term persistent memory."""
        before_count = len(memory_manager.list_memories())

        # Casual conversations
        brain.process_command("Hello Jarvis, how are you doing today?")
        brain.process_command("What is the weather like outside?")
        brain.process_command("Tell me a funny joke.")

        after_count = len(memory_manager.list_memories())
        self.assertEqual(before_count, after_count, "Casual conversation should not be added to memory table.")

    def test_07_router_memory_tools(self):
        """Verify that memory tools execute properly through the router."""
        # Add memory via router
        add_res = router.execute("add_memory", fact="The sky is blue", key="sky_color")
        self.assertTrue(add_res["success"])

        # Search memory via router
        search_res = router.execute("search_memory", query="sky")
        self.assertTrue(len(search_res) > 0)
        self.assertEqual(search_res[0]["key"], "sky_color")

        # Delete memory via router
        del_res = router.execute("delete_memory", key="sky_color")
        self.assertTrue(del_res["success"])


if __name__ == "__main__":
    unittest.main()
