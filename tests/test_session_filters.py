from expandr.session.filters import chunk_has_content, default_skip_apps, mask_secrets, should_record


def test_skip_list_blocks_password_managers():
    skip = default_skip_apps()
    assert should_record("KeePass.exe", skip, live=True, paused=False) is False
    assert should_record("1Password.exe", skip, live=True, paused=False) is False


def test_own_exe_is_skipped():
    skip = default_skip_apps()
    assert should_record("TextExpander.exe", skip, live=True, paused=False) is False


def test_no_live_session_records_nothing():
    assert should_record("cursor.exe", [], live=False, paused=False) is False


def test_paused_session_records_nothing():
    assert should_record("cursor.exe", [], live=True, paused=True) is False


def test_allowed_app_records_when_live():
    assert should_record("cursor.exe", default_skip_apps(), live=True, paused=False) is True


def test_mask_secrets_hides_token_shapes():
    text = "use sk-abc1234567890 and ghp_abcdefghij and AKIAIOSFODNN7"
    masked = mask_secrets(text)
    assert "sk-abc" not in masked
    assert "ghp_" not in masked
    assert "AKIA" not in masked
    assert masked.count("[hidden]") == 3


def test_chunk_has_content_ignores_blank_text():
    assert chunk_has_content({"text": "hello"}) is True
    assert chunk_has_content({"text": "[paste]"}) is True
    assert chunk_has_content({"text": ""}) is False
    assert chunk_has_content({"text": "   \n"}) is False

