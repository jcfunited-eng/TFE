"""
test_voice_reply_door.py — GL-FIX-VOICE-REPLY-DOOR-20260720: recognized
speech triggers a real reply (converse()), not just passive memory intake
(read_sentence()).

Root incident, confirmed live 2026-07-20: a full minute of continuously
recognized speech (7 consecutive successful transcriptions in the live
[voice-whisper] log) produced zero replies, because the sound_frame path
only ever called read_sentence() — which updates memory/presence but has
no step that composes a turn. converse() (the door typed chat uses) does
both. Fix replaces the read_sentence call on recognized speech with a
non-blocking converse() call on a dedicated single-worker executor, so a
slow (historically 49-94s) reply composition never blocks the live audio
stream, and back-to-back recognized utterances can't stack up overlapping
converse() calls.

Gates:
1. Recognized speech triggers exactly one converse() call, with the
   transcript and unresolved auditory-source provenance -- not read_sentence
   and never a fabricated Joe identity.
2. While a reply is composing, one additional recognized terminal is
   admitted to the single pending slot and composed afterward. A newer
   terminal REPLACES the pending one (visible "superseded" result, physical
   event discarded through the real mechanism) -- replies never overlap, no
   backlog can grow, and nothing is ever dropped silently
   (GL-FIX-VOICE-LOOP-UX-20260722).
3. The busy flag clears after completion, success or failure, so the
   NEXT utterance after the current one finishes is not permanently
   blocked.
4. A real (non-empty) reply gets written to substrate_runner's
   _last_autonomous_thought in the same shape the existing /thought
   polling already expects, tagged category="voice_reply".
5. A real reply self-hears (one mouth, GL Change 4) -- calls
   _guala._self_hear with the reply content.
6. An empty reply (real silence, a legitimate converse() outcome) does
   NOT write to _last_autonomous_thought or self-hear -- only a genuine
   commit does.
7. A silence_no_commit uses the same organism attempt as typed conversation;
   a real organism release reaches /thought and self-hears.
8. Bare labels, altered terminals, and duplicate event identities never enter
   cognition.
"""

import sys
import os
import asyncio
import hashlib
import json
import threading
import time
from dataclasses import replace
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dsf_ai_service.app as appmod
import dsf_ai_service.substrate_runner as srmod
from dsf_ai_service.substrate.auditory_incremental_terminal import (
    AUDITORY_INCREMENTAL_EVENT_SCHEMA,
    AuditoryIncrementalTerminalEvent,
)


def _digest(value):
    return hashlib.sha256(json.dumps(
        value, allow_nan=False, ensure_ascii=False,
        separators=(",", ":"), sort_keys=True,
    ).encode("utf-8")).hexdigest()


def _terminal(label, ordinal=0):
    stream_id = f"test-stream-{ordinal}"
    structural_fingerprint = _digest(
        {"label_witness": label, "ordinal": ordinal}
    )
    event_id = _digest({
        "source_sample_end": 160,
        "source_sample_start": 0,
        "stream_id": stream_id,
        "structural_fingerprint": structural_fingerprint,
    })
    l5_receipt = _digest({"l5": ordinal})
    transport = (_digest({"transport": ordinal}),)
    cochlear = (_digest({"cochlear": ordinal}),)
    joint = (_digest({"joint": ordinal}),)
    payload = {
        "cochlear_receipt_sha256s": list(cochlear),
        "event_id": event_id,
        "joint_settlement_receipt_sha256s": list(joint),
        "l5_authority_receipt_sha256": l5_receipt,
        "recognition_state": "unique",
        "sample_rate_hz": 16_000,
        "schema": AUDITORY_INCREMENTAL_EVENT_SCHEMA,
        "source_sample_end": 160,
        "source_sample_start": 0,
        "stream_id": stream_id,
        "structural_fingerprint": structural_fingerprint,
        "transport_receipt_sha256s": list(transport),
        "tutor_label": label,
    }
    return AuditoryIncrementalTerminalEvent(
        event_id=event_id,
        stream_id=stream_id,
        source_sample_start=0,
        source_sample_end=160,
        tutor_label=label,
        structural_fingerprint=structural_fingerprint,
        l5_authority_receipt_sha256=l5_receipt,
        transport_receipt_sha256s=transport,
        cochlear_receipt_sha256s=cochlear,
        joint_settlement_receipt_sha256s=joint,
        authority_receipt_sha256=_digest(payload),
    )


class _FakeTurnResult:
    def __init__(self, response, response_source="assemblage_commit",
                 causal_intake=None):
        self.response = response
        self.response_source = response_source
        self.emission_id = "test-emission-1"
        self.committed_sections = ("subject", "verb")
        self.commit_provenance = ()
        self.causal_experience_id = (
            causal_intake.event_id if causal_intake is not None else None
        )
        self.causal_intake_receipt_sha256 = (
            causal_intake.authority_receipt_sha256
            if causal_intake is not None else None
        )


class _FakeGuala:
    def __init__(self, reply="hello back", delay=0.0):
        self.tick = 12345
        self._reply = reply
        self._delay = delay
        self.converse_calls = []
        self.causal_intakes = []
        self.self_hear_calls = []
        self.discarded_terminals = []

    def converse(self, text, source="unknown", causal_intake=None):
        self.converse_calls.append((text, source))
        self.causal_intakes.append(causal_intake)
        if self._delay:
            time.sleep(self._delay)
        return _FakeTurnResult(self._reply, causal_intake=causal_intake)

    def _self_hear(self, content, who, **kw):
        self.self_hear_calls.append((content, who, kw))

    def _log_substrate_event(self, *a, **kw):
        pass

    def discard_unadmitted_auditory_terminal(self, terminal_event):
        self.discarded_terminals.append(terminal_event)
        return True


def _reset():
    with appmod._voice_reply_state_lock:
        appmod._voice_reply_busy.clear()
        appmod._voice_reply_pending = None
        appmod._voice_reply_active_event_id = None
        appmod._voice_turn_results.clear()


def test_gate1_recognized_speech_calls_converse_not_read_sentence():
    print("Gate 1: converse() called with unresolved auditory provenance...")
    _reset()
    fake = _FakeGuala(reply="")
    appmod._guala = fake
    terminal = _terminal("hello guala")
    ok = appmod._maybe_trigger_voice_reply(terminal, fake.tick)
    assert ok == "started"
    for _ in range(50):
        if not appmod._voice_reply_busy.is_set():
            break
        time.sleep(0.05)
    assert fake.converse_calls == [
        ("hello guala", "auditory:unresolved_source")
    ], fake.converse_calls
    assert fake.causal_intakes == [terminal]
    print("  PASS: converse() called exactly once, correct args")


def test_gate2_pending_slot_is_bounded_and_replaces_with_newest():
    print("Gate 2: bounded pending slot holds the NEWEST utterance...")
    _reset()
    fake = _FakeGuala(reply="reply one", delay=0.3)
    appmod._guala = fake
    first_terminal = _terminal("first utterance", 1)
    second_terminal = _terminal("second utterance", 2)
    third_terminal = _terminal("third utterance", 3)
    first = appmod._maybe_trigger_voice_reply(first_terminal, fake.tick)
    assert first == "started"
    assert appmod._voice_reply_busy.is_set()
    second = appmod._maybe_trigger_voice_reply(second_terminal, fake.tick)
    third = appmod._maybe_trigger_voice_reply(third_terminal, fake.tick)
    assert second == "queued", "one pending utterance must be admitted"
    assert third == "queued", (
        "a newer utterance must REPLACE the pending one, never drop silently"
    )
    for _ in range(50):
        if not appmod._voice_reply_busy.is_set():
            break
        time.sleep(0.05)
    assert fake.converse_calls == [
        ("first utterance", "auditory:unresolved_source"),
        ("third utterance", "auditory:unresolved_source"),
    ], fake.converse_calls
    assert fake.causal_intakes == [first_terminal, third_terminal]
    assert fake.discarded_terminals == [second_terminal], (
        "the replaced pending terminal's physical event must be discarded "
        "through the real mechanism"
    )
    superseded = asyncio.run(
        appmod.auditory_terminal_reply(second_terminal.event_id)
    )
    assert superseded["status"] == "superseded", (
        "a replaced utterance must resolve to a VISIBLE terminal state"
    )
    assert superseded["heard"] == "second utterance"
    assert (superseded["superseded_by_terminal_event_id"]
            == third_terminal.event_id)
    print("  PASS: newest utterance kept, replaced one visibly superseded")


def test_duplicate_active_event_does_not_revoke_its_authority():
    _reset()
    fake = _FakeGuala(reply="reply", delay=0.2)
    appmod._guala = fake
    terminal = _terminal("one physical event", 30)

    assert appmod._maybe_trigger_voice_reply(terminal, fake.tick) == "started"
    assert appmod._maybe_trigger_voice_reply(terminal, fake.tick) is False
    assert fake.discarded_terminals == []
    for _ in range(50):
        if not appmod._voice_reply_busy.is_set():
            break
        time.sleep(0.05)
    assert fake.causal_intakes == [terminal]
    assert appmod._maybe_trigger_voice_reply(terminal, fake.tick) is False
    assert fake.discarded_terminals == [terminal]


def test_gate3_busy_flag_clears_after_completion():
    print("Gate 3: busy flag clears (success and failure)...")
    _reset()
    fake_ok = _FakeGuala(reply="")
    appmod._guala = fake_ok
    appmod._maybe_trigger_voice_reply(_terminal("ok case", 4), fake_ok.tick)
    for _ in range(50):
        if not appmod._voice_reply_busy.is_set():
            break
        time.sleep(0.05)
    assert not appmod._voice_reply_busy.is_set()

    class _RaisingGuala(_FakeGuala):
        def converse(self, text, source="unknown", causal_intake=None):
            raise RuntimeError("simulated composition failure")

    _reset()
    fake_fail = _RaisingGuala()
    appmod._guala = fake_fail
    appmod._maybe_trigger_voice_reply(
        _terminal("failure case", 5), fake_fail.tick
    )
    for _ in range(50):
        if not appmod._voice_reply_busy.is_set():
            break
        time.sleep(0.05)
    assert not appmod._voice_reply_busy.is_set(), \
        "busy flag must clear even when converse() raises"
    print("  PASS: busy flag clears after both success and failure")


def test_gate4_real_reply_reaches_last_autonomous_thought():
    print("Gate 4: a real reply surfaces via _last_autonomous_thought...")
    _reset()
    srmod._last_autonomous_thought = {"speech": "", "tick": 0, "ts": 0.0}
    fake = _FakeGuala(reply="a real committed reply")
    appmod._guala = fake
    terminal = _terminal("say something", 6)
    terminal_event_id = terminal.event_id
    appmod._maybe_trigger_voice_reply(terminal, fake.tick)
    for _ in range(50):
        if not appmod._voice_reply_busy.is_set():
            break
        time.sleep(0.05)
    with srmod._autonomous_thought_lock:
        t = dict(srmod._last_autonomous_thought)
    assert t["speech"] == "a real committed reply"
    assert t["category"] == "voice_reply"
    assert t["source"] == "guala"
    assert t["response_source"] == "assemblage_commit"
    assert t["terminal_event_id"] == terminal_event_id
    assert t["causal_experience_id"] == terminal_event_id
    assert (t["causal_intake_receipt_sha256"]
            == terminal.authority_receipt_sha256)
    delivered = asyncio.run(
        appmod.auditory_terminal_reply(terminal_event_id)
    )
    assert delivered["status"] == "completed"
    assert delivered["speech"] == "a real committed reply"
    assert delivered["emission_id"] == "test-emission-1"
    assert delivered["causal_experience_id"] == terminal_event_id
    print("  PASS: real reply written in the existing /thought poll shape")


def test_gate5_real_reply_self_hears():
    print("Gate 5: a real reply self-hears...")
    _reset()
    fake = _FakeGuala(reply="hear this")
    appmod._guala = fake
    appmod._maybe_trigger_voice_reply(_terminal("prompt", 7), fake.tick)
    for _ in range(50):
        if not appmod._voice_reply_busy.is_set():
            break
        time.sleep(0.05)
    assert len(fake.self_hear_calls) == 1
    assert fake.self_hear_calls[0][0] == "hear this"
    assert fake.self_hear_calls[0][1] == "guala"
    print("  PASS: self-hear fired with the real reply content")


def test_gate6_empty_reply_does_not_surface_or_self_hear():
    print("Gate 6: honest silence does not fabricate a surfaced reply...")
    _reset()
    srmod._last_autonomous_thought = {"speech": "sentinel-untouched", "tick": 0, "ts": 0.0}
    fake = _FakeGuala(reply="")
    appmod._guala = fake
    terminal = _terminal("unanswerable prompt", 8)
    appmod._maybe_trigger_voice_reply(terminal, fake.tick)
    for _ in range(50):
        if not appmod._voice_reply_busy.is_set():
            break
        time.sleep(0.05)
    with srmod._autonomous_thought_lock:
        t = dict(srmod._last_autonomous_thought)
    assert t["speech"] == "sentinel-untouched", \
        "an empty (honest silence) reply must never overwrite the thought slot"
    assert fake.self_hear_calls == [], \
        "an empty reply must never self-hear"
    delivered = asyncio.run(appmod.auditory_terminal_reply(terminal.event_id))
    assert delivered["status"] == "completed_without_speech"
    assert delivered["response_source"] == "assemblage_commit"
    assert delivered["causal_experience_id"] == terminal.event_id
    print("  PASS: empty reply stays honestly silent, no fabricated surfacing")


def test_gate7_structural_silence_uses_typed_organism_fallthrough():
    print("Gate 7: spoken structural silence reaches the typed organism attempt...")
    _reset()
    srmod._last_autonomous_thought = {"speech": "", "tick": 0, "ts": 0.0}

    class _SilentThenOrganismGuala(_FakeGuala):
        def __init__(self):
            super().__init__(reply="")
            self.lock = threading.RLock()
            self.seeds = None

        def converse(self, text, source="unknown", causal_intake=None):
            self.converse_calls.append((text, source))
            self.causal_intakes.append(causal_intake)
            return _FakeTurnResult(
                "", response_source="silence_no_commit",
                causal_intake=causal_intake,
            )

        def precompute_organism_attempt(self, seeds):
            self.seeds = seeds
            return {"real": "votes"}

        def _compose_organism_attempt(self, seeds, deadline, *,
                                      organism_votes, conversational):
            assert seeds == self.seeds
            assert organism_votes == {"real": "votes"}
            assert conversational is True
            return {"content": "the and of",
                    "response_source": "organism_attempt"}

    fake = _SilentThenOrganismGuala()
    appmod._guala = fake
    appmod._maybe_trigger_voice_reply(
        _terminal("your name is guala", 9), fake.tick
    )
    for _ in range(50):
        if not appmod._voice_reply_busy.is_set():
            break
        time.sleep(0.05)
    with srmod._autonomous_thought_lock:
        thought = dict(srmod._last_autonomous_thought)
    assert thought["speech"] == "the and of"
    assert thought["response_source"] == "organism_attempt"
    assert fake.self_hear_calls[0][0] == "the and of"
    print("  PASS: voice and typed turns share one organism fall-through")


def test_gate8_only_one_verified_terminal_identity_enters_cognition():
    print("Gate 8: label-only, altered, and duplicate intake fails closed...")
    _reset()
    fake = _FakeGuala(reply="", delay=0.2)
    appmod._guala = fake
    terminal = _terminal("one physical event", 10)

    try:
        appmod._maybe_trigger_voice_reply("one physical event", fake.tick)
        raise AssertionError("a bare label entered the auditory door")
    except TypeError as error:
        assert "requires an auditory terminal" in str(error)
    altered = replace(terminal, authority_receipt_sha256="0" * 64)
    try:
        appmod._maybe_trigger_voice_reply(altered, fake.tick)
        raise AssertionError("an altered terminal entered the auditory door")
    except ValueError as error:
        assert "receipt was altered" in str(error)

    assert appmod._maybe_trigger_voice_reply(terminal, fake.tick) == "started"
    assert appmod._maybe_trigger_voice_reply(terminal, fake.tick) is False
    for _ in range(50):
        if not appmod._voice_reply_busy.is_set():
            break
        time.sleep(0.05)
    assert fake.causal_intakes == [terminal]
    assert appmod._maybe_trigger_voice_reply(terminal, fake.tick) is False
    print("  PASS: exactly one verified physical event entered cognition")


def test_gate9_delivery_and_thought_carry_the_real_heard_form():
    print("Gate 9: reply delivery + /thought carry the recognizer's form...")
    _reset()
    srmod._last_autonomous_thought = {"speech": "", "tick": 0, "ts": 0.0}
    fake = _FakeGuala(reply="a real committed reply")
    appmod._guala = fake
    terminal = _terminal("what she actually heard", 40)
    appmod._maybe_trigger_voice_reply(terminal, fake.tick)
    for _ in range(50):
        if not appmod._voice_reply_busy.is_set():
            break
        time.sleep(0.05)
    delivered = asyncio.run(appmod.auditory_terminal_reply(terminal.event_id))
    assert delivered["heard"] == "what she actually heard", (
        "the delivery must carry the recognizer's released form so the "
        "dialog and teacher thumbs never invent the heard input"
    )
    with srmod._autonomous_thought_lock:
        thought = dict(srmod._last_autonomous_thought)
    assert thought["heard"] == "what she actually heard"
    print("  PASS: heard form rides delivery and thought unchanged")


def _pcm_message(sight_captured_ms):
    return appmod.GLMessage(
        text="AA==",
        audio_encoding="pcm_s16le",
        audio_stream_id="stream",
        audio_sequence=0,
        audio_first_sample_index=0,
        audio_sample_count=80_000,
        audio_sample_rate_hz=16_000,
        audio_source_epoch_ms=10_000,
        sight_b64="Zg==",
        sight_captured_ms=sight_captured_ms,
    )


def test_gate10_out_of_interval_sight_drops_pairing_never_kills_sound():
    print("Gate 10: bad sight pairing drops the pairing, keeps hearing...")
    # Chunk interval: [10s, 15s). In-interval pairing anchors normally.
    inside = appmod._authoritative_capture_times(
        _pcm_message(12_000), paired_sight=True
    )
    assert inside["sight_pairing_dropped"] is None
    assert inside["sight_source_anchor_ns"] == 12_000 * 1_000_000
    # A jitter-late capture outside the interval must NOT raise (a raise
    # used to terminally reject the PCM epoch and kill hearing) -- the
    # pairing is dropped, honestly named, and sound continuity is intact.
    outside = appmod._authoritative_capture_times(
        _pcm_message(15_500), paired_sight=True
    )
    assert outside["sight_pairing_dropped"] is not None
    assert "outside the PCM interval" in outside["sight_pairing_dropped"]
    assert outside["sight_source_anchor_ns"] is None
    assert outside["source_time_start_ns"] == 10_000 * 1_000_000
    assert outside["source_time_end_ns"] == 15_000 * 1_000_000
    # Same for a missing timestamp: unprovable pairing, not a stream fault.
    missing = appmod._authoritative_capture_times(
        _pcm_message(None), paired_sight=True
    )
    assert missing["sight_pairing_dropped"] is not None
    assert missing["sight_source_anchor_ns"] is None
    # The legacy (non-PCM) branch keeps its strict behaviour unchanged.
    legacy = appmod.GLMessage(
        text="AA==", capture_started_ms=1_000, capture_ended_ms=2_000,
        sight_b64="Zg==", sight_captured_ms=5_000,
    )
    try:
        appmod._authoritative_capture_times(legacy, paired_sight=True)
        raise AssertionError("legacy paired-sight validation must still raise")
    except ValueError as error:
        assert "outside the audio interval" in str(error)
    print("  PASS: pairing dropped honestly; sound authority untouched")


class _TeachableGuala(_FakeGuala):
    """Records exist exactly as converse() writes them; no new stores."""

    def __init__(self):
        super().__init__(reply="")
        self._emission_records = {
            "voice-emission-1": {
                "emission_id": "voice-emission-1",
                "text": "her committed voice reply",
                "input_text": "what she actually heard",
                "response_source": "assemblage_commit",
                "n_commits": 3,
                "tick": 12345,
            },
            "stale-uncommitted": {
                "emission_id": "stale-uncommitted",
                "text": "fabricated",
                "input_text": "x",
                "response_source": "silence_no_commit",
                "n_commits": 0,
                "tick": 12345,
            },
        }
        self.corrections = []

    def _certified_emission_record(self, emission_id):
        return None  # voice replies are never fact-certified

    def apply_teacher_correction(self, **kw):
        self.corrections.append(kw)
        return {"ok": True, "affected": []}


def test_gate11_voice_replies_are_teachable_via_existing_gateway():
    print("Gate 11: teacher thumbs work on voice replies, real errors...")
    from fastapi import HTTPException
    _reset()
    fake = _TeachableGuala()
    appmod._guala = fake

    # 1. A committed (assemblage) voice reply resolves through the engine's
    #    own emission record -- heard input becomes original_input.
    req = appmod.TeacherFeedbackRequest(
        emission_id="voice-emission-1", source="joe"
    )
    result = appmod.handle_teacher_feedback_local(req)
    assert result["ok"] is True
    assert fake.corrections[-1]["original_input"] == "what she actually heard"
    assert fake.corrections[-1]["her_emission"] == "her committed voice reply"
    assert fake.corrections[-1]["correct"] is True

    # 2. An organism-attempt voice reply (no record, emission_id=None)
    #    teaches through the SAME gateway with the displayed real pair.
    req = appmod.TeacherFeedbackRequest(
        emission_id=None, source="joe",
        original_input="what she actually heard",
        her_emission="the and of",
    )
    result = appmod.handle_teacher_feedback_local(req)
    assert result["ok"] is True
    assert fake.corrections[-1]["her_emission"] == "the and of"

    # 3. A record without a real commit stays ineligible (nothing
    #    fabricated can be reinforced), and the error text is REAL.
    req = appmod.TeacherFeedbackRequest(
        emission_id="stale-uncommitted", source="joe"
    )
    try:
        appmod.handle_teacher_feedback_local(req)
        raise AssertionError("uncommitted record must stay unteachable")
    except HTTPException as error:
        assert error.status_code == 400
        assert "not teachable" in error.detail

    # 4. Corrections accept the same resolution (thumbs-down path).
    creq = appmod.TeacherCorrectionRequest(
        emission_id="voice-emission-1", corrected_text="say this instead",
        source="joe",
    )
    result = appmod.handle_teacher_correction_local(creq)
    assert result["ok"] is True
    assert fake.corrections[-1]["correct"] is False
    assert fake.corrections[-1]["original_input"] == "what she actually heard"
    assert fake.corrections[-1]["corrected_text"] == "say this instead"

    # 5. The correction model actually declares the page-supplied pair
    #    (it was silently discarded by pydantic before this fix).
    creq = appmod.TeacherCorrectionRequest(
        emission_id=None, corrected_text="say this instead", source="joe",
        original_input="what she actually heard", her_emission="the and of",
    )
    result = appmod.handle_teacher_correction_local(creq)
    assert result["ok"] is True
    assert fake.corrections[-1]["her_emission"] == "the and of"
    print("  PASS: voice replies teachable; unteachable stays refused loudly")


if __name__ == "__main__":
    test_gate1_recognized_speech_calls_converse_not_read_sentence()
    test_gate2_pending_slot_is_bounded_and_replaces_with_newest()
    test_gate3_busy_flag_clears_after_completion()
    test_gate4_real_reply_reaches_last_autonomous_thought()
    test_gate5_real_reply_self_hears()
    test_gate6_empty_reply_does_not_surface_or_self_hear()
    test_gate7_structural_silence_uses_typed_organism_fallthrough()
    test_gate8_only_one_verified_terminal_identity_enters_cognition()
    test_gate9_delivery_and_thought_carry_the_real_heard_form()
    test_gate10_out_of_interval_sight_drops_pairing_never_kills_sound()
    test_gate11_voice_replies_are_teachable_via_existing_gateway()
    print("\nAll voice-reply-door gates pass.")
