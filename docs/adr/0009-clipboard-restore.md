# ADR 0009: Restore the clipboard only if it is still ours

## Status
Accepted. Amends the restore sentence in [ADR 0003](0003-hook-and-clipboard-insert.md).

## Context
Insert places the snippet on the clipboard, sends Ctrl+V, then wrote the previous clipboard back after a fixed 0.25s (`RESTORE_S`). Two failures came from that:

- A copy the user made in that window was overwritten by the restore.
- A slow target could process Ctrl+V after the restore and paste the previous clipboard instead of the snippet.

Windows does not tell us when a target has read the clipboard. `GetClipboardSequenceNumber` changes only when something writes it.

## Decision
Remember the clipboard sequence number immediately after the snippet is placed.

Wait `RESTORE_AFTER_PASTE_S` (1.0s) after Ctrl+V before restoring, so a slow target usually reads the snippet first. The wait runs on the existing daemon thread; the UI thread does not block for it.

Restore the previous text only when the sequence number is still the one we recorded and the clipboard text is still the snippet. If either differs, leave the clipboard alone. That includes a copy of the same characters and a non-text copy. If the sequence cannot be read, compare text only at place time, and skip the restore if a later read fails.

If there was no previous text, do not write the clipboard back. If the clipboard cannot be set, keep the typed-Unicode fallback from ADR 0003.

Delayed rendering (`WM_RENDERFORMAT`) would learn the moment a target reads the clipboard, but it needs a clipboard-owner window on a message loop. That is a larger change than this release, so the bounded wait plus the ownership check is the contract.

## Consequences
A user copy during the one-second window is kept. Targets that paste within that second receive the snippet. A target slower than one second can still paste the restored clipboard; raise `RESTORE_AFTER_PASTE_S` if that shows up, rather than restoring unconditionally. The snippet remains on the clipboard for that whole second when the user does not copy.
