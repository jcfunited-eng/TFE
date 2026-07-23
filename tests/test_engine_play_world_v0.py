"""Production-path proofs for exact embodied PLAYING admission."""

from __future__ import annotations

from copy import deepcopy

import pytest

from dsf_ai_service.substrate.causal_action_cycle import ActionCommand
from dsf_ai_service.substrate.embodiment_sensory_outcome import (
    EmbodimentSensoryOutcomeAuthority,
)
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    MoveCommand,
    PickCommand,
    PoseMM,
    PositionMM,
    encode_command,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.v4.gualaloom_v5_engine import (
    ACTIVITY_TICK_BUDGETS,
    PLAY_CAUSAL_ADMISSION_SCHEMA,
    Activity,
    Guala,
)


def _configure(monkeypatch, key: str) -> None:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    monkeypatch.setenv("SELF_VOICE_AUDIO_ENABLED", "0")
    monkeypatch.setenv("GUALA_CAUSAL_ACTION_KEY", key)


def _playing(guala: Guala) -> Activity:
    return Activity(
        kind="PLAYING",
        target=None,
        started_tick=guala.tick,
        expected_end_tick=(
            guala.tick + ACTIVITY_TICK_BUDGETS["PLAYING"]
        ),
    )


def _current_w1_trigger(guala: Guala, key: str):
    owner = ExactCausalExperienceOwner(
        on_settlement=lambda settlement: None,
        log_event=lambda *args, **kwargs: None,
        max_transitions=8,
    )
    return EmbodimentSensoryOutcomeAuthority(
        authority_key=key
    ).transduce(
        guala._embodiment_world.observation_snapshot(),
        causal_owner=owner,
        commit=True,
    ).causal_settlement


def _teach(
    guala: Guala,
    trigger,
    action: ActionCommand,
    nonce: str,
) -> None:
    guala._causal_action_cycle.accept(trigger)
    guala._causal_action_cycle.teach(
        trigger_reference=trigger.event_id,
        action=action,
        source="joe",
        nonce=nonce,
    )


def _move(y: int) -> ActionCommand:
    return ActionCommand.embodiment(
        PORT_ID,
        encode_command(
            MoveCommand(
                target_pose=PoseMM(
                    position=PositionMM(1000, y, 0),
                    heading_millidegrees=90_000,
                )
            )
        ),
    )


def test_playing_admits_current_w1_once_and_bypasses_legacy_authorities(
    monkeypatch,
) -> None:
    key = "play-admission-unknown-key"
    _configure(monkeypatch, key)
    guala = Guala()
    try:
        before = guala._embodiment_world.encoded_snapshot()
        accepted = []
        real_accept = guala._accept_causal_settlement

        def track(settlement):
            accepted.append(settlement.authority_receipt_sha256)
            return real_accept(settlement)

        guala._accept_causal_settlement = track
        activity = _playing(guala)
        assert guala._start_activity(activity) is True
        record = activity.metadata["_causal_play_admission"]
        assert record["schema"] == PLAY_CAUSAL_ADMISSION_SCHEMA
        assert record["dispatch_status"] == "unknown"
        assert record["dispatch_reason"] == "action_unknown"
        assert record["world_revision_before"] == 0
        assert record["world_revision_after"] == 0
        assert len(accepted) == 0
        assert guala._embodiment_outcome_causal_owner.status()["settled"] == 1
        assert guala._embodiment_world.encoded_snapshot() == before

        needs_before = guala.needs.snapshot()
        guala._play_revisit_known_pairing = lambda: pytest.fail(
            "legacy chi revisit became PLAYING authority"
        )
        guala._organism_imagine_tick = lambda **kwargs: pytest.fail(
            "organism imagination became PLAYING authority"
        )
        for tick in (500, 1000, 1500):
            guala.tick = tick
            guala._atick_playing(activity)
        assert guala.needs.snapshot() == needs_before
        assert len(accepted) == 0
        assert guala._admit_playing_world_experience(activity) is True
        assert len(accepted) == 0
    finally:
        guala.shutdown()


def test_legacy_ambiguous_actions_are_excluded_from_guided_play(
    monkeypatch,
) -> None:
    key = "play-admission-ambiguous-key"
    _configure(monkeypatch, key)
    guala = Guala()
    try:
        trigger = _current_w1_trigger(guala, key)
        _teach(guala, trigger, _move(1200), "play-ambiguous-move-0001")
        _teach(
            guala,
            trigger,
            ActionCommand.embodiment(
                PORT_ID, encode_command(PickCommand("W1-object-1"))
            ),
            "play-ambiguous-pick-0001",
        )
        before = guala._embodiment_world.encoded_snapshot()
        needs_before = guala.needs.snapshot()
        activity = _playing(guala)
        assert guala._start_activity(activity) is True
        record = activity.metadata["_causal_play_admission"]
        assert record["dispatch_status"] == "unknown"
        assert record["dispatch_reason"] == "action_unknown"
        assert record["world_revision_before"] == record["world_revision_after"]
        assert guala._embodiment_world.encoded_snapshot() == before
        assert guala._causal_action_cycle.status()["intents"] == 0
        guala._atick_playing(activity)
        assert guala.needs.snapshot() == needs_before
    finally:
        guala.shutdown()


def test_legacy_body_action_cannot_execute_through_guided_play(
    monkeypatch,
) -> None:
    key = "play-admission-action-key"
    _configure(monkeypatch, key)
    guala = Guala()
    try:
        trigger = _current_w1_trigger(guala, key)
        _teach(guala, trigger, _move(2000), "play-action-move-0001")
        activity = _playing(guala)
        assert guala._start_activity(activity) is True

        observed = guala._embodiment_world.observation_snapshot()
        record = activity.metadata["_causal_play_admission"]
        assert record["dispatch_status"] == "unknown"
        assert record["dispatch_phase"] == "selection"
        assert record["world_revision_before"] == 0
        assert record["world_revision_after"] == 0
        assert observed.revision == 0
        assert next(
            item for item in observed.bodies
            if item.body_id == observed.self_body_id
        ).pose.position == PositionMM(1000, 1000, 0)
        assert guala._embodiment_outcome_causal_owner.status()["settled"] == 1
        status = guala._causal_action_cycle.status()
        assert status["closures"] == 0
        assert status["intents"] == status["executions"] == status["outcomes"] == 0
        assert guala._causal_action_dispatcher.status()["active"] is False

        world_after = guala._embodiment_world.encoded_snapshot()
        assert guala._admit_playing_world_experience(activity) is True
        guala._atick_playing(activity)
        assert guala._embodiment_world.encoded_snapshot() == world_after
        assert guala._causal_action_cycle.status()["closures"] == 0
    finally:
        guala.shutdown()


def test_busy_dispatcher_refuses_playing_without_any_play_admission_mutation(
    monkeypatch,
) -> None:
    key = "play-admission-busy-key"
    _configure(monkeypatch, key)
    guala = Guala()
    try:
        trigger = _current_w1_trigger(guala, key)
        _teach(
            guala,
            trigger,
            ActionCommand.speech("hello"),
            "play-busy-speech-0001",
        )
        guala._accept_causal_settlement(trigger)
        assert guala._causal_action_dispatcher.status()["active"] is True

        world_before = guala._embodiment_world.encoded_snapshot()
        cycle_before = guala._causal_action_cycle.encoded_snapshot()
        owner_before = guala._embodiment_outcome_causal_owner.status()
        activity = _playing(guala)
        assert guala._start_activity(activity) is False
        assert guala._current_activity is None
        assert "_causal_play_admission" not in activity.metadata
        assert guala._embodiment_world.encoded_snapshot() == world_before
        assert guala._causal_action_cycle.encoded_snapshot() == cycle_before
        assert guala._embodiment_outcome_causal_owner.status() == owner_before
    finally:
        guala.shutdown()


def test_legacy_rejected_geometry_is_never_dispatched_by_guided_play(
    monkeypatch,
) -> None:
    key = "play-admission-rejected-key"
    _configure(monkeypatch, key)
    guala = Guala()
    try:
        trigger = _current_w1_trigger(guala, key)
        _teach(guala, trigger, _move(100), "play-rejected-move-0001")
        world_before = guala._embodiment_world.encoded_snapshot()
        activity = _playing(guala)
        assert guala._start_activity(activity) is True

        record = activity.metadata["_causal_play_admission"]
        assert record["dispatch_status"] == "unknown"
        assert record["dispatch_phase"] == "selection"
        assert record["dispatch_reason"] == "action_unknown"
        assert record["embodiment_rejection_reason"] is None
        assert record["world_revision_before"] == record["world_revision_after"]
        assert guala._embodiment_world.encoded_snapshot() == world_before
        assert guala._causal_action_cycle.status()["closures"] == 0
        assert guala._causal_action_dispatcher.status()["active"] is False
    finally:
        guala.shutdown()


def test_restored_legacy_play_marker_never_dispatches_an_action(
    monkeypatch,
    tmp_path,
) -> None:
    key = "play-admission-restart-key"
    _configure(monkeypatch, key)
    writer = Guala()
    restored = None
    try:
        trigger = _current_w1_trigger(writer, key)
        _teach(writer, trigger, _move(2000), "play-restart-move-0001")
        activity = _playing(writer)
        assert writer._start_activity(activity) is True
        marker = deepcopy(activity.metadata["_causal_play_admission"])
        assert marker["dispatch_status"] == "unknown"
        assert writer._embodiment_world.observation_snapshot().revision == 0
        writer.save_full_state(str(tmp_path))
        writer.shutdown()
        writer = None

        restored = Guala()
        restored.load_full_state(str(tmp_path))
        assert restored._load_successful, restored._load_errors
        assert restored._current_activity.kind == "PLAYING"
        assert (
            restored._current_activity.metadata["_causal_play_admission"]
            == marker
        )
        assert restored._embodiment_world.observation_snapshot().revision == 0
        assert restored._causal_action_cycle.status()["closures"] == 0

        world_before_tick = restored._embodiment_world.encoded_snapshot()
        restored._atick_playing(restored._current_activity)
        assert restored._embodiment_world.encoded_snapshot() == world_before_tick
        assert restored._causal_action_cycle.status()["closures"] == 0
    finally:
        if writer is not None:
            writer.shutdown()
        if restored is not None:
            restored.shutdown()
