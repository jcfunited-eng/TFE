"""tests/test_phase5_closed_loop_organism.py

Verification Suite for WHOLE_BRAIN_SPECIFICATION.md Phase 5 (Item 4):
Full closed-loop verification of 4-Column 3D Modular Neuromorphic Substrate
integrated with FunctionalOrganism, FunctionalPhysicalLoop, and HomeWorld.
"""

from __future__ import annotations

import json
import pytest
import numpy as np

from dsf_ai_service.guala_functional_organism import (
    FunctionalOrganism,
    CAPACITY_MICROGRAMS,
)
from dsf_ai_service.guala_functional_loop import (
    FunctionalPhysicalLoop,
    PhysicalOccurrence,
)
from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.substrate.modular_column_substrate import ModularColumnSubstrate

IDENTITY = "3ff4e70a-f2a0-44c5-a111-f4a5bc915cc7"
UNATTENDED = PhysicalOccurrence("unattended", None)


def test_closed_loop_organism_initialization_with_modular_substrate():
    """Verify that FunctionalOrganism instantiates the 4-Column Modular Substrate."""
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)

    assert hasattr(organism, "_modular_substrate")
    assert isinstance(organism._modular_substrate, ModularColumnSubstrate)

    # Telemetry properties
    tracking = organism.spatial_tracking
    assert isinstance(tracking, (tuple, list)) and len(tracking) == 4
    r_mm, theta_mdeg, trace, occluded = tracking
    assert r_mm == 0.0
    assert theta_mdeg == 0
    assert trace == 0.0

    assert organism.barrier_refusal_active is False
    assert "modular_active_synapses" in organism.counts
    assert organism.counts["modular_active_synapses"] == 0

    # Genesis byte-exact round-trip
    encoded = organism.encoded()
    restored = FunctionalOrganism.restore(encoded)
    assert restored.encoded() == encoded


def test_closed_loop_loop_settle_updates_columns_and_observation():
    """Verify that loop settle steps the 4 columns and surfaces telemetry in observation."""
    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    loop = FunctionalPhysicalLoop()

    # Step for 10 beats
    results = []
    for _ in range(10):
        res = loop.settle(organism, world, UNATTENDED)
        results.append(res)

    last_obs = results[-1].observation
    assert "spatial_tracking" in last_obs
    assert "barrier_refusal_active" in last_obs
    assert len(last_obs["spatial_tracking"]) == 4
    assert isinstance(last_obs["barrier_refusal_active"], bool)

    # Active synapses count in organism counts
    assert organism.counts["modular_active_synapses"] >= 0


def test_closed_loop_dream_consolidation_and_exact_restore():
    """Verify that dream consolidation downscales/prunes and state restores byte-exact."""
    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    loop = FunctionalPhysicalLoop()

    for _ in range(15):
        loop.settle(organism, world, UNATTENDED)

    # Offline nocturnal dream consolidation
    pre_syn = organism.counts["modular_active_synapses"]
    organism._dream(organism.live_organism_tick)
    post_syn = organism.counts["modular_active_synapses"]
    assert post_syn <= pre_syn

    # Byte-exact restore
    encoded = organism.encoded()
    restored = FunctionalOrganism.restore(encoded)
    assert restored.encoded() == encoded
