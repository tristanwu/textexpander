# ADR 0004: Portable library bundle instead of a hosted DB

## Status
Accepted

## Context
There is no hosted database (ADR 0001). The user still needs to move folders, snippets, triggers, and disabled-app settings to another laptop after cloning the repo or copying `TextExpander.exe`.

CSV (`folder,label,shortcut,content`) is useful for spreadsheets but drops trigger mode, enabled flags, and settings.

## Decision
The primary transfer format is a tagged JSON bundle:

```json
{ "format": "expandr-library", "version": 1, "library": { ... } }
```

Import also accepts a raw `%AppData%\TextExpander\library.json`. Replace swaps snippets on this PC. Merge updates by snippet id (or same shortcut in the same folder) and keeps snippets the file does not mention. Machine-only flags (`paused`, `seen_coach`, `start_with_windows`) are not overwritten on replace except that import always unpauses.

CSV import/export stays as a secondary spreadsheet path.

## Consequences
A single file is enough to set up a new PC. Users can also copy `library.json` by hand. Schema changes must bump `version` and keep reading version 1. A saved `paused` flag is cleared on the next launch ([ADR 0010](0010-pause-is-visible-and-not-sticky.md)); import replace still unpauses.
