# ADR 0005: Start menu shortcut instead of an MSI installer

## Status
Accepted

## Context
Windows Search only lists apps that have a Start menu entry. A full MSI/MSIX installer would add signing, an installer UI, and another toolchain.

## Decision
Install is a Start menu `.lnk` named TextExpander. In development it launches `pythonw -m expandr` from the repo. A packaged `TextExpander.exe` points the same shortcut at itself. `install.bat` and Settings → Show in Start menu create it.

## Consequences
No Programs and Features uninstall entry. Removing the shortcut (or turning the setting off) is enough. Search can take a short time to index a new shortcut.
