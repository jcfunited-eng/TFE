"""Global pytest fixtures for Tao Financial Engine test suite."""

import sys
import pytest


@pytest.fixture(autouse=True)
def isolate_caretaker_environment(tmp_path, monkeypatch):
    """Isolate caretaker production log, state files, and network transport for all tests,
    preventing test ticks and mock events from contaminating production caretaker.log or
    accessing live network endpoints (REG-A1-06 closure)."""
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
                monkeypatch.setattr(mod, "BASE", "http://127.0.0.1:9/isolated-test-base", raising=False)
                # In-process sensory transport stubs by default so routines execute offline
                monkeypatch.setattr(mod, "sing_block", lambda pcm: {"observation": {"live_tick": 1, "last_occurrence": {"native_tick": 1}}}, raising=False)
                monkeypatch.setattr(mod, "say_word", lambda word: 1, raising=False)
        except (ImportError, KeyError):
            pass

    # Fail-closed network isolation across all tests: deny live HTTP requests
    def fail_closed_urlopen(req, *args, **kwargs):
        url = getattr(req, "full_url", req)
        raise RuntimeError(f"REG-A1-06 VIOLATION: Test attempted unmocked live network access to {url}")

    monkeypatch.setattr("urllib.request.urlopen", fail_closed_urlopen)
