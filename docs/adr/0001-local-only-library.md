# ADR 0001: Local-only library, no hosted database

## Status
Accepted

## Context
TextExpander exists so snippets are not capped by a SaaS plan. A hosted database would reintroduce accounts, sync, and a service to operate.

## Decision
Store the library as `%AppData%\TextExpander\library.json` on the machine that runs the app. Do not add a cloud backend. A first launch migrates `%AppData%\Expandr` if that older folder is present.

## Consequences
Another PC does not see snippets until the user copies a library file. That is handled by the portable bundle in ADR 0004. Offline use stays simple.
