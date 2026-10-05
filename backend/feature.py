# import playsound
# import eel


# @eel.expose
# def playAssistantSound():
#     music_dir = "frontend\\assets\\audio\\start_sound.mp3"
#     playsound(music_dir)


from compileall import compile_path
from openai import OpenAI
import os
import re
from shlex import quote
import struct
import subprocess
import time
import webbrowser
import eel 
import pvporcupine
import pyaudio
import pyautogui
import pywhatkit as kit
import pygame
from backend.command import speak
from backend.config import ASSISTANT_NAME, START_SOUND_PATH
import sqlite3

from backend.helper import extract_yt_term, remove_words
conn = sqlite3.connect("jarvis.db")
cursor = conn.cursor()
# Initialize pygame mixer safely
try:
    if not pygame.mixer.get_init():
        pygame.mixer.init()
except Exception as e:
    print(f"Warning: pygame mixer init error: {e}")

# Define the function to play sound
@eel.expose
def play_assistant_sound():
    try:
        sound_file = str(START_SOUND_PATH)
        if os.path.exists(sound_file):
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(sound_file)
            pygame.mixer.music.play()
    except Exception as e:
        print(f"play_assistant_sound error: {e}")
    
    
def openCommand(query):
    query = query.replace(ASSISTANT_NAME,"")
    query = query.replace("open","")
    query = query.lower()
    
    app_name = query.strip()

    if app_name != "":

        try:
            cursor.execute( 
                'SELECT path FROM sys_command WHERE name IN (?)', (app_name,))
            results = cursor.fetchall()

            if len(results) != 0:
                speak("Opening "+query)
                os.startfile(results[0][0])

            elif len(results) == 0: 
                cursor.execute(
                'SELECT url FROM web_command WHERE name IN (?)', (app_name,))
                results = cursor.fetchall()
                
                if len(results) != 0:
                    speak("Opening "+query)
                    webbrowser.open(results[0][0])

                else:
                    speak("Opening "+query)
                    try:
                        os.system('start '+query)
                    except:
                        speak("not found")
        except Exception as e:
                print(f"openCommand error: {e}")
                speak("Sorry, something went wrong")


def PlayYoutube(query):
    search_term = extract_yt_term(query)
    speak("Playing "+search_term+" on YouTube")
    kit.playonyt(search_term)


def _trigger_hotword_event():
    """
    Simulate Win+J keystroke to summon JARVIS UI without PyAutoGUI failsafe issues.
    """
    try:
        import ctypes
        user32 = ctypes.windll.user32
        VK_LWIN = 0x5B
        VK_J = 0x4A
        # Press Win+J
        user32.keybd_event(VK_LWIN, 0, 0, 0)
        user32.keybd_event(VK_J, 0, 0, 0)
        time.sleep(0.05)
        user32.keybd_event(VK_J, 0, 2, 0)
        user32.keybd_event(VK_LWIN, 0, 2, 0)
    except Exception as e:
        print(f"Hotword keystroke trigger failed: {e}")


def _fallback_speech_hotword():
    """
    Fallback hotword detection using SpeechRecognition when Porcupine access key is not set.
    """
    print("Hotword: Running speech recognition standby (say 'Jarvis')...")
    import speech_recognition as sr
    r = sr.Recognizer()
    r.pause_threshold = 0.8

    while True:
        try:
            with sr.Microphone() as source:
                r.adjust_for_ambient_noise(source, duration=0.5)
                audio = r.listen(source, timeout=6, phrase_time_limit=4)
            text = r.recognize_google(audio, language="en-US").lower()
            if "jarvis" in text or "alexa" in text:
                print(f"Hotword detected: '{text}'")
                _trigger_hotword_event()
                time.sleep(2)
        except (sr.WaitTimeoutError, sr.UnknownValueError):
            continue
        except Exception as e:
            time.sleep(1)


def hotword():
    """
    Continuous hotword detector. Uses Picovoice Porcupine if PORCUPINE_ACCESS_KEY is set,
    otherwise falls back to SpeechRecognition standby listener.
    """
    access_key = os.getenv("PORCUPINE_ACCESS_KEY")
    if not access_key:
        print("Notice: PORCUPINE_ACCESS_KEY not configured in .env.")
        _fallback_speech_hotword()
        return

    porcupine = None
    paud = None
    audio_stream = None
    try:
        porcupine = pvporcupine.create(access_key=access_key, keywords=["jarvis", "alexa"])
        paud = pyaudio.PyAudio()
        audio_stream = paud.open(
            rate=porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=porcupine.frame_length
        )

        print("Hotword: Porcupine engine active. Listening for 'Jarvis'...")
        while True:
            keyword = audio_stream.read(porcupine.frame_length, exception_on_overflow=False)
            keyword = struct.unpack_from("h" * porcupine.frame_length, keyword)
            keyword_index = porcupine.process(keyword)

            if keyword_index >= 0:
                print("Hotword detected via Porcupine!")
                _trigger_hotword_event()
                time.sleep(2)

    except Exception as e:
        print(f"Porcupine hotword warning ({e}). Switching to speech fallback.")
        _fallback_speech_hotword()
    finally:
        if porcupine is not None:
            porcupine.delete()
        if audio_stream is not None:
            audio_stream.close()
        if paud is not None:
            paud.terminate()


def findContact(query):
    
    words_to_remove = [ASSISTANT_NAME, 'make', 'a', 'to', 'phone', 'call', 'send', 'message', 'wahtsapp', 'video']
    query = remove_words(query, words_to_remove)

    try:
        query = query.strip().lower()
        cursor.execute("SELECT Phone FROM contacts WHERE LOWER(name) LIKE ? OR LOWER(name) LIKE ?", ('%' + query + '%', query + '%'))
        results = cursor.fetchall()
        print(results[0][0])
        mobile_number_str = str(results[0][0])

        if not mobile_number_str.startswith('+91'):
            mobile_number_str = '+91' + mobile_number_str

        return mobile_number_str, query
    except:
        speak('not exist in contacts')
        return 0, 0
    
    
def whatsApp(Phone, message, flag, name):
    

    if flag == 'message':
        target_tab = 12
        jarvis_message = "message send successfully to "+name

    elif flag == 'call':
        target_tab = 7
        message = ''
        jarvis_message = "calling to "+name

    else:
        target_tab = 6
        message = ''
        jarvis_message = "staring video call with "+name


    # Encode the message for URL
    encoded_message = quote(message)
    print(encoded_message)
    # Construct the URL
    whatsapp_url = f"whatsapp://send?phone={Phone}&text={encoded_message}"

    # Construct the full command
    full_command = f'start "" "{whatsapp_url}"'

    # Open WhatsApp with the constructed URL using cmd.exe
    subprocess.run(full_command, shell=True)
    time.sleep(5)
    subprocess.run(full_command, shell=True)
    
    pyautogui.hotkey('ctrl', 'f')

    for i in range(1, target_tab):
        pyautogui.hotkey('tab')

    pyautogui.hotkey('enter')
    speak(jarvis_message)


def chatBot(query):
    try:
        from backend.services.llm_service import llm_service
        answer = llm_service.generate_chat_response(query)
        eel.receiverText(answer)
        speak(answer)
        return answer
    except Exception as e:
        print(f"chatBot error: {e}")
        message = "Sorry, I could not answer that right now."
        eel.receiverText(message)
        speak(message)
        return message