@echo off
title Aurelion Voice Process
echo Starting Aurelion...

REM Change directory to your Aurelion folder
cd /d "C:\Users\joeta\OneDrive\Desktop\Aurelion"

REM OPTIONAL: Activate environment if you ever use venv
REM call venv\Scripts\activate

echo Launching voice shell...
start "" python aurelion_voice_shell.py

echo Launching background orchestrator...
start "" python aurelion_master_orchestrator.py

echo Aurelion is now running.
echo You may close this window or minimize it.
pause >nul
