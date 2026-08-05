from __future__ import annotations

import json

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.causal_thing_sensory_expansion import (
    CausalThingSensoryExpansionAdmission,
    CausalThingSensoryExpansionOwner,
    PreparedCausalThingSensoryExpansionAdmission,
    THING_SENSORY_EXPANSION_CONSUMER_ID,
    THING_SENSORY_GROUNDING_CONSUMER_ID,
)
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    PickCommand,
    encode_command,
)
from dsf_ai_service.v4.guala_physical_runtime import Guala
from tests.test_lived_vocal_teaching_episode import (
    _external_mount,
    _modulated_tone_pcm,
)
from tests.test_w1_audiovisual_physical_evidence import (
    _authority,
    _world,
)


@pytest.fixture
def engine(monkeypatch) -> Guala:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("WAVE_SUMMARY_ENQUEUE_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    monkeypatch.setenv(
        "GUALA_CAUSAL_ACTION_KEY",
        "sensory-expansion-transaction-authority-key-v1",
    )
    value = Guala()
    try:
        yield value
    finally:
        value.shutdown()


def _retained_av_capability(
    engine,
    settlement,
    ordinal: int,
    *,
    sound_observed: bool = True,
):
    custody = engine._retained_audiovisual_custody.admit(
        settlement=settlement,
        frame_sha256s=(f"{ordinal:x}" * 64,),
        canonical_audio_sha256=(
            f"{ordinal + 8:x}" * 64 if sound_observed else None
        ),
    )
    capability = engine._retained_audiovisual_custody.issue_child(
        custody,
        THING_SENSORY_EXPANSION_CONSUMER_ID,
    )
    return custody, capability


def _held_thing(guala: Guala):
    before = guala._embodiment_world.observation_snapshot()
    execution = guala._embodiment_world.execute_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(
            PickCommand(
                "W1-object-1",
                duration_microseconds=200_000,
            )
        ),
        causal_intent_receipt_sha256="a" * 64,
        expected_revision=before.revision,
    )
    mount = guala._w1_physical_evidence.mount_action_outcome(execution)
    custody = guala._settled_prediction_custody(
        mount,
        world_execution=execution,
    )
    return guala._admit_thing_genesis_from_custody(custody)


def _owner(
    engine,
    *,
    max_expansions: int = 4,
    max_roots: int = 512,
    max_state_bytes: int = 128 * 1024 * 1024,
) -> CausalThingSensoryExpansionOwner:
    return CausalThingSensoryExpansionOwner(
        authority_key=engine._thing_vocal_key,
        thing_owner=engine._causal_thing_mosaic_owner,
        max_expansions=max_expansions,
        max_roots_per_expansion=max_roots,
        max_state_bytes=max_state_bytes,
    )


def _contact_custody(engine):
    observation = engine._embodiment_world.observation_snapshot()
    mount = engine._w1_physical_evidence.mount_authenticated_observation(
        observation,
        commit=True,
    )
    custody = engine._settled_prediction_custody(
        mount,
        world_observation=observation,
    )
    capability = custody.authority.issue_child(
        THING_SENSORY_GROUNDING_CONSUMER_ID
    )
    return custody.authority, capability


def _ground(
    owner,
    engine,
    media_capability,
    contact_authority,
    contact_capability,
):
    return owner.admit_lived_contact_tutor(
        custody_authority=engine._retained_audiovisual_custody,
        custody_capability=media_capability,
        contact_custody_authority=contact_authority,
        contact_custody_capability=contact_capability,
    )


def test_live_av_expansion_transaction_is_exact_reversible_and_bounded(
    engine,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        engine,
        "_run_causal_play_episode",
        lambda **_values: None,
    )
    thing = _held_thing(engine)
    world = _world()
    physical = _authority(world)
    pressure = _modulated_tone_pcm(11_000)
    first_mount = physical.mount_authenticated_observation(
        world.observation_snapshot(),
        commit=True,
    )
    first_custody, first_capability = _retained_av_capability(
        engine,
        first_mount.causal_settlement,
        1,
        sound_observed=False,
    )
    _second_execution, second_mount = _external_mount(
        world,
        physical,
        pressure,
    )
    second_custody, second_capability = _retained_av_capability(
        engine,
        second_mount.causal_settlement,
        2,
    )
    _third_execution, third_mount = _external_mount(
        world,
        physical,
        pressure,
    )
    _third_custody, third_capability = _retained_av_capability(
        engine,
        third_mount.causal_settlement,
        3,
    )
    contact_authority, contact_capability = _contact_custody(engine)

    owner = _owner(engine)
    grounded = _ground(
        owner,
        engine,
        first_capability,
        contact_authority,
        contact_capability,
    )
    assert grounded.thing_id == thing.thing_id
    assert {root.sense for root in grounded.full_field_roots} == {
        "sight",
    }
    before = owner.snapshot_encoded()

    prepared = owner.prepare_known_sight_admission(
        custody_authority=engine._retained_audiovisual_custody,
        custody_capability=second_capability,
    )
    assert isinstance(
        prepared,
        PreparedCausalThingSensoryExpansionAdmission,
    )
    owner.verify_prepared_admission(prepared)
    assert owner.snapshot_encoded() == before
    expansion = prepared.admission.expansion
    assert expansion is not None
    assert expansion.thing_id == thing.thing_id
    assert expansion.settlement_receipt_sha256 == (
        second_custody.settlement.authority_receipt_sha256
    )
    assert expansion.full_field_roots
    assert {root.sense for root in expansion.full_field_roots} == {
        "sight",
        "sound",
    }
    assert all(
        tuple(
            pair[0]
            for pair in field_tuple["fields"]
        )
        == DSF_FIELD_ORDER
        for root in expansion.full_field_roots
        for field_tuple in json.loads(root.full_evidence_json)[
            "field_tuples"
        ]
    )

    undo = owner.commit_prepared_admission(prepared)
    committed = owner.snapshot_encoded()
    assert committed != before

    other = _owner(engine)
    _ground(
        other,
        engine,
        first_capability,
        contact_authority,
        contact_capability,
    )
    with pytest.raises(ValueError, match="changed custody"):
        other.rollback_committed_admission(undo)

    owner.rollback_committed_admission(undo)
    assert owner.snapshot_encoded() == before
    with pytest.raises(ValueError, match="changed custody"):
        owner.rollback_committed_admission(undo)

    retried = owner.prepare_known_sight_admission(
        custody_authority=engine._retained_audiovisual_custody,
        custody_capability=second_capability,
    )
    assert isinstance(
        retried,
        PreparedCausalThingSensoryExpansionAdmission,
    )
    assert retried.admission == prepared.admission
    retry_undo = owner.commit_prepared_admission(retried)
    assert owner.snapshot_encoded() == committed
    replay_before = owner.snapshot_encoded()
    replay = owner.prepare_known_sight_admission(
        custody_authority=engine._retained_audiovisual_custody,
        custody_capability=second_capability,
    )
    assert isinstance(replay, CausalThingSensoryExpansionAdmission)
    assert replay.expansion == expansion
    assert owner.snapshot_encoded() == replay_before

    later = owner.prepare_known_sight_admission(
        custody_authority=engine._retained_audiovisual_custody,
        custody_capability=third_capability,
    )
    assert isinstance(
        later,
        PreparedCausalThingSensoryExpansionAdmission,
    )
    owner.commit_prepared_admission(later)
    later_state = owner.snapshot_encoded()
    with pytest.raises(RuntimeError, match="undo is stale"):
        owner.rollback_committed_admission(retry_undo)
    assert owner.snapshot_encoded() == later_state

    expansion_limited = _owner(engine, max_expansions=1)
    _ground(
        expansion_limited,
        engine,
        first_capability,
        contact_authority,
        contact_capability,
    )
    limited_before = expansion_limited.snapshot_encoded()
    with pytest.raises(RuntimeError, match="capacity exhausted"):
        expansion_limited.prepare_known_sight_admission(
            custody_authority=engine._retained_audiovisual_custody,
            custody_capability=second_capability,
        )
    assert expansion_limited.snapshot_encoded() == limited_before

    grounded_root_count = len(grounded.full_field_roots)
    root_limited = _owner(engine, max_roots=grounded_root_count)
    _ground(
        root_limited,
        engine,
        first_capability,
        contact_authority,
        contact_capability,
    )
    root_before = root_limited.snapshot_encoded()
    with pytest.raises(RuntimeError, match="root capacity exhausted"):
        root_limited.prepare_known_sight_admission(
            custody_authority=engine._retained_audiovisual_custody,
            custody_capability=second_capability,
        )
    assert root_limited.snapshot_encoded() == root_before

    candidate_bytes = len(
        owner._encoded(prepared._staged_expansions)
    )
    state_limited = _owner(
        engine,
        max_state_bytes=candidate_bytes - 1_024,
    )
    _ground(
        state_limited,
        engine,
        first_capability,
        contact_authority,
        contact_capability,
    )
    state_before = state_limited.snapshot_encoded()
    with pytest.raises(RuntimeError, match="state capacity exhausted"):
        state_limited.prepare_known_sight_admission(
            custody_authority=engine._retained_audiovisual_custody,
            custody_capability=second_capability,
        )
    assert state_limited.snapshot_encoded() == state_before

    encoded = owner.snapshot_encoded()
    lowered = encoded.lower()
    for forbidden in (
        b"canonical_audio_sha256",
        b"frame_sha256s",
        b"label",
        b"meaning",
        b"pcm_s16le",
        b"transcript",
    ):
        assert forbidden not in lowered
