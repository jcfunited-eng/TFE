"""Exact exterior-grade Gram receipt conformance.

The fixture in this file is not synthesized to be rank-deficient.  It runs
the real five-sense virtual-story chemistry -> frozen L0-L4 kernel pipeline
(``story_chemistry`` + ``closed_experience``) that production code actually
uses, over a genuinely short common replay grid.  On this architecture that
grid structurally never crosses the L1 gate-segmentation threshold
(``uf_core.layer1.segment_gates``, ``tau_D=0.20``), so every port always
resolves to exactly one gate; with n=1 gates most of the 19 transport
coordinates become forced constants regardless of input, and only
``TVR_V``/``TVR_R`` carry genuine per-lane variation.  The result is a real,
reproducible rank-3-of-5 event -- not a test-fixture artifact.

These tests confirm ``exact_port_gram_exterior_geometry`` reports that exact
structure (rank, and every nonzero principal Gram volume) without changing
``exact_port_gram_geometry``'s or ``evaluate_event_support``'s existing
rank-5-or-fail-closed behavior, and cross-check against a hand-built
genuinely full-rank synthetic case as a sanity control.
"""

from __future__ import annotations

import itertools
from dataclasses import replace
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.closed_experience import (
    ClosedExperienceEvidencePreparation,
    prepare_closed_experience_evidence,
)
from dsf_ai_service.glew_runtime.event_support import (
    EventSupportEvaluationStatus,
    ExactPortGramExteriorReceipt,
    ExteriorPortGramSubsetVolume,
    MemoryEnergyAuthority,
    evaluate_event_support,
    exact_port_gram_exterior_geometry,
    exact_port_gram_exterior_receipt_payload,
    exact_port_gram_geometry,
    memory_energy_authority_receipt_payload,
)
from dsf_ai_service.glew_runtime.experience_origin import (
    ExperienceOriginAuthority,
    ExperienceOriginKind,
    experience_origin_authority_receipt_payload,
)
from dsf_ai_service.glew_runtime.expressions import (
    FieldExpressionStep,
    PrecisionScheduleAuthority,
    create_closed_experience_expression,
    precision_schedule_authority_receipt_payload,
)
from dsf_ai_service.glew_runtime.field import (
    ExactComplex,
    FieldEvolutionAuthority,
    PortFiber,
    PortTransportEvidence,
    canonical_component_partition,
    evolution_authority_receipt_payload,
    source_coefficients_for_injection,
)
from dsf_ai_service.glew_runtime.model import (
    ReceiptError,
    ReceiptRecord,
    ReceiptRegistry,
    receipt_sha256,
)
from dsf_ai_service.glew_runtime.operators import (
    CausalGrid,
    MountedResonanceGraph,
    MountedSupportDomain,
    RequiredEdge,
    ResonanceOperatorAuthority,
    causal_grid_receipt_payload,
    resonance_graph_receipt_payload,
    resonance_operator_receipt_payload,
    support_domain_receipt_payload,
)
from dsf_ai_service.glew_runtime.story_chemistry import (
    StoryChemistryStatus,
    StoryKernelBridgeStatus,
    build_story_frozen_kernel_inputs,
    evolve_story_chemistry_event,
)
from tests.glew_runtime.test_field import (
    evidence as synthetic_evidence,
    exact_state,
    registry,
    topology as make_topology,
)
from tests.glew_runtime.test_story_chemistry import (
    AUDITORY_PORT,
    SMELL_PORT,
    TASTE_PORT,
    TOUCH_PORT,
    VISION_PORT,
    _mount,
    _multisense_event,
)


# ---------------------------------------------------------------------------
# Real rank-3-of-5 fixture: genuine L0-L4 kernel output, not hand-picked.
# ---------------------------------------------------------------------------


def _extend_registry(receipts: ReceiptRegistry, *payloads: bytes) -> ReceiptRegistry:
    records = {record.digest: record.payload for record in receipts.records}
    for payload in payloads:
        records[receipt_sha256(payload)] = payload
    return ReceiptRegistry(
        receipts.profile_binding_sha256,
        tuple(ReceiptRecord(digest, records[digest]) for digest in sorted(records)),
    )


def _prepare_real_five_sense_rank_three():
    """Run the real story-chemistry -> frozen L0-L4 pipeline for five senses.

    Each lane is held at a distinct, genuinely lane-specific flux across two
    frames of a short (2-sample) common replay grid, with a distinct
    per-lane delta between frames (mirroring genuinely distinct sensor
    growth/decay/kappa dynamics per lane).  The grid never crosses the L1
    gate-segmentation threshold, so this closes as exactly one gate per port
    -- the structural condition the audit identified.
    """

    mounted = _mount()
    assert mounted.runtime is not None

    base_flux = dict(
        auditory_flux=Fraction(-3, 11),
        smell_flux=Fraction(7, 13),
        taste_flux=Fraction(-2, 9),
        touch_flux=Fraction(5, 17),
        vision_flux=Fraction(1, 19),
    )
    # Genuinely distinct per-lane deltas, small enough that D(t) stays under
    # the L1 boundary threshold (tau_D = 0.20) so the gate never splits.
    deltas = dict(
        auditory_flux=Fraction(1, 100),
        smell_flux=Fraction(2, 100),
        taste_flux=Fraction(-1, 100),
        touch_flux=Fraction(3, 100),
        vision_flux=Fraction(-2, 100),
    )
    next_flux = {key: base_flux[key] + deltas[key] for key in base_flux}

    first = evolve_story_chemistry_event(
        runtime=mounted.runtime,
        event=_multisense_event(
            event_id="exterior-receipt-frame-1",
            start=Fraction(0),
            end=Fraction(1),
            **base_flux,
        ),
    )
    assert first.status is StoryChemistryStatus.EVOLVED
    second = evolve_story_chemistry_event(
        runtime=first.runtime,
        event=_multisense_event(
            event_id="exterior-receipt-frame-2",
            start=Fraction(1),
            end=Fraction(2),
            **next_flux,
        ),
    )
    assert second.status is StoryChemistryStatus.EVOLVED

    bridge = build_story_frozen_kernel_inputs(
        runtime=second.runtime,
        output_frames=(first.outputs, second.outputs),
        source_epoch="exterior-receipt-epoch",
    )
    assert bridge.status is StoryKernelBridgeStatus.READY

    fibers = (
        PortFiber("sound", AUDITORY_PORT),
        PortFiber("smell", SMELL_PORT),
        PortFiber("taste", TASTE_PORT),
        PortFiber("touch", TOUCH_PORT),
        PortFiber("sight", VISION_PORT),
    )
    topology, topology_payload = make_topology(*fibers)
    timestamps = tuple(sample.timestamp for sample in bridge.streams[0].samples)
    weights = tuple(Fraction(1) for _ in timestamps)
    grid_payload = causal_grid_receipt_payload(
        "exterior-receipt-grid", timestamps, weights
    )
    grid = CausalGrid(
        "exterior-receipt-grid", timestamps, weights, receipt_sha256(grid_payload)
    )
    support_payload = support_domain_receipt_payload(
        "exterior-receipt-support", tuple(stream.key for stream in bridge.streams)
    )
    support = MountedSupportDomain(
        "exterior-receipt-support",
        tuple(stream.key for stream in bridge.streams),
        receipt_sha256(support_payload),
    )
    edges = tuple(
        RequiredEdge(left.key, right.key)
        for left, right in zip(bridge.streams[:-1], bridge.streams[1:], strict=True)
    )
    graph_payload = resonance_graph_receipt_payload(
        "exterior-receipt-resonance-graph", edges
    )
    graph = MountedResonanceGraph(
        "exterior-receipt-resonance-graph", edges, receipt_sha256(graph_payload)
    )
    operator_payload = resonance_operator_receipt_payload(
        "exterior-receipt-resonance", 256
    )
    operator = ResonanceOperatorAuthority(
        "exterior-receipt-resonance", 256, receipt_sha256(operator_payload)
    )
    receipt_registry = _extend_registry(
        bridge.receipt_registry,
        topology_payload,
        grid_payload,
        support_payload,
        graph_payload,
        operator_payload,
    )

    prepared = prepare_closed_experience_evidence(
        streams=bridge.streams,
        kernel_inputs=bridge.kernel_inputs,
        source_time_start=Fraction(0),
        grid=grid,
        support_domain=support,
        resonance_graph=graph,
        resonance_operator=operator,
        topology=topology,
        receipt_registry=receipt_registry,
    )
    assert prepared.events
    assert isinstance(prepared, ClosedExperienceEvidencePreparation)
    return topology, prepared


@pytest.fixture(scope="module")
def real_rank_three_context():
    """(topology, ClosedExperienceEvidencePreparation) for the real fixture."""

    return _prepare_real_five_sense_rank_three()


@pytest.fixture(scope="module")
def real_rank_three_evidence(
    real_rank_three_context,
) -> tuple[PortTransportEvidence, ...]:
    _topology, prepared = real_rank_three_context
    return tuple(sorted(prepared.evidence, key=lambda value: value.key))


def _synthetic_full_rank_evidence() -> tuple[PortTransportEvidence, ...]:
    """Five hand-built, genuinely linearly independent 19-dim port vectors."""

    lanes = ("sight", "smell", "sound", "taste", "touch")
    return tuple(
        synthetic_evidence(lane, "one", tuple(
            Fraction(1) if index == axis else Fraction(0) for index in range(19)
        ))[0]
        for axis, lane in enumerate(lanes)
    )


# ---------------------------------------------------------------------------
# Real rank-3-of-5 conformance
# ---------------------------------------------------------------------------


def test_real_five_sense_short_grid_replay_is_exactly_rank_three(
    real_rank_three_evidence,
):
    receipt = exact_port_gram_exterior_geometry(real_rank_three_evidence)

    assert isinstance(receipt, ExactPortGramExteriorReceipt)
    assert receipt.rank == 3
    assert len(receipt.port_keys) == 5
    assert len(receipt.subsets) == 31  # C(5,1..5)


def test_every_subset_size_matches_the_confirmed_nonzero_pattern(
    real_rank_three_evidence,
):
    receipt = exact_port_gram_exterior_geometry(real_rank_three_evidence)

    by_size: dict[int, list[ExteriorPortGramSubsetVolume]] = {}
    for subset in receipt.subsets:
        by_size.setdefault(len(subset.port_keys), []).append(subset)

    assert sorted(by_size) == [1, 2, 3, 4, 5]
    assert len(by_size[1]) == 5
    assert len(by_size[2]) == 10
    assert len(by_size[3]) == 10
    assert len(by_size[4]) == 5
    assert len(by_size[5]) == 1

    # Every size-1/2/3 principal subset genuinely spans an independent
    # volume; every size-4/5 subset is exactly degenerate.  This is the
    # confirmed structural fact (rank 3 of 5), not a coincidence of this
    # particular fixture's numbers.
    for size in (1, 2, 3):
        assert all(subset.nonzero for subset in by_size[size])
        assert all(subset.exact_normalized_volume > 0 for subset in by_size[size])
    for size in (4, 5):
        assert not any(subset.nonzero for subset in by_size[size])
        assert all(subset.exact_normalized_volume == 0 for subset in by_size[size])


def test_full_set_subset_matches_the_unchanged_existing_geometry(
    real_rank_three_evidence,
):
    """The 5-of-5 subset entry must equal exact_port_gram_geometry's own result."""

    receipt = exact_port_gram_exterior_geometry(real_rank_three_evidence)
    full_key = tuple(value.key for value in real_rank_three_evidence)

    full_subset = receipt.subset(full_key)
    existing_result = exact_port_gram_geometry(real_rank_three_evidence)

    assert existing_result == Fraction(0)
    assert full_subset.nonzero is False
    assert full_subset.exact_normalized_volume == existing_result == Fraction(0)


def test_receipt_payload_is_canonical_and_verifies_against_a_mounted_registry(
    real_rank_three_evidence,
):
    receipt = exact_port_gram_exterior_geometry(real_rank_three_evidence)
    payload = receipt.payload()

    assert receipt_sha256(payload) == receipt.receipt_sha256

    receipts = registry(payload)
    receipt.verify(receipts)  # must not raise

    # A receipt whose digest was never mounted fails closed.
    unmounted = replace(receipt, receipt_sha256="0" * 64)
    with pytest.raises(ReceiptError):
        unmounted.verify(registry())


def test_tampered_rank_is_rejected_before_it_can_be_mounted(real_rank_three_evidence):
    receipt = exact_port_gram_exterior_geometry(real_rank_three_evidence)
    tampered = replace(receipt, rank=5)

    with pytest.raises(ReceiptError, match="largest independent"):
        tampered.payload()


def test_tampered_subset_nonzero_flag_fails_closed(real_rank_three_evidence):
    receipt = exact_port_gram_exterior_geometry(real_rank_three_evidence)
    degenerate_full = receipt.subset(tuple(value.key for value in real_rank_three_evidence))

    with pytest.raises(ReceiptError, match="differs from its exact determinant"):
        replace(degenerate_full, nonzero=True)


def test_subset_lookup_is_order_independent(real_rank_three_evidence):
    receipt = exact_port_gram_exterior_geometry(real_rank_three_evidence)
    keys = tuple(value.key for value in real_rank_three_evidence)

    forward = receipt.subset(keys[:3])
    reversed_lookup = receipt.subset(tuple(reversed(keys[:3])))

    assert forward is reversed_lookup


def test_receipt_covers_every_principal_subset_exactly_once(real_rank_three_evidence):
    receipt = exact_port_gram_exterior_geometry(real_rank_three_evidence)
    keys = tuple(value.key for value in real_rank_three_evidence)

    expected = set()
    for size in range(1, len(keys) + 1):
        expected.update(itertools.combinations(sorted(keys), size))

    actual = {subset.port_keys for subset in receipt.subsets}
    assert actual == expected


_EXTERIOR_TEST_PHYSICAL_PROFILE_AUTHORITY = (
    b"exterior-receipt-physical-profile-authority"
)


def _evolution_authority_for_real_event(topology, event, authority_id: str):
    """Build a FieldEvolutionAuthority for a real (sparse) prepared event.

    Mirrors ``tests/glew_runtime/test_closed_experience_provider.py``'s own
    ``_evolution_authority`` helper: a sparse event's source coefficients
    come from ``source_coefficients_for_injection``, not from a dense
    ``.vector`` (which only ``MapInjection`` has).
    """

    source = source_coefficients_for_injection(
        event.injection, event.source_time_end - event.source_time_start
    )
    components = canonical_component_partition(topology.dimension, ())
    payload = evolution_authority_receipt_payload(
        authority_id=authority_id,
        physical_profile_receipt_sha256=receipt_sha256(
            _EXTERIOR_TEST_PHYSICAL_PROFILE_AUTHORITY
        ),
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        map_injection_receipt_sha256=event.injection.receipt_sha256,
        source_time_start=event.source_time_start,
        source_time_end=event.source_time_end,
        source_time_unit="structural_second",
        hbar=Fraction(1),
        hamiltonian=(),
        local_rates=(),
        source=source,
        component_partition=components,
        max_connected_component_dimension=1,
        precision_bits=256,
    )
    authority = FieldEvolutionAuthority(
        authority_id=authority_id,
        physical_profile_receipt_sha256=receipt_sha256(
            _EXTERIOR_TEST_PHYSICAL_PROFILE_AUTHORITY
        ),
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        map_injection_receipt_sha256=event.injection.receipt_sha256,
        source_time_start=event.source_time_start,
        source_time_end=event.source_time_end,
        source_time_unit="structural_second",
        hbar=Fraction(1),
        hamiltonian=(),
        local_rates=(),
        source=source,
        max_connected_component_dimension=1,
        precision_bits=256,
        authority_receipt_sha256=receipt_sha256(payload),
    )
    return authority, payload


def test_evaluate_event_support_fail_closed_behavior_is_unchanged(
    real_rank_three_context, real_rank_three_evidence
):
    """The production R_event path must still resolve to exact zero geometry.

    This builds the real evaluate_event_support call on the real prepared
    rank-3-of-5 event (same topology, same sparse MapInject, same receipt
    registry ``prepare_closed_experience_evidence`` already verified) and
    confirms it is unaffected by the new receipt: the interval's
    exact_r_geometry is still exactly zero (fail-closed), and the richer
    receipt built independently from the same evidence still reports the
    full rank-3 structure alongside it.
    """

    topology, prepared = real_rank_three_context
    event = prepared.events[-1]

    authority, authority_payload = _evolution_authority_for_real_event(
        topology, event, "real-five-sense-rank-three-field-step"
    )
    initial, initial_payload = exact_state(
        topology,
        event.source_time_start,
        (ExactComplex(Fraction(0)),) * topology.dimension,
    )
    precision_payload = precision_schedule_authority_receipt_payload(
        authority_id="exterior-receipt-precision",
        maximum_precision_bits=4096,
    )
    precision = PrecisionScheduleAuthority(
        "exterior-receipt-precision", 4096, receipt_sha256(precision_payload)
    )
    derivation = b"exterior-receipt-memory-energy-derivation"
    energy_payload = memory_energy_authority_receipt_payload(
        authority_id="exterior-receipt-memory-energy",
        energy_unit_id="exterior-receipt-energy-unit",
        exact_memory_energy=Fraction(1),
        derivation_receipt_sha256=receipt_sha256(derivation),
        physical_profile_receipt_sha256=authority.physical_profile_receipt_sha256,
    )
    energy = MemoryEnergyAuthority(
        "exterior-receipt-memory-energy",
        "exterior-receipt-energy-unit",
        Fraction(1),
        receipt_sha256(derivation),
        authority.physical_profile_receipt_sha256,
        receipt_sha256(energy_payload),
    )
    receipts = _extend_registry(
        prepared.receipt_registry,
        _EXTERIOR_TEST_PHYSICAL_PROFILE_AUTHORITY,
        authority_payload,
        initial_payload,
        precision_payload,
        derivation,
        energy_payload,
    )
    expression = create_closed_experience_expression(
        topology=topology,
        initial_state=initial,
        steps=(FieldExpressionStep(event.injection, authority),),
        precision_authority=precision,
        receipt_registry=receipts,
    )
    receipts = _extend_registry(receipts, expression.receipt_payload)

    experience_receipt = receipt_sha256(b"real-five-sense-rank-three-experience")
    origin_source = b"real-five-sense-rank-three-origin-source"
    origin_payload = experience_origin_authority_receipt_payload(
        origin_id="real-five-sense-rank-three-origin",
        kind=ExperienceOriginKind.FRESH_EXTERNAL,
        profile_binding_sha256=receipts.profile_binding_sha256,
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        closed_experience_receipt_sha256=experience_receipt,
        source_authority_receipt_sha256=receipt_sha256(origin_source),
    )
    origin = ExperienceOriginAuthority(
        "real-five-sense-rank-three-origin",
        ExperienceOriginKind.FRESH_EXTERNAL,
        receipts.profile_binding_sha256,
        topology.authority_receipt_sha256,
        experience_receipt,
        receipt_sha256(origin_source),
        receipt_sha256(origin_payload),
    )
    receipts = _extend_registry(receipts, origin_source, origin_payload)

    result = evaluate_event_support(
        authority_id="real-five-sense-rank-three-R-event",
        origin=origin,
        topology=topology,
        closed_experience_receipt_sha256=experience_receipt,
        expression=expression,
        memory_energy=energy,
        receipt_registry=receipts,
    )

    assert result.status is EventSupportEvaluationStatus.RESOLVED
    assert result.intervals[0].exact_r_geometry == Fraction(0)
    assert result.exact_r_event == Fraction(0)

    # The additive receipt, built independently from the identical evidence,
    # still reports the full rank-3 exterior structure.
    receipt = exact_port_gram_exterior_geometry(real_rank_three_evidence)
    assert receipt.rank == 3


# ---------------------------------------------------------------------------
# Synthetic full-rank sanity control (not the real fixture)
# ---------------------------------------------------------------------------


def test_synthetic_full_rank_five_vectors_report_rank_five_and_every_subset_nonzero():
    evidence = _synthetic_full_rank_evidence()
    receipt = exact_port_gram_exterior_geometry(evidence)

    assert exact_port_gram_geometry(evidence) == Fraction(1)
    assert receipt.rank == 5
    assert len(receipt.subsets) == 31
    assert all(subset.nonzero for subset in receipt.subsets)
    # Orthonormal one-hot vectors: every principal minor is the identity
    # submatrix, so every normalized volume is exactly 1.
    assert all(subset.exact_normalized_volume == 1 for subset in receipt.subsets)

    full_key = tuple(value.key for value in evidence)
    assert receipt.subset(full_key).exact_normalized_volume == Fraction(1)


def test_exact_port_gram_exterior_receipt_payload_rejects_incomplete_subset_coverage(
    real_rank_three_evidence,
):
    receipt = exact_port_gram_exterior_geometry(real_rank_three_evidence)

    with pytest.raises(ReceiptError, match="every principal port subset"):
        exact_port_gram_exterior_receipt_payload(
            port_keys=receipt.port_keys,
            rank=receipt.rank,
            subsets=receipt.subsets[:-1],
        )
