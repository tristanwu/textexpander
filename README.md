# TextExpander

A local Windows text expander. No account, no subscription, no 20-snippet cap, no 2,500-character cap.

Type a shortcut like `/ty` in any app. TextExpander replaces it with your snippet. Forms, dates, and simple formulas work. Everything lives in `%AppData%\TextExpander\library.json` on your machine.

## What to click

| File | What it does |
| --- | --- |
| `run.bat` | Starts the app on this PC (tray). Use this after Quit. |
| `install.bat` | Adds **TextExpander** to the Start menu so Windows Search can find it. Does not build an `.exe`. |
| `build.bat` | Packages `dist\TextExpander.exe` for another laptop that has no Python. |

## This machine

1. Double-click `run.bat` to start it.
2. Double-click `install.bat` once (or Settings → **Show in Start menu / search**).
3. Search Windows for **TextExpander**.

```bat
py -3 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m expandr
```

## New laptop (no Python)

1. On a machine with Python, double-click `build.bat`.
2. Copy `dist\TextExpander.exe` to the new laptop.
3. Double-click `TextExpander.exe`, then Settings → **Show in Start menu / search**.

Optional: **Start with Windows**.

## How to use

- **Type a shortcut** at the start of a word (`/ty`, `/sig`, `/date`, `/meet`, `/long`). Shortcuts need 2+ characters.
- **Search:** `Ctrl+Shift+/`
- **Pause:** `Ctrl+Shift+P`
- **Tray icon:** open the library or quit. The library does not open on launch.
- **Move to another PC:** Settings → **Export library**. Copy the JSON file to the new laptop, run TextExpander, Settings → **Import library**. Choose replace on a fresh install, or merge to keep snippets already on that PC. A raw `%AppData%\TextExpander\library.json` also imports.
- **Settings:** disabled apps, folder trigger, CSV import/export for spreadsheets (`folder,label,shortcut,content`).

### Commands (Text Blaze-style)

```
{time: YYYY-MM-DD}
{time: MMMM D, YYYY; shift=+3D}
{clipboard}
{cursor}
{formtext: name=name; default=Jane}
{formparagraph: name=notes}
{formmenu: A; B; C; name=choice}
{formdate: YYYY-MM-DD; name=when}
{formtoggle: name=extra; default=no}optional line{endformtoggle}
{if: price > 10}expensive{else}cheap{endif}
{= price * 1.1}
{note}hidden helper{endnote}
{import: /sig}
```

## Development

```bat
.venv\Scripts\python.exe -m pytest
```

Write the failing test first. Decisions that should stick go in `docs/adr/`. See `CONTRIBUTING.md`.

The Python package is still `expandr` (`python -m expandr`). The name you see in the tray and Start menu is TextExpander.

## Why this stack

A fresh Windows laptop should not need Visual Studio, a .NET SDK, or a global Python install. TextExpander is written in Python so it is easy to change, then packaged with PyInstaller into one `.exe` the laptop can run as-is.
