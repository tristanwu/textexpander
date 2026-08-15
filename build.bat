@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  py -3 -m venv .venv
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip install pyinstaller
.venv\Scripts\python.exe -m pytest tests -q
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --noconsole --onefile --name Expandr --collect-all customtkinter expandr\__main__.py
echo.
echo Built: dist\Expandr.exe
echo Copy that file to any Windows laptop and double-click. No Python install required.
