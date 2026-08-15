# ADR 0003: Wait-free keyboard hook and clipboard insert

## Status
Accepted

## Context
A low-level keyboard hook that does heavy work (`ToUnicodeEx`, file I/O, a non-reentrant lock) can freeze input and block Quit. Windows 11 Notepad also drops `KEYEVENTF_UNICODE` `SendInput`.

## Decision
The hook callback only posts a message and returns. Matching runs on the hook thread message loop with an `RLock`. Insert uses clipboard + Ctrl+V first; typed Unicode is a fallback. Mark Expandr's own `SendInput` with a private `dwExtraInfo` so we do not treat our paste as user typing.

## Consequences
US-layout virtual-key mapping covers the shortcuts we care about. Non-US layouts may need a later mapping pass. Clipboard paste briefly overwrites the clipboard; we restore it after a short delay.
