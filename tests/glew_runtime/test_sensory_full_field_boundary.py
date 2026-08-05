"""Isolated contracts for the lossless six-sense pre-L5 boundary."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.global_uf import (
    DSF_FIELD_ORDER,
    ExactDSFFieldTupleReceipt,
    LayerBranchGateSignature,
    NamedSignZeroClass,
    PortKernelBasinSignature,
    SignZeroClass,
    exact_dsf_field_tuple_receipt_payload,
    port_kernel_basin_receipt_payload,
)
from dsf_ai_service.glew_runtime.model import (
    ReceiptError,
    ReceiptRegistry,
    receipt_sha256,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    NativeSenseTopology,
    NativeSubstreamProfile,
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
    SensoryFullFieldBoundary,
    SensorySubstreamFullField,
    SixSenseFullFieldBoundary,
    native_sense_topology_receipt_payload,
    native_substream_profile_receipt_payload,
    sensory_full_field_boundary_receipt_payload,
    six_sense_full_field_boundary_receipt_payload,
)


def _sign(value: Fraction) -> SignZeroClass:
    if value < 0:
        return SignZeroClass.NEGATIVE
    if value > 0:
        return SignZeroClass.POSITIVE
    return SignZeroClass.EXACT_ZERO


def _layers(
    exact_tuples: tuple[ExactDSFFieldTupleReceipt, ...],
) -> tuple[LayerBranchGateSignature, ...]:
    l4_classes = tuple(
        sorted(
            (
                NamedSignZeroClass(
                    f"{item.tuple_index:08d}:{field_name}",
                    _sign(getattr(item, field_name)),
                )
                for item in exact_tuples
                for field_name in DSF_FIELD_ORDER
            ),
            key=lambda value: value.coordinate_id,
        )
    )
    return tuple(
        LayerBranchGateSignature(
            layer_index,
            f"native-L{layer_index}-branch",
            (f"native-L{layer_index}-gate",),
            l4_classes if layer_index == 4 else (),
        )
        for layer_index in range(5)
    )


@dataclass(frozen=True)
class BoundaryFixture:
    assembly: SixSenseFullFieldBoundary
    registry: ReceiptRegistry
    sound: SensoryFullFieldBoundary


def _fixture() -> BoundaryFixture:
    profile_payload = b"sensory-boundary-test-profile"
    payloads: dict[str, bytes] = {}

    def mount(payload: bytes) -> str:
        digest = receipt_sha256(payload)
        payloads[digest] = payload
        return digest

    causal_digest = mount(b"causal-window-7")
    start = Fraction(11, 2)
    end = Fraction(23, 4)
    sound_profiles: list[NativeSubstreamProfile] = []
    sound_substreams: list[SensorySubstreamFullField] = []

    exact_values = (
        (
            Fraction(1, 2),
            Fraction(-2, 3),
            Fraction(3, 5),
            Fraction(4, 7),
            Fraction(-5, 11),
            Fraction(6, 13),
            Fraction(7, 17),
        ),
        (
            Fraction(-8, 19),
            Fraction(9, 23),
            Fraction(0),
            Fraction(10, 29),
            Fraction(11, 31),
            Fraction(-12, 37),
            Fraction(13, 41),
        ),
    )

    for topology_index, substream_id in enumerate(("left-cochlea", "right-cochlea")):
        derivation_digest = mount(
            f"physical-derivation:{substream_id}".encode("utf-8")
        )
        coordinates = (
            NativeAxisCoordinate("ear", "left" if topology_index == 0 else "right"),
            NativeAxisCoordinate("frequency-bin", "native-all-bins"),
        )
        native_payload = native_substream_profile_receipt_payload(
            sense=PhysicalSense.SOUND,
            sensor_id="cochlear-array",
            substream_id=substream_id,
            topology_index=topology_index,
            coordinates=coordinates,
            physical_quantity="sound-pressure",
            physical_unit="pascal",
            physical_derivation_receipt_sha256=derivation_digest,
        )
        profile = NativeSubstreamProfile(
            PhysicalSense.SOUND,
            "cochlear-array",
            substream_id,
            topology_index,
            coordinates,
            "sound-pressure",
            "pascal",
            derivation_digest,
            mount(native_payload),
        )
        sound_profiles.append(profile)

        trace_digest = mount(f"exact-L0-L4:{substream_id}".encode("utf-8"))
        exact_tuples: list[ExactDSFFieldTupleReceipt] = []
        for tuple_index, values in enumerate(exact_values):
            shifted = tuple(
                value + Fraction(topology_index, 101) for value in values
            )
            exact_payload = exact_dsf_field_tuple_receipt_payload(
                lane_id=PhysicalSense.SOUND.value,
                port_id=substream_id,
                tuple_index=tuple_index,
                D_k=shifted[0],
                M_k=shifted[1],
                R_rev_k=shifted[2],
                U_star_k=shifted[3],
                C_k=shifted[4],
                P_k=shifted[5],
                B_k=shifted[6],
                source_l0_l4_trace_receipt_sha256=trace_digest,
            )
            exact_tuples.append(
                ExactDSFFieldTupleReceipt(
                    PhysicalSense.SOUND.value,
                    substream_id,
                    tuple_index,
                    *shifted,
                    trace_digest,
                    mount(exact_payload),
                )
            )
        tuple_values = tuple(exact_tuples)
        layers = _layers(tuple_values)
        kernel_payload = port_kernel_basin_receipt_payload(
            lane_id=PhysicalSense.SOUND.value,
            port_id=substream_id,
            layers=layers,
            exact_dsf_field_tuples=tuple_values,
        )
        kernel = PortKernelBasinSignature(
            PhysicalSense.SOUND.value,
            substream_id,
            layers,
            tuple_values,
            mount(kernel_payload),
        )
        sound_substreams.append(SensorySubstreamFullField(profile, kernel))

    profiles = tuple(sound_profiles)
    topology_payload = native_sense_topology_receipt_payload(
        topology_id="sound-native-topology",
        sense=PhysicalSense.SOUND,
        profiles=profiles,
    )
    topology = NativeSenseTopology(
        "sound-native-topology",
        PhysicalSense.SOUND,
        profiles,
        mount(topology_payload),
    )

    boundaries: list[SensoryFullFieldBoundary] = []
    sound_boundary: SensoryFullFieldBoundary | None = None
    for sense in SENSE_ORDER:
        state_digest = mount(f"state-evidence:{sense.value}".encode("utf-8"))
        state = (
            SenseBoundaryState.OBSERVED
            if sense is PhysicalSense.SOUND
            else SenseBoundaryState.SENSOR_UNAVAILABLE
            if sense in (PhysicalSense.SMELL, PhysicalSense.TASTE)
            else SenseBoundaryState.UNKNOWN
        )
        sense_topology = topology if sense is PhysicalSense.SOUND else None
        substreams = (
            tuple(sound_substreams) if sense is PhysicalSense.SOUND else ()
        )
        boundary_payload = sensory_full_field_boundary_receipt_payload(
            boundary_id=f"boundary-{sense.value}",
            sense=sense,
            state=state,
            source_time_start=start,
            source_time_end=end,
            causal_window_receipt_sha256=causal_digest,
            state_evidence_receipt_sha256=state_digest,
            topology=sense_topology,
            substreams=substreams,
        )
        boundary = SensoryFullFieldBoundary(
            f"boundary-{sense.value}",
            sense,
            state,
            start,
            end,
            causal_digest,
            state_digest,
            sense_topology,
            substreams,
            mount(boundary_payload),
        )
        boundaries.append(boundary)
        if sense is PhysicalSense.SOUND:
            sound_boundary = boundary

    boundary_tuple = tuple(boundaries)
    assembly_payload = six_sense_full_field_boundary_receipt_payload(
        assembly_id="six-sense-window-7",
        boundaries=boundary_tuple,
    )
    assembly = SixSenseFullFieldBoundary(
        "six-sense-window-7",
        boundary_tuple,
        mount(assembly_payload),
    )
    registry = ReceiptRegistry.from_payloads(
        profile_payload=profile_payload,
        receipt_payloads=tuple(payloads.values()),
    )
    assert sound_boundary is not None
    return BoundaryFixture(assembly, registry, sound_boundary)


def test_complete_six_sense_boundary_verifies_without_field_reduction() -> None:
    fixture = _fixture()

    fixture.assembly.verify(fixture.registry)

    assert tuple(value.sense for value in fixture.assembly.boundaries) == SENSE_ORDER
    assert fixture.sound.topology is not None
    assert tuple(
        value.profile for value in fixture.sound.substreams
    ) == fixture.sound.topology.profiles
    assert tuple(
        item.as_tuple()
        for substream in fixture.sound.substreams
        for item in substream.kernel_basin.exact_dsf_field_tuples
    ) == tuple(
        item.as_tuple()
        for substream in fixture.sound.substreams
        for item in substream.kernel_basin.exact_dsf_field_tuples
    )
    assert all(
        len(item.as_tuple()) == len(DSF_FIELD_ORDER)
        for substream in fixture.sound.substreams
        for item in substream.kernel_basin.exact_dsf_field_tuples
    )

    mounted_payload = fixture.registry.resolve(
        fixture.sound.authority_receipt_sha256
    )
    decoded = json.loads(mounted_payload)
    assert decoded["schema"] == "guala.sensory.full_field_boundary.v2"
    assert decoded["native_topology_receipt_sha256"] == (
        fixture.sound.topology.authority_receipt_sha256
    )
    assert decoded["substreams"][0]["exact_l4_tuple_receipt_sha256s"] == [
        item.authority_receipt_sha256
        for item in fixture.sound.substreams[0].kernel_basin.exact_dsf_field_tuples
    ]
    assert "score" not in decoded
    assert "decision_vector" not in decoded


def test_observed_boundary_rejects_omitted_native_substream() -> None:
    sound = _fixture().sound

    with pytest.raises(
        ReceiptError,
        match="do not exactly cover native topology",
    ):
        replace(sound, substreams=sound.substreams[:1])


def test_exact_l4_field_tamper_is_rejected_by_mounted_receipts() -> None:
    fixture = _fixture()
    sound = fixture.sound
    first_substream = sound.substreams[0]
    old_kernel = first_substream.kernel_basin
    old_tuple = old_kernel.exact_dsf_field_tuples[0]
    changed_tuple = replace(old_tuple, P_k=old_tuple.P_k + Fraction(1, 997))
    changed_tuples = (changed_tuple, *old_kernel.exact_dsf_field_tuples[1:])
    changed_kernel = PortKernelBasinSignature(
        old_kernel.lane_id,
        old_kernel.port_id,
        _layers(changed_tuples),
        changed_tuples,
        old_kernel.authority_receipt_sha256,
    )
    changed_substream = SensorySubstreamFullField(
        first_substream.profile,
        changed_kernel,
    )
    changed_sound = replace(
        sound,
        substreams=(changed_substream, *sound.substreams[1:]),
    )

    with pytest.raises(ReceiptError, match="differs from mounted authority bytes"):
        changed_sound.verify(fixture.registry)


def test_six_sense_assembly_rejects_wrong_order_and_mixed_windows() -> None:
    fixture = _fixture()
    boundaries = fixture.assembly.boundaries

    with pytest.raises(ReceiptError, match="canonical order"):
        SixSenseFullFieldBoundary(
            "wrong-order",
            (boundaries[1], boundaries[0], *boundaries[2:]),
            fixture.assembly.authority_receipt_sha256,
        )

    other_window = receipt_sha256(b"another-valid-digest-shaped-window")
    changed_last = replace(boundaries[-1], causal_window_receipt_sha256=other_window)
    with pytest.raises(ReceiptError, match="do not share one causal window"):
        SixSenseFullFieldBoundary(
            "mixed-window",
            (*boundaries[:-1], changed_last),
            fixture.assembly.authority_receipt_sha256,
        )


def test_absent_or_unknown_sense_cannot_fabricate_observations() -> None:
    sound = _fixture().sound

    with pytest.raises(
        ReceiptError,
        match="unavailable or unknown sense cannot carry observations",
    ):
        replace(sound, state=SenseBoundaryState.UNKNOWN)


def test_topology_receipt_prevents_redeclaring_complete_port_set() -> None:
    fixture = _fixture()
    topology = fixture.sound.topology
    assert topology is not None
    shortened_profiles = topology.profiles[:1]
    shortened_payload = native_sense_topology_receipt_payload(
        topology_id=topology.topology_id,
        sense=topology.sense,
        profiles=shortened_profiles,
    )
    shortened = NativeSenseTopology(
        topology.topology_id,
        topology.sense,
        shortened_profiles,
        receipt_sha256(shortened_payload),
    )

    with pytest.raises(ReceiptError, match="not mounted"):
        shortened.verify(fixture.registry)

