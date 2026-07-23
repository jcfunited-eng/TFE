from __future__ import annotations

import base64
import asyncio
import io
import os
import time
import wave

import numpy as np
import pytest

import dsf_ai_service.substrate_runner as runner
from dsf_ai_service.substrate.causal_action_cycle import ActionCommand
from dsf_ai_service.substrate.causal_speech_delivery import (
    CausalSpeechDeliveryState,
    MAX_ATTEMPTS,
    MAX_WAV_BYTES,
    decode_state,
    encode_state,
)
from dsf_ai_service.v4.gualaloom_v5_engine import Guala
from dsf_ai_service.v4.gualaloom_v5_engine import ConversationTurnResult
from test_causal_settlement_dispatcher import _settlement


def _configure(monkeypatch, tmp_path, key="speech-delivery-test-key"):
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    monkeypatch.setenv("SELF_VOICE_AUDIO_ENABLED", "0")
    monkeypatch.setenv("GUALA_CAUSAL_ACTION_KEY", key)
    monkeypatch.setenv("STATE_DIR", str(tmp_path))
    monkeypatch.setattr(runner, "STATE_DIR", str(tmp_path))


def _wav_bytes(frequency_hz=440, sample_count=800):
    samples = np.asarray(
        [
            int(12_000 * np.sin(2 * np.pi * frequency_hz * index / 16_000))
            for index in range(sample_count)
        ],
        dtype="<i2",
    )
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16_000)
        wav.writeframes(samples.tobytes())
    return output.getvalue()


def _live_speech(engine, *, name="delivery", text="hello daddy"):
    taught = _settlement(f"{name}-taught")
    trigger = _settlement(f"{name}-trigger")
    engine._causal_action_cycle.accept(taught)
    engine._causal_action_cycle.teach(
        trigger_reference=taught.event_id,
        action=ActionCommand.speech(text),
        source="joe",
        nonce=f"{name}-teacher-authority-0001",
    )
    engine._accept_causal_settlement(trigger)
    release = engine._emit_from_invariants(
        (), (), causal_settlement=trigger
    )
    assert release.content == text
    return release


def test_signed_state_is_receipt_keyed_bounded_and_tamper_evident():
    state = CausalSpeechDeliveryState.queued(
        request_receipt_sha256="1" * 64,
        execution_receipt_sha256="2" * 64,
        action_text="hello daddy",
    ).begin_attempt().record_wav(_wav_bytes())
    envelope = encode_state(state, authority_key=b"state-key")

    restored = decode_state(envelope, authority_key=b"state-key")

    assert restored == state
    assert restored.wav_bytes == _wav_bytes()
    assert len(restored.wav_bytes) < MAX_WAV_BYTES
    assert MAX_ATTEMPTS == 2
    changed = dict(envelope)
    changed["state_hmac_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="HMAC"):
        decode_state(changed, authority_key=b"state-key")


def test_success_returns_and_observes_the_same_exact_server_wav(
    monkeypatch, tmp_path
):
    _configure(monkeypatch, tmp_path)
    engine = Guala()
    exact_wav = _wav_bytes()
    try:
        release = _live_speech(engine, name="exact-success")
        request_receipt = engine.causal_speech_output_status()[
            "request_receipt_sha256"
        ]
        monkeypatch.setattr(runner, "_guala", engine)
        monkeypatch.setattr(
            runner,
            "_synthesize_voice",
            lambda text: base64.b64encode(exact_wav).decode("ascii"),
        )

        encoded = runner._synthesize_released_voice(
            release.content, "causal_action_cycle_commit"
        )

        assert base64.b64decode(encoded, validate=True) == exact_wav
        assert engine._causal_speech_delivery_state.request_receipt_sha256 == (
            request_receipt
        )
        assert engine._causal_speech_delivery_state.phase == "completed"
        assert engine._causal_speech_delivery_state.attempts == 1
        assert engine._causal_action_dispatcher.status()["active"] is False
        settled_before = engine._causal_settlement_accepted
        duplicate = engine.observe_causal_speech_output(exact_wav)
        assert duplicate["status"] == "already_completed"
        assert engine._causal_settlement_accepted == settled_before
        checkpoint = tmp_path / "guala_causal_speech_delivery.json"
        assert checkpoint.is_file()
        assert checkpoint.stat().st_size < 56 * 1024 * 1024
    finally:
        engine.shutdown()


def test_teacher_review_failure_cannot_reopen_completed_speech(
    monkeypatch, tmp_path, capsys
):
    _configure(monkeypatch, tmp_path, "speech-review-failure-key")
    engine = Guala()
    exact_wav = _wav_bytes(495)
    try:
        release = _live_speech(engine, name="review-failure")
        status = engine.causal_speech_output_status()
        binding_id = engine._causal_action_cycle.live_execution_binding_id(
            status["execution_receipt_sha256"]
        )
        engine._causal_cycle_pending_review = {
            "binding_id": binding_id,
            "decision": "confirm",
            "execution_receipt_sha256": status[
                "execution_receipt_sha256"
            ],
            "source": "joe",
            "nonce": "review-failure-authority-0001",
        }
        monkeypatch.setattr(runner, "_guala", engine)
        monkeypatch.setattr(
            runner,
            "_synthesize_voice",
            lambda _text: base64.b64encode(exact_wav).decode("ascii"),
        )

        def fail_review(**_kwargs):
            raise RuntimeError("teacher review store unavailable")

        monkeypatch.setattr(
            engine._causal_action_cycle,
            "review_latest_closure",
            fail_review,
        )

        encoded = runner._synthesize_released_voice(
            release.content, "causal_action_cycle_commit"
        )

        assert base64.b64decode(encoded, validate=True) == exact_wav
        assert engine._causal_speech_delivery_state.phase == "completed"
        assert engine._causal_action_dispatcher.status()["active"] is False
        assert engine._causal_cycle_pending_review is None
        assert "speech closed but teacher review failed" in capsys.readouterr().out
    finally:
        engine.shutdown()


def test_first_synthesis_failure_recovers_same_receipt_on_second_attempt(
    monkeypatch, tmp_path
):
    _configure(monkeypatch, tmp_path, "speech-retry-key")
    engine = Guala()
    exact_wav = _wav_bytes(550)
    calls = []
    try:
        release = _live_speech(engine, name="retry-success")
        before = engine.causal_speech_output_status()
        monkeypatch.setattr(runner, "_guala", engine)

        def synthesize(_text):
            calls.append(True)
            if len(calls) == 1:
                return None
            return base64.b64encode(exact_wav).decode("ascii")

        monkeypatch.setattr(runner, "_synthesize_voice", synthesize)

        encoded = runner._synthesize_released_voice(
            release.content, "causal_action_cycle_commit"
        )

        assert len(calls) == 2
        assert base64.b64decode(encoded, validate=True) == exact_wav
        state = engine._causal_speech_delivery_state
        assert state.phase == "completed"
        assert state.attempts == 2
        assert state.request_receipt_sha256 == before[
            "request_receipt_sha256"
        ]
        assert state.execution_receipt_sha256 == before[
            "execution_receipt_sha256"
        ]
    finally:
        engine.shutdown()


def test_synthesis_exception_recovers_on_the_same_event(
    monkeypatch, tmp_path
):
    _configure(monkeypatch, tmp_path, "speech-exception-retry-key")
    engine = Guala()
    exact_wav = _wav_bytes(605)
    calls = []
    try:
        release = _live_speech(engine, name="exception-retry")
        before = engine.causal_speech_output_status()
        monkeypatch.setattr(runner, "_guala", engine)

        def synthesize(_text):
            calls.append(True)
            if len(calls) == 1:
                raise RuntimeError("speech process exited")
            return base64.b64encode(exact_wav).decode("ascii")

        monkeypatch.setattr(runner, "_synthesize_voice", synthesize)

        encoded = runner._synthesize_released_voice(
            release.content, "causal_action_cycle_commit"
        )

        assert len(calls) == 2
        assert base64.b64decode(encoded, validate=True) == exact_wav
        state = engine._causal_speech_delivery_state
        assert state.phase == "completed"
        assert state.attempts == 2
        assert state.request_receipt_sha256 == before[
            "request_receipt_sha256"
        ]
        assert state.execution_receipt_sha256 == before[
            "execution_receipt_sha256"
        ]
    finally:
        engine.shutdown()


def test_second_failure_closes_as_unavailable_without_speech(
    monkeypatch, tmp_path
):
    _configure(monkeypatch, tmp_path, "speech-exhaust-key")
    engine = Guala()
    restored = None
    calls = []
    try:
        release = _live_speech(engine, name="exhaust")
        monkeypatch.setattr(runner, "_guala", engine)
        monkeypatch.setattr(
            runner,
            "_synthesize_voice",
            lambda _text: calls.append(True) or None,
        )

        encoded = runner._synthesize_released_voice(
            release.content, "causal_action_cycle_commit"
        )

        assert encoded is None
        assert len(calls) == 2
        assert engine._causal_speech_delivery_state.phase == "exhausted"
        assert engine._causal_speech_delivery_state.attempts == 2
        assert engine._causal_action_dispatcher.status()["active"] is False
        assert engine._causal_speech_release is None
        states = {
            item.sense: item.state
            for item in engine._latest_causal_settlement.interpretations
        }
        assert states == {
            "sight": "sensor_unavailable",
            "sound": "sensor_unavailable",
            "touch": "sensor_unavailable",
            "smell": "sensor_unavailable",
            "taste": "sensor_unavailable",
            "body": "sensor_unavailable",
        }
        assert engine._latest_causal_settlement.language_events == ()

        restored = Guala()
        assert restored.restore_causal_speech_delivery_checkpoint(
            str(tmp_path)
        ) is True
        assert restored._causal_speech_delivery_state.phase == "exhausted"
        assert restored._causal_action_dispatcher.status()["active"] is False
    finally:
        engine.shutdown()
        if restored is not None:
            restored.shutdown()


@pytest.mark.parametrize(
    ("phase", "expected_attempts", "synthesis_calls", "terminal"),
    (
        ("queued", 1, 1, "completed"),
        ("attempt_started", 2, 1, "completed"),
        ("wav_ready", 1, 0, "completed"),
        ("observation_started", 1, 0, "exhausted"),
    ),
)
def test_restart_at_each_persisted_phase_never_duplicates_observation(
    monkeypatch,
    tmp_path,
    phase,
    expected_attempts,
    synthesis_calls,
    terminal,
):
    _configure(monkeypatch, tmp_path, f"restart-{phase}-key")
    writer = Guala()
    restored = None
    exact_wav = _wav_bytes(660)
    try:
        release = _live_speech(writer, name=f"restart-{phase}")
        if phase != "queued":
            writer.prepare_causal_speech_delivery(
                release.content, state_dir=str(tmp_path)
            )
        if phase in {"wav_ready", "observation_started"}:
            writer.record_causal_speech_wav(
                exact_wav, state_dir=str(tmp_path)
            )
        if phase == "observation_started":
            writer.begin_causal_speech_observation(
                state_dir=str(tmp_path)
            )
        assert writer._full_field_prediction.status()["armed_action"] is True
        assert writer._full_field_prediction.relation_records() == ()

        restored = Guala()
        assert restored.restore_causal_speech_delivery_checkpoint(
            str(tmp_path)
        ) is True
        assert restored._full_field_prediction.status()["armed_action"] is False
        attempt = restored._full_field_prediction.current_attempt()
        if attempt is not None:
            assert attempt.mode == "passive"
        calls = []
        monkeypatch.setattr(runner, "_guala", restored)
        monkeypatch.setattr(
            runner,
            "_synthesize_voice",
            lambda _text: calls.append(True)
            or base64.b64encode(exact_wav).decode("ascii"),
        )

        result = runner.resume_pending_causal_speech_delivery()

        assert len(calls) == synthesis_calls
        assert restored._causal_speech_delivery_state.phase == terminal
        assert restored._causal_speech_delivery_state.attempts == expected_attempts
        assert restored._causal_action_dispatcher.status()["active"] is False
        assert restored._full_field_prediction.relation_records() == ()
        if terminal == "completed":
            assert base64.b64decode(result, validate=True) == exact_wav
            assert {
                item.sense: item.state
                for item in restored._latest_causal_settlement.interpretations
            }["sound"] == "observed"
        else:
            assert result is None
            assert restored._causal_speech_delivery_state.wav_bytes == exact_wav
            assert all(
                item.state == "sensor_unavailable"
                for item in restored._latest_causal_settlement.interpretations
            )
    finally:
        writer.shutdown()
        if restored is not None:
            restored.shutdown()


def test_restart_finishes_exhaustion_interrupted_before_failure_closure(
    monkeypatch, tmp_path
):
    _configure(monkeypatch, tmp_path, "exhaustion-closure-restart-key")
    writer = Guala()
    restored = None
    exact_wav = _wav_bytes(690)
    try:
        release = _live_speech(writer, name="exhaustion-closure-restart")
        writer.prepare_causal_speech_delivery(
            release.content, state_dir=str(tmp_path)
        )
        writer.record_causal_speech_wav(
            exact_wav, state_dir=str(tmp_path)
        )
        writer.begin_causal_speech_observation(state_dir=str(tmp_path))

        def interrupt_before_closure():
            raise RuntimeError("process stopped before failure closure")

        monkeypatch.setattr(
            writer,
            "_settle_causal_speech_unavailable_locked",
            interrupt_before_closure,
        )
        with pytest.raises(RuntimeError, match="before failure closure"):
            writer.fail_causal_speech_delivery(
                stage="engine_observation",
                error=RuntimeError("uncertain observation"),
                state_dir=str(tmp_path),
                uncertain_observation=True,
            )

        restored = Guala()
        assert restored.restore_causal_speech_delivery_checkpoint(
            str(tmp_path)
        ) is True

        assert restored._causal_speech_delivery_state.phase == "exhausted"
        assert restored._causal_action_dispatcher.status()["active"] is False
        assert all(
            item.state == "sensor_unavailable"
            for item in restored._latest_causal_settlement.interpretations
        )
    finally:
        writer.shutdown()
        if restored is not None:
            restored.shutdown()


def test_noncausal_release_preserves_existing_voice_behavior(monkeypatch):
    encoded = base64.b64encode(b"legacy-audio").decode("ascii")
    calls = []
    monkeypatch.setattr(
        runner,
        "_synthesize_voice",
        lambda text: calls.append(text) or encoded,
    )

    assert runner._synthesize_released_voice(
        "ordinary release", "assemblage_commit"
    ) == encoded
    assert calls == ["ordinary release"]


def test_repeated_restarts_cannot_exceed_two_authorized_attempts(
    monkeypatch, tmp_path
):
    _configure(monkeypatch, tmp_path, "repeated-restart-key")
    first = Guala()
    second = None
    third = None
    try:
        release = _live_speech(first, name="repeated-restart")
        first.prepare_causal_speech_delivery(
            release.content, state_dir=str(tmp_path)
        )

        second = Guala()
        second.restore_causal_speech_delivery_checkpoint(str(tmp_path))
        assert second._causal_speech_delivery_state.phase == "retryable"
        assert second._causal_speech_delivery_state.attempts == 1
        second.prepare_causal_speech_delivery(
            release.content, state_dir=str(tmp_path)
        )

        third = Guala()
        third.restore_causal_speech_delivery_checkpoint(str(tmp_path))

        assert third._causal_speech_delivery_state.phase == "exhausted"
        assert third._causal_speech_delivery_state.attempts == 2
        assert third._causal_action_dispatcher.status()["active"] is False
        monkeypatch.setattr(runner, "_guala", third)
        assert runner.resume_pending_causal_speech_delivery() is None
    finally:
        first.shutdown()
        if second is not None:
            second.shutdown()
        if third is not None:
            third.shutdown()


def test_terminal_checkpoint_cannot_replace_a_newer_live_execution(
    monkeypatch, tmp_path
):
    _configure(monkeypatch, tmp_path, "terminal-newer-live-key")
    prior = Guala()
    current = None
    checkpoint = tmp_path / "guala_causal_speech_delivery.json"
    try:
        prior_release = _live_speech(prior, name="prior-terminal")
        monkeypatch.setattr(runner, "_guala", prior)
        monkeypatch.setattr(
            runner,
            "_synthesize_voice",
            lambda _text: base64.b64encode(_wav_bytes(715)).decode("ascii"),
        )
        assert runner._synthesize_released_voice(
            prior_release.content, "causal_action_cycle_commit"
        )
        terminal_checkpoint = checkpoint.read_bytes()

        current = Guala()
        _live_speech(current, name="newer-live")
        newer = current.causal_speech_output_status()
        checkpoint.write_bytes(terminal_checkpoint)

        assert current.restore_causal_speech_delivery_checkpoint(
            str(tmp_path)
        ) is True

        preserved = current.causal_speech_output_status()
        assert preserved["request_receipt_sha256"] == newer[
            "request_receipt_sha256"
        ]
        assert preserved["execution_receipt_sha256"] == newer[
            "execution_receipt_sha256"
        ]
        assert current._causal_action_dispatcher.status()["active"] is True
    finally:
        prior.shutdown()
        if current is not None:
            current.shutdown()


def test_embedded_typed_path_returns_exact_server_wav(
    monkeypatch, tmp_path
):
    import dsf_ai_service.app as app_module

    exact_wav = _wav_bytes(770)
    encoded = base64.b64encode(exact_wav).decode("ascii")

    class _EmbeddedEngine:
        tick = 17
        is_asleep = False
        vocab = {"hello", "daddy"}
        _pictures = {}

        def converse(self, text, source):
            assert text == "hello guala"
            assert source == "joe"
            return ConversationTurnResult(
                response="hello daddy",
                response_source="causal_action_cycle_commit",
                emission_id="typed-causal-emission",
                committed_sections=("causal_action_cycle",),
                source_turn_index=1,
            )

        def log_event(self, *_args, **_kwargs):
            return None

    task_id = "typed-causal-task"
    app_module._converse_tasks[task_id] = {
        "task_id": task_id,
        "status": "queued",
        "phase": None,
        "response": None,
        "response_source": None,
        "motifs": 0,
        "started_tick": 17,
        "started_at": time.time(),
        "source": "joe",
    }
    monkeypatch.setattr(app_module, "_guala", _EmbeddedEngine())
    monkeypatch.setattr(app_module, "_is_remote", lambda: False)
    calls = []
    monkeypatch.setattr(
        runner,
        "_synthesize_released_voice",
        lambda text, source: calls.append((text, source)) or encoded,
    )

    asyncio.run(
        app_module._run_converse(task_id, "hello guala", "joe")
    )

    task = app_module._converse_tasks.pop(task_id)
    assert task["status"] == "complete"
    assert task["speech_output_status"] == "delivered"
    assert base64.b64decode(task["speech_audio"], validate=True) == exact_wav
    assert calls == [("hello daddy", "causal_action_cycle_commit")]


def test_embedded_spoken_path_returns_exact_server_wav(monkeypatch):
    import dsf_ai_service.app as app_module
    from tests.test_auditory_causal_conversation_boundary import _terminal

    terminal = _terminal("hello guala")
    exact_wav = _wav_bytes(880)
    encoded = base64.b64encode(exact_wav).decode("ascii")

    class _EmbeddedEngine:
        tick = 29

        def converse(self, text, source, causal_intake):
            assert text == terminal.tutor_label
            assert source == "auditory:unresolved_source"
            assert causal_intake == terminal
            return ConversationTurnResult(
                response="hello daddy",
                response_source="causal_action_cycle_commit",
                emission_id="spoken-causal-emission",
                committed_sections=("causal_action_cycle",),
                causal_experience_id=terminal.event_id,
                causal_intake_receipt_sha256=(
                    terminal.authority_receipt_sha256
                ),
            )

        def _log_substrate_event(self, *_args, **_kwargs):
            return None

    app_module._voice_turn_results.clear()
    app_module._voice_reply_pending = None
    app_module._voice_reply_active_event_id = terminal.event_id
    app_module._voice_reply_busy.set()
    monkeypatch.setattr(app_module, "_guala", _EmbeddedEngine())
    calls = []
    monkeypatch.setattr(
        runner,
        "_synthesize_released_voice",
        lambda text, source: calls.append((text, source)) or encoded,
    )

    app_module._run_voice_reply(terminal, 29)

    delivery = app_module._voice_turn_results.pop(terminal.event_id)
    assert delivery["status"] == "completed"
    assert delivery["speech_output_status"] == "delivered"
    assert delivery["speech"] == "hello daddy"
    assert base64.b64decode(
        delivery["speech_audio"], validate=True
    ) == exact_wav
    assert calls == [("hello daddy", "causal_action_cycle_commit")]


def test_embedded_spoken_path_reports_exhausted_actuator_without_speech(
    monkeypatch,
):
    import dsf_ai_service.app as app_module
    from tests.test_auditory_causal_conversation_boundary import _terminal

    terminal = _terminal("hello guala")

    class _EmbeddedEngine:
        tick = 31

        def converse(self, text, source, causal_intake):
            return ConversationTurnResult(
                response="hello daddy",
                response_source="causal_action_cycle_commit",
                emission_id="spoken-exhausted-emission",
                committed_sections=("causal_action_cycle",),
                causal_experience_id=terminal.event_id,
                causal_intake_receipt_sha256=(
                    terminal.authority_receipt_sha256
                ),
            )

        def _log_substrate_event(self, *_args, **_kwargs):
            return None

    app_module._voice_turn_results.clear()
    app_module._voice_reply_pending = None
    app_module._voice_reply_active_event_id = terminal.event_id
    app_module._voice_reply_busy.set()
    monkeypatch.setattr(app_module, "_guala", _EmbeddedEngine())
    monkeypatch.setattr(
        runner, "_synthesize_released_voice", lambda _text, _source: None
    )

    app_module._run_voice_reply(terminal, 31)

    delivery = app_module._voice_turn_results.pop(terminal.event_id)
    assert delivery["status"] == "completed_without_speech"
    assert delivery["speech_output_status"] == "actuator_unavailable"
    assert delivery["intended_speech"] == "hello daddy"
    assert "speech" not in delivery
    assert delivery["speech_audio"] is None


def test_browser_never_resynthesizes_a_causal_server_wav():
    page = (
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "dsf_ai_service",
            "static",
            "gualaloom.html",
        )
    )
    with open(page, encoding="utf-8") as page_file:
        source = page_file.read()

    assert "function gualaPlayExactWav" in source
    assert "gualaPlayExactWav(d.speech_audio);" in source
    assert (
        "if(result.speech_audio)gualaPlayExactWav(result.speech_audio)"
        in source
    )
    assert "speech actuator unavailable — intended reply" in source
