from backend.core.brain import brain
from backend.memory.memory_manager import memory_manager

commands = [
    "Jarvis, please open notepad for me",
    "check my system status and ram",
    "minimize all windows",
    "remember that my preferred programming language is Python",
    "what do you remember",
    "search the web for artificial intelligence",
]

print("\n==============================")
print("TESTING JARVIS COGNITIVE BRAIN")
print("==============================")

for command in commands:
    print("\n------------------------------")
    print("USER INPUT:", command)
    print("------------------------------")
    result = brain.process_command(command)
    print("SUCCESS:   ", result.get("success"))
    print("SPOKEN:    ", result.get("spoken"))
    print("TOOL USED: ", result.get("tool"))
    if result.get("data"):
        data_preview = str(result["data"])
        if len(data_preview) > 100:
            data_preview = data_preview[:100] + "..."
        print("DATA:      ", data_preview)

print("\n------------------------------")
print("RECENT CONVERSATION IN MEMORY:")
print("------------------------------")
for item in memory_manager.get_recent_conversation(limit=4):
    print(f"[{item['role'].upper()}]: {item['content']}")