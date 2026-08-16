from __future__ import annotations

import base64
import hashlib
import hmac
import inspect
import json
import math
import struct
from dataclasses import replace
from fractions import Fraction
from pathlib import Path

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    PhysicalSense,
    SenseBoundaryState,
)
from dsf_ai_service.substrate import embodiment_world as world_module
from dsf_ai_service.substrate.approved_curriculum_physical_surfaces import (
    _APPROVED_ALPHABET_ASSET_NAMES,
    _APPROVED_NUMBER_ASSET_NAMES,
    _APPROVED_WORD_ASSET_NAMES,
    _APPROVED_ZERO_ASSET_NAMES,
)
from dsf_ai_service.substrate.embodiment_world import (
    MAX_MATERIAL_ACTION_DURATION_US,
    PORT_ID,
    AdvancePhysicalTimeCommand,
    AirVolumeState,
    EmbodiedObject,
    EmbodimentWorldAuthority,
    ObjectMaterialState,
    OralContactCommand,
    PickCommand,
    MoveCommand,
    PoseMM,
    PositionMM,
    PreparedActionExecution,
    TouchContactCommand,
    encode_command,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.w1_binaural_acoustic_physics import (
    binaural_sound_field_inputs,
)
from dsf_ai_service.substrate.w1_coupled_material_sensory_physics import (
    build_coupled_six_sense_full_field,
    material_interval_states,
    material_receptor_substreams,
    settle_coupled_six_sense_experience,
)
from dsf_ai_service.substrate.w1_physical_receptors import (
    physical_receptor_substreams,
)


KEY = b"w1-world-owned-material-physics-test-key"
INTENT = "9" * 64


def _pcm() -> bytes:
    sample_count = 3_200
    samples = tuple(
        round(
            8_000
            * math.sin(2.0 * math.pi * 440.0 * index / 16_000.0)
        )
        for index in range(sample_count)
    )
    return struct.pack(f"<{sample_count}h", *samples)


def _sound():
    source_start = Fraction(0)
    pcm = _pcm()
    left = binaural_sound_field_inputs(
        ear="left",
        topology_index=0,
        pcm=pcm,
        source_time_start=source_start,
    )
    right = binaural_sound_field_inputs(
        ear="right",
        topology_index=len(left),
        pcm=pcm,
        source_time_start=source_start,
    )
    return left, right


def _execute(world, command, *, digit: str):
    before = world.observation_snapshot()
    return world.execute_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(command),
        causal_intent_receipt_sha256=digit * 64,
        expected_revision=before.revision,
    )


def _odorant_total(observation) -> tuple[int, ...]:
    result = [0] * 8
    for region in observation.regions:
        if region.air is not None:
            for index, value in enumerate(
                region.air.odorant_mass_nanograms
            ):
                result[index] += value
    for item in observation.objects:
        if item.material is not None:
            for index, value in enumerate(
                item.material.odorant_reservoir_nanograms
            ):
                result[index] += value
    return tuple(result)


def _pre_material_record(value):
    record = value.as_record()
    if "active_contact" in record:
        del record["active_contact"]
        del record["receptor_geometry"]
    if "material" in record:
        del record["material"]
    if "optical_surface" in record:
        del record["optical_surface"]
    if "air" in record:
        del record["air"]
    if "air_flow_cubic_mm_per_second" in record:
        del record["air_flow_cubic_mm_per_second"]
    return record


def _authenticated_v4_snapshot(
    world: EmbodimentWorldAuthority,
) -> bytes:
    observation = world.observation_snapshot()
    world_record = {
        "bodies": [
            _pre_material_record(item)
            for item in observation.bodies
        ],
        "objects": [
            _pre_material_record(item)
            for item in observation.objects
            if item.optical_surface is None
        ],
        "portals": [
            _pre_material_record(item)
            for item in observation.portals
        ],
        "regions": [
            _pre_material_record(item)
            for item in observation.regions
        ],
        "revision": observation.revision,
        "room_bounds": observation.room_bounds.as_record(),
        "room_id": observation.room_id,
        "self_body_id": observation.self_body_id,
    }
    body = {
        "actor_ports": [
            item.as_record() for item in world.actor_ports
        ],
        "limits": {
            "max_bodies": world_module.DEFAULT_MAX_BODIES,
            "max_command_bytes": (
                world_module.DEFAULT_MAX_COMMAND_BYTES
            ),
            "max_encoded_state_bytes": (
                world_module.DEFAULT_MAX_ENCODED_STATE_BYTES
            ),
            "max_objects": 16,
            "max_portals": world_module.DEFAULT_MAX_PORTALS,
            "max_regions": world_module.DEFAULT_MAX_REGIONS,
            "receipt_capacity": (
                world_module.DEFAULT_RECEIPT_CAPACITY
            ),
        },
        "migration_receipt": None,
        "recent_applied_receipts": [],
        "schema": world_module.V4_STATE_SCHEMA,
        "world": world_record,
    }
    payload = world_module._canonical(body)
    signature = hmac.new(
        KEY,
        world_module.V4_STATE_DOMAIN + payload,
        hashlib.sha256,
    ).hexdigest()
    return world_module._canonical({
        "authority_hmac_sha256": signature,
        "payload_base64": base64.b64encode(payload).decode("ascii"),
        "schema": world_module.V4_ENVELOPE_SCHEMA,
    })


def test_one_world_edge_settles_all_six_senses_with_full_fields():
    world = EmbodimentWorldAuthority(authority_key=KEY)
    picked = _execute(
        world,
        PickCommand("W1-object-1", 200_000),
        digit="1",
    )
    assert picked.disposition == "applied"
    execution = _execute(
        world,
        OralContactCommand(
            object_id="W1-object-1",
            duration_microseconds=200_000,
        ),
        digit="2",
    )
    assert execution.disposition == "applied"
    assert execution.elapsed_nanoseconds == 200_000_000
    assert execution.after.bodies[0].active_contact.kind == "oral"
    left, right = _sound()
    committed = []
    experience = settle_coupled_six_sense_experience(
        causal_owner=ExactCausalExperienceOwner(
            on_settlement=committed.append,
            log_event=lambda *_args, **_kwargs: None,
        ),
        assembly_id="world-owned-coupled-six-sense-occurrence",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1, 5),
        world_authority=world,
        execution_receipt=execution,
        left_sound=left,
        right_sound=right,
    )

    assert committed == [experience.settlement]
    assert {
        interpretation.sense: interpretation.state
        for interpretation in experience.settlement.interpretations
    } == {
        sense.value: SenseBoundaryState.OBSERVED.value
        for sense in PhysicalSense
    }
    assert {
        interpretation.sense: len(interpretation.substreams)
        for interpretation in experience.settlement.interpretations
    } == {
        PhysicalSense.SIGHT.value: 162,
        PhysicalSense.SOUND.value: 64,
        PhysicalSense.TOUCH.value: 6,
        PhysicalSense.SMELL.value: 8,
        PhysicalSense.TASTE.value: 5,
        PhysicalSense.BODY.value: 4,
    }
    assert all(
        tuple(name for name, _value in field_tuple.fields)
        == DSF_FIELD_ORDER
        for interpretation in experience.settlement.interpretations
        for substream in interpretation.substreams
        for field_tuple in substream.field_tuples
    )
    native = material_receptor_substreams(
        world_authority=world,
        before=execution.before,
        after=execution.after,
        source_time_start=Fraction(0),
        source_time_end=Fraction(1, 5),
    )
    assert native[PhysicalSense.TOUCH][0].normalized_signal == (
        0.0,
        1.0,
    )
    assert all(
        substream.normalized_signal[1] > 0
        for substream in native[PhysicalSense.TASTE]
    )
    assert all(
        substream.phase_turns
        == (Fraction(0), Fraction(0))
        for substreams in native.values()
        for substream in substreams
    )
    receptor_text = repr(native)
    assert "W1-object-" not in receptor_text
    assert "label" not in receptor_text
    assert "score" not in receptor_text
    with pytest.raises(
        ValueError,
        match="signed world elapsed time",
    ):
        build_coupled_six_sense_full_field(
            assembly_id="wrong-material-time-edge",
            source_time_start=Fraction(0),
            source_time_end=Fraction(1, 4),
            world_authority=world,
            execution_receipt=execution,
            left_sound=left,
            right_sound=right,
        )


def test_one_timed_move_settles_changed_body_and_sight_on_all_six_senses():
    world = EmbodimentWorldAuthority(authority_key=KEY)
    execution = _execute(
        world,
        MoveCommand(
            PoseMM(PositionMM(1_000, 1_200, 0), 0),
            200_000,
        ),
        digit="a",
    )

    assert execution.disposition == "applied"
    assert execution.elapsed_nanoseconds == 200_000_000
    physical = physical_receptor_substreams(
        execution.before,
        execution.after,
        causal_transition=True,
        source_time_start=Fraction(0),
        source_time_end=Fraction(1, 5),
    )
    assert any(
        item.normalized_signal[0] != item.normalized_signal[1]
        for item in physical[PhysicalSense.SIGHT]
    )
    assert any(
        item.normalized_signal[0] != item.normalized_signal[1]
        for item in physical[PhysicalSense.BODY]
    )
    assert material_interval_states(
        world_authority=world,
        before=execution.before,
        after=execution.after,
    ) == {
        PhysicalSense.TOUCH: SenseBoundaryState.OBSERVED,
        PhysicalSense.SMELL: SenseBoundaryState.OBSERVED,
        PhysicalSense.TASTE: SenseBoundaryState.OBSERVED,
    }
    left, right = _sound()
    committed = []
    experience = settle_coupled_six_sense_experience(
        causal_owner=ExactCausalExperienceOwner(
            on_settlement=committed.append,
            log_event=lambda *_args, **_kwargs: None,
        ),
        assembly_id="timed-move-six-sense-occurrence",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1, 5),
        world_authority=world,
        execution_receipt=execution,
        left_sound=left,
        right_sound=right,
    )

    assert committed == [experience.settlement]
    assert {
        interpretation.sense: interpretation.state
        for interpretation in experience.settlement.interpretations
    } == {
        sense.value: SenseBoundaryState.OBSERVED.value
        for sense in PhysicalSense
    }
    assert all(
        tuple(name for name, _value in field_tuple.fields)
        == DSF_FIELD_ORDER
        for interpretation in experience.settlement.interpretations
        for substream in interpretation.substreams
        for field_tuple in substream.field_tuples
    )


def test_odor_transport_has_explicit_time_and_conserves_mass():
    world = EmbodimentWorldAuthority(
        authority_key=KEY,
        initial_objects=(
            EmbodiedObject(
                object_id="physical-object",
                radius_mm=100,
                mass_grams=500,
                position=PositionMM(1500, 1000, 0),
                material=ObjectMaterialState(
                    odorant_reservoir_nanograms=(
                        2_000_000,
                        2_000_000,
                        2_000_000,
                        2_000_000,
                        2_000_000,
                        2_000_000,
                        2_000_000,
                        2_000_000,
                    ),
                    odorant_release_nanograms_per_second=(
                        1_000,
                        1_000,
                        1_000,
                        1_000,
                        1_000,
                        1_000,
                        1_000,
                        1_000,
                    ),
                    tastant_mass_micrograms=(1, 1, 1, 1, 1),
                    surface_temperature_millikelvin=300_000,
                    compliance_ppm=100_000,
                    roughness_micrometers=1_000,
                    moisture_ppm=100_000,
                ),
            ),
        ),
    )
    before = world.observation_snapshot()
    assert all(
        mass == 0
        for region in before.regions
        for mass in region.air.odorant_mass_nanograms
    )
    execution = _execute(
        world,
        AdvancePhysicalTimeCommand(
            duration_microseconds=1_000_000
        ),
        digit="3",
    )
    assert execution.disposition == "applied"
    assert _odorant_total(execution.before) == _odorant_total(
        execution.after
    )
    assert sum(
        execution.after.regions[0].air.odorant_mass_nanograms
    ) > 0
    assert sum(
        execution.after.regions[1].air.odorant_mass_nanograms
    ) > 0
    assert execution.before.regions[1].air.odorant_mass_nanograms == (
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
    )
    assert execution.lifecycle[-2:] == (
        "physical_time_transport_validated",
        "applied",
    )


def test_contact_geometry_is_world_derived_and_rejection_is_pure():
    world = EmbodimentWorldAuthority(authority_key=KEY)
    before = world.observation_snapshot()
    rejected = _execute(
        world,
        OralContactCommand(
            object_id="W1-object-1",
            duration_microseconds=200_000,
        ),
        digit="4",
    )
    assert rejected.disposition == "rejected"
    assert rejected.reason == "oral_contact_requires_held_object"
    assert world.observation_snapshot() == before
    assert tuple(inspect.signature(OralContactCommand).parameters) == (
        "object_id",
        "duration_microseconds",
    )
    assert "contact_area" not in encode_command(
        TouchContactCommand(
            object_id="W1-object-1",
            duration_microseconds=200_000,
        )
    ).decode("utf-8")


def test_material_commit_rollback_restores_world_and_mass_exactly():
    world = EmbodimentWorldAuthority(authority_key=KEY)
    _execute(
        world,
        PickCommand("W1-object-1", 200_000),
        digit="5",
    )
    before = world.observation_snapshot()
    prepared = world.prepare_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(OralContactCommand(
            object_id="W1-object-1",
            duration_microseconds=500_000,
        )),
        causal_intent_receipt_sha256="6" * 64,
        expected_revision=before.revision,
    )
    assert isinstance(prepared, PreparedActionExecution)
    committed = world.commit_prepared_action(prepared)
    assert committed.after != before

    with world.committed_prepared_action_rollback_transaction(
        prepared
    ) as rollback:
        rollback()

    assert world.observation_snapshot() == before
    assert _odorant_total(world.observation_snapshot()) == (
        _odorant_total(before)
    )


def test_current_cold_restore_and_exact_bounds_fail_closed():
    world = EmbodimentWorldAuthority(authority_key=KEY)
    _execute(
        world,
        AdvancePhysicalTimeCommand(1_000_000),
        digit="7",
    )
    encoded = world.encoded_snapshot()
    cold = EmbodimentWorldAuthority(authority_key=KEY)

    cold.restore_encoded(encoded)

    assert cold.encoded_snapshot() == encoded
    assert cold.observation_snapshot() == world.observation_snapshot()
    with pytest.raises(ValueError, match="outside its exact integer"):
        encode_command(AdvancePhysicalTimeCommand(
            MAX_MATERIAL_ACTION_DURATION_US + 1
        ))
    with pytest.raises(ValueError, match="bounded integer masses"):
        AirVolumeState(
            volume_cubic_mm=1,
            odorant_mass_nanograms=(-1, 0, 0, 0, 0, 0, 0, 0),
        ).verify()
    damaged = bytearray(encoded)
    damaged[-10] ^= 1
    with pytest.raises(ValueError):
        cold.restore_encoded(bytes(damaged))


def test_authenticated_v4_migrates_without_inventing_material_senses():
    source = EmbodimentWorldAuthority(authority_key=KEY)
    encoded_v4 = _authenticated_v4_snapshot(source)
    cold = EmbodimentWorldAuthority(authority_key=KEY)

    cold.restore_encoded(encoded_v4)

    migrated = cold.observation_snapshot()
    assert migrated.revision == 1
    migrated_surfaces = tuple(
        item
        for item in migrated.objects
        if item.optical_surface is not None
    )
    migrated_prior_objects = tuple(
        item
        for item in migrated.objects
        if item.optical_surface is None
    )
    assert len(migrated_surfaces) == len(
        _APPROVED_ALPHABET_ASSET_NAMES
        + _APPROVED_NUMBER_ASSET_NAMES
        + _APPROVED_WORD_ASSET_NAMES
        + _APPROVED_ZERO_ASSET_NAMES
    )
    assert all(item.material is not None for item in migrated_surfaces)
    assert all(item.material is None for item in migrated_prior_objects)
    assert all(
        body.receptor_geometry is None
        for body in migrated.bodies
    )
    assert all(region.air is None for region in migrated.regions)
    assert all(
        portal.air_flow_cubic_mm_per_second is None
        for portal in migrated.portals
    )
    original = source.observation_snapshot()
    assert [
        _pre_material_record(item) for item in migrated_prior_objects
    ] == [
        _pre_material_record(item) for item in original.objects
        if item.optical_surface is None
    ]
    execution = _execute(
        cold,
        AdvancePhysicalTimeCommand(1_000_000),
        digit="8",
    )
    assert material_interval_states(
        world_authority=cold,
        before=execution.before,
        after=execution.after,
    ) == {
        PhysicalSense.TOUCH: (
            SenseBoundaryState.SENSOR_UNAVAILABLE
        ),
        PhysicalSense.SMELL: (
            SenseBoundaryState.SENSOR_UNAVAILABLE
        ),
        PhysicalSense.TASTE: (
            SenseBoundaryState.SENSOR_UNAVAILABLE
        ),
    }


def test_world_material_path_has_no_manifest_reachability():
    root = Path(__file__).resolve().parents[1]
    paths = (
        root / "dsf_ai_service/substrate/embodiment_world.py",
        root
        / "dsf_ai_service/substrate/"
        "w1_coupled_material_sensory_physics.py",
        root / "dsf_ai_service/substrate/w1_physical_receptors.py",
    )
    joined = "\n".join(path.read_text() for path in paths)

    assert "w1_default_material_manifest" not in joined
    assert "canonical_w1_material_inventory" not in joined
    assert "ObjectMaterialProperties" not in joined
    assert "W1CoupledMaterialPhysicsAuthority" not in joined
    assert "contact_area_square_mm" not in joined
    assert "odorant_emission_ppm" not in joined
    assert "distance lookup" not in joined
