# ADR 0001: Local-only library, no hosted database

## Status
Accepted

## Context
Expandr exists so snippets are not capped by a SaaS plan. A hosted database would reintroduce accounts, sync, and a service to operate.

## Decision
Store the library as `%AppData%\Expandr\library.json` on the machine that runs the app. Do not add a cloud backend.

## Consequences
Another PC does not see snippets until the user copies a library file. That is handled by the portable bundle in ADR 0004. Offline use stays simple.
