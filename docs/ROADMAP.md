# Roadmap

TextExpander is at package version **v0.1.0**. This page is a short history of what shipped, then the planned milestones. The live backlog is [GitHub Issues](https://github.com/tristanwu/textexpander/issues) and [milestones](https://github.com/tristanwu/textexpander/milestones).

## History

**August 15, 2026.** The first commit added Expandr 0.1.0, a local Windows tray expander. The app is Python and CustomTkinter, with a PyInstaller build for a machine that has no Python ([ADR 0002](adr/0002-python-desktop-stack.md)). Snippets live in `%AppData%\Expandr\library.json` on that PC ([ADR 0001](adr/0001-local-only-library.md)). A low-level keyboard hook only posts a message and returns; matching runs on the hook thread, and expansion pastes through the clipboard, with typed Unicode as a fallback ([ADR 0003](adr/0003-hook-and-clipboard-insert.md)). Folders, snippets, triggers, and settings move between computers as a versioned JSON bundle, with CSV import and export for spreadsheets ([ADR 0004](adr/0004-portable-library-bundle.md)). Snippets include forms, dates, clipboard, and simple formulas.

The same day the product was renamed TextExpander. The Python package stayed `expandr`. A first launch migrates an older `%AppData%\Expandr` folder into `%AppData%\TextExpander`. Install is a Start menu shortcut from `install.bat` or Settings, so Windows Search can find the app ([ADR 0005](adr/0005-start-menu-shortcut.md)).

**August 22, 2026.** Settings gained **Create backup** and **Restore from backup**. A backup is a timestamped library bundle under `backups/`, committed on its own and left for the user to push ([ADR 0006](adr/0006-git-backed-library-backups.md)). Startup registration became a `TextExpander.lnk` in the user Startup folder, so Task Manager lists it under the app name and can enable or disable it ([ADR 0007](adr/0007-task-manager-startup-registration.md)). Optional typing sessions were added beside the expander: off until Start, tagged by app, stored under `%AppData%\TextExpander\sessions`, and kept out of `library.json` ([ADR 0008](adr/0008-local-typing-sessions.md)).

Later that day, an unreadable `library.json` started being moved aside and replaced with a new library, with a warning that names the quarantined file. The Sessions window and `transcript.md` started omitting empty chunks and leaving the session files unchanged.

**September 1, 2026.** First library backup committed: `backups/textexpander-library-20260901-235426.json`.

**October 22, 2026.** Second library backup committed: `backups/textexpander-library-20261022-085039.json`. The library window and Settings were then tightened: a toolbar for Settings, Sessions, and Quit, folder-grouped snippet rows, and tests for that layout. That is the current v0.1.0 tree.

## Roadmap

### v0.1.1 — Reliability fixes

- Fix the `/grillme` shortcut not expanding.
- Fix the clipboard restore race in insert.
- Add better hook and insert tests.

### v0.2.0 — Release pipeline

- Run pytest in GitHub Actions.
- Pin dependencies and split development dependencies from the runtime list.
- Publish tagged releases with `TextExpander.exe` attached.
- Turn on branch protection and a pull-request workflow.

### v0.3.0 — Safety & polish

- Support non-US keyboard layouts.
- Harden typing sessions.
- Clean up startup registration and packaging.
