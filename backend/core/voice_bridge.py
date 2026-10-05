from backend.core.bridge import handle_user_command


def process_voice_command(command):
    """
    Receives text from Jarvis voice system
    and sends it to the new Jarvis Brain.
    """

    if not command:
        return "I didn't hear anything."

    command = command.strip()

    if not command:
        return "I didn't hear anything."

    return handle_user_command(command)
