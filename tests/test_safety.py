import pytest

from jarvis.config import Settings
from jarvis.safety import SafetyError, assert_safe_command, assert_safe_path


def test_blocks_rm():
    settings = Settings(allowed_bins=["rm"], forbidden_patterns=["rm -rf"])
    with pytest.raises(SafetyError):
        assert_safe_command("rm -rf /", settings)


def test_blocks_bin_not_whitelisted():
    settings = Settings(allowed_bins=["firefox"], forbidden_patterns=[])
    with pytest.raises(SafetyError):
        assert_safe_command("nmap 1.1.1.1", settings)


def test_safe_path_home(tmp_path, monkeypatch):
    monkeypatch.setattr("jarvis.safety.HOME", tmp_path)
    path = assert_safe_path(str(tmp_path / "a.txt"))
    assert path == (tmp_path / "a.txt").resolve()
