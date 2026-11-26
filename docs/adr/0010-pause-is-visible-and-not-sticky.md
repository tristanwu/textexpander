# ADR 0010: Pause is visible, tray-only, and not sticky

## Status
Accepted

## Context
`/grillme` stopped expanding because `library.json` had `"paused": true`. The low-level hook treated Ctrl+Shift+P as "toggle pause" and the flag was saved with the library, so it survived restart. Ctrl+Shift+P is also the command palette in editors, so the chord is easy to hit while typing the shortcuts the expander is for. Nothing in the tray showed that expansion was off, beyond a tooltip suffix of "expansion paused".

## Decision
The hook does not bind a pause chord. Pause and resume are the tray menu items that already existed. Ctrl+Shift+/ still opens search.

Pause is in memory for this process. `load_library` clears a saved `paused: true` and rewrites `library.json` when that write succeeds. If the rewrite fails, expansion is still on for this launch. While the app is running, toggling pause still saves the flag so the file matches the current process; the next launch clears it again.

The tray icon is amber with a pause glyph while expansion is paused, and the tooltip includes `EXPANSION PAUSED`. Toggling pause shows a notification. If a launch cleared a saved pause, the tray shows that once when the icon is ready. A session's own pause is unchanged and still does not pause expansion ([ADR 0008](0008-local-typing-sessions.md)).

`pause_hotkey` stays in the JSON so existing libraries keep loading. It is not bound.

## Consequences
Opening a command palette no longer stops expansion. Quitting while paused, or a crash while paused, comes back with expansion on. Someone who wanted pause to survive a restart uses the tray after each launch. [ADR 0004](0004-portable-library-bundle.md) still unpauses on import replace; launch now unpauses as well.
