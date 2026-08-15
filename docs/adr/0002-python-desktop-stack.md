# ADR 0002: Python desktop app packaged as one exe

## Status
Accepted

## Context
A new Windows laptop should run TextExpander without Visual Studio, a .NET SDK, or a global Python install. The code should stay easy to change.

## Decision
Implement the app in Python with CustomTkinter. Ship a single `TextExpander.exe` via PyInstaller. Development uses `run.bat` and a project venv. The import package stays `expandr`.

## Consequences
Windows-only is enough for this product. Startup is a tray process, not a web UI. Native hooks and SendInput stay in one process.
