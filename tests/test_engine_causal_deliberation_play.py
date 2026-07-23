from __future__ import annotations

import inspect

from dsf_ai_service.substrate.causal_action_cycle import ActionCommand
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    MoveCommand,
    PoseMM,
    PositionMM,
    encode_command,
)
from dsf_ai_service.v4.gualaloom_v5_engine import Guala


def _configure(monkeypatch, key: str) -> None:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    monkeypatch.setenv("SELF_VOICE_AUDIO_ENABLED", "0")
    monkeypatch.setenv("GUALA_CAUSAL_ACTION_KEY", key)


def _move(y_mm: int, heading: int) -> bytes:
    return encode_command(MoveCommand(PoseMM(
        PositionMM(1000, y_mm, 0),
        heading,
    )))


def _enable_test_publisher(guala: Guala) -> None:
    guala._authoritative_hot_generation_publisher = lambda **_values: None
    guala.save_hot_state = lambda _state_dir: None


def test_guided_relations_drive_two_actual_w1_steps_then_recurrence(
    monkeypatch,
) -> None:
    _configure(monkeypatch, "deliberation-two-step-key")
    guala = Guala()
    try:
        _enable_test_publisher(guala)
        first = guala.durably_demonstrate_embodied_action(
            tutor_id="joe",
            nonce="deliberation-two-step-demo-0001",
            port_id=PORT_ID,
            command_payload=_move(1400, 90_000),
            state_dir="unused",
        )
        assert first["causal_play"]["steps"] == []

        second = guala.durably_demonstrate_embodied_action(
            tutor_id="joe",
            nonce="deliberation-two-step-demo-0002",
            port_id=PORT_ID,
            command_payload=_move(1000, 0),
            state_dir="unused",
        )
        play = second["causal_play"]
        assert len(play["steps"]) == 2
        assert play["dispatch_reason"] == "recurrence"
        assert guala._embodiment_world.observation_snapshot().revision == 4
        assert guala._causal_deliberation.status()["terminal_reason"] == (
            "recurrence"
        )
        assert guala._causal_action_dispatcher.status()["active"] is False
        assert guala._causal_action_cycle.status()["closures"] == 2
    finally:
        guala.shutdown()


def test_legacy_speech_relation_never_enters_guided_play_admission(
    monkeypatch,
) -> None:
    _configure(monkeypatch, "deliberation-filter-key")
    guala = Guala()
    try:
        _enable_test_publisher(guala)
        before = guala._embodiment_world.observation_snapshot()
        embodied = guala._embodiment_sensory_outcome_authority.transduce(
            before,
            causal_owner=guala._embodiment_outcome_causal_owner,
            commit=False,
        )
        guala._causal_action_cycle.accept(embodied.causal_settlement)
        guala._causal_action_cycle.teach(
            trigger_reference=embodied.causal_settlement.event_id,
            action=ActionCommand.speech("legacy"),
            source="joe",
            nonce="deliberation-legacy-speech-0001",
        )

        record = guala._run_causal_play_episode(
            trigger="external_world_change",
        )
        assert record["dispatch_status"] == "unknown"
        assert record["steps"] == []
        assert guala._embodiment_world.observation_snapshot().revision == 0
        assert guala._causal_action_cycle.status()["intents"] == 0
    finally:
        guala.shutdown()


def test_play_is_not_a_scalar_scheduler_candidate_or_tick_process(
    monkeypatch,
) -> None:
    _configure(monkeypatch, "deliberation-scheduler-key")
    guala = Guala()
    try:
        assert all(
            kind != "PLAYING"
            for kind, _target in guala._candidate_activities()
        )
        source = inspect.getsource(
            Guala._run_causal_play_episode
        ).lower()
        forbidden = (
            "self.needs",
            "self.atlas",
            "salience",
            "routing_chis",
            "self.tick",
            "random",
            "top_k",
            "score",
        )
        assert all(item not in source for item in forbidden)
    finally:
        guala.shutdown()


def test_terminal_chain_restores_without_replaying_world_actions(
    monkeypatch,
    tmp_path,
) -> None:
    _configure(monkeypatch, "deliberation-restore-key")
    writer = Guala()
    restored = None
    try:
        writer._authoritative_hot_generation_publisher = (
            lambda **_values: None
        )
        writer.save_full_state(str(tmp_path))
        writer.durably_demonstrate_embodied_action(
            tutor_id="joe",
            nonce="deliberation-restore-demo-0001",
            port_id=PORT_ID,
            command_payload=_move(1400, 90_000),
            state_dir=str(tmp_path),
        )
        final = writer.durably_demonstrate_embodied_action(
            tutor_id="joe",
            nonce="deliberation-restore-demo-0002",
            port_id=PORT_ID,
            command_payload=_move(1000, 0),
            state_dir=str(tmp_path),
        )
        assert len(final["causal_play"]["steps"]) == 2
        assert writer._embodiment_world.observation_snapshot().revision == 4
        writer.save_full_state(str(tmp_path))
        writer.shutdown()
        writer = None

        restored = Guala()
        restored.load_full_state(str(tmp_path))
        assert restored._load_successful, restored._load_errors
        assert restored._embodiment_world.observation_snapshot().revision == 4
        assert restored._causal_action_cycle.status()["closures"] == 2
        assert restored._causal_deliberation.status()["terminal_reason"] == (
            "recurrence"
        )
        assert restored._causal_action_dispatcher.status()["active"] is False
    finally:
        if writer is not None:
            writer.shutdown()
        if restored is not None:
            restored.shutdown()
