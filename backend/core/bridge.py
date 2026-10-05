from backend.core.brain import brain


def handle_user_command(command):
    if not command or not command.strip():
        return "Please provide a command."

    return brain.process_command(command.strip())