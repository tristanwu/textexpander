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

Do not install a real keyboard hook in tests. Drive `KeyboardEngine._handle_key` or pure functions.

## Architecture Decision Records

If a change picks a direction that later work should not casually undo, add a file under `docs/adr/` and link it from `docs/adr/README.md`. See that README for the template.

## Clean code

- One module, one job. File I/O for transfer lives in `expandr/transfer.py`; merge rules live on `Library`.
- Names say what the caller needs, not how Windows works, unless the module is the Win32 boundary.
- Prefer a small, named result (`ImportResult`) over a tuple of ints.
- Do not add a service, account, or database to move snippets between machines.
