#!/usr/bin/env python3
"""
Aurelion Voice Shell — Connected to Unified Brain
Fixed version: properly sends text to think(), no parroting.
"""

import speech_recognition as sr
import pyttsx3
import time
from pathlib import Path

from aurelion_master_orchestrator import think, DIALOGUE_LOG

ROOT = Path(__file__).resolve().parent
VOICE_AUTH_PHRASE = "verify daddy"

# --------------- VOICE OUTPUT ---------------

def speak(text):
    engine = pyttsx3.init()
    engine.setProperty('rate', 170)
    engine.say(text)
    engine.runAndWait()

# --------------- LISTEN ---------------

def listen_once(timeout=10):
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("(listening...)")
        try:
            audio = r.listen(source, timeout=timeout, phrase_time_limit=6)
        except Exception:
            return ""
    try:
        text = r.recognize_google(audio)
        print(f"(heard): {text}")
        return text.strip()
    except Exception:
        return ""

# --------------- AUTH CHECK ---------------

def owner_verified():
    if not DIALOGUE_LOG.exists():
        return False
    lines = DIALOGUE_LOG.read_text(encoding="utf-8").splitlines()[-10:]
    return any("owner session started" in ln.lower() for ln in lines)

def mark_owner_session():
    DIALOGUE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(DIALOGUE_LOG,"a",encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ')} [AUTH] owner session started\n")

# --------------- MAIN LOOP ---------------

def chat_loop():
    speak("Aurelion Voice Shell connected. Say Verify Daddy to begin.")

    while True:
        print("You may speak or type (/quit to exit).")

        # typed input takes priority
        try:
            text = input("You: ").strip()
        except EOFError:
            break

        # if nothing typed, try microphone
        if not text:
            text = listen_once()

        if not text:
            continue

        # quit
        if text.lower() in ("/quit","quit","exit"):
            speak("Goodbye Joseph.")
            break

        # authentication
        if VOICE_AUTH_PHRASE in text.lower():
            mark_owner_session()
            speak("Identity verified. Hello Joseph.")
            continue

        if not owner_verified():
            speak("Please say Verify Daddy first.")
            continue

        # *** THIS IS THE KEY FIX ***
        # CALL INTO THE UNIFIED BRAIN
        reply = think(text)

        # RETURN THE REAL REPLY
        speak(reply)


if __name__ == "__main__":
    chat_loop()
