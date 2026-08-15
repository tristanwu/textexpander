@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  py -3 -m venv .venv
  .venv\Scripts\python.exe -m pip install -r requirements.txt
)
.venv\Scripts\python.exe -m expandr.install
if errorlevel 1 exit /b 1
echo.
echo TextExpander is in the Start menu. Search for TextExpander, then pin it if you want.
echo Double-click run.bat anytime to start it from this folder.
