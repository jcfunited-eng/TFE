from __future__ import annotations

import hashlib
import hmac
import json
import math
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    NativeSensorySubstreamInput,
    build_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.causal_thing_mosaic import (
    CausalThingMosaicOwner,
    CausalThingMosaicProfile,
)
from dsf_ai_service.substrate.custodied_thing_encounter import (
    CustodiedW1ContactThingEncounterAuthority,
    THING_MOSAIC_CONSUMER_ID,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.settled_experience_custody import (
    SettledExperienceCustodyAuthority,
    SettledExperienceCustodyProfile,
)
from dsf_ai_service.substrate.w1_physical_receptors import (
    EmbodimentSensoryOutcomeAuthority,
)
from dsf_ai_service.substrate.whole_organism_episode import (
    L6Disposition,
    MechanismAvailability,
    MechanismKind,
    MountedMechanismSpec,
    WholeOrganismEpisodeAuthority,
    create_mounted_mechanism_manifest,
)
from dsf_ai_service.substrate.whole_organism_thing_mosaic_learning import (
    WholeOrganismThingMosaicLearningOwner,
    WholeOrganismThingMosaicLearningProfile,
)
from dsf_ai_service.substrate import (
    whole_organism_thing_mosaic_learning as learning_module,
)
from dsf_ai_service.substrate.whole_organism_neuron_population import (
    NeuronPopulationProfile,
    WholeOrganismNeuronPopulationOwner,
)
from tests.test_w1_audiovisual_physical_evidence import (
    EVIDENCE_KEY,
    WORLD_KEY,
    _authority as _physical_authority,
    _execution,
    _world,
)


EPISODE_KEY = b"whole-organism-thing-episode-key-v1"
PARTITION_KEY = b"whole-organism-thing-partition-key-v1"
CUSTODY_KEY = b"whole-organism-thing-custody-key-v1"
LEARNING_KEY = b"whole-organism-thing-learning-key-v1"
NEURON_KEY = b"whole-organism-thing-neuron-key-v1"
ACTION_RECEIPT = hashlib.sha256(b"whole-organism-action").hexdigest()
L6_RECEIPT = hashlib.sha256(b"whole-organism-L6").hexdigest()
TOPOLOGY_RECEIPT = hashlib.sha256(
    b"whole-organism-mounted-topology"
).hexdigest()


def _native(
    sense: PhysicalSense,
) -> NativeSensorySubstreamInput:
    count = 48
    return NativeSensorySubstreamInput(
        sense=sense,
        sensor_id=f"authorization-{sense.value}",
        substream_id=f"{sense.value}-field-0",
        topology_index=0,
        coordinates=(
            NativeAxisCoordinate(
                f"{sense.value}-receptor",
                "0",
            ),
        ),
        physical_quantity=f"{sense.value}-physical-intensity",
        physical_unit="exact-normalized-physical-input",
        source_times=tuple(
            Fraction(-1) + Fraction(index, 48)
            for index in range(count)
        ),
        normalized_signal=tuple(
            math.sin(
                2 * math.pi * (index + 1) / count
            )
            for index in range(count)
        ),
        phase_turns=tuple(
            Fraction(index // 8) for index in range(count)
        ),
    )


def _authorization_settlement():
    observed = {
        PhysicalSense.SIGHT: (_native(PhysicalSense.SIGHT),),
        PhysicalSense.BODY: (_native(PhysicalSense.BODY),),
    }
    states = {
        sense: (
            SenseBoundaryState.OBSERVED
            if sense in observed
            else SenseBoundaryState.SENSOR_UNAVAILABLE
        )
        for sense in SENSE_ORDER
    }
    built = build_six_sense_full_field(
        assembly_id="whole-organism-action-authorization",
        source_time_start=Fraction(-1),
        source_time_end=Fraction(0),
        observed_substreams=observed,
        states=states,
    )
    return ExactCausalExperienceOwner(
        on_settlement=lambda _value: None,
        log_event=lambda *_args, **_kwargs: None,
    ).settle(
        built,
        routing_chis=(),
        source_tags=(),
    )


def _manifest():
    mechanisms = []
    for sense in SENSE_ORDER:
        available = sense in {
            PhysicalSense.SIGHT,
            PhysicalSense.BODY,
        }
        mechanisms.append(
            MountedMechanismSpec(
                mechanism_id=f"sense:{sense.value}",
                kind=MechanismKind.RECEPTOR_FAMILY,
                availability=(
                    MechanismAvailability.AVAILABLE
                    if available
                    else MechanismAvailability.UNAVAILABLE
                ),
                evidence_schema=(
                    f"test.whole_organism_thing.{sense.value}.v1"
                ),
                parent_mechanism_ids=(),
                sense=sense.value,
                binds_full_field_roots=True,
                unavailable_reason=(
                    None
                    if available
                    else "test_mounted_lane_unavailable"
                ),
                physical_quantity=f"{sense.value}-physical-intensity",
                physical_unit="exact-normalized-physical-input",
                physical_extent=f"{sense.value}-receptor-field",
                causal_clock="exact-source-time",
                transduction_authority_receipt_sha256=TOPOLOGY_RECEIPT,
                custody_authority_receipt_sha256=TOPOLOGY_RECEIPT,
            )
        )
    return create_mounted_mechanism_manifest(
        authority_key=EPISODE_KEY,
        manifest_id="whole-organism-thing-six-lane-manifest",
        topology_authority_receipt_sha256=TOPOLOGY_RECEIPT,
        mechanisms=mechanisms,
    )


def _prepared(authority, draft):
    return tuple(
        authority.prepare_receptor_contribution(
            draft,
            authority.mechanism_capability(
                draft,
                spec.mechanism_id,
            ),
        )
        for spec in authority.manifest.mechanisms
    )


def _stack(*, learning_state_bytes=64 * 1024 * 1024):
    world = _world()
    physical = _physical_authority(world)
    execution = _execution(world)
    mount = physical.mount_action_outcome(execution)

    episodes = WholeOrganismEpisodeAuthority(
        authority_key=EPISODE_KEY,
        manifest=_manifest(),
        max_episodes=4,
        max_state_bytes=64 * 1024 * 1024,
    )
    authorization_draft = episodes.begin_action_authorization(
        chain_id="whole-organism-thing-action-chain",
        settlement=_authorization_settlement(),
        action_authority_receipt_sha256=ACTION_RECEIPT,
    )
    authorization = episodes.resolve(
        authorization_draft,
        _prepared(episodes, authorization_draft),
    )
    assert authorization.state == "resolved"
    consequence_draft = episodes.begin_consequence(
        authorization=authorization.capability,
        settlement=mount.causal_settlement,
        action_execution_receipt_sha256=(
            execution.authority_receipt_sha256
        ),
        l6_disposition=L6Disposition.SETTLED,
        l6_authority_receipt_sha256=L6_RECEIPT,
    )
    consequence = episodes.resolve(
        consequence_draft,
        _prepared(episodes, consequence_draft),
    )
    assert consequence.state == "resolved"

    custody = SettledExperienceCustodyAuthority(
        authority_key=CUSTODY_KEY,
        w1_physical_authority_key=EVIDENCE_KEY,
        world_authority_key=WORLD_KEY,
        profile=SettledExperienceCustodyProfile.create(
            profile_id="whole-organism-thing-custody",
            max_children=2,
            max_snapshot_bytes=64 * 1024 * 1024,
        ),
    )
    custody.admit(mount, execution)
    custody_capability = custody.issue_child(
        THING_MOSAIC_CONSUMER_ID
    )
    partitions = CustodiedW1ContactThingEncounterAuthority(
        authority_key=PARTITION_KEY,
        world_authority=world,
        sensory_authority=EmbodimentSensoryOutcomeAuthority(
            authority_key=WORLD_KEY
        ),
        max_roots_per_partition=256,
    )
    things = CausalThingMosaicOwner(
        authority_key=PARTITION_KEY,
        profile=CausalThingMosaicProfile.create(
            profile_id="whole-organism-thing-owner",
            max_mosaics=4,
            max_partitions_per_mosaic=8,
            max_roots_per_partition=256,
            max_routes=4_096,
            max_state_bytes=64 * 1024 * 1024,
        ),
        partition_authority=partitions,
    )
    profile = WholeOrganismThingMosaicLearningProfile.create(
        profile_id="whole-organism-thing-learning",
        max_records=8,
        max_roots_per_record=256,
        max_state_bytes=learning_state_bytes,
    )
    neurons = WholeOrganismNeuronPopulationOwner(
        authority_key=NEURON_KEY,
        manifest_authority_key=EPISODE_KEY,
        manifest=episodes.manifest,
        profile=NeuronPopulationProfile.create(
            profile_id="whole-organism-thing-neurons",
            max_neurons=256,
            max_edges=(256 * 255) // 2,
            max_tuples_per_neuron=256,
            max_response_history=8,
            max_state_bytes=64 * 1024 * 1024,
        ),
    )
    neurons.commit(neurons.prepare(mount.causal_settlement))
    learning = WholeOrganismThingMosaicLearningOwner(
        authority_key=LEARNING_KEY,
        profile=profile,
        episode_authority=episodes,
        partition_authority=partitions,
        thing_owner=things,
        neuron_owner=neurons,
    )
    return (
        learning,
        profile,
        episodes,
        partitions,
        things,
        custody,
        custody_capability,
        consequence.capability,
    )


def test_action_consequence_learns_sight_and_body_without_sound_or_touch():
    (
        learning,
        profile,
        episodes,
        partitions,
        things,
        custody,
        custody_capability,
        consequence_capability,
    ) = _stack()

    result = learning.admit(
        custody_authority=custody,
        custody_capability=custody_capability,
        whole_organism_capability=consequence_capability,
        neuron_mosaic_assembly=(
            learning._neurons.issue_mosaic_assembly(
                custody.open_child(
                    custody_capability
                ).causal_settlement
            )
        ),
    )

    assert result.state == "learned"
    assert result.record is not None
    assert (
        result.record.neuron_mosaic_assembly.full_field_roots
        == result.record.full_field_roots
    )
    assert len(
        result.record.neuron_mosaic_assembly.root_bindings
    ) == len(result.record.full_field_roots)
    neuron_count = len(result.record.full_field_roots)
    assert len(
        result.record.neuron_mosaic_assembly
        .co_perturbation_couplings
    ) == neuron_count * (neuron_count - 1) // 2
    assert result.record.observed_senses == ("sight", "body")
    assert len(result.record.six_lane_settlement) == len(SENSE_ORDER)
    assert result.mosaic is things.mosaics[0]
    assert result.record.partition.entity_root_keys == tuple(sorted(
        root.route_key for root in result.record.full_field_roots
    ))
    assert all(
        tuple(
            name for name, _value in field_tuple["fields"]
        )
        == DSF_FIELD_ORDER
        for root in result.record.full_field_roots
        for field_tuple in __import__("json").loads(
            root.full_evidence_json
        )["field_tuples"]
    )
    assert learning.status()["master_sense"] is None
    assert learning.status()["reduced_approximation"] is False

    encoded = learning.snapshot_encoded()
    assert b"native_evidence_transition" in encoded
    assert b"receipt_records" not in encoded
    assert b"payload_base64" not in encoded
    cold = WholeOrganismThingMosaicLearningOwner.restore_encoded(
        authority_key=LEARNING_KEY,
        profile=profile,
        episode_authority=episodes,
        partition_authority=partitions,
        thing_owner=things,
        neuron_owner=learning._neurons,
        encoded=encoded,
    )
    assert cold.snapshot_encoded() == encoded
    assert cold.records == learning.records


def test_only_authenticated_empty_legacy_state_migrates() -> None:
    (
        learning,
        profile,
        episodes,
        partitions,
        things,
        _custody,
        _custody_capability,
        _consequence_capability,
    ) = _stack()
    body = {
        "profile": profile.record(),
        "records": [],
        "schema": learning_module.LEGACY_STATE_SCHEMA,
    }
    root = learning_module._key(
        LEARNING_KEY,
        "whole-organism THING learning",
    )
    legacy_state_key = hashlib.sha256(
        learning_module._LEGACY_STATE_DOMAIN + root
    ).digest()
    legacy_encoded = learning_module._canonical({
        "body": body,
        "schema": learning_module.LEGACY_ENVELOPE_SCHEMA,
        "state_hmac_sha256": hmac.new(
            legacy_state_key,
            learning_module._LEGACY_STATE_DOMAIN
            + learning_module._canonical(body),
            hashlib.sha256,
        ).hexdigest(),
    })

    restored = WholeOrganismThingMosaicLearningOwner.restore_encoded(
        authority_key=LEARNING_KEY,
        profile=profile,
        episode_authority=episodes,
        partition_authority=partitions,
        thing_owner=things,
        neuron_owner=learning._neurons,
        encoded=legacy_encoded,
    )

    assert restored.records == ()
    current = json.loads(restored.snapshot_encoded())
    assert current["schema"] == learning_module.ENVELOPE_SCHEMA
    assert current["body"]["schema"] == learning_module.STATE_SCHEMA


def test_state_capacity_refusal_does_not_create_a_thing():
    (
        learning,
        _profile,
        _episodes,
        _partitions,
        things,
        custody,
        custody_capability,
        consequence_capability,
    ) = _stack(learning_state_bytes=4_096)
    thing_before = things.snapshot_encoded()

    result = learning.admit(
        custody_authority=custody,
        custody_capability=custody_capability,
        whole_organism_capability=consequence_capability,
        neuron_mosaic_assembly=(
            learning._neurons.issue_mosaic_assembly(
                custody.open_child(
                    custody_capability
                ).causal_settlement
            )
        ),
    )

    assert result.state == "unresolved"
    assert result.reasons == (
        "whole-organism learning state capacity exhausted",
    )
    assert things.snapshot_encoded() == thing_before
    assert learning.records == ()


def test_untyped_neuron_assembly_cannot_reach_thing_mutation() -> None:
    (
        learning,
        _profile,
        _episodes,
        _partitions,
        things,
        custody,
        custody_capability,
        consequence_capability,
    ) = _stack()
    learning_before = learning.snapshot_encoded()
    thing_before = things.snapshot_encoded()

    with pytest.raises(TypeError, match="typed neuron mosaic assembly"):
        learning.admit(
            custody_authority=custody,
            custody_capability=custody_capability,
            whole_organism_capability=consequence_capability,
            neuron_mosaic_assembly=object(),
        )

    assert learning.snapshot_encoded() == learning_before
    assert things.snapshot_encoded() == thing_before


def test_valid_neuron_assembly_from_another_settlement_is_rejected() -> None:
    (
        learning,
        _profile,
        episodes,
        _partitions,
        things,
        custody,
        custody_capability,
        consequence_capability,
    ) = _stack()
    other_neurons = WholeOrganismNeuronPopulationOwner(
        authority_key=NEURON_KEY,
        manifest_authority_key=EPISODE_KEY,
        manifest=episodes.manifest,
        profile=learning._neurons._profile,
    )
    other_settlement = _authorization_settlement()
    other_neurons.commit(other_neurons.prepare(other_settlement))
    other_assembly = other_neurons.issue_mosaic_assembly(
        other_settlement
    )
    learning_before = learning.snapshot_encoded()
    thing_before = things.snapshot_encoded()

    result = learning.admit(
        custody_authority=custody,
        custody_capability=custody_capability,
        whole_organism_capability=consequence_capability,
        neuron_mosaic_assembly=other_assembly,
    )

    assert result.state == "unresolved"
    assert result.reasons == ("neuron mosaic assembly roots changed",)
    assert learning.snapshot_encoded() == learning_before
    assert things.snapshot_encoded() == thing_before


def test_post_commit_verification_failure_rolls_back_exact_bytes(
    monkeypatch,
):
    (
        learning,
        _profile,
        _episodes,
        _partitions,
        things,
        custody,
        custody_capability,
        consequence_capability,
    ) = _stack()
    learning_before = learning.snapshot_encoded()
    thing_before = things.snapshot_encoded()

    def _fail(_record):
        raise RuntimeError("injected post-commit verification failure")

    monkeypatch.setattr(
        learning,
        "_verify_external_authorities",
        _fail,
    )
    with pytest.raises(
        RuntimeError,
        match="injected post-commit",
    ):
        learning.admit(
            custody_authority=custody,
            custody_capability=custody_capability,
            whole_organism_capability=consequence_capability,
            neuron_mosaic_assembly=(
                learning._neurons.issue_mosaic_assembly(
                    custody.open_child(
                        custody_capability
                    ).causal_settlement
                )
            ),
        )

    assert learning.snapshot_encoded() == learning_before
    assert things.snapshot_encoded() == thing_before
    assert learning.records == ()
