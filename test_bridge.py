from backend.core.bridge import handle_user_command


commands = [
    "open calculator",
    "system info",
    "take screenshot"
]


for command in commands:

    print("\n==============================")
    print("USER:", command)
    print("==============================")

    result = handle_user_command(command)

    print("JARVIS:", result)
    