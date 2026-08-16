from __future__ import annotations

import pytest

from dsf_ai_service.glew_runtime.native_resident_organism import (
    create_native_resident_organism,
)
from tests.test_native_resident_production_mount import (
    IDENTITY,
    _growth_dna_fixture,
)


def test_one_native_body_candidate_commits_at_most_once() -> None:
    organism = create_native_resident_organism(
        organism_identity=IDENTITY,
        organism_tick=0,
        growth_dna=_growth_dna_fixture(),
        max_envelope_bytes=67_108_864,
        max_fabric_bytes=67_108_000,
        max_logical_peak_bytes=536_870_912,
    )
    before = organism.readiness()
    prepared = organism.prepare_articulated_body_observation()

    assert prepared.predecessor_state_sha256 == before.state_sha256
    assert prepared.prepared_state_sha256 != before.state_sha256
    assert prepared.receptor_ingress_sense_counts == (0, 0, 0, 0, 0, 74)
    assert organism.readiness().state_sha256 == before.state_sha256

    committed = organism.commit(prepared.token)
    assert committed.state_sha256 == prepared.prepared_state_sha256
    assert committed.organism_tick == before.organism_tick + 1

    with pytest.raises(ValueError, match="pending candidate"):
        organism.commit(prepared.token)
    assert organism.readiness().state_sha256 == committed.state_sha256
