from __future__ import annotations

import json
from dataclasses import replace
from fractions import Fraction

import numpy as np
import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.model import (
    ReceiptError,
    ReceiptRecord,
    ReceiptRegistry,
    receipt_sha256,
)
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    build_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.auditory_kernel_mount import (
    AUDITORY_KERNEL_COMPONENT_COUNT,
    auditory_kernel_component_inputs,
)
from dsf_ai_service.substrate.auditory_l5 import (
    AUDITORY_L5_AUTHORITY_PROFILE,
    AUDITORY_L5_AUTHORITY_SCHEMA,
    AUDITORY_L5_COMPONENT_SCHEMA,
    AUDITORY_L5_PAIR_SCHEMA,
    AUDITORY_L5_SCHEMA,
    MAX_AUDITORY_L5_RECEIPT_RECORDS,
    AuditoryL5CochlearChannel,
    AuditoryL5ComponentKind,
    AuditoryL5KernelComponent,
    AuditoryL5Owner,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    AUDITORY_CHANNELS,
    COCHLEAR_CHANNEL_COUNT,
    OBSERVATION_HOP_SAMPLES,
    MAX_CAPTURE_SECONDS,
    REQUIRED_SAMPLE_RATE_HZ,
    transduce_auditory_full_field,
)


SOURCE_ANCHOR = Fraction(7, 3)


def _inputs():
    sample_count = OBSERVATION_HOP_SAMPLES * 5
    time = np.arange(sample_count, dtype=np.float64) / REQUIRED_SAMPLE_RATE_HZ
    capture = transduce_auditory_full_field(
        0.4 * np.sin(2.0 * np.pi * 440.0 * time),
        sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ,
    )
    return auditory_kernel_component_inputs(
        capture,
        source_anchor=SOURCE_ANCHOR,
    )


def _built(inputs, *, assembly_id: str = "auditory-l5-v3-test"):
    return build_six_sense_full_field(
        assembly_id=assembly_id,
        source_time_start=SOURCE_ANCHOR,
        source_time_end=SOURCE_ANCHOR + 1,
        observed_substreams={PhysicalSense.SOUND: tuple(inputs)},
        states={
            sense: (
                SenseBoundaryState.OBSERVED
                if sense is PhysicalSense.SOUND
                else SenseBoundaryState.SENSOR_UNAVAILABLE
            )
            for sense in SENSE_ORDER
        },
    )


def _owner():
    events = []
    return AuditoryL5Owner(log_event=lambda *args, **kwargs: events.append(
        (args, kwargs)
    )), events


def _assert_rejected_before_mutation(built, message: str) -> None:
    owner, events = _owner()
    before = owner.status()
    with pytest.raises(ReceiptError, match=message):
        owner.settle(built, event_boundary="utterance")
    assert owner.status() == before
    assert owner.latest is None
    assert events == []


def test_v3_groups_canonical_32_mount_as_16_typed_independent_pairs() -> None:
    built = _built(_inputs())
    owner, events = _owner()

    experience = owner.settle(built, event_boundary="utterance")

    assert experience is not None
    experience.verify()
    assert AUDITORY_L5_SCHEMA == "guala.auditory_l5.full_field.v4"
    assert len(experience.channels) == COCHLEAR_CHANNEL_COUNT == 16
    assert not hasattr(experience, "ports")
    assert all(
        isinstance(channel, AuditoryL5CochlearChannel)
        for channel in experience.channels
    )
    assert tuple(channel.channel_id for channel in experience.channels) == tuple(
        definition.name for definition in AUDITORY_CHANNELS
    )
    assert tuple(
        component.topology_index
        for channel in experience.channels
        for component in (channel.pressure, channel.carrier_phase_advance)
    ) == tuple(range(32))

    for channel in experience.channels:
        pressure = channel.pressure
        phase = channel.carrier_phase_advance
        assert isinstance(pressure, AuditoryL5KernelComponent)
        assert isinstance(phase, AuditoryL5KernelComponent)
        assert pressure.kind is AuditoryL5ComponentKind.PRESSURE
        assert phase.kind is AuditoryL5ComponentKind.CARRIER_PHASE_ADVANCE
        assert pressure.samples is not phase.samples
        assert pressure.source_stream_receipt_sha256 != (
            phase.source_stream_receipt_sha256
        )
        assert pressure.kernel_basin_receipt_sha256 != (
            phase.kernel_basin_receipt_sha256
        )
        assert tuple(
            (sample.source_index, sample.source_time, sample.causal_offset)
            for sample in pressure.samples
        ) == tuple(
            (sample.source_index, sample.source_time, sample.causal_offset)
            for sample in phase.samples
        )
        assert all(sample.phase_turns == 0 for sample in pressure.samples)
        assert all(
            Fraction.from_float(float(sample.signal)) == sample.signal
            and Fraction.from_float(float(sample.phase_turns))
            == sample.phase_turns
            for sample in phase.samples
        )
        assert tuple(sample.relevance for sample in pressure.samples) == (
            tuple(sample.signal ** 2 for sample in pressure.samples)
        )
        assert tuple(sample.relevance for sample in phase.samples) == (
            tuple(sample.relevance for sample in pressure.samples)
        )
    assert len(events) == 1
    assert events[0][1]["channel_count"] == 16
    assert events[0][1]["kernel_component_count"] == 32


def test_v3_receipts_bind_both_complete_l4_sequences_and_each_pair() -> None:
    built = _built(_inputs())
    experience = AuditoryL5Owner(
        log_event=lambda *_args, **_kwargs: None
    ).settle(built, event_boundary="ambient")
    assert experience is not None

    assert experience.receipt_registry.profile_binding_sha256 == receipt_sha256(
        AUDITORY_L5_AUTHORITY_PROFILE
    )
    authority = json.loads(experience.receipt_registry.resolve(
        experience.authority_receipt_sha256
    ))
    assert authority["schema"] == AUDITORY_L5_AUTHORITY_SCHEMA
    assert AUDITORY_L5_COMPONENT_SCHEMA.endswith(".v2")
    assert AUDITORY_L5_PAIR_SCHEMA.endswith(".v2")
    assert tuple(
        (value["cochlear_index"], value["channel_id"])
        for value in authority["channels"]
    ) == tuple(
        (channel.cochlear_index, channel.channel_id)
        for channel in experience.channels
    )
    for channel, authority_channel in zip(
        experience.channels, authority["channels"], strict=True
    ):
        assert authority_channel["pair_receipt_sha256"] == (
            channel.pair_receipt_sha256
        )
        assert authority_channel["pressure"][
            "component_receipt_sha256"
        ] == channel.pressure.authority_receipt_sha256
        assert authority_channel["pressure"][
            "l4_field_receipt_sha256s"
        ] == [
            value.authority_receipt_sha256
            for value in channel.pressure.l4_field_tuples
        ]
        assert authority_channel["carrier_phase_advance"][
            "component_receipt_sha256"
        ] == channel.carrier_phase_advance.authority_receipt_sha256
        assert authority_channel["carrier_phase_advance"][
            "l4_field_receipt_sha256s"
        ] == [
            value.authority_receipt_sha256
            for value in channel.carrier_phase_advance.l4_field_tuples
        ]
        pair = json.loads(experience.receipt_registry.resolve(
            channel.pair_receipt_sha256
        ))
        assert pair["schema"] == AUDITORY_L5_PAIR_SCHEMA
        assert pair["pressure_component_receipt_sha256"] == (
            channel.pressure.authority_receipt_sha256
        )
        assert pair["carrier_phase_advance_component_receipt_sha256"] == (
            channel.carrier_phase_advance.authority_receipt_sha256
        )
        for component in (
            channel.pressure,
            channel.carrier_phase_advance,
        ):
            component_payload = json.loads(
                experience.receipt_registry.resolve(
                    component.authority_receipt_sha256
                )
            )
            assert component_payload["schema"] == AUDITORY_L5_COMPONENT_SCHEMA
            assert component.l4_field_tuples
            assert tuple(
                value.tuple_index for value in component.l4_field_tuples
            ) == tuple(range(len(component.l4_field_tuples)))
            assert all(
                tuple(name for name, _field in value.fields) == DSF_FIELD_ORDER
                and value.source_l0_l4_trace_receipt_sha256
                == component.l0_l4_trace_receipt_sha256
                for value in component.l4_field_tuples
            )


def test_v3_later_verify_resolves_every_named_upstream_receipt() -> None:
    built = _built(_inputs(), assembly_id="complete-upstream-chain")
    experience = AuditoryL5Owner(
        log_event=lambda *_args, **_kwargs: None
    ).settle(built, event_boundary="ambient")
    assert experience is not None

    mounted = {
        record.digest
        for record in experience.upstream_receipt_registry.records
    }
    upstream = {record.digest for record in built.receipt_registry.records}
    assert upstream == mounted
    assert experience.upstream_receipt_registry is built.receipt_registry
    experience.verify()

    first = experience.channels[0].pressure
    required = (
        experience.assembly_receipt_sha256,
        first.source_stream_receipt_sha256,
        first.l0_l4_trace_receipt_sha256,
        first.kernel_basin_receipt_sha256,
        first.l4_field_tuples[0].authority_receipt_sha256,
    )
    for digest in required:
        registry = ReceiptRegistry(
            profile_binding_sha256=(
                experience.upstream_receipt_registry.profile_binding_sha256
            ),
            records=tuple(
                record
                for record in experience.upstream_receipt_registry.records
                if record.digest != digest
            ),
        )
        with pytest.raises(ReceiptError, match="not mounted"):
            replace(
                experience,
                upstream_receipt_registry=registry,
            ).verify()


def test_v3_upstream_receipt_tamper_cannot_satisfy_later_verify() -> None:
    experience = AuditoryL5Owner(
        log_event=lambda *_args, **_kwargs: None
    ).settle(
        _built(_inputs(), assembly_id="tampered-upstream-chain"),
        event_boundary="ambient",
    )
    assert experience is not None
    source_digest = (
        experience.channels[0].pressure.source_stream_receipt_sha256
    )
    source_record = next(
        record
        for record in experience.upstream_receipt_registry.records
        if record.digest == source_digest
    )
    tampered_payload = source_record.payload + b" "
    with pytest.raises(ReceiptError, match="does not match"):
        ReceiptRecord(source_digest, tampered_payload)

    tampered_record = ReceiptRecord(
        receipt_sha256(tampered_payload),
        tampered_payload,
    )
    registry = ReceiptRegistry(
        profile_binding_sha256=(
            experience.upstream_receipt_registry.profile_binding_sha256
        ),
        records=tuple(
            tampered_record if record.digest == source_digest else record
            for record in experience.upstream_receipt_registry.records
        ),
    )
    with pytest.raises(ReceiptError, match="not mounted"):
        replace(
            experience,
            upstream_receipt_registry=registry,
        ).verify()


def test_v3_maximum_capture_receipt_registry_remains_bounded() -> None:
    sample_count = REQUIRED_SAMPLE_RATE_HZ * MAX_CAPTURE_SECONDS
    capture = transduce_auditory_full_field(
        np.zeros(sample_count, dtype=np.float64),
        sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ,
    )
    inputs = auditory_kernel_component_inputs(
        capture,
        source_anchor=SOURCE_ANCHOR,
    )
    built = build_six_sense_full_field(
        assembly_id="auditory-l5-maximum-capture",
        source_time_start=SOURCE_ANCHOR,
        source_time_end=SOURCE_ANCHOR + MAX_CAPTURE_SECONDS,
        observed_substreams={PhysicalSense.SOUND: tuple(inputs)},
        states={
            sense: (
                SenseBoundaryState.OBSERVED
                if sense is PhysicalSense.SOUND
                else SenseBoundaryState.SENSOR_UNAVAILABLE
            )
            for sense in SENSE_ORDER
        },
    )
    experience = AuditoryL5Owner(
        log_event=lambda *_args, **_kwargs: None
    ).settle(built, event_boundary="ambient")
    assert experience is not None
    experience.verify()

    expected_l5_records = (
        1
        + AUDITORY_KERNEL_COMPONENT_COUNT
        + COCHLEAR_CHANNEL_COUNT
        + 1
    )
    exact_tuple_records = sum(
        len(substream.kernel_basin.exact_dsf_field_tuples)
        for boundary in built.boundary.boundaries
        for substream in boundary.substreams
    )
    admitted_substreams = sum(
        len(boundary.substreams) for boundary in built.boundary.boundaries
    )
    observed_senses = sum(
        boundary.state is SenseBoundaryState.OBSERVED
        for boundary in built.boundary.boundaries
    )
    adapter_profile_count = len({
        value.kernel_input_map.profile_payload for value in inputs
    })
    expected_upstream_records = (
        1
        + admitted_substreams
        + adapter_profile_count
        + 6 * admitted_substreams
        + exact_tuple_records
        + observed_senses
        + 1
        + 2 * len(SENSE_ORDER)
        + 1
    )
    assert len(experience.receipt_registry.records) == expected_l5_records
    assert (
        len(experience.upstream_receipt_registry.records)
        == expected_upstream_records
    )
    assert experience.upstream_receipt_registry is built.receipt_registry
    assert (
        len(experience.receipt_registry.records)
        + len(experience.upstream_receipt_registry.records)
        <= MAX_AUDITORY_L5_RECEIPT_RECORDS
    )


def test_old_unpaired_16_component_field_fails_before_owner_mutation() -> None:
    old_pressure_only = tuple(
        replace(value, topology_index=index)
        for index, value in enumerate(_inputs()[::2])
    )
    built = _built(old_pressure_only, assembly_id="old-unpaired-v2")

    _assert_rejected_before_mutation(built, "canonical 32-component")


@pytest.mark.parametrize(
    ("alter", "message"),
    (
        (
            lambda values: (
                replace(values[1], topology_index=0),
                replace(values[0], topology_index=1),
                *values[2:],
            ),
            "canonical v4",
        ),
        (
            lambda values: (
                replace(
                    values[0],
                    coordinates=(
                        NativeAxisCoordinate("cochlear-channel", "wrong"),
                        *values[0].coordinates[1:],
                    ),
                ),
                *values[1:],
            ),
            "canonical v4",
        ),
        (
            lambda values: (
                replace(values[0], physical_unit="wrong-unit"),
                *values[1:],
            ),
            "canonical v4",
        ),
        (
            lambda values: (
                replace(
                    values[0],
                    phase_turns=(
                        Fraction.from_float(0.01),
                        *values[0].phase_turns[1:],
                    ),
                ),
                *values[1:],
            ),
            "pressure component phase is not zero",
        ),
        (
            lambda values: (
                values[0],
                replace(
                    values[1],
                    source_relevance=(
                        (
                            Fraction(0)
                            if values[1].source_relevance[0] != 0
                            else Fraction(1)
                        ),
                        *values[1].source_relevance[1:],
                    ),
                ),
                *values[2:],
            ),
            "pair relevance diverged",
        ),
        (
            lambda values: (
                values[0],
                replace(
                    values[1],
                    source_times=tuple(
                        value + Fraction(1, 1_000_000_000)
                        for value in values[1].source_times
                    ),
                ),
                *values[2:],
            ),
            "component grids differ",
        ),
    ),
)
def test_noncanonical_pair_invariants_fail_before_mutation(
    alter, message: str
) -> None:
    built = _built(alter(_inputs()), assembly_id=f"invalid-{message}")
    _assert_rejected_before_mutation(built, message)


def test_incomplete_l4_fails_before_owner_mutation() -> None:
    built = _built(_inputs(), assembly_id="incomplete-l4")
    sound = next(
        boundary
        for boundary in built.boundary.boundaries
        if boundary.sense is PhysicalSense.SOUND
    )
    object.__setattr__(
        sound.substreams[0].kernel_basin,
        "exact_dsf_field_tuples",
        (),
    )

    _assert_rejected_before_mutation(built, "kernel basin")
