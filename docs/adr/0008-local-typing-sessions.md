# ADR 0008: Local typing sessions beside the expander

## Status
Accepted

## Context
The expander is always on and already owns one wait-free `WH_KEYBOARD_LL` hook (ADR 0003). The founder wants an optional trail of their own typing, tagged by app, so they can review vibe-coding prompt patterns later. That data must not live in `library.json` (ADR 0001 / 0004) and must not start when Windows starts.

## Decision
Sessions is a separate module with its own Start / Stop / Pause. Expansion is never started, stopped, or paused by a session. A session is off until Start, and Quit or crash ends only the session.

Recording is a side channel on the existing hook: `on_key` enqueues `vk`, `mods`, and hwnd with `put_nowait`. The writer thread resolves the exe name, maps characters as a best-effort US/Latin VK trail, and appends JSONL under `%AppData%\TextExpander\sessions\`. Events are the source of truth; chunks are a projection. Export writes `transcript.md`. Paste and expander use are markers only. Token-shaped secrets are masked on write.

`shutdown()` stops the session (drain, flush, join) before `engine.stop()`. An orphan session is repaired to `ended_reason: quit` and does not resume.

## Consequences
The expander stays the always-on product. Long in-process sessions are durable. IME and non-US layouts are not accurate in v1. Window titles and clipboard bodies stay out. Antivirus may still treat the hook as keyboard access; the UI never calls this a keylogger.
