from __future__ import annotations

import json
from dataclasses import replace

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.auditory_recurrent_motif import (
    AuditoryMotifResourceProfile,
    AuditoryRecurrentMotifOwner,
)
from dsf_ai_service.substrate.w1_binaural_grounding_evidence import (
    W1BinauralGroundingEvidenceAuthority,
    W1BinauralGroundingResourceProfile,
)
from tests.test_w1_audiovisual_physical_evidence import (
    _authority,
    _emission,
    _vocal_execution,
    _world,
)
from tests.test_w1_self_acoustic_propagation import (
    _modulated_tone_pcm,
)


KEY = b"W1-binaural-grounding-evidence-test-key"


def test_atomic_two_ear_firing_retains_full_field_grounding_evidence():
    world = _world()
    physical = _authority(world)
    epoch = physical.open_epoch()
    q_owner = AuditoryRecurrentMotifOwner(
        AuditoryMotifResourceProfile.create(
            profile_id="W1-grounding-binaural-q-proof",
            ear_count=2,
            max_motif_neurons=24_192,
            max_pending_experiences=8,
            max_work_cells_per_observation=8_000_000,
            max_exact_fraction_text_bytes=4_096,
            encoded_state_allocation_bytes=128 * 1024 * 1024,
        ),
        ear_ids=("left", "right"),
    )
    mounts = []
    source_start = 0
    for sequence in range(3):
        pressure = _modulated_tone_pcm(11_000)
        execution = _vocal_execution(
            world,
            epoch,
            sequence=sequence,
            source_sample_start=source_start,
            pcm=pressure,
        )
        mounts.append(physical.mount(
            epoch_token=epoch,
            sequence=sequence,
            execution_receipt=execution,
            acoustic_emission=_emission(
                physical,
                epoch,
                execution,
                sequence=sequence,
                source_sample_start=source_start,
                pcm=pressure,
            ),
        ))
        source_start += len(pressure) // 2

    first, second, third = mounts
    assert first.binaural_receptor_settlement is not None
    assert second.binaural_receptor_settlement is not None
    assert third.binaural_receptor_settlement is not None
    q_owner.observe_binaural(first.binaural_receptor_settlement)
    grown = q_owner.observe_binaural(
        second.binaural_receptor_settlement
    )
    assert grown.observation.newly_grown_motif_neuron_ids
    firing = q_owner.fire_binaural(
        third.binaural_receptor_settlement
    )
    assert firing.activations
    authority = W1BinauralGroundingEvidenceAuthority(
        authority_key=KEY,
        resource_profile=W1BinauralGroundingResourceProfile.create(
            profile_id="W1-binaural-grounding-evidence-proof",
            max_activations=4_096,
            max_roots=256,
            max_evidence_bytes=32 * 1024 * 1024,
        ),
    )
    assert third.causal_settlement is not None
    evidence = authority.admit(
        settlement=third.causal_settlement,
        receptor_settlement=(
            third.binaural_receptor_settlement
        ),
        firing=firing,
        motif_owner=q_owner,
    )

    authority.verify(evidence)
    assert {
        activation.ear_id for activation in evidence.activations
    } == {"left", "right"}
    assert any(
        json.loads(root.value_json)["boundary_state"] == "observed"
        and json.loads(root.value_json)["sense"] != "sound"
        for root in evidence.roots
    )
    assert all(
        tuple(
            item[0]
            for item in occurrence[field_name]
        ) == DSF_FIELD_ORDER
        for activation in evidence.activations
        for occurrence in json.loads(
            activation.activation_json
        )["full_field_occurrences"]
        for field_name in ("pressure_fields", "phase_fields")
    )
    assert not hasattr(evidence, "text")
    assert not hasattr(evidence, "label")

    with pytest.raises(
        ValueError,
        match="lost ear identity",
    ):
        replace(
            evidence.activations[0],
            ear_id="mono",
        ).verify()
