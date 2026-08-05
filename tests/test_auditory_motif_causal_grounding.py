from __future__ import annotations

import hashlib
import json
import math
from fractions import Fraction
from types import SimpleNamespace

import pytest
import numpy as np

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    NativeSensorySubstreamInput,
    build_six_sense_full_field,
    build_transaction_owned_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate import auditory_motif_causal_grounding as grounding
from dsf_ai_service.substrate.auditory_kernel_mount import (
    auditory_kernel_component_inputs,
)
from dsf_ai_service.substrate.auditory_l5 import AuditoryL5Owner
from dsf_ai_service.substrate.auditory_receptor_event_boundary import (
    AuditoryReceptorEventState,
    settle_auditory_receptor_event,
)
from dsf_ai_service.substrate.auditory_recurrent_motif import (
    AuditoryMotifActivation,
    AuditoryMotifObservationState,
    AuditoryMotifResourceProfile,
    AuditoryReceptorExperience,
    AuditoryReceptorIdentity,
    AuditoryReceptorOccurrence,
    AuditoryRecurrentMotifOwner,
    _digest as _motif_digest,
    _rank_proof,
    receptor_experience_from_full_field_event,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    AUDITORY_CHANNELS,
    COCHLEAR_CHANNEL_COUNT,
    OBSERVATION_HOP_SAMPLES,
    REQUIRED_SAMPLE_RATE_HZ,
    transduce_auditory_full_field,
)


AUTHORITY_KEY = b"auditory-motif-grounding-test-key"


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _profile(
    *,
    max_firing_motifs: int = 16,
    max_activations: int = 32,
) -> grounding.AuditoryMotifGroundingResourceProfile:
    return grounding.AuditoryMotifGroundingResourceProfile.create(
        profile_id="focused-controlled-grounding",
        max_episodes=32,
        max_distinctions=8,
        max_firing_motifs_per_episode=max_firing_motifs,
        max_activations_per_episode=max_activations,
        max_roots_per_episode=32,
        max_episode_bytes=2 * 1024 * 1024,
        max_state_bytes=32 * 1024 * 1024,
    )


def _settlement(
    *,
    assembly_id: str,
    frequency: int,
    object_provenance: str = "object-not-identity",
):
    sample_count = 96
    signal = tuple(
        math.sin(2 * math.pi * frequency * index / 200)
        for index in range(sample_count)
    )
    sight = NativeSensorySubstreamInput(
        sense=PhysicalSense.SIGHT,
        sensor_id="test-camera",
        substream_id=f"visible-object-{object_provenance}",
        topology_index=0,
        coordinates=(
            NativeAxisCoordinate("reference-frame", "body-centered"),
            NativeAxisCoordinate("object-identity", object_provenance),
        ),
        physical_quantity="light-intensity",
        physical_unit="normalized-intensity",
        source_times=tuple(
            Fraction(index, 200) for index in range(sample_count)
        ),
        normalized_signal=signal,
        phase_turns=tuple(
            Fraction(index // 12) for index in range(sample_count)
        ),
    )
    built = build_six_sense_full_field(
        assembly_id=assembly_id,
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
        observed_substreams={PhysicalSense.SIGHT: (sight,)},
        states={
            sense: (
                SenseBoundaryState.OBSERVED
                if sense is PhysicalSense.SIGHT
                else SenseBoundaryState.SENSOR_UNAVAILABLE
            )
            for sense in SENSE_ORDER
        },
    )
    return ExactCausalExperienceOwner(
        on_settlement=lambda _value: None,
        log_event=lambda *_args, **_kwargs: None,
    ).settle(
        built,
        routing_chis=(),
        source_tags=(),
    )


def _occurrence(seed: int) -> AuditoryReceptorOccurrence:
    receptor = AuditoryReceptorIdentity(
        cochlear_index=0,
        channel_id=AUDITORY_CHANNELS[0].name,
        winding_direction=1,
    )
    pressure_fields = tuple(
        (name, Fraction(seed + ordinal + 1, 100))
        for ordinal, name in enumerate(DSF_FIELD_ORDER)
    )
    phase_fields = tuple(
        (name, Fraction(seed + ordinal + 21, 100))
        for ordinal, name in enumerate(DSF_FIELD_ORDER)
    )
    provisional = AuditoryReceptorOccurrence(
        receptor=receptor,
        source_index=seed,
        source_time=Fraction(seed + 1, 100),
        causal_interval_end=Fraction(seed + 2, 100),
        winding_delta=1,
        pressure_fields=pressure_fields,
        phase_fields=phase_fields,
        pressure_field_receipt_sha256=_sha(f"pressure-{seed}"),
        phase_field_receipt_sha256=_sha(f"phase-{seed}"),
        authority_receipt_sha256="0" * 64,
    )
    result = AuditoryReceptorOccurrence(
        receptor=provisional.receptor,
        source_index=provisional.source_index,
        source_time=provisional.source_time,
        causal_interval_end=provisional.causal_interval_end,
        winding_delta=provisional.winding_delta,
        pressure_fields=provisional.pressure_fields,
        phase_fields=provisional.phase_fields,
        pressure_field_receipt_sha256=(
            provisional.pressure_field_receipt_sha256
        ),
        phase_field_receipt_sha256=(
            provisional.phase_field_receipt_sha256
        ),
        authority_receipt_sha256=grounding._digest(
            provisional.payload()
        ),
    )
    result.verify()
    return result


def _activation(
    motif_id: str,
    ordinal: int,
) -> grounding.GroundingActivationEvidence:
    occurrence = _occurrence(ordinal)
    return grounding.GroundingActivationEvidence.from_activation(
        AuditoryMotifActivation(
            neuron_id=motif_id,
            segment_index=0,
            state_ordinal_start=0,
            state_ordinal_end=1,
            source_index_start=ordinal,
            source_index_end=ordinal,
            source_time_start=occurrence.source_time,
            source_time_end=occurrence.causal_interval_end,
            full_field_occurrences=(occurrence,),
        )
    )


def _install_episode(
    owner: grounding.AuditoryMotifCausalGroundingOwner,
    *,
    occurrence_name: str,
    firing_names: tuple[str, ...],
    frequency: int,
    object_provenance: str = "object-not-identity",
    auditory_source_name: str | None = None,
) -> grounding.GroundingEpisode:
    settlement = _settlement(
        assembly_id=f"assembly-{occurrence_name}",
        frequency=frequency,
        object_provenance=object_provenance,
    )
    motif_ids = tuple(sorted(_sha(value) for value in firing_names))
    roots = grounding._roots_from_settlement(settlement)
    activations = tuple(
        _activation(motif_id, ordinal)
        for ordinal, motif_id in enumerate(motif_ids)
    )
    experience_receipt = _sha(f"experience-{occurrence_name}")
    source_event_receipt = _sha(
        f"source-{auditory_source_name or occurrence_name}"
    )
    identity_payload = {
        "auditory_experience_receipt_sha256": experience_receipt,
        "auditory_source_event_receipt_sha256": source_event_receipt,
        "firing_motif_neuron_ids": list(motif_ids),
        "roots": [
            [value.root_id, value.value_sha256] for value in roots
        ],
        "source_time_end": "1/1",
        "source_time_start": "0/1",
    }
    provisional = grounding.GroundingEpisode(
        episode_id=grounding._digest(identity_payload),
        auditory_experience_receipt_sha256=experience_receipt,
        auditory_source_event_receipt_sha256=source_event_receipt,
        settlement_authority_receipt_sha256=(
            settlement.authority_receipt_sha256
        ),
        motif_bank_state_sha256=_sha("motif-bank"),
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
        firing_motif_neuron_ids=motif_ids,
        unresolved_source_indices=(0,),
        activations=activations,
        roots=roots,
        authority_hmac_sha256="",
    )
    episode = grounding.GroundingEpisode(
        episode_id=provisional.episode_id,
        auditory_experience_receipt_sha256=(
            provisional.auditory_experience_receipt_sha256
        ),
        auditory_source_event_receipt_sha256=(
            provisional.auditory_source_event_receipt_sha256
        ),
        settlement_authority_receipt_sha256=(
            provisional.settlement_authority_receipt_sha256
        ),
        motif_bank_state_sha256=provisional.motif_bank_state_sha256,
        source_time_start=provisional.source_time_start,
        source_time_end=provisional.source_time_end,
        firing_motif_neuron_ids=provisional.firing_motif_neuron_ids,
        unresolved_source_indices=provisional.unresolved_source_indices,
        activations=provisional.activations,
        roots=provisional.roots,
        authority_hmac_sha256=grounding._sign(
            owner._episode_key,
            grounding._EPISODE_DOMAIN,
            provisional.payload(),
        ),
    )
    episode.verify(
        authority_key=owner._episode_key,
        profile=owner.resource_profile,
    )
    owner._episodes[episode.episode_id] = episode
    return episode


def _install_hello_daddy_curriculum(
    owner: grounding.AuditoryMotifCausalGroundingOwner,
):
    hello_one = _install_episode(
        owner=owner,
        occurrence_name="hello-one",
        firing_names=("shared", "hello-leak", "hello-diagnostic", "noise-a"),
        frequency=8,
    )
    hello_two = _install_episode(
        owner=owner,
        occurrence_name="hello-two",
        firing_names=("shared", "hello-leak", "hello-diagnostic", "noise-b"),
        frequency=8,
        object_provenance="different-id-same-physics",
    )
    daddy_one = _install_episode(
        owner=owner,
        occurrence_name="daddy-one",
        firing_names=("shared", "hello-leak", "daddy-diagnostic", "noise-c"),
        frequency=9,
    )
    daddy_two = _install_episode(
        owner=owner,
        occurrence_name="daddy-two",
        firing_names=("shared", "hello-leak", "daddy-diagnostic", "noise-d"),
        frequency=9,
    )
    result = owner.learn_controlled_distinction(tuple(sorted(
        value.episode_id
        for value in (hello_one, hello_two, daddy_one, daddy_two)
    )))
    assert result.state is grounding.GroundingLearningState.SETTLED
    assert result.distinction is not None
    return result.distinction


def _resolve(
    monkeypatch: pytest.MonkeyPatch,
    owner: grounding.AuditoryMotifCausalGroundingOwner,
    firing_names: tuple[str, ...],
):
    motif_ids = tuple(sorted(_sha(value) for value in firing_names))
    firing = SimpleNamespace(
        state=AuditoryMotifObservationState.OBSERVED,
        firing_motif_neuron_ids=motif_ids,
        unresolved_source_indices=(),
        activations=(),
        reason="test exact firing",
    )
    monkeypatch.setattr(
        grounding,
        "_stable_firing",
        lambda **_kwargs: (firing, _sha("stable-bank"), ""),
    )
    return owner.resolve(
        motif_owner=object(),
        auditory_experience=object(),
    )


def test_controlled_conjunction_excludes_shared_and_incidental_motifs() -> None:
    owner = grounding.AuditoryMotifCausalGroundingOwner(
        authority_key=AUTHORITY_KEY,
        resource_profile=_profile(),
    )
    distinction = _install_hello_daddy_curriculum(owner)

    diagnostics = {
        item.root.value_sha256: item.diagnostic_motif_neuron_ids
        for item in distinction.alternatives
    }

    assert set(diagnostics.values()) == {
        (_sha("hello-diagnostic"),),
        (_sha("daddy-diagnostic"),),
    }
    assert all(
        _sha("shared") not in value
        and _sha("hello-leak") not in value
        and _sha("noise-a") not in value
        for value in diagnostics.values()
    )


def test_shared_daddy_firing_does_not_false_resolve_hello(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = grounding.AuditoryMotifCausalGroundingOwner(
        authority_key=AUTHORITY_KEY,
        resource_profile=_profile(),
    )
    _install_hello_daddy_curriculum(owner)

    result = _resolve(
        monkeypatch,
        owner,
        ("shared", "hello-leak", "daddy-diagnostic"),
    )

    assert result.state is grounding.GroundingResolutionState.RESOLVED
    assert len(result.referents) == 1
    assert result.referents[0].contributing_motif_neuron_ids == (
        _sha("daddy-diagnostic"),
    )
    hello_diagnostic = next(
        value for value in result.diagnostics
        if value.required_motif_neuron_ids
        == (_sha("hello-diagnostic"),)
    )
    assert hello_diagnostic.state is grounding.DiagnosticActivationState.ABSENT


def test_overlap_superset_resolves_both_independent_referents(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = grounding.AuditoryMotifCausalGroundingOwner(
        authority_key=AUTHORITY_KEY,
        resource_profile=_profile(),
    )
    _install_hello_daddy_curriculum(owner)

    result = _resolve(
        monkeypatch,
        owner,
        (
            "shared",
            "hello-leak",
            "hello-diagnostic",
            "daddy-diagnostic",
            "mixture-noise",
        ),
    )

    assert result.state is grounding.GroundingResolutionState.RESOLVED
    assert {
        value.contributing_motif_neuron_ids
        for value in result.referents
    } == {
        (_sha("hello-diagnostic"),),
        (_sha("daddy-diagnostic"),),
    }
    assert result.ungrounded_motif_neuron_ids == tuple(sorted((
        _sha("hello-leak"),
        _sha("mixture-noise"),
        _sha("shared"),
    )))


def test_empty_diagnostic_conjunction_remains_unresolved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = grounding.AuditoryMotifCausalGroundingOwner(
        authority_key=AUTHORITY_KEY,
        resource_profile=_profile(),
    )
    episodes = (
        _install_episode(
            owner,
            occurrence_name="a-one",
            firing_names=("shared", "same"),
            frequency=10,
        ),
        _install_episode(
            owner,
            occurrence_name="a-two",
            firing_names=("shared", "same"),
            frequency=10,
        ),
        _install_episode(
            owner,
            occurrence_name="b-one",
            firing_names=("shared", "same", "noise-one"),
            frequency=11,
        ),
        _install_episode(
            owner,
            occurrence_name="b-two",
            firing_names=("shared", "same", "noise-two"),
            frequency=11,
        ),
    )
    learned = owner.learn_controlled_distinction(tuple(sorted(
        value.episode_id for value in episodes
    )))

    assert learned.state is grounding.GroundingLearningState.SETTLED
    assert len(learned.unresolved_referent_value_sha256s) == 2
    result = _resolve(monkeypatch, owner, ("shared", "same"))
    assert result.state is grounding.GroundingResolutionState.UNKNOWN
    assert not result.referents
    assert {
        value.state for value in result.diagnostics
    } == {grounding.DiagnosticActivationState.UNRESOLVED_EMPTY}


def test_replayed_auditory_source_cannot_satisfy_positive_recurrence() -> None:
    owner = grounding.AuditoryMotifCausalGroundingOwner(
        authority_key=AUTHORITY_KEY,
        resource_profile=_profile(),
    )
    episodes = (
        _install_episode(
            owner,
            occurrence_name="replay-a-one",
            auditory_source_name="same-auditory-event",
            firing_names=("shared", "a-diagnostic"),
            frequency=12,
        ),
        _install_episode(
            owner,
            occurrence_name="replay-a-two",
            auditory_source_name="same-auditory-event",
            firing_names=("shared", "a-diagnostic"),
            frequency=12,
        ),
        _install_episode(
            owner,
            occurrence_name="replay-b-one",
            firing_names=("shared", "b-diagnostic"),
            frequency=13,
        ),
        _install_episode(
            owner,
            occurrence_name="replay-b-two",
            firing_names=("shared", "b-diagnostic"),
            frequency=13,
        ),
    )

    learned = owner.learn_controlled_distinction(tuple(sorted(
        value.episode_id for value in episodes
    )))

    assert learned.state is grounding.GroundingLearningState.UNKNOWN
    assert learned.distinction is None
    assert "distinct physical auditory source events" in learned.reason
    assert owner.status()["distinction_count"] == 0


def test_contextual_positive_refines_fragile_diagnostic_by_exact_intersection():
    owner = grounding.AuditoryMotifCausalGroundingOwner(
        authority_key=AUTHORITY_KEY,
        resource_profile=_profile(),
    )
    hello = (
        _install_episode(
            owner,
            occurrence_name="context-hello-one",
            firing_names=("common", "hello-diagnostic"),
            frequency=14,
        ),
        _install_episode(
            owner,
            occurrence_name="context-hello-two",
            firing_names=("common", "hello-diagnostic"),
            frequency=14,
        ),
    )
    daddy = (
        _install_episode(
            owner,
            occurrence_name="context-daddy-clean",
            firing_names=(
                "common",
                "daddy-diagnostic",
                "fragile-context-only",
            ),
            frequency=15,
        ),
        _install_episode(
            owner,
            occurrence_name="context-daddy-half-gain",
            firing_names=(
                "common",
                "daddy-diagnostic",
                "fragile-context-only",
            ),
            frequency=15,
        ),
    )
    first = owner.learn_controlled_distinction(tuple(sorted(
        value.episode_id for value in (*hello, *daddy)
    )))
    assert first.distinction is not None
    daddy_root_sha = {
        root.root_id: root.value_sha256 for root in daddy[0].roots
    }[first.distinction.referent_root_id]
    first_daddy = next(
        value for value in first.distinction.alternatives
        if value.root.value_sha256 == daddy_root_sha
    )
    assert set(first_daddy.diagnostic_motif_neuron_ids) == {
        _sha("daddy-diagnostic"),
        _sha("fragile-context-only"),
    }
    contextual = _install_episode(
        owner,
        occurrence_name="context-daddy-overlap",
        firing_names=(
            "common",
            "hello-diagnostic",
            "daddy-diagnostic",
        ),
        frequency=15,
    )

    refined = owner.learn_controlled_distinction(tuple(sorted(
        value.episode_id for value in (*hello, *daddy, contextual)
    )))

    assert refined.state is grounding.GroundingLearningState.SETTLED
    assert refined.distinction is not None
    refined_daddy = next(
        value for value in refined.distinction.alternatives
        if value.root.value_sha256 == daddy_root_sha
    )
    assert refined_daddy.diagnostic_motif_neuron_ids == (
        _sha("daddy-diagnostic"),
    )


def _reseal_changed_root(
    owner: grounding.AuditoryMotifCausalGroundingOwner,
    encoded: bytes,
    *,
    removed_field: str | None,
) -> bytes:
    envelope = json.loads(encoded)
    episode = envelope["body"]["episodes"][0]
    root = next(
        value for value in episode["roots"]
        if json.loads(value["value_json"])["field_tuples"]
    )
    root_value = json.loads(root["value_json"])
    first_tuple = root_value["field_tuples"][0]
    if removed_field is None:
        del first_tuple["source_index_end"]
    else:
        first_tuple["fields"] = [
            value for value in first_tuple["fields"]
            if value[0] != removed_field
        ]
    root["value_json"] = grounding._canonical_json_text(root_value)
    root["value_sha256"] = grounding._digest(
        grounding._physical_root_identity(root_value)
    )
    identity_payload = {
        "auditory_experience_receipt_sha256": (
            episode["auditory_experience_receipt_sha256"]
        ),
        "auditory_source_event_receipt_sha256": (
            episode["auditory_source_event_receipt_sha256"]
        ),
        "firing_motif_neuron_ids": episode["firing_motif_neuron_ids"],
        "roots": [
            [value["root_id"], value["value_sha256"]]
            for value in episode["roots"]
        ],
        "source_time_end": episode["source_time_end"],
        "source_time_start": episode["source_time_start"],
    }
    episode["episode_id"] = grounding._digest(identity_payload)
    episode_payload = {
        key: value for key, value in episode.items()
        if key not in {"authority_hmac_sha256", "episode_id"}
    }
    episode["authority_hmac_sha256"] = grounding._sign(
        owner._episode_key,
        grounding._EPISODE_DOMAIN,
        episode_payload,
    )
    envelope["state_hmac_sha256"] = grounding._sign(
        owner._state_key,
        grounding._STATE_DOMAIN,
        envelope["body"],
    )
    return grounding._canonical(envelope)


@pytest.mark.parametrize("removed_field", (*DSF_FIELD_ORDER, None))
def test_resealed_state_rejects_field_or_causal_support_loss(
    removed_field: str | None,
) -> None:
    owner = grounding.AuditoryMotifCausalGroundingOwner(
        authority_key=AUTHORITY_KEY,
        resource_profile=_profile(),
    )
    _install_hello_daddy_curriculum(owner)
    tampered = _reseal_changed_root(
        owner,
        owner.snapshot_encoded(),
        removed_field=removed_field,
    )

    with pytest.raises(ValueError):
        grounding.AuditoryMotifCausalGroundingOwner.restore_encoded(
            authority_key=AUTHORITY_KEY,
            encoded=tampered,
        )


def test_persistence_round_trip_retains_full_field_authority() -> None:
    owner = grounding.AuditoryMotifCausalGroundingOwner(
        authority_key=AUTHORITY_KEY,
        resource_profile=_profile(),
    )
    _install_hello_daddy_curriculum(owner)

    encoded = owner.snapshot_encoded()
    restored = grounding.AuditoryMotifCausalGroundingOwner.restore_encoded(
        authority_key=AUTHORITY_KEY,
        encoded=encoded,
    )

    assert restored.snapshot_encoded() == encoded
    assert restored.episodes == owner.episodes
    assert restored.distinctions == owner.distinctions
    for episode in restored.episodes:
        for activation in episode.activations:
            decoded = json.loads(activation.activation_json)
            for occurrence in decoded["full_field_occurrences"]:
                assert tuple(
                    value[0] for value in occurrence["pressure_fields"]
                ) == DSF_FIELD_ORDER
                assert tuple(
                    value[0] for value in occurrence["phase_fields"]
                ) == DSF_FIELD_ORDER
    status = restored.status()
    assert status["episode_count"] == 4
    assert status["distinction_count"] == 1
    assert status["learned_referent_count"] == 2
    assert status["unresolved_referent_count"] == 0
    assert status["retained_proof_episode_count"] == 4
    assert status["unsettled_episode_count"] == 0
    assert not status["episode_capacity_exhausted"]
    assert status["encoded_state_bytes"] == len(encoded)


def _exact_experience(
    *,
    occurrence_name: str,
    motif_receptor_pairs: tuple[
        tuple[AuditoryReceptorIdentity, AuditoryReceptorIdentity], ...
    ],
    seed: int,
) -> AuditoryReceptorExperience:
    occurrences = []
    segments = []
    segment_indices = []
    source_index = 0
    for pair in motif_receptor_pairs:
        states = []
        indices = []
        for receptor in pair:
            pressure_fields = tuple(
                (name, Fraction(seed + source_index + ordinal + 1, 1000))
                for ordinal, name in enumerate(DSF_FIELD_ORDER)
            )
            phase_fields = tuple(
                (name, Fraction(seed + source_index + ordinal + 21, 1000))
                for ordinal, name in enumerate(DSF_FIELD_ORDER)
            )
            provisional = AuditoryReceptorOccurrence(
                receptor=receptor,
                source_index=source_index,
                source_time=Fraction(source_index + 1, 100),
                causal_interval_end=Fraction(source_index + 2, 100),
                winding_delta=receptor.winding_direction,
                pressure_fields=pressure_fields,
                phase_fields=phase_fields,
                pressure_field_receipt_sha256=_sha(
                    f"{occurrence_name}-pressure-{source_index}"
                ),
                phase_field_receipt_sha256=_sha(
                    f"{occurrence_name}-phase-{source_index}"
                ),
                authority_receipt_sha256="0" * 64,
            )
            occurrence = AuditoryReceptorOccurrence(
                receptor=provisional.receptor,
                source_index=provisional.source_index,
                source_time=provisional.source_time,
                causal_interval_end=provisional.causal_interval_end,
                winding_delta=provisional.winding_delta,
                pressure_fields=provisional.pressure_fields,
                phase_fields=provisional.phase_fields,
                pressure_field_receipt_sha256=(
                    provisional.pressure_field_receipt_sha256
                ),
                phase_field_receipt_sha256=(
                    provisional.phase_field_receipt_sha256
                ),
                authority_receipt_sha256=_motif_digest(
                    provisional.payload()
                ),
            )
            occurrence.verify()
            occurrences.append(occurrence)
            states.append((receptor,))
            indices.append(source_index)
            source_index += 1
        segments.append(tuple(states))
        segment_indices.append(tuple(indices))
    occurrence_tuple = tuple(occurrences)
    proofs = []
    for channel_index in range(COCHLEAR_CHANNEL_COUNT):
        channel_occurrences = tuple(
            value for value in occurrence_tuple
            if value.receptor.cochlear_index == channel_index
        )
        for kind in ("pressure", "phase"):
            proofs.append(_rank_proof(
                component_id=(
                    f"{AUDITORY_CHANNELS[channel_index].name}_{kind}"
                ),
                component_kind=kind,
                rows=tuple(
                    tuple(field for _name, field in (
                        value.pressure_fields
                        if kind == "pressure"
                        else value.phase_fields
                    ))
                    for value in channel_occurrences
                ),
                source_receipts=tuple(
                    value.pressure_field_receipt_sha256
                    if kind == "pressure"
                    else value.phase_field_receipt_sha256
                    for value in channel_occurrences
                ),
            ))
    source_receipt = _sha(f"source-event-{occurrence_name}")
    provisional_experience = AuditoryReceptorExperience(
        source_event_receipt_sha256=source_receipt,
        source_event_receipt_sha256s=(source_receipt,),
        source_continuity_receipt_sha256s=(),
        source_frame_count=source_index,
        occurrences=occurrence_tuple,
        causal_segments=tuple(segments),
        causal_segment_source_indices=tuple(segment_indices),
        unresolved_source_indices=(),
        component_rank_proofs=tuple(proofs),
        resonance_graph_authority_receipt_sha256=None,
        resonance_operator_authority_receipt_sha256=None,
        resonance_result_receipt_sha256=None,
        authority_receipt_sha256="0" * 64,
    )
    experience = AuditoryReceptorExperience(
        source_event_receipt_sha256=(
            provisional_experience.source_event_receipt_sha256
        ),
        source_event_receipt_sha256s=(
            provisional_experience.source_event_receipt_sha256s
        ),
        source_continuity_receipt_sha256s=(
            provisional_experience.source_continuity_receipt_sha256s
        ),
        source_frame_count=provisional_experience.source_frame_count,
        occurrences=provisional_experience.occurrences,
        causal_segments=provisional_experience.causal_segments,
        causal_segment_source_indices=(
            provisional_experience.causal_segment_source_indices
        ),
        unresolved_source_indices=(
            provisional_experience.unresolved_source_indices
        ),
        component_rank_proofs=(
            provisional_experience.component_rank_proofs
        ),
        resonance_graph_authority_receipt_sha256=None,
        resonance_operator_authority_receipt_sha256=None,
        resonance_result_receipt_sha256=None,
        authority_receipt_sha256=_motif_digest(
            provisional_experience.payload()
        ),
    )
    experience.verify()
    return experience


def _physical_linked_episode(
    *,
    auditory_frequency: int,
    sight_frequency: int,
    ordinal: int,
):
    sample_count = 3200
    source_anchor = Fraction(ordinal)
    source_times = np.arange(sample_count) / REQUIRED_SAMPLE_RATE_HZ
    amplitude = 10_000 + (ordinal % 2) * 1_000
    pcm = np.rint(
        amplitude
        * (
            0.55
            + 0.4 * np.sin(2 * math.pi * 5 * source_times)
        )
        * np.sin(
            2
            * math.pi
            * auditory_frequency
            * source_times
        )
    ).astype("<i2")
    capture = transduce_auditory_full_field(
        pcm.astype(np.float64) / 32768.0,
        sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ,
    )
    auditory = auditory_kernel_component_inputs(
        capture,
        source_anchor=source_anchor,
    )
    sight_count = 96
    sight = NativeSensorySubstreamInput(
        sense=PhysicalSense.SIGHT,
        sensor_id="linked-grounding-camera",
        substream_id=f"linked-visible-provenance-{ordinal}",
        topology_index=0,
        coordinates=(
            NativeAxisCoordinate("reference-frame", "body-centered"),
            NativeAxisCoordinate("object-provenance", str(ordinal)),
        ),
        physical_quantity="light-intensity",
        physical_unit="normalized-intensity",
        source_times=tuple(
            source_anchor + Fraction(index, 1000)
            for index in range(sight_count)
        ),
        normalized_signal=tuple(
            math.sin(
                2 * math.pi * sight_frequency * index / 1000
            )
            for index in range(sight_count)
        ),
        phase_turns=tuple(
            Fraction(index // 12) for index in range(sight_count)
        ),
    )
    built = build_transaction_owned_six_sense_full_field(
        assembly_id=f"linked-grounding-{ordinal}",
        source_time_start=source_anchor,
        source_time_end=source_anchor + Fraction(
            (capture.frame_count + 1) * OBSERVATION_HOP_SAMPLES,
            REQUIRED_SAMPLE_RATE_HZ,
        ),
        observed_substreams={
            PhysicalSense.SIGHT: (sight,),
            PhysicalSense.SOUND: auditory,
        },
        states={
            sense: (
                SenseBoundaryState.OBSERVED
                if sense in (PhysicalSense.SIGHT, PhysicalSense.SOUND)
                else SenseBoundaryState.SENSOR_UNAVAILABLE
            )
            for sense in SENSE_ORDER
        },
    )
    auditory_l5 = AuditoryL5Owner(
        log_event=lambda *_args, **_kwargs: None
    ).settle(built, event_boundary="utterance")
    assert auditory_l5 is not None
    boundary = settle_auditory_receptor_event(
        capture=capture,
        auditory_l5=auditory_l5,
    )
    assert boundary.state is AuditoryReceptorEventState.OBSERVED
    assert boundary.event is not None
    experience = receptor_experience_from_full_field_event(
        boundary.event
    )
    settlement = ExactCausalExperienceOwner(
        on_settlement=lambda _value: None,
        log_event=lambda *_args, **_kwargs: None,
    ).settle(
        built,
        routing_chis=(),
        source_tags=(),
    )
    return boundary.event, experience, settlement


def test_public_motif_grounding_chain_rejects_cross_paired_transactions():
    motif_owner = AuditoryRecurrentMotifOwner(
        AuditoryMotifResourceProfile.create(
            profile_id="public-physical-grounding-chain-motifs",
            ear_count=1,
            max_motif_neurons=12_096,
            max_pending_experiences=16,
            max_work_cells_per_observation=1_000_000,
            max_exact_fraction_text_bytes=4096,
            encoded_state_allocation_bytes=64 * 1024 * 1024,
        )
    )
    training_one = _physical_linked_episode(
        auditory_frequency=440,
        sight_frequency=8,
        ordinal=1,
    )
    training_two = _physical_linked_episode(
        auditory_frequency=440,
        sight_frequency=8,
        ordinal=2,
    )
    motif_owner.observe(training_one[1])
    observed = motif_owner.observe(training_two[1])
    assert observed.newly_grown_motif_neuron_ids

    first = _physical_linked_episode(
        auditory_frequency=440,
        sight_frequency=8,
        ordinal=3,
    )
    second = _physical_linked_episode(
        auditory_frequency=440,
        sight_frequency=8,
        ordinal=4,
    )
    grounding_owner = grounding.AuditoryMotifCausalGroundingOwner(
        authority_key=AUTHORITY_KEY,
        resource_profile=_profile(
            max_firing_motifs=128,
            max_activations=128,
        ),
    )
    with pytest.raises(
        ValueError,
        match="not mounted in this settlement",
    ):
        grounding_owner.admit_episode(
            motif_owner=motif_owner,
            auditory_event=first[0],
            auditory_experience=first[1],
            settlement=second[2],
        )
    admitted = grounding_owner.admit_episode(
        motif_owner=motif_owner,
        auditory_event=first[0],
        auditory_experience=first[1],
        settlement=first[2],
    )
    assert admitted.state is grounding.GroundingAdmissionState.ADMITTED
    assert admitted.episode is not None
