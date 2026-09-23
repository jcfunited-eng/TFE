"""Global pytest fixtures for Tao Financial Engine test suite."""

import sys
import pytest


@pytest.fixture(autouse=True)
def isolate_caretaker_logs_and_state(tmp_path, monkeypatch):
    """Isolate caretaker production log and state files to tmp_path for all tests,
    preventing test ticks and mock events from contaminating production caretaker.log."""
    test_log = str(tmp_path / "test_caretaker.log")
    test_state = str(tmp_path / "test_state.json")
    for mod_name in ("guala_caretaker.caretaker", "caretaker"):
        try:
            mod = sys.modules.get(mod_name)
            if mod is None:
                __import__(mod_name)
                mod = sys.modules.get(mod_name)
            if mod is not None:
                monkeypatch.setattr(mod, "LOG", test_log, raising=False)
                monkeypatch.setattr(mod, "STATE", test_state, raising=False)
        except (ImportError, KeyError):
            pass
