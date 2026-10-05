from backend.tools.terminal_tools import (
    run_command,
    is_dangerous
)


print("\n--- TEST 1: Python version ---")
print(run_command("python --version"))


print("\n--- TEST 2: Current directory ---")
print(run_command("cd"))


print("\n--- TEST 3: List files ---")
print(run_command("dir"))


print("\n--- TEST 4: Dangerous command check ---")
print(is_dangerous("shutdown /s /t 0"))


print("\n--- TEST 5: Dangerous command ---")
print(run_command("shutdown /s /t 0"))