from __future__ import annotations

import pytest

from dsf_ai_service.substrate.auditory_recurrent_motif import (
    AuditoryMotifResourceProfile,
    AuditoryRecurrentMotifOwner,
)
from dsf_ai_service.substrate.embodiment_world import PositionMM
from dsf_ai_service.substrate.w1_binaural_controlled_distinction import (
    W1BinauralControlledDistinctionOwner,
    W1ControlledDistinctionResourceProfile,
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


KEY = b"W1-binaural-controlled-distinction-test-key"


def _episodes_at(
    *,
    position: PositionMM,
    q_owner: AuditoryRecurrentMotifOwner,
    grounding: W1BinauralGroundingEvidenceAuthority,
):
    world = _world(external_position=position)
    physical = _authority(world)
    epoch = physical.open_epoch()
    mounts = []
    source_start = 0
    for sequence in range(4):
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
    q_owner.observe_binaural(
        mounts[0].binaural_receptor_settlement
    )
    grown = q_owner.observe_binaural(
        mounts[1].binaural_receptor_settlement
    )
    assert grown.observation.newly_grown_motif_neuron_ids
    episodes = []
    for mount in mounts[2:]:
        firing = q_owner.fire_binaural(
            mount.binaural_receptor_settlement
        )
        assert firing.activations
        episodes.append(grounding.admit(
            settlement=mount.causal_settlement,
            receptor_settlement=(
                mount.binaural_receptor_settlement
            ),
            firing=firing,
            motif_owner=q_owner,
        ))
    return tuple(episodes)


def test_static_position_cannot_become_a_reduced_grounding_proxy():
    q_owner = AuditoryRecurrentMotifOwner(
        AuditoryMotifResourceProfile.create(
            profile_id="W1-controlled-distinction-q-proof",
            ear_count=2,
            max_motif_neurons=24_192,
            max_pending_experiences=8,
            max_work_cells_per_observation=8_000_000,
            max_exact_fraction_text_bytes=4_096,
            encoded_state_allocation_bytes=128 * 1024 * 1024,
        ),
        ear_ids=("left", "right"),
    )
    grounding = W1BinauralGroundingEvidenceAuthority(
        authority_key=KEY,
        resource_profile=W1BinauralGroundingResourceProfile.create(
            profile_id="W1-controlled-grounding-proof",
            max_activations=4_096,
            max_roots=256,
            max_evidence_bytes=32 * 1024 * 1024,
        ),
    )
    first = _episodes_at(
        position=PositionMM(3_500, 2_500, 0),
        q_owner=q_owner,
        grounding=grounding,
    )
    second = _episodes_at(
        position=PositionMM(4_500, 1_500, 0),
        q_owner=q_owner,
        grounding=grounding,
    )
    all_episodes = (*first, *second)
    root_values = {
        root_id: {
            next(
                root.value_sha256
                for root in episode.roots
                if root.root_id == root_id
            )
            for episode in all_episodes
        }
        for root_id in (
            root.root_id for root in all_episodes[0].roots
        )
    }
    varying = tuple(
        root_id
        for root_id, values in root_values.items()
        if len(values) > 1
    )
    assert varying == ()
    owner = W1BinauralControlledDistinctionOwner(
        authority_key=KEY,
        resource_profile=(
            W1ControlledDistinctionResourceProfile.create(
                profile_id="W1-controlled-distinction-proof",
                max_distinctions=8,
                max_episodes_per_distinction=16,
                max_alternatives_per_distinction=8,
                max_diagnostic_cells_per_alternative=24_192,
                max_state_bytes=16 * 1024 * 1024,
            )
        ),
        grounding_authority=grounding,
    )
    with pytest.raises(
        ValueError,
        match="two independent positives per physical alternative",
    ):
        owner.learn(
            varying_root_id=all_episodes[0].roots[0].root_id,
            episodes=all_episodes,
        )
    assert owner.status()["count"] == 0
