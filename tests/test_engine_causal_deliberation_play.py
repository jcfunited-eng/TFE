from __future__ import annotations

import inspect
from dataclasses import replace

import pytest

from dsf_ai_service.substrate.causal_action_cycle import ActionCommand
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    MoveCommand,
    PickCommand,
    PlaceCommand,
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
        action_outcomes = []
        advances = []
        mount_action_outcome = (
            guala._w1_physical_evidence.mount_action_outcome
        )
        advance = guala._causal_deliberation.advance

        def capture_action_outcome(
            execution, *, commit=True, reserve=False
        ):
            mounted = mount_action_outcome(
                execution,
                commit=commit,
                reserve=reserve,
            )
            if reserve:
                action_outcomes.append((execution, mounted))
            return mounted

        def capture_advance(settlement, **values):
            advances.append((settlement, values.get("action_outcome")))
            return advance(settlement, **values)

        guala._w1_physical_evidence.mount_action_outcome = (
            capture_action_outcome
        )
        guala._causal_deliberation.advance = capture_advance

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
        assert len(action_outcomes) == len(advances) == 2
        for (execution, mounted), (stable, transition) in zip(
            action_outcomes, advances, strict=True
        ):
            receipt = mounted.evidence_receipt
            assert receipt.world_execution_receipt_sha256 == (
                execution.authority_receipt_sha256
            )
            assert receipt.world_observation_before_receipt_sha256 == (
                execution.before.authority_receipt_sha256
            )
            assert receipt.world_observation_after_receipt_sha256 == (
                execution.after.authority_receipt_sha256
            )
            assert transition == mounted.causal_settlement
            assert stable.authority_receipt_sha256 != (
                transition.authority_receipt_sha256
            )
    finally:
        guala.shutdown()


def test_guided_pick_and_replace_replays_two_physical_steps_then_recurrence(
    monkeypatch,
) -> None:
    _configure(monkeypatch, "deliberation-pick-place-key")
    guala = Guala()
    try:
        _enable_test_publisher(guala)
        first = guala.durably_demonstrate_embodied_action(
            tutor_id="joe",
            nonce="deliberation-pick-demo-0001",
            port_id=PORT_ID,
            command_payload=encode_command(PickCommand("W1-object-1")),
            state_dir="unused",
        )
        assert first["causal_play"]["steps"] == []
        second = guala.durably_demonstrate_embodied_action(
            tutor_id="joe",
            nonce="deliberation-place-demo-0002",
            port_id=PORT_ID,
            command_payload=encode_command(PlaceCommand(
                "W1-object-1",
                PositionMM(1500, 1000, 0),
            )),
            state_dir="unused",
        )

        play = second["causal_play"]
        assert len(play["steps"]) == 2
        assert play["dispatch_status"] == "completed"
        assert play["dispatch_reason"] == "recurrence"
        world = guala._embodiment_world.observation_snapshot()
        assert world.revision == 4
        body = next(
            item
            for item in world.bodies
            if item.body_id == world.self_body_id
        )
        object_one = next(
            item
            for item in world.objects
            if item.object_id == "W1-object-1"
        )
        assert body.held_object_id is None
        assert object_one.held_by_body_id is None
        assert object_one.position == PositionMM(1500, 1000, 0)
        assert guala._causal_deliberation.status()["terminal_reason"] == (
            "recurrence"
        )
        assert guala._causal_action_dispatcher.status()["active"] is False
        assert guala._causal_action_cycle.status()["closures"] == 2
    finally:
        guala.shutdown()


def test_live_play_never_calls_legacy_geometry_transducer(monkeypatch) -> None:
    _configure(monkeypatch, "deliberation-no-legacy-key")
    guala = Guala()
    try:
        _enable_test_publisher(guala)

        def reject_legacy(*_args, **_kwargs):
            raise AssertionError("legacy geometry transducer was called")

        guala._embodiment_sensory_outcome_authority.transduce = reject_legacy
        guala.durably_demonstrate_embodied_action(
            tutor_id="joe",
            nonce="deliberation-no-legacy-demo-0001",
            port_id=PORT_ID,
            command_payload=_move(1400, 90_000),
            state_dir="unused",
        )
        result = guala.durably_demonstrate_embodied_action(
            tutor_id="joe",
            nonce="deliberation-no-legacy-demo-0002",
            port_id=PORT_ID,
            command_payload=_move(1000, 0),
            state_dir="unused",
        )

        assert len(result["causal_play"]["steps"]) == 2
    finally:
        guala.shutdown()


def test_unsettled_w1_action_evidence_rolls_back_the_entire_live_step(
    monkeypatch,
) -> None:
    _configure(monkeypatch, "deliberation-unsettled-w1-key")
    guala = Guala()
    try:
        _enable_test_publisher(guala)
        guala.durably_demonstrate_embodied_action(
            tutor_id="joe",
            nonce="deliberation-unsettled-w1-demo-0001",
            port_id=PORT_ID,
            command_payload=_move(1400, 90_000),
            state_dir="unused",
        )
        current = guala._embodiment_world.observation_snapshot()
        returned = guala._embodiment_world.execute_port_command(
            port_id=PORT_ID,
            command_payload=_move(1000, 0),
            causal_intent_receipt_sha256="4" * 64,
            expected_revision=current.revision,
        )
        assert returned.disposition == "applied"
        before_world = guala._embodiment_world.encoded_snapshot()
        before_cycle = guala._causal_action_cycle.encoded_snapshot()
        before_dispatcher = (
            guala._causal_action_dispatcher.encoded_snapshot()
        )
        owner_before_action = []
        mount_action_outcome = (
            guala._w1_physical_evidence.mount_action_outcome
        )

        def unsettle(execution, *, commit=True, reserve=False):
            assert commit is False
            assert reserve is True
            owner_before_action.append(dict(
                guala._embodiment_outcome_causal_owner.status()
            ))
            mounted = mount_action_outcome(
                execution,
                commit=commit,
                reserve=reserve,
            )
            return replace(
                mounted,
                evidence_receipt=None,
            )

        guala._w1_physical_evidence.mount_action_outcome = unsettle
        with pytest.raises(RuntimeError, match="did not produce"):
            guala._run_causal_play_episode(trigger="test")

        assert guala._embodiment_world.encoded_snapshot() == before_world
        assert guala._causal_action_cycle.encoded_snapshot() == before_cycle
        assert (
            guala._causal_action_dispatcher.encoded_snapshot()
            == before_dispatcher
        )
        assert guala._causal_action_dispatcher.status()["active"] is False
        assert len(owner_before_action) == 1
        assert guala._embodiment_outcome_causal_owner.status() == (
            owner_before_action[0]
        )
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
