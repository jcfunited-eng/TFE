"""Component-level discrete-afferent conduction, tract-dependent transmission,
in-memory round-trip, and world-command settlement probe.

Scope & Boundary Notice (A1 Audit Conformance):
  1. Input: This test uses a discrete component trit fixture (slots 16..23). It does
     NOT exercise recorded acoustic PCM through the cochlear ERB transducer.
  2. Control: Structural tract severing removes both baseline elastic coupling and
     plastic transmission; it demonstrates forward inter-column conduction, NOT
     matched-state plastic memory causation. Matched motor divergence remains A11 (OPEN).
  3. Action: Manual MoveCommand translation tests world geometry and receipt mechanics;
     it does NOT demonstrate autonomous organism decision-making or closed-loop sensory return.
  4. Continuity: In-memory codec comparison asserts ARCLOOM4 round-trip equivalence within
     one process; it does NOT demonstrate cross-process coupled organism/world cold continuity.
  5. Spoken-command learning and command comprehension remain UNIMPLEMENTED / OPEN.
"""

from __future__ import annotations

import numpy as np
import pytest

from dsf_ai_service.substrate.modular_column_substrate import ModularColumnSubstrate
from dsf_ai_service.guala_functional_organism import motor_efferent_to_locomotion_command
from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.substrate.embodiment_world import (
    ActionExecutionReceipt,
    PORT_ID,
    encode_command,
)


def _component_discrete_afferent_pattern() -> list[float]:
    """16-channel component discrete pattern populating auditory slots 16..23."""
    pattern = [0.0] * 16
    for i in range(4, 12):
        pattern[i] = 1.0
    return pattern


def test_discrete_afferent_conduction_and_tract_dependent_motor_drive() -> None:
    """Prove that discrete afferent stimulation drives inter-column laminar flow
    and actuates motor efferents, while tract severing interrupts forward transmission."""
    # 1. Fresh substrate starts with zero active synapses and zero motor efferents
    sub_intact = ModularColumnSubstrate(
        yield_threshold=0.50, plastic_rate=0.08, activation_threshold=0.15, columns=64
    )
    assert sub_intact.active_synapses() == 0
    assert sub_intact.get_motor_efferent() == (0.0, 0.0, 0.0, 0.0)

    trits_quiet = sub_intact.encode_sensory_stream()
    somatic_quiet = sub_intact.encode_somatic_apical()

    y_quiet, s_quiet = sub_intact.step(trits_quiet, somatic_quiet)
    assert y_quiet == 0
    assert s_quiet == 0.0
    assert sub_intact.get_motor_efferent() == (0.0, 0.0, 0.0, 0.0)

    # 2. Present discrete component afferent pattern (consumed by Cols 8..15)
    component_cue = _component_discrete_afferent_pattern()
    trits_cue = sub_intact.encode_sensory_stream(cochlear_channels=component_cue)

    # Verify discrete trits are populated in component slots 16..31
    assert any(t != 0 for t in trits_cue[16:32])
    # Verify non-auditory sensory slots remain unpopulated
    assert all(t == 0 for t in trits_cue[:16])  # Optical
    assert all(t == 0 for t in trits_cue[32:48])  # Palmar/thermal

    # Step through discrete presentation
    yield_history = []
    for _ in range(5):
        y, s = sub_intact.step(trits_cue, somatic_quiet)
        yield_history.append(y)

    # Prove plastic yield occurred and persistent conductances formed
    assert sum(yield_history) > 0, "Discrete stimulation must produce non-zero plastic yields"
    assert sub_intact.active_synapses() > 0, "Synaptic conductances must deform past yield threshold"

    # 3. Motor efferent actuation under connected conduction
    eff_intact = sub_intact.get_motor_efferent()
    vocal, stride, steer, grip = eff_intact
    assert stride > 0.0, f"Connected conduction must actuate motor stride efferent, got stride={stride}"
    assert vocal > 0.0, f"Connected conduction must actuate vocal drive efferent, got vocal={vocal}"

    # 4. Structural Tract Severing Control:
    # Under the exact same discrete input, sever inter-column tracts into motor columns (40..47)
    sub_severed = ModularColumnSubstrate(
        yield_threshold=0.50, plastic_rate=0.08, activation_threshold=0.15, columns=64
    )
    for c_to in range(40, 48):
        for c_from in range(64):
            if c_from < 40 or c_from >= 48:
                sub_severed.sever_tract(c_from, c_to)
                sub_severed.sever_tract(c_to, c_from)

    for _ in range(5):
        sub_severed.step(trits_cue, somatic_quiet)

    eff_severed = sub_severed.get_motor_efferent()
    assert eff_severed == (0.0, 0.0, 0.0, 0.0), (
        f"Severing motor fascicular tracts must interrupt transmission under identical discrete input, got {eff_severed}"
    )


def test_component_arcloom4_codec_and_in_memory_round_trip() -> None:
    """Prove that component state persists byte-for-byte in ARCLOOM4
    and reproduces identical motor efferents upon in-memory restoration."""
    sub_source = ModularColumnSubstrate(
        yield_threshold=0.50, plastic_rate=0.08, activation_threshold=0.15, columns=64
    )
    component_cue = _component_discrete_afferent_pattern()
    trits_cue = sub_source.encode_sensory_stream(cochlear_channels=component_cue)
    somatic_quiet = sub_source.encode_somatic_apical()

    for _ in range(5):
        sub_source.step(trits_cue, somatic_quiet)

    expected_synapses = sub_source.active_synapses()
    expected_eff = sub_source.get_motor_efferent()
    assert expected_synapses > 0
    assert expected_eff[1] > 0.0

    # Export canonical binary ARCLOOM4 checkpoint
    checkpoint_bytes = sub_source.export_sparse_bytes(version=4)
    assert len(checkpoint_bytes) > 0
    assert bytes(checkpoint_bytes).startswith(b"ARCLOOM4")

    # Restore into recipient substrate instance in same process
    sub_restored = ModularColumnSubstrate(
        yield_threshold=0.50, plastic_rate=0.08, activation_threshold=0.15, columns=64
    )
    sub_restored.import_sparse_bytes(checkpoint_bytes)

    # Prove byte-for-byte serialization identity and identical synapse count
    restored_bytes = sub_restored.export_sparse_bytes(version=4)
    assert bytes(restored_bytes) == bytes(checkpoint_bytes)
    assert sub_restored.active_synapses() == expected_synapses

    # Stepping restored instance under the same discrete input yields identical motor efferent
    sub_restored.step(trits_cue, somatic_quiet)
    sub_source.step(trits_cue, somatic_quiet)
    assert sub_restored.get_motor_efferent() == sub_source.get_motor_efferent()


def test_component_motor_efferent_to_world_settlement() -> None:
    """Prove that component motor efferents translate into valid MoveCommands
    and settle in the simulated home_world_authority, while tract-severed controls remain stationary."""
    sub_intact = ModularColumnSubstrate(
        yield_threshold=0.50, plastic_rate=0.08, activation_threshold=0.15, columns=64
    )
    sub_severed = ModularColumnSubstrate(
        yield_threshold=0.50, plastic_rate=0.08, activation_threshold=0.15, columns=64
    )

    for c_to in range(40, 48):
        for c_from in range(64):
            if c_from < 40 or c_from >= 48:
                sub_severed.sever_tract(c_from, c_to)
                sub_severed.sever_tract(c_to, c_from)

    component_cue = _component_discrete_afferent_pattern()
    trits_cue = sub_intact.encode_sensory_stream(cochlear_channels=component_cue)
    somatic_quiet = sub_intact.encode_somatic_apical()

    for _ in range(5):
        sub_intact.step(trits_cue, somatic_quiet)
        sub_severed.step(trits_cue, somatic_quiet)

    eff_intact = sub_intact.get_motor_efferent()
    eff_severed = sub_severed.get_motor_efferent()

    # World Authority Setup
    world_intact = home_world_authority(identity="1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1")
    world_severed = home_world_authority(identity="1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1")

    snap_in = world_intact.observation_snapshot()
    snap_sev = world_severed.observation_snapshot()
    body_in_before = next(b for b in snap_in.bodies if b.body_id == snap_in.self_body_id)
    body_sev_before = next(b for b in snap_sev.bodies if b.body_id == snap_sev.self_body_id)
    assert body_in_before.pose == body_sev_before.pose

    # Convert efferents to canonical MoveCommand
    cmd_intact = motor_efferent_to_locomotion_command(eff_intact, body_in_before.pose)
    cmd_severed = motor_efferent_to_locomotion_command(eff_severed, body_sev_before.pose)

    assert cmd_intact is not None, "Intact component efferent must yield a valid MoveCommand"
    assert cmd_severed is None, "Severed component efferent must yield None (zero locomotion command)"

    # Execute intact MoveCommand in world authority
    prep_in = world_intact.prepare_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(cmd_intact),
        causal_intent_receipt_sha256="aa" * 32,
        expected_revision=snap_in.revision,
    )
    assert not isinstance(prep_in, ActionExecutionReceipt)
    with world_intact.prepared_action_visibility_transaction(prep_in):
        receipt_in = world_intact.commit_prepared_action(prep_in)
    assert receipt_in.disposition == "applied"

    # Observe world positions after action
    body_in_after = next(b for b in world_intact.observation_snapshot().bodies if b.body_id == snap_in.self_body_id)
    body_sev_after = next(b for b in world_severed.observation_snapshot().bodies if b.body_id == snap_sev.self_body_id)

    # Prove physical displacement in world coordinates for intact, and zero for severed
    assert body_in_after.pose.position != body_in_before.pose.position, (
        f"Evoked motor command must displace body: before={body_in_before.pose.position}, after={body_in_after.pose.position}"
    )
    assert body_sev_after.pose.position == body_sev_before.pose.position, (
        "Severed control body must remain at initial position"
    )
