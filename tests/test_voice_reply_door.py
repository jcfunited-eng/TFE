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
"""

import sys
import os
import asyncio
import threading
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dsf_ai_service.app as appmod
import dsf_ai_service.substrate_runner as srmod


class _FakeTurnResult:
    def __init__(self, response, response_source="assemblage_commit"):
        self.response = response
        self.response_source = response_source
        self.emission_id = "test-emission-1"
        self.committed_sections = ("subject", "verb")
        self.commit_provenance = ()


class _FakeGuala:
    def __init__(self, reply="hello back", delay=0.0):
        self.tick = 12345
        self._reply = reply
        self._delay = delay
        self.converse_calls = []
        self.self_hear_calls = []

    def converse(self, text, source="unknown"):
        self.converse_calls.append((text, source))
        if self._delay:
            time.sleep(self._delay)
        return _FakeTurnResult(self._reply)

    def _self_hear(self, content, who, **kw):
        self.self_hear_calls.append((content, who, kw))

    def _log_substrate_event(self, *a, **kw):
        pass


def _reset():
    with appmod._voice_reply_state_lock:
        appmod._voice_reply_busy.clear()
        appmod._voice_reply_pending = None
        appmod._voice_turn_results.clear()


def test_gate1_recognized_speech_calls_converse_not_read_sentence():
    print("Gate 1: converse() called with unresolved auditory provenance...")
    _reset()
    fake = _FakeGuala(reply="")
    appmod._guala = fake
    ok = appmod._maybe_trigger_voice_reply("hello guala", fake.tick)
    assert ok is True
    for _ in range(50):
        if not appmod._voice_reply_busy.is_set():
            break
        time.sleep(0.05)
    assert fake.converse_calls == [
        ("hello guala", "auditory:unresolved_source")
    ], fake.converse_calls
    print("  PASS: converse() called exactly once, correct args")


def test_gate2_one_pending_utterance_is_bounded_and_serial():
    print("Gate 2: one pending utterance is admitted without overlap...")
    _reset()
    fake = _FakeGuala(reply="reply one", delay=0.3)
    appmod._guala = fake
    first = appmod._maybe_trigger_voice_reply("first utterance", fake.tick)
    assert first is True
    assert appmod._voice_reply_busy.is_set()
    second = appmod._maybe_trigger_voice_reply("second utterance", fake.tick)
    third = appmod._maybe_trigger_voice_reply("third utterance", fake.tick)
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
    print("  PASS: one pending utterance composed serially; third rejected")


def test_gate3_busy_flag_clears_after_completion():
    print("Gate 3: busy flag clears (success and failure)...")
    _reset()
    fake_ok = _FakeGuala(reply="")
    appmod._guala = fake_ok
    appmod._maybe_trigger_voice_reply("ok case", fake_ok.tick)
    for _ in range(50):
        if not appmod._voice_reply_busy.is_set():
            break
        time.sleep(0.05)
    assert not appmod._voice_reply_busy.is_set()

    class _RaisingGuala(_FakeGuala):
        def converse(self, text, source="unknown"):
            raise RuntimeError("simulated composition failure")

    _reset()
    fake_fail = _RaisingGuala()
    appmod._guala = fake_fail
    appmod._maybe_trigger_voice_reply("failure case", fake_fail.tick)
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
    terminal_event_id = "a" * 64
    appmod._maybe_trigger_voice_reply(
        "say something", fake.tick, terminal_event_id
    )
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
    delivered = asyncio.run(
        appmod.auditory_terminal_reply(terminal_event_id)
    )
    assert delivered["status"] == "completed"
    assert delivered["speech"] == "a real committed reply"
    assert delivered["emission_id"] == "test-emission-1"
    print("  PASS: real reply written in the existing /thought poll shape")


def test_gate5_real_reply_self_hears():
    print("Gate 5: a real reply self-hears...")
    _reset()
    fake = _FakeGuala(reply="hear this")
    appmod._guala = fake
    appmod._maybe_trigger_voice_reply("prompt", fake.tick)
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
    appmod._maybe_trigger_voice_reply("unanswerable prompt", fake.tick)
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

        def converse(self, text, source="unknown"):
            self.converse_calls.append((text, source))
            return _FakeTurnResult("", response_source="silence_no_commit")

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
    appmod._maybe_trigger_voice_reply("your name is guala", fake.tick)
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


if __name__ == "__main__":
    test_gate1_recognized_speech_calls_converse_not_read_sentence()
    test_gate2_one_pending_utterance_is_bounded_and_serial()
    test_gate3_busy_flag_clears_after_completion()
    test_gate4_real_reply_reaches_last_autonomous_thought()
    test_gate5_real_reply_self_hears()
    test_gate6_empty_reply_does_not_surface_or_self_hear()
    test_gate7_structural_silence_uses_typed_organism_fallthrough()
    print("\nAll voice-reply-door gates pass.")
