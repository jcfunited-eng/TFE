#!/usr/bin/env python3
"""
Start Aurelion — background loop + voice shell.
"""

import os, subprocess, time, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VOICE = ROOT / "aurelion_voice_shell.py"

def run_voice_shell():
    subprocess.Popen([sys.executable, str(VOICE)], cwd=str(ROOT))

def main_loop():
    print("Aurelion background loop starting...")
    while True:
        # placeholder for periodic updates (reflective diary, NCF, etc.)
        time.sleep(300)  # every 5 minutes
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        with open(ROOT/"logs"/"daemon.log","a",encoding="utf-8") as f:
            f.write(f"[{ts}] background heartbeat\n")

if __name__ == "__main__":
    run_voice_shell()
    try:
        main_loop()
    except KeyboardInterrupt:
        print("Stopped.")
