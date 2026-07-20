"""GL-FIX-CONVERSE-ADMIT-GUARD-20260720 — real tests for the typed-converse
admission guard.

Root cause (live-observed 2026-07-20): unlike voice replies, which have an
explicit busy/skip-ahead guard (_voice_reply_busy) so a backlog of stale
turns can never build up, typed converse (both the plain-text path and the
/listen command) had NO admission guard at all. Every request immediately
created a new task and scheduled it against the shared engine lock, no
matter how many turns were already queued. Each real turn is measured at
49-94s; a handful of prompts arriving close together stacked additively and
produced live-observed waits up to ~1000s for the last one in line.

Fix: reuse _converse_inflight (already correctly incremented/decremented
around the full body of _run_converse, always cleared in a finally -- see
tests/test_converse_frame_priority.py) as an admission gate. While a turn
is in flight, a new typed-converse request is rejected with an honest 409
instead of being accepted and left to queue silently.

These tests exercise the REAL app-module functions (_converse_admission_busy,
_converse_admission_rejected_response, the real gualaloom_chat coroutine) --
only the unrelated background-scheduling collaborator is stubbed, so the
admission decision itself is real, same convention as
test_converse_frame_priority.py.
"""

from __future__ import annotations

import asyncio
import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dsf_ai_service.app as appmod  # noqa: E402


@pytest.fixture
def clean_converse_state():
    """Snapshot + restore in-flight counter, task registry, and _guala."""
    saved_inflight = appmod._converse_inflight
    saved_tasks = dict(appmod._converse_tasks)
    saved_guala = appmod._guala
    appmod._converse_inflight = 0
    appmod._converse_tasks.clear()
    appmod._guala = SimpleNamespace(tick=7)
    try:
        yield
    finally:
        appmod._converse_inflight = saved_inflight
        appmod._converse_tasks.clear()
        appmod._converse_tasks.update(saved_tasks)
        appmod._guala = saved_guala


@pytest.fixture
def stub_scheduler(monkeypatch):
    """Replace the real background scheduler with a recorder -- isolates the
    admission decision from _run_converse's own (separately-tested) behavior."""
    calls = []

    def _fake_schedule(coroutine_factory, *, name):
        calls.append(name)
        coroutine_factory().close()  # never actually run, just avoid an
                                      # "unawaited coroutine" warning
        return SimpleNamespace(get_name=lambda: name, done=lambda: True)

    monkeypatch.setattr(appmod, "_schedule_mutating_background", _fake_schedule)
    return calls


# ── the primitives ───────────────────────────────────────────────────────

def test_admission_busy_reflects_inflight_counter(clean_converse_state):
    assert appmod._converse_admission_busy() is False
    appmod._converse_turn_begin()
    assert appmod._converse_admission_busy() is True
    appmod._converse_turn_end()
    assert appmod._converse_admission_busy() is False


def test_rejected_response_is_honest_409(clean_converse_state):
    resp = appmod._converse_admission_rejected_response()
    assert resp.status_code == 409
    import json
    body = json.loads(resp.body)
    assert body["ok"] is False
    assert body["busy"] is True
    assert isinstance(body["response"], str) and body["response"]


# ── plain-text converse path (sendMsg / _converseAndRender in the UI) ──────

def test_plain_converse_rejected_while_turn_in_flight(
        clean_converse_state, stub_scheduler):
    appmod._converse_turn_begin()
    try:
        resp = asyncio.run(appmod.gualaloom_chat(
            appmod.GLMessage(text="are you there", source="joe")))
    finally:
        appmod._converse_turn_end()

    assert resp.status_code == 409
    assert stub_scheduler == [], "no background task scheduled while busy"
    assert appmod._converse_tasks == {}, "no task left behind for a rejected turn"


def test_plain_converse_admitted_when_idle(clean_converse_state, stub_scheduler):
    assert appmod._converse_admission_busy() is False
    resp = asyncio.run(appmod.gualaloom_chat(
        appmod.GLMessage(text="are you there", source="joe")))

    assert resp.status_code == 202
    assert len(stub_scheduler) == 1, "scheduled exactly once"
    assert len(appmod._converse_tasks) == 1, "one task registered"
    (task,) = appmod._converse_tasks.values()
    assert task["status"] == "queued"
    assert task["source"] == "joe"


# ── /listen command path (other authenticated text callers) ────────────────

def test_listen_rejected_while_turn_in_flight(clean_converse_state, stub_scheduler):
    appmod._converse_turn_begin()
    try:
        resp = asyncio.run(appmod.gualaloom_chat(
            appmod.GLMessage(text="hello", command="/listen", source="wc")))
    finally:
        appmod._converse_turn_end()

    assert resp.status_code == 409
    assert stub_scheduler == []
    assert appmod._converse_tasks == {}


def test_listen_admitted_when_idle(clean_converse_state, stub_scheduler):
    resp = asyncio.run(appmod.gualaloom_chat(
        appmod.GLMessage(text="hello", command="/listen", source="wc")))

    assert resp.status_code == 202
    assert len(stub_scheduler) == 1
    (task,) = appmod._converse_tasks.values()
    assert task["source"] == "wc"


# ── the guard is scoped to converse admission only ──────────────────────────

def test_unrelated_command_unaffected_by_inflight_turn(clean_converse_state):
    """A busy converse turn must not block totally unrelated commands --
    the guard is only at the two converse-admission sites, nowhere else."""
    appmod._converse_turn_begin()
    try:
        result = asyncio.run(appmod.gualaloom_chat(
            appmod.GLMessage(text="", command="/mail", source="joe")))
    finally:
        appmod._converse_turn_end()

    assert result == {"letters": []}, "unrelated command still answered normally"
