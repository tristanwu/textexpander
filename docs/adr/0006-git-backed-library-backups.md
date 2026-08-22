# ADR 0006: Git-backed library backups

## Status
Accepted

## Context
The live library belongs in `%AppData%\TextExpander\library.json`, but a source checkout needs a simple way to preserve library revisions and carry them to another computer without adding a database or hosted service.

## Decision
Settings provides **Create backup**, which writes a timestamped portable library bundle under the repository's `backups/` directory and creates a Git commit containing only that file. It does not automatically push.

**Restore from backup** starts in that directory and replaces the local snippets from the selected bundle. Machine-only settings keep the same import behavior defined in ADR 0004.

Repository discovery uses Git, so these actions report an error when TextExpander is not running from a checkout or Git is unavailable. Normal export and import remain available for packaged copies.

## Consequences
Backups are readable JSON with Git history and can move between computers through the existing repository remote after the user pushes them. Creating a backup requires Git author identity to be configured. Unrelated staged or working-tree changes are excluded from the backup commit.
