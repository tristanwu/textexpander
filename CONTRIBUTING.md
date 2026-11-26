# Contributing

## Test-driven development

Change behavior by writing a failing test first, then the smallest code that passes, then rename for clarity.

```bat
.venv\Scripts\python.exe -m pytest
```

Put tests next to the behavior, not the UI:

| Behavior | Tests |
| --- | --- |
| Matching | `tests/test_matcher.py` |
| Snippet language | `tests/test_parser.py` |
| Library transfer | `tests/test_transfer.py` |
| CSV interop | `tests/test_csv_io.py` |
| Key mapping | `tests/test_hook_chars.py` |
| Engine match path | `tests/test_engine.py` |
| Start menu install | `tests/test_install.py` |
| Windows startup registration | `tests/test_startup.py` |
| Repository backups | `tests/test_backup.py` |
| Library load/save | `tests/test_store.py` |
| Expand orchestration | `tests/test_expand.py` |
| Clipboard insert | `tests/test_insert.py` |
| Pause and tray state | `tests/test_pause.py` |
| Session filters | `tests/test_session_filters.py` |
| Session store | `tests/test_session_store.py` |
| Session writer | `tests/test_session_engine.py` |
| Snippet list rows | `tests/test_listing.py` |
| Settings and library layout | `tests/test_window_layout.py` |

Do not install a real keyboard hook in tests. Drive `KeyboardEngine._handle_key` or pure functions.

## Architecture Decision Records

If a change picks a direction that later work should not casually undo, add a file under `docs/adr/` and link it from `docs/adr/README.md`. See that README for the template.

## Clean code

- One module, one job. File I/O for transfer lives in `expandr/transfer.py`; merge rules live on `Library`.
- Names say what the caller needs, not how Windows works, unless the module is the Win32 boundary.
- Prefer a small, named result (`ImportResult`) over a tuple of ints.
- Do not add a service, account, or database to move snippets between machines.
