from pathlib import Path

import expandr.startup as startup


class _Key:
    def __init__(self, path):
        self.path = path

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class FakeWinreg:
    HKEY_CURRENT_USER = object()
    KEY_SET_VALUE = 1
    KEY_READ = 2
    REG_SZ = 1
    REG_BINARY = 3

    def __init__(self, values=None):
        self.values = values or {}

    def CreateKey(self, root, path):
        assert root is self.HKEY_CURRENT_USER
        self.values.setdefault(path, {})
        return _Key(path)

    def OpenKey(self, root, path, _reserved, access):
        assert root is self.HKEY_CURRENT_USER
        assert access in (self.KEY_SET_VALUE, self.KEY_READ)
        if path not in self.values:
            raise FileNotFoundError
        return _Key(path)

    def SetValueEx(self, key, name, _reserved, kind, value):
        assert kind in (self.REG_SZ, self.REG_BINARY)
        self.values[key.path][name] = value

    def DeleteValue(self, key, name):
        if name not in self.values[key.path]:
            raise FileNotFoundError
        del self.values[key.path][name]

    def QueryValueEx(self, key, name):
        try:
            return self.values[key.path][name], None
        except KeyError:
            raise FileNotFoundError


def _fake_windows(monkeypatch, tmp_path, *, values=None, frozen=False):
    registry = FakeWinreg(values)
    created = []
    startup_folder = tmp_path / "Startup"
    startup_folder.mkdir(exist_ok=True)
    scripts = tmp_path / ".venv" / "Scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    (scripts / "pythonw.exe").write_text("interpreter", encoding="utf-8")

    def fake_create(spec):
        created.append(spec)
        spec.path.write_text("shortcut", encoding="utf-8")
        return spec.path

    monkeypatch.setattr(startup, "winreg", registry)
    monkeypatch.setattr(startup, "startup_dir", lambda: startup_folder)
    monkeypatch.setattr(startup, "create_shortcut", fake_create)
    monkeypatch.setattr(startup, "write_ico", lambda path: path)
    monkeypatch.setattr(startup, "data_dir", lambda: tmp_path / "data")
    monkeypatch.setattr(startup, "is_frozen", lambda: frozen)
    monkeypatch.setattr(startup, "project_dir", lambda: Path(r"C:\code\TextExpander"))
    monkeypatch.setattr(startup.os, "environ", {"APPDATA": str(tmp_path / "AppData")})
    monkeypatch.setattr(startup.sys, "executable", str(scripts / "python.exe"))
    return registry, created


def test_startup_runs_an_exe_named_after_the_app_so_windows_lists_it_that_way(tmp_path, monkeypatch):
    registry, created = _fake_windows(monkeypatch, tmp_path)

    startup.set_start_with_windows(True)

    spec = created[0]
    assert Path(spec.target).name == "TextExpander.exe"
    assert Path(spec.target).exists()
    assert spec.arguments == "-m expandr"
    assert spec.working_directory == r"C:\code\TextExpander"
    assert registry.values[startup.APPROVED_KEY]["TextExpander.lnk"] == startup.ENABLED_VALUE


def test_launcher_copy_lives_beside_the_interpreter_that_has_the_packages(tmp_path, monkeypatch):
    _fake_windows(monkeypatch, tmp_path)

    launcher = startup.ensure_launcher_exe()

    assert launcher == tmp_path / ".venv" / "Scripts" / "TextExpander.exe"
    assert launcher.read_text(encoding="utf-8") == "interpreter"


def test_launcher_falls_back_to_the_interpreter_when_the_copy_fails(tmp_path, monkeypatch):
    _fake_windows(monkeypatch, tmp_path)

    def refuse(*_args, **_kwargs):
        raise OSError("locked")

    monkeypatch.setattr(startup.shutil, "copy2", refuse)

    assert startup.ensure_launcher_exe() == tmp_path / ".venv" / "Scripts" / "pythonw.exe"


def test_frozen_build_starts_its_own_executable(tmp_path, monkeypatch):
    _fake_windows(monkeypatch, tmp_path, frozen=True)
    exe = tmp_path / "dist" / "TextExpander.exe"
    monkeypatch.setattr(startup.sys, "executable", str(exe))

    assert startup.launch_target() == (str(exe), "", str(exe.parent))


def test_disabling_startup_keeps_the_entry_visible_in_task_manager(tmp_path, monkeypatch):
    registry, _ = _fake_windows(monkeypatch, tmp_path)

    startup.set_start_with_windows(False)

    assert startup.startup_shortcut().exists()
    assert registry.values[startup.APPROVED_KEY]["TextExpander.lnk"] == startup.DISABLED_VALUE
    assert startup.is_start_with_windows() is False


def test_registration_removes_the_old_batch_and_run_key_launchers(tmp_path, monkeypatch):
    values = {
        startup.RUN_KEY: {"TextExpander": "cmd.exe /d /c launcher.bat", "Expandr": "legacy"},
        startup.RUN_APPROVED_KEY: {"TextExpander": startup.ENABLED_VALUE},
    }
    registry, _ = _fake_windows(monkeypatch, tmp_path, values=values)
    for obsolete in startup.obsolete_launchers():
        obsolete.parent.mkdir(parents=True, exist_ok=True)
        obsolete.write_text("old launcher", encoding="utf-8")

    startup.set_start_with_windows(True)

    assert not any(path.exists() for path in startup.obsolete_launchers())
    assert registry.values[startup.RUN_KEY] == {}
    assert registry.values[startup.RUN_APPROVED_KEY] == {}


def test_existing_task_manager_choice_wins_over_the_saved_setting(tmp_path, monkeypatch):
    registry, created = _fake_windows(monkeypatch, tmp_path)
    startup.set_start_with_windows(True)
    created.clear()
    registry.values[startup.APPROVED_KEY] = {"TextExpander.lnk": startup.DISABLED_VALUE}

    assert startup.ensure_startup_registration(default_enabled=True) is False
    assert created == []


def test_registration_rewrites_a_shortcut_that_points_somewhere_stale(tmp_path, monkeypatch):
    _registry, created = _fake_windows(monkeypatch, tmp_path)
    startup.set_start_with_windows(True)
    created.clear()
    monkeypatch.setattr(startup, "project_dir", lambda: Path(r"D:\moved\TextExpander"))

    startup.ensure_startup_registration(default_enabled=True)

    assert created[0].working_directory == r"D:\moved\TextExpander"


def test_registration_defaults_to_the_saved_setting_when_unregistered(tmp_path, monkeypatch):
    registry, created = _fake_windows(monkeypatch, tmp_path)

    assert startup.ensure_startup_registration(default_enabled=True) is True
    assert len(created) == 1
    assert registry.values[startup.APPROVED_KEY]["TextExpander.lnk"] == startup.ENABLED_VALUE
