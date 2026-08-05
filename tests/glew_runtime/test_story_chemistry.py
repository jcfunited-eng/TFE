from __future__ import annotations

import json
from dataclasses import replace
from fractions import Fraction
from pathlib import Path

from dsf_ai_service.glew_runtime.certified_backend import CertifiedBall
from dsf_ai_service.glew_runtime.chemical_receiver import (
    CertifiedChemicalRelevance,
    chemical_backend_authority_receipt_payload,
    certified_chemical_relevance_receipt_payload,
)
from dsf_ai_service.glew_runtime.closed_experience import (
    ClosedExperienceEvidencePreparation,
    prepare_closed_experience_evidence,
)
from dsf_ai_service.glew_runtime.field import PortFiber
from dsf_ai_service.glew_runtime.model import (
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
    Binary64RoundingStatus,
    StoryChemistryStatus,
    StoryKernelBridgeStatus,
    StoryPhysicalBoundaryEvent,
    StoryPhysicalBoundaryObservation,
    authenticated_story_envelope_payload,
    build_story_frozen_kernel_inputs,
    certify_unique_binary64_relevance,
    evolve_story_chemistry_event,
    mount_story_chemistry,
    restore_story_chemistry,
    story_boundary_observation_receipt_payload,
    story_chemistry_checkpoint_payload,
)
from tests.glew_runtime.test_field import topology as make_topology


FIXTURE = (
    Path(__file__).parent / "fixtures" / "candidate_story_chemistry_manifest.json"
)
CANDIDATE_KEY = b"transparent candidate test key; never production authority"
CANDIDATE_KEY_ID = "candidate-test-hmac-key-not-production"
AUDITORY_PORT = "story-auditory.native-port-0"
AUDITORY_UNIT = "virtual-normalized-acoustic-boundary-flux"
SMELL_PORT = "story-smell.native-port-0"
SMELL_UNIT = "virtual-normalized-olfactory-boundary-flux"
TASTE_PORT = "story-taste.native-port-0"
TASTE_UNIT = "virtual-normalized-gustatory-boundary-flux"
TOUCH_PORT = "story-touch.native-port-0"
TOUCH_UNIT = "virtual-normalized-tactile-boundary-flux"
VISION_PORT = "story-vision.native-port-0"
VISION_UNIT = "virtual-normalized-optical-boundary-flux"


def _mount(payload: bytes | None = None):
    return mount_story_chemistry(
        manifest_envelope_payload=FIXTURE.read_bytes() if payload is None else payload,
        trusted_authentication_key=CANDIDATE_KEY,
        expected_key_id=CANDIDATE_KEY_ID,
    )


def _observation(
    *,
    event_id: str,
    observation_id: str,
    port_id: str,
    unit: str,
    start: Fraction,
    end: Fraction,
    flux: Fraction,
) -> StoryPhysicalBoundaryObservation:
    provenance = json.dumps(
        {
            "boundary": observation_id,
            "explanation": "explicit physical candidate fixture observation",
            "schema": "glew.story_chemistry.test_provenance.v1",
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    payload = story_boundary_observation_receipt_payload(
        event_id=event_id,
        observation_id=observation_id,
        port_id=port_id,
        source_time_start=start,
        source_time_end=end,
        signed_native_flux=flux,
        native_flux_unit=unit,
        provenance_receipt_sha256=receipt_sha256(provenance),
    )
    return StoryPhysicalBoundaryObservation(
        event_id=event_id,
        observation_id=observation_id,
        port_id=port_id,
        source_time_start=start,
        source_time_end=end,
        signed_native_flux=flux,
        native_flux_unit=unit,
        provenance_receipt_sha256=receipt_sha256(provenance),
        provenance_receipt_payload=provenance,
        observation_receipt_sha256=receipt_sha256(payload),
        observation_receipt_payload=payload,
    )


def _single_event(
    *, event_id: str, start: Fraction, end: Fraction, flux: Fraction
) -> StoryPhysicalBoundaryEvent:
    return StoryPhysicalBoundaryEvent(
        event_id=event_id,
        observations=(
            _observation(
                event_id=event_id,
                observation_id=f"{event_id}:auditory-boundary",
                port_id=AUDITORY_PORT,
                unit=AUDITORY_UNIT,
                start=start,
                end=end,
                flux=flux,
            ),
        ),
    )


def _multisense_event(
    *,
    event_id: str,
    start: Fraction,
    end: Fraction,
    auditory_flux: Fraction,
    smell_flux: Fraction,
    taste_flux: Fraction,
    touch_flux: Fraction,
    vision_flux: Fraction,
) -> StoryPhysicalBoundaryEvent:
    return StoryPhysicalBoundaryEvent(
        event_id=event_id,
        observations=(
            _observation(
                event_id=event_id,
                observation_id=f"{event_id}:auditory-boundary",
                port_id=AUDITORY_PORT,
                unit=AUDITORY_UNIT,
                start=start,
                end=end,
                flux=auditory_flux,
            ),
            _observation(
                event_id=event_id,
                observation_id=f"{event_id}:smell-boundary",
                port_id=SMELL_PORT,
                unit=SMELL_UNIT,
                start=start,
                end=end,
                flux=smell_flux,
            ),
            _observation(
                event_id=event_id,
                observation_id=f"{event_id}:taste-boundary",
                port_id=TASTE_PORT,
                unit=TASTE_UNIT,
                start=start,
                end=end,
                flux=taste_flux,
            ),
            _observation(
                event_id=event_id,
                observation_id=f"{event_id}:touch-boundary",
                port_id=TOUCH_PORT,
                unit=TOUCH_UNIT,
                start=start,
                end=end,
                flux=touch_flux,
            ),
            _observation(
                event_id=event_id,
                observation_id=f"{event_id}:vision-boundary",
                port_id=VISION_PORT,
                unit=VISION_UNIT,
                start=start,
                end=end,
                flux=vision_flux,
            ),
        ),
    )


def _extend_registry(
    registry: ReceiptRegistry,
    payloads: tuple[bytes, ...],
) -> ReceiptRegistry:
    records = {record.digest: record.payload for record in registry.records}
    for payload in payloads:
        records[receipt_sha256(payload)] = payload
    return ReceiptRegistry(
        registry.profile_binding_sha256,
        tuple(
            ReceiptRecord(digest, records[digest]) for digest in sorted(records)
        ),
    )


def test_transparent_fixture_is_authenticated_and_explicitly_not_production_authority():
    mounted = _mount()

    assert mounted.status is StoryChemistryStatus.MOUNTED
    assert mounted.runtime is not None
    manifest = mounted.runtime.manifest
    assert manifest.authority_scope == "candidate_test_only_not_production_authority"
    assert [backend.working_precision_bits for backend in manifest.backends] == [128, 256]
    auditory = manifest.port(AUDITORY_PORT)
    vision = manifest.port(VISION_PORT)
    assert tuple(port.port_id for port in manifest.ports) == (
        AUDITORY_PORT,
        SMELL_PORT,
        TASTE_PORT,
        TOUCH_PORT,
        VISION_PORT,
    )
    assert len(
        {
            port.activation_susceptibility.authority_receipt_sha256
            for port in manifest.ports
        }
    ) == 5
    assert auditory.time_unit.seconds_per_unit == Fraction(1)
    assert vision.time_unit.seconds_per_unit == Fraction(1)
    assert (
        auditory.activation_susceptibility
        .susceptibility_per_native_signal_unit_per_time_unit
        == Fraction(1)
    )
    assert [rate.rate_per_time_unit for rate in auditory.rates] == [
        Fraction(1),
        Fraction(0),
        Fraction(1),
    ]


def test_manifest_authentication_and_every_declared_receipt_fail_closed():
    envelope = json.loads(FIXTURE.read_text(encoding="utf-8"))
    envelope["body"]["ports"][0]["activation_susceptibility"][
        "susceptibility_per_native_signal_unit_per_time_unit"
    ] = "2/1"
    tampered = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()

    unauthenticated = _mount(tampered)
    resigned_with_stale_rate_receipt = _mount(
        authenticated_story_envelope_payload(
            body=envelope["body"],
            authentication_key=CANDIDATE_KEY,
            key_id=CANDIDATE_KEY_ID,
        )
    )

    assert unauthenticated.status is StoryChemistryStatus.UNKNOWN
    assert unauthenticated.runtime is None
    assert "authentication failed" in unauthenticated.reason
    assert resigned_with_stale_rate_receipt.status is StoryChemistryStatus.UNKNOWN
    assert resigned_with_stale_rate_receipt.runtime is None
    assert "differs from the signed manifest" in resigned_with_stale_rate_receipt.reason


def test_multisense_event_preserves_each_port_and_keeps_flux_separate_from_relevance():
    mounted = _mount()
    assert mounted.runtime is not None
    event = StoryPhysicalBoundaryEvent(
        event_id="candidate-event-1",
        observations=(
            _observation(
                event_id="candidate-event-1",
                observation_id="candidate-event-1:auditory-boundary",
                port_id=AUDITORY_PORT,
                unit=AUDITORY_UNIT,
                start=Fraction(0),
                end=Fraction(1),
                flux=Fraction(-2, 5),
            ),
            _observation(
                event_id="candidate-event-1",
                observation_id="candidate-event-1:vision-boundary",
                port_id=VISION_PORT,
                unit=VISION_UNIT,
                start=Fraction(0),
                end=Fraction(1),
                flux=Fraction(3, 7),
            ),
        ),
    )

    evolved = evolve_story_chemistry_event(runtime=mounted.runtime, event=event)

    assert evolved.status is StoryChemistryStatus.EVOLVED
    assert evolved.runtime is not mounted.runtime
    assert [output.port_id for output in evolved.outputs] == [AUDITORY_PORT, VISION_PORT]
    assert [output.signed_native_flux for output in evolved.outputs] == [
        Fraction(-2, 5),
        Fraction(3, 7),
    ]
    for output in evolved.outputs:
        rounding = output.kernel_binary64_relevance
        assert rounding.status is Binary64RoundingStatus.CERTIFIED
        assert rounding.exact_binary64 == Fraction.from_float(rounding.binary64_value)
        assert rounding.complete_enclosure is output.relevance.value
        assert output.relevance.state_receipt_sha256 == output.state.receipt_sha256
        assert output.relevance.active_mass is output.state.active_mass
        assert output.state.total_receptor_mass == Fraction(1)


def test_unobserved_port_is_not_resampled_or_filled_with_zero_evidence():
    mounted = _mount()
    assert mounted.runtime is not None
    retained_vision = mounted.runtime.state(VISION_PORT)

    evolved = evolve_story_chemistry_event(
        runtime=mounted.runtime,
        event=_single_event(
            event_id="auditory-only-event",
            start=Fraction(0),
            end=Fraction(1),
            flux=Fraction(1, 4),
        ),
    )

    assert evolved.status is StoryChemistryStatus.EVOLVED
    assert [output.port_id for output in evolved.outputs] == [AUDITORY_PORT]
    assert evolved.runtime.state(VISION_PORT) is retained_vision


def test_tampered_second_port_makes_whole_event_unknown_without_mutation():
    mounted = _mount()
    assert mounted.runtime is not None
    auditory = _observation(
        event_id="atomic-event",
        observation_id="atomic-event:auditory",
        port_id=AUDITORY_PORT,
        unit=AUDITORY_UNIT,
        start=Fraction(0),
        end=Fraction(1),
        flux=Fraction(1, 5),
    )
    vision = _observation(
        event_id="atomic-event",
        observation_id="atomic-event:vision",
        port_id=VISION_PORT,
        unit=VISION_UNIT,
        start=Fraction(0),
        end=Fraction(1),
        flux=Fraction(2, 5),
    )
    tampered_vision = replace(vision, signed_native_flux=Fraction(3, 5))

    result = evolve_story_chemistry_event(
        runtime=mounted.runtime,
        event=StoryPhysicalBoundaryEvent(
            event_id="atomic-event",
            observations=(auditory, tampered_vision),
        ),
    )

    assert result.status is StoryChemistryStatus.UNKNOWN
    assert result.runtime is mounted.runtime
    assert result.outputs == ()
    assert mounted.runtime.state(AUDITORY_PORT).source_time == 0
    assert "tampered" in result.reason


def test_signed_precision_sequence_escalates_instead_of_selecting_a_midpoint():
    envelope = json.loads(FIXTURE.read_text(encoding="utf-8"))
    body = envelope["body"]
    authority_id = "candidate-story-arb-2"
    backend_payload = chemical_backend_authority_receipt_payload(
        authority_id=authority_id,
        working_precision_bits=2,
    )
    body["backends"].insert(
        0,
        {
            "authority_id": authority_id,
            "authority_receipt_sha256": receipt_sha256(backend_payload),
            "working_precision_bits": 2,
        },
    )
    signed = authenticated_story_envelope_payload(
        body=body,
        authentication_key=CANDIDATE_KEY,
        key_id=CANDIDATE_KEY_ID,
    )
    mounted = _mount(signed)
    assert mounted.runtime is not None

    result = evolve_story_chemistry_event(
        runtime=mounted.runtime,
        event=_single_event(
            event_id="precision-escalation-event",
            start=Fraction(0),
            end=Fraction(1),
            flux=Fraction(1, 3),
        ),
    )

    assert result.status is StoryChemistryStatus.EVOLVED
    assert result.outputs[0].backend_authority_receipt_sha256 == (
        mounted.runtime.manifest.backends[1].authority_receipt_sha256
    )
    assert result.outputs[0].backend_authority_receipt_sha256 != (
        mounted.runtime.manifest.backends[0].authority_receipt_sha256
    )


def test_binary64_boundary_rejects_enclosure_that_straddles_rounding_cells():
    midpoint = (2**53 + 1) * Fraction(2) ** -54
    upper = midpoint + Fraction(2) ** -60
    ball = CertifiedBall(
        lower_mantissa=midpoint.numerator,
        lower_exponent=-(midpoint.denominator.bit_length() - 1),
        upper_mantissa=upper.numerator,
        upper_exponent=-(upper.denominator.bit_length() - 1),
        working_precision_bits=128,
    )
    state_payload = b'{"schema":"glew.story_chemistry.test_state.v1"}'
    preliminary = CertifiedChemicalRelevance(
        port_id=AUDITORY_PORT,
        state_receipt_sha256=receipt_sha256(state_payload),
        active_mass=ball,
        total_receptor_mass=Fraction(1),
        value=ball,
        receipt_sha256="0" * 64,
        receipt_payload=b"placeholder",
    )
    relevance_payload = certified_chemical_relevance_receipt_payload(
        port_id=preliminary.port_id,
        state_receipt_sha256=preliminary.state_receipt_sha256,
        active_mass=preliminary.active_mass,
        total_receptor_mass=preliminary.total_receptor_mass,
        relevance=preliminary.value,
    )
    relevance = replace(
        preliminary,
        receipt_sha256=receipt_sha256(relevance_payload),
        receipt_payload=relevance_payload,
    )
    profile = b'{"schema":"glew.story_chemistry.rounding_test_profile.v1"}'
    registry = ReceiptRegistry.from_payloads(
        profile_payload=profile,
        receipt_payloads=(state_payload, relevance_payload),
    )

    result = certify_unique_binary64_relevance(
        relevance=relevance,
        receipt_registry=registry,
    )

    assert result.status is Binary64RoundingStatus.UNKNOWN
    assert result.binary64_value is None
    assert result.exact_binary64 is None
    assert result.complete_enclosure == ball
    assert "does not prove one binary64" in result.reason


def test_authenticated_checkpoint_restores_and_continues_bit_exactly():
    mounted = _mount()
    assert mounted.runtime is not None
    first = evolve_story_chemistry_event(
        runtime=mounted.runtime,
        event=_single_event(
            event_id="restart-event-1",
            start=Fraction(0),
            end=Fraction(1),
            flux=Fraction(-1, 3),
        ),
    )
    assert first.status is StoryChemistryStatus.EVOLVED
    checkpoint = story_chemistry_checkpoint_payload(
        runtime=first.runtime,
        checkpoint_id="candidate-checkpoint-after-event-1",
        authentication_key=CANDIDATE_KEY,
        key_id=CANDIDATE_KEY_ID,
    )

    restored = restore_story_chemistry(
        manifest_envelope_payload=FIXTURE.read_bytes(),
        manifest_authentication_key=CANDIDATE_KEY,
        manifest_expected_key_id=CANDIDATE_KEY_ID,
        checkpoint_envelope_payload=checkpoint,
        checkpoint_authentication_key=CANDIDATE_KEY,
        checkpoint_expected_key_id=CANDIDATE_KEY_ID,
    )

    assert restored.status is StoryChemistryStatus.MOUNTED
    assert restored.runtime is not None
    assert restored.runtime.states == first.runtime.states
    assert {
        record.digest: record.payload for record in restored.runtime.receipt_registry.records
    } == {
        record.digest: record.payload for record in first.runtime.receipt_registry.records
    }
    second_event = _single_event(
        event_id="restart-event-2",
        start=Fraction(1),
        end=Fraction(2),
        flux=Fraction(2, 7),
    )
    uninterrupted = evolve_story_chemistry_event(
        runtime=first.runtime,
        event=second_event,
    )
    after_restart = evolve_story_chemistry_event(
        runtime=restored.runtime,
        event=second_event,
    )
    assert uninterrupted.status is StoryChemistryStatus.EVOLVED
    assert after_restart.status is StoryChemistryStatus.EVOLVED
    assert after_restart.runtime.states == uninterrupted.runtime.states
    assert after_restart.outputs == uninterrupted.outputs


def test_authenticated_checkpoint_with_missing_state_receipt_is_refused():
    mounted = _mount()
    assert mounted.runtime is not None
    first = evolve_story_chemistry_event(
        runtime=mounted.runtime,
        event=_single_event(
            event_id="missing-state-event",
            start=Fraction(0),
            end=Fraction(1),
            flux=Fraction(1, 6),
        ),
    )
    checkpoint = story_chemistry_checkpoint_payload(
        runtime=first.runtime,
        checkpoint_id="candidate-checkpoint-to-tamper",
        authentication_key=CANDIDATE_KEY,
        key_id=CANDIDATE_KEY_ID,
    )
    envelope = json.loads(checkpoint)
    state_digest = envelope["body"]["states"][0]["receipt_sha256"]
    envelope["body"]["receipt_records"] = [
        record
        for record in envelope["body"]["receipt_records"]
        if record["sha256"] != state_digest
    ]
    resigned = authenticated_story_envelope_payload(
        body=envelope["body"],
        authentication_key=CANDIDATE_KEY,
        key_id=CANDIDATE_KEY_ID,
    )

    restored = restore_story_chemistry(
        manifest_envelope_payload=FIXTURE.read_bytes(),
        manifest_authentication_key=CANDIDATE_KEY,
        manifest_expected_key_id=CANDIDATE_KEY_ID,
        checkpoint_envelope_payload=resigned,
        checkpoint_authentication_key=CANDIDATE_KEY,
        checkpoint_expected_key_id=CANDIDATE_KEY_ID,
    )

    assert restored.status is StoryChemistryStatus.UNKNOWN
    assert restored.runtime is None
    assert "not mounted" in restored.reason


def test_five_real_sensory_story_frames_enter_frozen_l0_l4_without_flattening():
    mounted = _mount()
    assert mounted.runtime is not None
    first = evolve_story_chemistry_event(
        runtime=mounted.runtime,
        event=_multisense_event(
            event_id="frozen-kernel-story-frame-1",
            start=Fraction(0),
            end=Fraction(1),
            auditory_flux=Fraction(-1, 2),
            smell_flux=Fraction(1, 5),
            taste_flux=Fraction(-1, 6),
            touch_flux=Fraction(2, 5),
            vision_flux=Fraction(1, 3),
        ),
    )
    assert first.status is StoryChemistryStatus.EVOLVED
    second = evolve_story_chemistry_event(
        runtime=first.runtime,
        event=_multisense_event(
            event_id="frozen-kernel-story-frame-2",
            start=Fraction(1),
            end=Fraction(2),
            auditory_flux=Fraction(-1, 2),
            smell_flux=Fraction(1, 5),
            taste_flux=Fraction(-1, 6),
            touch_flux=Fraction(2, 5),
            vision_flux=Fraction(1, 3),
        ),
    )
    assert second.status is StoryChemistryStatus.EVOLVED

    bridge = build_story_frozen_kernel_inputs(
        runtime=second.runtime,
        output_frames=(first.outputs, second.outputs),
        source_epoch="nondimensional-story-experience-1",
    )
    assert bridge.status is StoryKernelBridgeStatus.READY
    assert tuple(stream.lane_id for stream in bridge.streams) == (
        "sound",
        "smell",
        "taste",
        "touch",
        "sight",
    )
    assert tuple(sample.signal for sample in bridge.streams[0].samples) == (
        Fraction(-1, 2),
        Fraction(-1, 2),
    )
    assert tuple(
        sample.l0_relevance for sample in bridge.kernel_inputs[0].samples
    ) == tuple(sample.relevance for sample in bridge.streams[0].samples)
    assert tuple(
        sample.dimensionless_field for sample in bridge.kernel_inputs[0].samples
    ) == (Fraction(3, 4), Fraction(3, 4))

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
        "story-frozen-kernel-grid",
        timestamps,
        weights,
    )
    grid = CausalGrid(
        "story-frozen-kernel-grid",
        timestamps,
        weights,
        receipt_sha256(grid_payload),
    )
    support_payload = support_domain_receipt_payload(
        "story-frozen-kernel-support",
        tuple(stream.key for stream in bridge.streams),
    )
    support = MountedSupportDomain(
        "story-frozen-kernel-support",
        tuple(stream.key for stream in bridge.streams),
        receipt_sha256(support_payload),
    )
    edges = tuple(
        RequiredEdge(left.key, right.key)
        for left, right in zip(
            bridge.streams[:-1],
            bridge.streams[1:],
            strict=True,
        )
    )
    graph_payload = resonance_graph_receipt_payload(
        "story-frozen-kernel-resonance-graph",
        edges,
    )
    graph = MountedResonanceGraph(
        "story-frozen-kernel-resonance-graph",
        edges,
        receipt_sha256(graph_payload),
    )
    operator_payload = resonance_operator_receipt_payload(
        "story-frozen-kernel-resonance",
        256,
    )
    operator = ResonanceOperatorAuthority(
        "story-frozen-kernel-resonance",
        256,
        receipt_sha256(operator_payload),
    )
    receipt_registry = _extend_registry(
        bridge.receipt_registry,
        (
            topology_payload,
            grid_payload,
            support_payload,
            graph_payload,
            operator_payload,
        ),
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

    assert isinstance(prepared, ClosedExperienceEvidencePreparation)
    assert prepared.events
    assert tuple(
        (evidence.lane_id, evidence.port_id)
        for evidence in prepared.events[-1].evidence
    ) == (
        ("sound", AUDITORY_PORT),
        ("smell", SMELL_PORT),
        ("taste", TASTE_PORT),
        ("touch", TOUCH_PORT),
        ("sight", VISION_PORT),
    )
