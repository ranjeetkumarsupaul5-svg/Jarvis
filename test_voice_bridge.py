from backend.core.voice_bridge import process_voice_command


commands = [
    "open notepad",
    "system info",
    "take screenshot",
    "minimize windows"
]


for command in commands:

    print("\n==============================")
    print("VOICE COMMAND:", command)
    print("==============================")

    response = process_voice_command(command)

    print("JARVIS:", response)