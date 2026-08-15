# Expandr

A local Windows text expander. No account, no subscription, no 20-snippet cap, no 2,500-character cap.

Type a shortcut like `/ty` in any app. Expandr replaces it with your snippet. Forms, dates, and simple formulas work. Everything lives in `%AppData%\Expandr\library.json` on your machine.

## New laptop (no Python, no .NET)

1. Build once on a machine that has Python: double-click `build.bat`.
2. Copy `dist\Expandr.exe` to the new laptop.
3. Double-click `Expandr.exe`.

That is the whole install. Optional: Settings → **Start with Windows**.

## This machine (development)

Double-click `run.bat`. It creates a local `.venv` if needed and starts Expandr in the tray.

Or:

```bat
py -3 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m expandr
```

## How to use

- **Type a shortcut** at the start of a word (`/ty`, `/sig`, `/date`, `/meet`, `/long`). Shortcuts need 2+ characters.
- **Search:** `Ctrl+Shift+/`
- **Pause:** `Ctrl+Shift+P`
- **Tray icon:** open the library or quit. The library does not open on launch.
- **Move to another PC:** Settings → **Export library**. Copy the JSON file to the new laptop, run Expandr, Settings → **Import library**. Choose replace on a fresh install, or merge to keep snippets already on that PC. A raw `%AppData%\Expandr\library.json` also imports.
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

## Why this stack

A fresh Windows laptop should not need Visual Studio, a .NET SDK, or a global Python install. Expandr is written in Python so it is easy to change, then packaged with PyInstaller into one `.exe` the laptop can run as-is.
