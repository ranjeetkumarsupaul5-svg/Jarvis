from backend.core.router import router


print("\n==============================")
print("AVAILABLE JARVIS TOOLS")
print("==============================")

for tool in router.list_tools():
    print("-", tool)


print("\n==============================")
print("TEST 1: SYSTEM INFO")
print("==============================")

result = router.execute("get_system_info")
print(result)


print("\n==============================")
print("TEST 2: OPEN NOTEPAD")
print("==============================")

result = router.execute("open_application", "notepad")
print(result)


print("\n==============================")
print("TEST 3: TERMINAL")
print("==============================")

result = router.execute("run_command", "python --version")
print(result)


print("\n==============================")
print("TEST 4: WEB TOOL")
print("==============================")

result = router.execute("search_web", "artificial intelligence")
print(result)