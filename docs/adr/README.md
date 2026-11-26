# Architecture Decision Records

ADRs capture a choice we made and why, so the next change does not relitigate it by accident.

Write a new ADR when a decision is costly to reverse: storage, packaging, input injection, or how libraries move between machines.

## Template

```md
# ADR NNNN: Title

## Status
Accepted

## Context
What problem and constraints forced a choice.

## Decision
What we will do.

## Consequences
What becomes easier, harder, or off-limits.
```

## Index

- [0001 — Local-only library, no hosted database](0001-local-only-library.md)
- [0002 — Python desktop app packaged as one exe](0002-python-desktop-stack.md)
- [0003 — Wait-free keyboard hook and clipboard insert](0003-hook-and-clipboard-insert.md)
- [0004 — Portable library bundle instead of a hosted DB](0004-portable-library-bundle.md)
- [0005 — Start menu shortcut instead of an MSI installer](0005-start-menu-shortcut.md)
- [0006 — Git-backed library backups](0006-git-backed-library-backups.md)
- [0007 — Task Manager startup registration](0007-task-manager-startup-registration.md)
- [0008 — Local typing sessions beside the expander](0008-local-typing-sessions.md)
- [0009 — Restore the clipboard only if it is still ours](0009-clipboard-restore.md)
- [0010 — Pause is visible, tray-only, and not sticky](0010-pause-is-visible-and-not-sticky.md)
