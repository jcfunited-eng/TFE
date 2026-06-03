@echo off
cd /d "%~dp0"
echo Checking dependencies...
python -m pip install pandas requests >nul 2>&1
cls
echo Starting Aurelion...
python aurelion_interface.py
pause
