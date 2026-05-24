@echo off
echo WARNING: Do not run this if the bot is already on Render.com!
echo Press Ctrl+C to cancel, or any key to start LOCAL bot only...
pause >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set PYTHONPATH=%~dp0
cd /d "%~dp0"
echo Starting Tutkafinder_bot...
"C:\Users\drozd\AppData\Local\Programs\Python\Python312\python.exe" -u bot_standalone.py
pause
