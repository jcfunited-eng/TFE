from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.commit import (
    closed_experience_seal_receipt_payload,
)
from dsf_ai_service.glew_runtime.fresh_recall_executor import (
    create_fresh_recall_archive_lineage,
)
from dsf_ai_service.glew_runtime.fresh_recall_provider import (
    verify_fresh_recall_archive_lineage_authority,
)
from dsf_ai_service.glew_runtime.language import encode_balanced_ternary_scalar
from dsf_ai_service.glew_runtime.model import (
    ReceiptError,
    ReceiptRecord,
    ReceiptRegistry,
    receipt_sha256,
)
from dsf_ai_service.glew_runtime.output import (
    MotifOutputBinding,
    OutputBindingKind,
    motif_output_binding_receipt_payload,
)
from tests.glew_runtime.test_recall_story_episode_archive import (
    admitted_archive,
)
from tests.glew_runtime.test_story_global_uf_basin import (
    _mounted_six_lane_preparation,
)


def _extend(registry: ReceiptRegistry, *payloads: bytes) -> ReceiptRegistry:
    mounted = {value.digest: value.payload for value in registry.records}
    for payload in payloads:
        digest = receipt_sha256(payload)
        assert mounted.get(digest, payload) == payload
        mounted[digest] = payload
    return ReceiptRegistry(
        registry.profile_binding_sha256,
        tuple(ReceiptRecord(key, mounted[key]) for key in sorted(mounted)),
    )


def _merge(left: ReceiptRegistry, right: ReceiptRegistry) -> ReceiptRegistry:
    assert left.profile_binding_sha256 == right.profile_binding_sha256
    return _extend(left, *(value.payload for value in right.records))


def _binding(episode, profile, registry):
    expression = episode.evidence_preparation_receipt_sha256
    recognition = episode.boundary_receipt_sha256
    closed_payload = closed_experience_seal_receipt_payload(
        experience_id="fresh-recall-lineage-source-experience",
        topology_authority_receipt_sha256=(
            profile.topology.authority_receipt_sha256
        ),
        input_expression_receipt_sha256=expression,
        recognition_receipt_sha256=recognition,
        ordered_evidence_receipt_sha256s=(
            episode.sensory_evidence_receipt_sha256s
        ),
        source_time_start=Fraction(0),
        source_time_end=Fraction(14),
        structural_time_unit="test-structural-time",
    )
    motif_payload = b'{"schema":"glew.test.fresh_recall_lineage_motif.v1"}'
    strand_payload = b'{"schema":"glew.test.fresh_recall_lineage_strand.v1"}'
    output_payload = b'{"schema":"glew.test.fresh_recall_lineage_output.v1"}'
    binding_payload = motif_output_binding_receipt_payload(
        binding_id="fresh-recall-lineage-binding",
        profile_binding_sha256=profile.authority_receipt_sha256,
        motif_receipt_sha256=receipt_sha256(motif_payload),
        closed_experience_receipt_sha256=receipt_sha256(closed_payload),
        fact_strand_receipt_sha256=receipt_sha256(strand_payload),
        sensory_evidence_receipt_sha256s=tuple(
            sorted(episode.sensory_evidence_receipt_sha256s)
        ),
        coexperienced_output_receipt_sha256=receipt_sha256(output_payload),
        kind=OutputBindingKind.LANGUAGE_SCALAR,
        trits=encode_balanced_ternary_scalar(ord("b")),
        language_scalar_cardinality=1,
        no_output_cardinality=0,
    )
    mounted = _extend(
        registry,
        episode.episode_receipt_payload,
        closed_payload,
        motif_payload,
        strand_payload,
        output_payload,
        binding_payload,
    )
    value = MotifOutputBinding(
        "fresh-recall-lineage-binding",
        profile.authority_receipt_sha256,
        receipt_sha256(motif_payload),
        receipt_sha256(closed_payload),
        receipt_sha256(strand_payload),
        tuple(sorted(episode.sensory_evidence_receipt_sha256s)),
        receipt_sha256(output_payload),
        OutputBindingKind.LANGUAGE_SCALAR,
        encode_balanced_ternary_scalar(ord("b")),
        1,
        0,
        receipt_sha256(binding_payload),
    )
    value.verify(mounted)
    return value, mounted


@pytest.fixture(scope="module")
def exact_lineage_case():
    (
        profile,
        _,
        _,
        _,
        _,
        _,
        episode,
        _,
    ) = admitted_archive.__wrapped__()
    preparation, _, _, _, _, _, fresh_registry = (
        _mounted_six_lane_preparation()
    )
    registry = _merge(
        ReceiptRegistry(profile.authority_receipt_sha256, episode.receipt_records),
        fresh_registry,
    )
    binding, registry = _binding(episode, profile, registry)
    base = preparation.contexts[0]
    fresh_sensory = tuple(
        value for value in base.sealed.evidence if value.lane_id != "language"
    )
    lineage, registry = create_fresh_recall_archive_lineage(
        episode=episode,
        source_binding_receipt_sha256=binding.binding_receipt_sha256,
        fresh_closed_experience_receipt_sha256=(
            base.sealed.closed_experience.authority_receipt_sha256
        ),
        fresh_sensory_evidence=fresh_sensory,
        receipt_registry=registry,
    )
    return (
        episode,
        binding,
        fresh_sensory,
        lineage,
        base.sealed.closed_experience.authority_receipt_sha256,
        registry,
    )


def test_provider_accepts_exact_raw_lineage_not_topology_receipt_equality(
    exact_lineage_case,
):
    episode, binding, fresh_sensory, lineage, closed_receipt, registry = (
        exact_lineage_case
    )

    assert tuple(sorted(episode.sensory_evidence_receipt_sha256s)) != tuple(
        sorted(value.evidence_receipt_sha256 for value in fresh_sensory)
    )
    assert len(lineage.entries) == 5
    assert all(
        value.archived_raw_record_sha256 == value.fresh_raw_record_sha256
        for value in lineage.entries
    )

    verify_fresh_recall_archive_lineage_authority(
        episode=episode,
        archive_lineage=lineage,
        fresh_closed_experience_receipt_sha256=closed_receipt,
        fresh_sensory_evidence=fresh_sensory,
        source_binding=binding,
        receipt_registry=registry,
    )


def test_provider_archive_lineage_survives_exact_registry_restart(
    exact_lineage_case,
):
    episode, binding, fresh_sensory, lineage, closed_receipt, registry = (
        exact_lineage_case
    )
    restarted = ReceiptRegistry(
        registry.profile_binding_sha256,
        tuple(
            ReceiptRecord(value.digest, bytes(value.payload))
            for value in reversed(registry.records)
        ),
    )

    verify_fresh_recall_archive_lineage_authority(
        episode=episode,
        archive_lineage=lineage,
        fresh_closed_experience_receipt_sha256=closed_receipt,
        fresh_sensory_evidence=fresh_sensory,
        source_binding=binding,
        receipt_registry=restarted,
    )


def test_provider_rejects_omitted_or_substituted_archive_lineage(
    exact_lineage_case,
):
    episode, binding, fresh_sensory, lineage, closed_receipt, registry = (
        exact_lineage_case
    )
    omitted = replace(lineage, entries=lineage.entries[:-1])
    substituted_entry = replace(
        lineage.entries[0],
        fresh_evidence_receipt_sha256=(
            lineage.entries[1].fresh_evidence_receipt_sha256
        ),
    )
    substituted = replace(
        lineage,
        entries=(substituted_entry, *lineage.entries[1:]),
    )

    for changed in (omitted, substituted):
        with pytest.raises(
            ReceiptError,
            match="exact evidence pairings",
        ):
            verify_fresh_recall_archive_lineage_authority(
                episode=episode,
                archive_lineage=changed,
                fresh_closed_experience_receipt_sha256=closed_receipt,
                fresh_sensory_evidence=fresh_sensory,
                source_binding=binding,
                receipt_registry=registry,
            )


def test_archive_lineage_rejects_raw_l0_l4_trace_substitution(
    exact_lineage_case,
):
    episode, binding, fresh_sensory, _, closed_receipt, registry = (
        exact_lineage_case
    )
    changed = replace(
        fresh_sensory[0],
        raw_record=fresh_sensory[1].raw_record,
    )

    with pytest.raises(ReceiptError, match="raw L0-L4 trace"):
        create_fresh_recall_archive_lineage(
            episode=episode,
            source_binding_receipt_sha256=binding.binding_receipt_sha256,
            fresh_closed_experience_receipt_sha256=closed_receipt,
            fresh_sensory_evidence=(changed, *fresh_sensory[1:]),
            receipt_registry=registry,
        )


def test_provider_rejects_missing_lineage_receipt_after_restart(
    exact_lineage_case,
):
    episode, binding, fresh_sensory, lineage, closed_receipt, registry = (
        exact_lineage_case
    )
    restarted_without_lineage = ReceiptRegistry(
        registry.profile_binding_sha256,
        tuple(
            value
            for value in registry.records
            if value.digest != lineage.authority_receipt_sha256
        ),
    )

    with pytest.raises(ReceiptError, match="not mounted"):
        verify_fresh_recall_archive_lineage_authority(
            episode=episode,
            archive_lineage=lineage,
            fresh_closed_experience_receipt_sha256=closed_receipt,
            fresh_sensory_evidence=fresh_sensory,
            source_binding=binding,
            receipt_registry=restarted_without_lineage,
        )
