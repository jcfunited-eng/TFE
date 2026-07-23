from __future__ import annotations

import io
import math
import wave
from fractions import Fraction

import numpy as np
import pytest

from dsf_ai_service.substrate.causal_action_cycle import ActionCommand
from dsf_ai_service.substrate.auditory_reciprocity import (
    AuditoryReciprocityOwner,
)
from dsf_ai_service.substrate.auditory_tutor_authority import (
    AuditoryTutorAuthority,
)
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    MoveCommand,
    PoseMM,
    PositionMM,
    encode_command,
)
from dsf_ai_service.v4.gualaloom_v5_engine import Guala
from test_causal_action_engine_integration import _artifacts
from test_causal_settlement_dispatcher import _settlement


def _configure(monkeypatch, key: str) -> None:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    monkeypatch.setenv("SELF_VOICE_AUDIO_ENABLED", "0")
    monkeypatch.setenv("GUALA_CAUSAL_ACTION_KEY", key)


def _teach(guala: Guala, trigger, action: ActionCommand, nonce: str) -> None:
    guala._causal_action_cycle.accept(trigger)
    guala._causal_action_cycle.teach(
        trigger_reference=trigger.event_id,
        action=action,
        source="joe",
        nonce=nonce,
    )


def _wav_bytes(*, frequency_hz: int = 440, sample_count: int = 800) -> bytes:
    samples = np.asarray(
        [
            int(12_000 * math.sin(2 * math.pi * frequency_hz * index / 16_000))
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


def test_w1_dispatch_closes_on_exact_embodied_outcome_without_recursive_action(
    monkeypatch,
) -> None:
    _configure(monkeypatch, "dispatcher-engine-w1-key")
    guala = Guala()
    try:
        taught = _settlement("engine-w1-teach")
        trigger = _settlement("engine-w1-trigger", routing_chis=(73,))
        command = ActionCommand.embodiment(
            PORT_ID,
            encode_command(
                MoveCommand(
                    target_pose=PoseMM(
                        position=PositionMM(1000, 2000, 0),
                        heading_millidegrees=90_000,
                    )
                )
            ),
        )
        _teach(
            guala,
            taught,
            command,
            "engine-w1-teacher-nonce-0001",
        )
        dispatches = []
        dispatch = guala._causal_action_dispatcher.dispatch

        def tracked(settlement):
            dispatches.append(settlement.authority_receipt_sha256)
            return dispatch(settlement)

        guala._causal_action_dispatcher.dispatch = tracked
        guala._accept_causal_settlement(trigger)

        observed = guala._embodiment_world.observation_snapshot()
        assert observed.revision == 1
        assert observed.body.pose.position == PositionMM(1000, 2000, 0)
        assert len(dispatches) == 1
        assert guala._causal_settlement_accepted == 2
        assert guala._latest_causal_settlement != trigger
        status = guala._causal_action_cycle.status()
        assert status["closures"] == 1
        assert status["intents"] == 0
        assert status["executions"] == 0
        assert status["outcomes"] == 0
        assert guala._causal_action_dispatcher.status() == {
            "active": False,
            "capacity": 1,
            "encoded_state_bytes": (
                guala._causal_action_dispatcher.status()["encoded_state_bytes"]
            ),
            "latest_terminal_status": "completed",
            "phase": "idle",
        }
    finally:
        guala.shutdown()


@pytest.mark.parametrize(
    "failed_event_kind",
    ("causal_experience_accepted", "causal_settlement_dispatched"),
)
def test_committed_dispatch_survives_loud_telemetry_failure(
    monkeypatch,
    capsys,
    failed_event_kind: str,
) -> None:
    _configure(monkeypatch, f"dispatcher-telemetry-{failed_event_kind}")
    guala = Guala()
    try:
        trigger = _settlement(f"engine-telemetry-{failed_event_kind}")
        real_log = guala._log_substrate_event

        def fail_one_event(event_kind, **detail):
            if event_kind == failed_event_kind:
                raise RuntimeError("injected observer failure")
            return real_log(event_kind, **detail)

        guala._log_substrate_event = fail_one_event
        guala._accept_causal_settlement(trigger)

        assert guala._causal_settlement_accepted == 1
        assert guala._latest_causal_settlement == trigger
        assert guala._causal_action_cycle.status()["working_perceptions"] == 1
        assert guala._causal_last_dispatch_result.status == "unknown"
        stderr = capsys.readouterr().err
        assert failed_event_kind in stderr
        assert "after authority commit (non-fatal)" in stderr
        assert "injected observer failure" in stderr
    finally:
        guala.shutdown()


def test_speech_release_is_consumed_once_and_only_actual_wav_closes(
    monkeypatch,
) -> None:
    _configure(monkeypatch, "dispatcher-engine-speech-key")
    guala = Guala()
    try:
        taught = _settlement("engine-speech-teach")
        trigger = _settlement("engine-speech-trigger", routing_chis=(44,))
        unrelated = _settlement("engine-speech-unrelated", frequency=13)
        _teach(
            guala,
            taught,
            ActionCommand.speech("hello"),
            "engine-speech-teacher-nonce-0001",
        )
        dispatches = []
        dispatch = guala._causal_action_dispatcher.dispatch

        def tracked(settlement):
            dispatches.append(settlement.authority_receipt_sha256)
            return dispatch(settlement)

        guala._causal_action_dispatcher.dispatch = tracked
        guala._accept_causal_settlement(trigger)
        released = guala._emit_from_invariants(
            (), (), causal_settlement=trigger
        )
        assert released.status == "committed"
        assert released.content == "hello"
        assert len(dispatches) == 1

        duplicate = guala._emit_from_invariants(
            (), (), causal_settlement=trigger
        )
        assert duplicate.content == ""
        assert duplicate.stop_reason == "causal_speech_audio_outcome_pending"
        assert len(dispatches) == 1

        guala._accept_causal_settlement(unrelated)
        pending = guala._causal_action_cycle.status()
        assert pending["intents"] == 1
        assert pending["executions"] == 1
        assert pending["outcomes"] == 0
        assert guala._causal_action_dispatcher.status()["active"] is True

        outcome = guala.observe_causal_speech_output(_wav_bytes())
        assert outcome["status"] == "completed"
        assert outcome["outcome_settlement_receipt_sha256"]
        closed = guala._causal_action_cycle.status()
        assert closed["closures"] == 1
        assert closed["intents"] == 0
        assert closed["executions"] == 0
        assert closed["outcomes"] == 0
        assert guala._causal_action_dispatcher.status()["active"] is False
        assert guala.causal_speech_output_status()["status"] == "idle"
        with pytest.raises(ValueError, match="no delivered"):
            guala.observe_causal_speech_output(_wav_bytes(frequency_hz=550))
    finally:
        guala.shutdown()


def test_causal_conversation_does_not_enter_legacy_text_or_self_voice_hearing(
    monkeypatch,
) -> None:
    _configure(monkeypatch, "dispatcher-engine-no-duplicate-key")
    reciprocity = AuditoryReciprocityOwner(
        log_event=lambda *_args, **_kwargs: None,
        tutor_authority=AuditoryTutorAuthority.unrequired(),
    )
    _tb, _tl5, trigger_terminal, trigger = _artifacts(
        name="dispatcher-no-duplicate-trigger",
        label="hello guala",
        values=(Fraction(1, 8),),
        reciprocity=reciprocity,
        teach=True,
    )
    _ab, _al5, action_terminal, action = _artifacts(
        name="dispatcher-no-duplicate-action",
        label="hello daddy",
        values=(Fraction(5, 8),),
        reciprocity=reciprocity,
        teach=True,
    )
    _cb, current_l5, current_terminal, _current = _artifacts(
        name="dispatcher-no-duplicate-current",
        label="hello guala",
        values=(Fraction(1, 8),),
        reciprocity=reciprocity,
        stream_id="dispatcher-no-duplicate-stream",
        source_sample_start=320,
    )
    guala = Guala()
    try:
        guala._causal_action_cycle.accept(trigger)
        guala._causal_action_cycle.accept(action)
        guala.teach_causal_action(
            trigger_experience_id=trigger_terminal.event_id,
            action_experience_id=action_terminal.event_id,
            source="joe",
        )
        with guala._auditory_incremental_terminals._lock:
            guala._auditory_incremental_terminals._issue_locked(
                current_terminal,
                current_l5,
            )
        self_heard = []
        guala._self_hear = lambda *_args, **_kwargs: self_heard.append(True)

        class _Finished:
            def join(self, timeout=None):
                return None

        def run_inline(target, args=(), **_kwargs):
            target(*args)
            return _Finished()

        guala._start_engine_background_thread = run_inline
        turn = guala.converse(
            current_terminal.tutor_label,
            source="auditory:unresolved_source",
            causal_intake=current_terminal,
        )
        assert turn.response == "hello daddy"
        assert turn.response_source == "causal_action_cycle_commit"
        assert self_heard == []
        assert guala._causal_action_dispatcher.status()["active"] is True
        assert guala.causal_speech_output_status()["status"] == (
            "awaiting_audio_outcome"
        )
    finally:
        guala.shutdown()


def test_speech_failure_retains_same_authenticated_request_for_explicit_retry(
    monkeypatch,
) -> None:
    _configure(monkeypatch, "dispatcher-engine-retry-key")
    guala = Guala()
    try:
        taught = _settlement("engine-retry-teach")
        trigger = _settlement("engine-retry-trigger")
        _teach(
            guala,
            taught,
            ActionCommand.speech("retry me"),
            "engine-retry-teacher-nonce-0001",
        )
        guala._accept_causal_settlement(trigger)
        first = guala._emit_from_invariants((), (), causal_settlement=trigger)
        assert first.content == "retry me"
        before = guala.causal_speech_output_status()
        failed = guala.report_causal_speech_output_failure(
            stage="tts_synthesis",
            error="synthesizer returned no WAV",
        )
        assert failed["status"] == "retryable"
        assert failed["request_receipt_sha256"] == before[
            "request_receipt_sha256"
        ]
        rearmed = guala.retry_causal_speech_release()
        assert rearmed["status"] == "queued"
        second = guala._emit_from_invariants((), ())
        assert second.content == "retry me"
        after = guala.causal_speech_output_status()
        assert after["request_receipt_sha256"] == before[
            "request_receipt_sha256"
        ]
        assert after["execution_receipt_sha256"] == before[
            "execution_receipt_sha256"
        ]
    finally:
        guala.shutdown()


def test_speech_over_tts_boundary_is_authenticated_rejection_not_truncation(
    monkeypatch,
) -> None:
    _configure(monkeypatch, "dispatcher-engine-overcap-key")
    guala = Guala()
    try:
        taught = _settlement("engine-overcap-teach")
        trigger = _settlement("engine-overcap-trigger")
        _teach(
            guala,
            taught,
            ActionCommand.speech("x" * 201),
            "engine-overcap-teacher-nonce-0001",
        )
        guala._accept_causal_settlement(trigger)
        rejected = guala._emit_from_invariants(
            (), (), causal_settlement=trigger
        )
        assert rejected.content == ""
        assert rejected.status == "rejected"
        assert rejected.stop_reason == "speech_action_exceeds_tts_boundary"
        assert guala._causal_speech_release is None
        assert guala._causal_action_dispatcher.status()["active"] is False
        assert guala._causal_action_cycle.status()["intents"] == 0
    finally:
        guala.shutdown()


def test_dispatcher_and_retryable_speech_transport_restore_without_legacy_pair(
    monkeypatch,
    tmp_path,
) -> None:
    _configure(monkeypatch, "dispatcher-engine-persistence-key")
    writer = Guala()
    restored = None
    try:
        taught = _settlement("engine-persist-teach")
        trigger = _settlement("engine-persist-trigger")
        _teach(
            writer,
            taught,
            ActionCommand.speech("persist me"),
            "engine-persist-teacher-nonce-0001",
        )
        writer._accept_causal_settlement(trigger)
        assert writer._emit_from_invariants(
            (), (), causal_settlement=trigger
        ).content == "persist me"
        writer.report_causal_speech_output_failure(
            stage="audio_device",
            error="output device unavailable",
        )
        payload = writer._teaching_persistence_payload()
        assert payload["causal_action_dispatcher"] is not None
        assert payload["causal_speech_release"] is not None
        assert "causal_action_cycle_pending_execution_receipt" not in payload
        assert "causal_action_cycle_pending_trigger_receipt" not in payload
        writer._validate_teaching_payload(payload, writer.tick)
        writer.save_full_state(str(tmp_path))
        writer.shutdown()
        writer = None

        restored = Guala()
        restored.load_full_state(str(tmp_path))
        assert restored._load_successful, restored._load_errors
        assert restored._causal_action_dispatcher.status()["active"] is True
        status = restored.causal_speech_output_status()
        assert status["status"] == "retryable"
        assert status["retryable"] is True
        assert restored.retry_causal_speech_release()["status"] == "queued"
        assert restored._emit_from_invariants((), ()).content == "persist me"
    finally:
        if writer is not None:
            writer.shutdown()
        if restored is not None:
            restored.shutdown()
