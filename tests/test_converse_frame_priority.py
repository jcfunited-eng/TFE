"""GL-CMD-CONVERSE-FRAME-PRIORITY — real tests for the frame/converse priority
yield.

Root cause (measured live, reproduced in a local timing harness): the
conversational turn (legacy converse() OR the GLEW MultiScalarTurnScheduler)
runs in the SAME single uvicorn process as continuous /sound_frame and
/sight_frame processing. One core + the GIL means those always-runnable frame
jobs starve the turn: the same real 5-scalar turn stretched x1.9 / x5.9 / x12.9
under 1 / 2 / 4 competing CPU threads.

Fix: while a real conversational turn is settling, the in-process
/sound_frame and /sight_frame handlers SHED the incoming frame using the same
honest backpressure response they already return at capacity (the UI already
renders it), so the turn gets the core. A plain GIL-atomic counter, marked in
_run_converse and cleared in its finally, drives the gate.

These tests exercise the REAL app-module functions (_converse_turn_begin/end/
in_flight, the real sight_frame/sound_frame coroutine handlers, the real
_run_converse) -- only UNRELATED collaborators (the heavy substrate decode /
GLEW scheduler) are stubbed to isolate the priority decision, never the gate
itself. Same convention as tests/test_camera_turn_latency_priority.py.
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
def clean_converse_flag():
    """Snapshot + restore the in-flight counter and _guala around each test."""
    saved = appmod._converse_inflight
    saved_started = appmod._converse_window_started_at
    saved_guala = appmod._guala
    appmod._converse_inflight = 0
    appmod._converse_window_started_at = 0.0
    try:
        yield
    finally:
        appmod._converse_inflight = saved
        appmod._converse_window_started_at = saved_started
        appmod._guala = saved_guala


def _task_record(source: str = "joe") -> dict:
    return {"status": "queued", "phase": None, "started_at": 1.0,
            "started_tick": 0, "source": source}


# ── the counter primitive ───────────────────────────────────────────────────

def test_flag_toggles_with_begin_end(clean_converse_flag):
    assert appmod._converse_turn_in_flight() is False
    appmod._converse_turn_begin()
    assert appmod._converse_turn_in_flight() is True
    appmod._converse_turn_end()
    assert appmod._converse_turn_in_flight() is False


def test_flag_is_a_counter_for_overlapping_turns(clean_converse_flag):
    """Two concurrent turns must both settle before frames resume."""
    appmod._converse_turn_begin()
    appmod._converse_turn_begin()
    assert appmod._converse_turn_in_flight() is True
    appmod._converse_turn_end()
    assert appmod._converse_turn_in_flight() is True   # one still settling
    appmod._converse_turn_end()
    assert appmod._converse_turn_in_flight() is False
    # over-release can never drive it negative / suppress the gate forever
    appmod._converse_turn_end()
    assert appmod._converse_inflight == 0
    assert appmod._converse_turn_in_flight() is False


# ── the priority window is TIME-BOXED (verified-defect amendment) ────────────

def test_priority_window_expires_for_a_slow_turn(clean_converse_flag):
    """A turn that outlives _CONVERSE_PRIORITY_WINDOW_S keeps settling but
    loses frame priority: senses resume mid-turn.  This is the fix for the
    verified defect where a slow turn blacked out all sensory intake (and both
    background tick sources) for its entire duration."""
    appmod._converse_turn_begin()
    try:
        assert appmod._converse_turn_in_flight() is True
        # age the window past the deadline instead of sleeping
        appmod._converse_window_started_at = (
            appmod.time.time() - appmod._CONVERSE_PRIORITY_WINDOW_S - 0.01)
        assert appmod._converse_inflight == 1, "turn is genuinely still settling"
        assert appmod._converse_turn_in_flight() is False, (
            "frames flow again even while the slow turn settles")
    finally:
        appmod._converse_turn_end()


def test_hung_turn_cannot_blind_frames_until_restart(clean_converse_flag):
    """The deadline doubles as the stuck-counter watchdog: if a turn's executor
    call never returns (finally never runs, counter never decrements), the
    expired window still lets frames through -- the verified shed-forever
    failure mode is structurally impossible now."""
    appmod._converse_turn_begin()          # simulate: never ended (hung await)
    appmod._converse_window_started_at = (
        appmod.time.time() - appmod._CONVERSE_PRIORITY_WINDOW_S - 0.01)
    assert appmod._converse_inflight == 1, "counter is stuck, by construction"
    assert appmod._converse_turn_in_flight() is False, (
        "frames are NOT shed despite the stuck counter")


def test_queued_turns_do_not_rearm_the_window(clean_converse_flag):
    """A steady stream of overlapping turns must not re-open the shed window
    each time (that would black out senses indefinitely under conversation
    load): the window is armed by the FIRST concurrent turn only."""
    appmod._converse_turn_begin()
    armed_at = appmod._converse_window_started_at
    appmod._converse_turn_begin()          # overlapping second turn
    assert appmod._converse_window_started_at == armed_at, (
        "second concurrent turn did not re-arm the window")
    appmod._converse_turn_end()
    appmod._converse_turn_end()


# ── frames SHED while a turn is in flight ───────────────────────────────────

def test_sound_frame_shed_while_turn_in_flight(clean_converse_flag):
    """A real /sound_frame call while a turn settles returns the honest
    backpressure response and NEVER touches the substrate decoder."""
    calls = []
    appmod._guala = SimpleNamespace(
        tick=5,
        process_sound_frame=lambda *a, **k: calls.append("processed"))

    appmod._converse_turn_begin()  # a turn is settling
    try:
        resp = asyncio.run(appmod.sound_frame(
            appmod.GLMessage(text="Zm9v", source="ambient")))
    finally:
        appmod._converse_turn_end()

    assert resp["ok"] is False
    assert resp["dropped"] is True
    assert resp["converse_priority"] is True
    assert "backpressure" in resp["reason"]
    assert calls == [], "frame was shed, decoder never ran while turn in flight"


def test_sight_frame_shed_while_turn_in_flight(clean_converse_flag):
    calls = []
    appmod._guala = SimpleNamespace(
        tick=5,
        process_sight_frame=lambda *a, **k: calls.append("processed"))

    appmod._converse_turn_begin()
    try:
        resp = asyncio.run(appmod.sight_frame(
            appmod.GLMessage(text="Zm9v", source="camera_stream")))
    finally:
        appmod._converse_turn_end()

    assert resp["ok"] is False
    assert resp["dropped"] is True
    assert resp["converse_priority"] is True
    assert "backpressure" in resp["reason"]
    assert calls == [], "sight frame shed, decoder never ran while turn in flight"


# ── frames processed normally when NO turn is in flight ─────────────────────

def test_sound_frame_processed_when_no_turn_in_flight(clean_converse_flag):
    """With no turn settling, the shed gate is not taken: the frame proceeds
    through the real handler (decode + process). Only the substrate decode
    collaborators are stubbed -- the gate/handler flow is real."""
    processed = []
    fake = SimpleNamespace(tick=9, _latest_causal_settlement=None)
    def process_sound_frame(wav, source=None, **_kwargs):
        processed.append(source)
        window_id = "priority-sound-window"
        fake._latest_causal_settlement = SimpleNamespace(
            assembly_id=f"causal-{window_id}",
            interpretations=(SimpleNamespace(sense="sound", state="observed"),),
            verify=lambda: None,
        )
        return {"accepted": True, "closed_window_id": window_id,
                "settlement": fake._latest_causal_settlement}
    fake.process_sound_frame = process_sound_frame
    appmod._guala = fake

    # Stub only the UNRELATED heavy collaborators (webm decoder + the vocab
    # recognition-availability helper) so the handler's OWN flow -- the priority
    # gate, backpressure acquire/release, and executor dispatch -- is all real.
    import dsf_ai_service.substrate_runner as sr
    import dsf_ai_service.substrate.grounded_vocab_integration as gvi
    saved_webm = sr._webm_to_wav_bytes
    saved_reco = gvi.spoken_word_recognition_unavailable
    sr._webm_to_wav_bytes = lambda b: b"RIFFwav"
    gvi.spoken_word_recognition_unavailable = lambda *a, **k: {"status": "unavailable"}
    try:
        assert appmod._converse_turn_in_flight() is False
        resp = asyncio.run(appmod.sound_frame(
            appmod.GLMessage(
                text="Zm9v", source="ambient",
                capture_started_ms=1_000, capture_ended_ms=6_000)))
    finally:
        sr._webm_to_wav_bytes = saved_webm
        gvi.spoken_word_recognition_unavailable = saved_reco

    assert "converse_priority" not in resp, "not shed when nothing is in flight"
    assert resp["ok"] is True
    assert processed == ["ambient"], "frame really processed"
    assert appmod._frame_inflight["sound"] == 0, "gate slot released"


# ── the flag is ALWAYS cleared, even when the turn errors ───────────────────

def test_flag_cleared_after_turn_error(clean_converse_flag, monkeypatch):
    """_run_converse's finally clears the in-flight mark even when the turn
    raises -- frames can never be starved forever by a failed turn. Driven
    through the real _run_converse with the GLEW flag on but no engine
    constructed (its documented fail-closed error path)."""
    monkeypatch.setattr(appmod, "_GLEW_ENGINE_ENABLED", True)
    monkeypatch.setattr(appmod, "_glew_scheduler", None)
    monkeypatch.setattr(appmod, "_glew_story_chemistry", None)
    monkeypatch.setattr(appmod, "_guala", SimpleNamespace(tick=0, is_asleep=False))

    appmod._converse_tasks["err-turn"] = _task_record()
    asyncio.run(appmod._run_converse("err-turn", "hello", "joe"))
    task = dict(appmod._converse_tasks.pop("err-turn"))

    assert task["status"] == "error"
    assert appmod._converse_inflight == 0, "flag cleared despite the turn error"
    assert appmod._converse_turn_in_flight() is False


def test_flag_is_set_during_the_turn_and_cleared_after(clean_converse_flag, monkeypatch):
    """Positive proof the mark is actually raised FOR THE DURATION of a turn:
    a stub GLEW scheduler observes _converse_turn_in_flight() is True while its
    run_turn executes, and the mark is cleared once _run_converse returns."""
    observed = {}

    class _ObservingScheduler:
        def run_turn(self, *, task_id, text, story_chemistry, source):
            observed["in_flight_during_turn"] = appmod._converse_turn_in_flight()
            return SimpleNamespace(
                all_silent=True, visible_scalar_texts=(), any_commit=False)

    monkeypatch.setattr(appmod, "_GLEW_ENGINE_ENABLED", True)
    monkeypatch.setattr(appmod, "_glew_scheduler", _ObservingScheduler())
    monkeypatch.setattr(appmod, "_glew_story_chemistry", object())
    monkeypatch.setattr(appmod, "_glew_engine",
                        SimpleNamespace(_mode_bank=SimpleNamespace(rank=0)))
    monkeypatch.setattr(appmod, "_guala", SimpleNamespace(tick=4))

    appmod._converse_tasks["obs-turn"] = _task_record()
    asyncio.run(appmod._run_converse("obs-turn", "hi", "joe"))
    task = dict(appmod._converse_tasks.pop("obs-turn"))

    assert task["status"] == "complete"
    assert observed["in_flight_during_turn"] is True, "mark raised during the turn"
    assert appmod._converse_inflight == 0, "mark cleared after the turn"
