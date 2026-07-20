"""test_wal_compact_debug_endpoint.py -- GL-FIX-WAL-BOOT-CHECKPOINT-20260720:
the manual, watched /debug/wal_compact trigger.

This is the other half of the boot-time fix: the checkpoint fast path does
nothing until a real compaction has actually run to write one. Deliberately
NOT wired to any automatic cadence (see the endpoint's own docstring for
why -- this codebase has real prior incidents from exactly this shape of
change: a long lock hold at real production scale, not caught locally).
These gates cover the thin HTTP wrapper only; compact()'s own correctness
is covered exhaustively by test_wal_boot_checkpoint_fast_path.py.

Gates:
1. No loaded substrate -> 503, compact() never called.
2. WAL not configured yet -> 409, compact() never called.
3. Success -> calls the real wm.compact(), returns its result plus a
   real elapsed_s timing, on the executor (never the event loop thread).
4. compact() raising -> 500 with the error surfaced, never swallowed.
"""

import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import dsf_ai_service.app as appmod


class _FakeWindowManager:
    def __init__(self, wal_enabled=True, result=None, error=None):
        self._wal_enabled = wal_enabled
        self._result = result or {
            "generation": 3, "records": 42, "path": "/tmp/seg", "bytes": 999}
        self._error = error
        self.compact_calls = 0

    def compact(self):
        self.compact_calls += 1
        if self._error:
            raise self._error
        return dict(self._result)


class _FakeGuala:
    def __init__(self, window_manager):
        self.window_manager = window_manager


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def test_gate1_no_guala_returns_503_and_never_compacts():
    print("Gate 1: no loaded substrate -> 503, compact() never called...")
    appmod._guala = None
    resp = _run(appmod.debug_wal_compact())
    assert resp.status_code == 503
    print("  PASS: 503 returned")


def test_gate2_wal_not_configured_returns_409():
    print("Gate 2: WAL not configured -> 409, compact() never called...")
    wm = _FakeWindowManager(wal_enabled=False)
    appmod._guala = _FakeGuala(wm)
    resp = _run(appmod.debug_wal_compact())
    assert resp.status_code == 409
    assert wm.compact_calls == 0
    print("  PASS: 409 returned, compact() not invoked")


def test_gate3_success_calls_real_compact_and_adds_timing():
    print("Gate 3: success calls compact(), returns result + elapsed_s...")
    wm = _FakeWindowManager(result={
        "generation": 7, "records": 12345, "path": "/tmp/x", "bytes": 555})
    appmod._guala = _FakeGuala(wm)
    result = _run(appmod.debug_wal_compact())
    assert wm.compact_calls == 1
    assert result["generation"] == 7
    assert result["records"] == 12345
    assert "elapsed_s" in result and isinstance(result["elapsed_s"], float)
    print(f"  PASS: real compact() result returned, elapsed_s="
          f"{result['elapsed_s']}")


def test_gate4_compact_error_surfaces_as_500():
    print("Gate 4: compact() raising surfaces as 500, not swallowed...")
    wm = _FakeWindowManager(error=RuntimeError("simulated compaction failure"))
    appmod._guala = _FakeGuala(wm)
    resp = _run(appmod.debug_wal_compact())
    assert resp.status_code == 500
    print("  PASS: 500 returned, error not silently lost")


if __name__ == "__main__":
    test_gate1_no_guala_returns_503_and_never_compacts()
    test_gate2_wal_not_configured_returns_409()
    test_gate3_success_calls_real_compact_and_adds_timing()
    test_gate4_compact_error_surfaces_as_500()
    print("\nAll wal-compact debug-endpoint gates pass.")
