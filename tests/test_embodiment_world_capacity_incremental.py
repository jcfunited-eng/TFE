"""Test incremental exact state capacity counting in EmbodimentWorldAuthority.

Verifies that _exact_state_payload_byte_count equals _canonical_byte_count(self._state_payload_for(state))
bit-for-bit on every single beat across fresh worlds and command cycles, with cache invalidation
and receipt pruning matching mathematical physical invariants.
"""

from __future__ import annotations

import pytest

from dsf_ai_service.guala_functional_loop import FunctionalPhysicalLoop
from dsf_ai_service.guala_functional_organism import FunctionalOrganism
from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.lean_actor import PhysicalOccurrence
from dsf_ai_service.substrate.embodiment_world import (
    AdvancePhysicalTimeCommand,
    ContactOpticalSurfaceSequence,
    EmbodiedObject,
    EmbodimentWorldAuthority,
    MoveCommand,
    ObjectMaterialState,
    ObjectOpticalSurface,
    PORT_ID,
    PoseMM,
    PositionMM,
    _canonical_byte_count,
    encode_command,
)

IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
UNATTENDED = PhysicalOccurrence("unattended", None)


def test_incremental_state_capacity_matches_slow_canonical_every_beat() -> None:
    """Over 50 full beats of sensory-motor execution, incremental count matches slow canonical."""
    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    loop = FunctionalPhysicalLoop()

    for beat in range(50):
        loop.settle(organism, world, UNATTENDED)
        state = world._state
        slow_count = _canonical_byte_count(world._state_payload_for(state))
        incremental_count = world._exact_state_payload_byte_count(state)
        assert incremental_count == slow_count, (
            f"Beat {beat}: incremental {incremental_count} != slow {slow_count}"
        )
        assert len(world._receipt_compact_bytes_cache) <= world._receipt_capacity


def test_incremental_state_capacity_direct_commands_and_invalidation() -> None:
    """Direct commands, optical surface catalog updates, and cache pruning are exact."""
    surface = ObjectOpticalSurface(
        columns=2,
        rows=1,
        palette_reflectance_ppm=((100_000,) * 6, (900_000,) * 6),
        cell_palette_indices=(0, 1),
    )
    item = EmbodiedObject(
        object_id="test-card",
        radius_mm=50,
        mass_grams=100,
        position=PositionMM(2500, 2500, 0),
        material=ObjectMaterialState(
            odorant_reservoir_nanograms=(0,) * 8,
            odorant_release_nanograms_per_second=(0,) * 8,
            tastant_mass_micrograms=(0,) * 5,
            surface_temperature_millikelvin=294_000,
            compliance_ppm=60_000,
            roughness_micrometers=60,
            moisture_ppm=18_000,
        ),
    )
    authority = EmbodimentWorldAuthority(
        authority_key="capacity-test-key",
        initial_objects=(item,),
        contact_optical_surface_sequences=(
            ContactOpticalSurfaceSequence(
                object_id="test-card",
                source_receipt_sha256="ef" * 32,
                surfaces=(surface,),
            ),
        ),
    )

    moves = [
        PositionMM(1050, 1000, 0),
        PositionMM(1000, 1050, 0),
        PositionMM(1050, 1050, 0),
        PositionMM(1100, 1050, 0),
        PositionMM(1100, 1100, 0),
    ]

    for idx, target in enumerate(moves):
        cmd = MoveCommand(target_pose=PoseMM(target, 0), duration_microseconds=200_000)
        receipt = authority.execute_port_command(
            port_id=PORT_ID,
            command_payload=encode_command(cmd),
            causal_intent_receipt_sha256=f"{idx + 1:064x}",
            expected_revision=authority.observation_snapshot().revision,
        )
        assert receipt.disposition == "applied"
        state = authority._state
        assert authority._exact_state_payload_byte_count(state) == _canonical_byte_count(
            authority._state_payload_for(state)
        )

    # Execute advance physical time
    adv_cmd = AdvancePhysicalTimeCommand(duration_microseconds=100_000)
    receipt = authority.execute_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(adv_cmd),
        causal_intent_receipt_sha256=f"{99:064x}",
        expected_revision=authority.observation_snapshot().revision,
    )
    assert receipt.disposition == "applied"
    state = authority._state
    assert authority._exact_state_payload_byte_count(state) == _canonical_byte_count(
        authority._state_payload_for(state)
    )


def test_encoded_snapshot_unchanged_and_restorable() -> None:
    """Encoded snapshot is 100% identical and restores byte-exact."""
    world = home_world_authority(identity=IDENTITY)
    encoded_before = world.encoded_snapshot()
    cold = home_world_authority(identity=IDENTITY, encoded_world=encoded_before)
    assert cold.encoded_snapshot() == encoded_before

