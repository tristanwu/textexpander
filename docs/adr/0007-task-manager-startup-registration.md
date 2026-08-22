# ADR 0007: Task Manager startup registration

## Status
Accepted

## Context
A batch file in the user's Startup folder launches the app, but it does not give the app-style registration and control expected on Task Manager's Startup apps page.

Windows names a startup entry after the file it runs, and ignores both the shortcut name and the target's version info. A `Run` value invoking `cmd.exe` is therefore listed as `cmd`, and a shortcut to `pythonw.exe` is listed as `pythonw`, even though that file's description reads `Python`. Getting the app's own name on the entry means starting it from a file named `TextExpander.exe`. A source checkout also needs the repository as its working directory, which a `Run` value cannot express on its own.

## Decision
Register startup as a `TextExpander.lnk` shortcut in the current user's Startup folder, and store its enabled state in `Explorer\StartupApproved\StartupFolder` so a disabled entry stays visible and can be enabled from Task Manager.

The shortcut runs a file named `TextExpander.exe`. A packaged build already is that file. A source checkout copies the environment's `pythonw.exe` to `TextExpander.exe` beside the original, which keeps that environment's packages, and passes `-m expandr` with the repository as the working directory. The copy is refreshed when the interpreter is newer, so recreating the virtual environment repairs it, and a failed copy falls back to `pythonw.exe` so startup keeps working under a less useful name.

At launch, the app keeps Task Manager's current choice, updates its Settings switch to match, and rewrites the shortcut when the recorded launch target no longer matches. Earlier `Run` values and Startup-folder batch launchers are removed during migration.

## Consequences
TextExpander appears in Task Manager under its own name whether enabled or disabled, needs no administrator access, and has a single startup source. In a source checkout the running process is still the interpreter the copy delegates to, so the Processes page continues to group it under Python. Renaming the app means renaming that copy, and the copy lives with the virtual environment rather than in the repository.
