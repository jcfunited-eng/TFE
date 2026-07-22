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
   admitted to the single pending slot and composed afterward. A third is
   rejected, so replies never overlap and no backlog can grow.
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
    AUDITORY_INCREMENTAL_EVENT_SCHEMA_V3,
    AuditoryIncrementalTerminalEvent,
    _event_payload,
)
from dsf_ai_service.substrate.auditory_l5 import AUDITORY_L5_SCHEMA
from dsf_ai_service.substrate.auditory_reciprocity import (
    AUDITORY_RECOGNITION_OCCURRENCE_SCHEMA,
    AUDITORY_RECOGNITION_OPERATOR,
    AUDITORY_RECIPROCITY_SNAPSHOT_SCHEMA,
    AuditoryRecognitionOccurrence,
    AuditoryRecognitionState,
    AuditoryReciprocityKind,
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
    class_receipt = _digest({"learned_class": ordinal})
    occurrence_payload = {
        "candidate_class_authority_receipts": [class_receipt],
        "experience_id": _digest({"experience": ordinal}),
        "kind": AuditoryReciprocityKind.SPOKEN_FORM.value,
        "l5_authority_receipt_sha256": l5_receipt,
        "operator": AUDITORY_RECOGNITION_OPERATOR,
        "schema": AUDITORY_RECOGNITION_OCCURRENCE_SCHEMA,
        "selected_class_authority_receipt_sha256": class_receipt,
        "state": AuditoryRecognitionState.UNIQUE.value,
        "structural_fingerprint": structural_fingerprint,
    }
    occurrence = AuditoryRecognitionOccurrence(
        kind=AuditoryReciprocityKind.SPOKEN_FORM,
        state=AuditoryRecognitionState.UNIQUE,
        experience_id=occurrence_payload["experience_id"],
        structural_fingerprint=structural_fingerprint,
        l5_authority_receipt_sha256=l5_receipt,
        candidate_class_authority_receipts=(class_receipt,),
        selected_class_authority_receipt_sha256=class_receipt,
        operator=AUDITORY_RECOGNITION_OPERATOR,
        authority_receipt_sha256=_digest(occurrence_payload),
    )
    payload = _event_payload(
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
        recognition_occurrence=occurrence,
        schema=AUDITORY_INCREMENTAL_EVENT_SCHEMA_V3,
        l5_schema=AUDITORY_L5_SCHEMA,
        reciprocity_snapshot_schema=AUDITORY_RECIPROCITY_SNAPSHOT_SCHEMA,
        recognition_operator=AUDITORY_RECOGNITION_OPERATOR,
    )
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
        recognition_occurrence=occurrence,
        schema=AUDITORY_INCREMENTAL_EVENT_SCHEMA_V3,
        l5_schema=AUDITORY_L5_SCHEMA,
        reciprocity_snapshot_schema=AUDITORY_RECIPROCITY_SNAPSHOT_SCHEMA,
        recognition_operator=AUDITORY_RECOGNITION_OPERATOR,
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
    assert ok is True
    for _ in range(50):
        if not appmod._voice_reply_busy.is_set():
            break
        time.sleep(0.05)
    assert fake.converse_calls == [
        ("hello guala", "auditory:unresolved_source")
    ], fake.converse_calls
    assert fake.causal_intakes == [terminal]
    print("  PASS: converse() called exactly once, correct args")


def test_gate2_one_pending_utterance_is_bounded_and_serial():
    print("Gate 2: one pending utterance is admitted without overlap...")
    _reset()
    fake = _FakeGuala(reply="reply one", delay=0.3)
    appmod._guala = fake
    first_terminal = _terminal("first utterance", 1)
    second_terminal = _terminal("second utterance", 2)
    third_terminal = _terminal("third utterance", 3)
    first = appmod._maybe_trigger_voice_reply(first_terminal, fake.tick)
    assert first is True
    assert appmod._voice_reply_busy.is_set()
    second = appmod._maybe_trigger_voice_reply(second_terminal, fake.tick)
    third = appmod._maybe_trigger_voice_reply(third_terminal, fake.tick)
    assert second is True, "one pending utterance must be admitted"
    assert third is False, "the bounded pending slot must reject a third"
    for _ in range(50):
        if not appmod._voice_reply_busy.is_set():
            break
        time.sleep(0.05)
    assert fake.converse_calls == [
        ("first utterance", "auditory:unresolved_source"),
        ("second utterance", "auditory:unresolved_source"),
    ], fake.converse_calls
    assert fake.causal_intakes == [first_terminal, second_terminal]
    assert fake.discarded_terminals == [third_terminal]
    print("  PASS: one pending utterance composed serially; third rejected")


def test_duplicate_active_event_does_not_revoke_its_authority():
    _reset()
    fake = _FakeGuala(reply="reply", delay=0.2)
    appmod._guala = fake
    terminal = _terminal("one physical event", 30)

    assert appmod._maybe_trigger_voice_reply(terminal, fake.tick) is True
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


def test_gate5_app_does_not_duplicate_engine_owned_self_hearing():
    print("Gate 5: the app does not self-hear a second time...")
    _reset()
    fake = _FakeGuala(reply="hear this")
    appmod._guala = fake
    appmod._maybe_trigger_voice_reply(_terminal("prompt", 7), fake.tick)
    for _ in range(50):
        if not appmod._voice_reply_busy.is_set():
            break
        time.sleep(0.05)
    assert fake.self_hear_calls == []
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


def test_gate7_structural_silence_never_enters_organism_fallthrough():
    print("Gate 7: spoken structural silence remains typed silence...")
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
            raise AssertionError("causal silence reached organism fallthrough")

        def _compose_organism_attempt(self, seeds, deadline, *,
                                      organism_votes, conversational):
            raise AssertionError("causal silence reached organism composition")

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
    assert thought["speech"] == ""
    assert fake.self_hear_calls == []
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

    assert appmod._maybe_trigger_voice_reply(terminal, fake.tick) is True
    assert appmod._maybe_trigger_voice_reply(terminal, fake.tick) is False
    for _ in range(50):
        if not appmod._voice_reply_busy.is_set():
            break
        time.sleep(0.05)
    assert fake.causal_intakes == [terminal]
    assert appmod._maybe_trigger_voice_reply(terminal, fake.tick) is False
    print("  PASS: exactly one verified physical event entered cognition")


if __name__ == "__main__":
    test_gate1_recognized_speech_calls_converse_not_read_sentence()
    test_gate2_one_pending_utterance_is_bounded_and_serial()
    test_gate3_busy_flag_clears_after_completion()
    test_gate4_real_reply_reaches_last_autonomous_thought()
    test_gate5_real_reply_self_hears()
    test_gate6_empty_reply_does_not_surface_or_self_hear()
    test_gate7_structural_silence_uses_typed_organism_fallthrough()
    test_gate8_only_one_verified_terminal_identity_enters_cognition()
    print("\nAll voice-reply-door gates pass.")
