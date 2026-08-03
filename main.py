import eel
from backend.auth import recoganize
from backend.feature import *
from backend.command import *


def start():
    eel.init("frontend")

    play_assistant_sound()

    @eel.expose
    def init():
        eel.hideLoader()
        speak("Welcome to Jarvis")
        speak("Ready for Face Authentication")

        flag = recoganize.AuthenticateFace()

        if flag == 1:
            speak("Face recognized successfully")
            eel.hideFaceAuth()
            eel.hideFaceAuthSuccess()
            speak("Welcome to Your Assistant")
            eel.hideStart()
            play_assistant_sound()
        else:
            speak("Face not recognized. Please try again")

    eel.start(
        "index.html",
        mode="chrome",
        host="127.0.0.1",
        port=8000,
        block=True
    )


if __name__ == "__main__":
    start()