from dataclasses import replace
from fractions import Fraction as F

import pytest

from dsf_ai_service.glew_runtime import (
    NativePortCalibration,
    NativePortSample,
    NativePortState,
    NativeSampleBatch,
    PortKind,
    ReceiptError,
    ReceiptRegistry,
    Sense,
    couple_mounted_sense,
    couple_native_port,
    native_port_calibration_receipt_payload,
    receipt_sha256,
)


PROFILE = b"glew-profile-fixture-v1"
PHYSICAL = b"touch-native-physical-profile-fixture-v1"
RELEVANCE = b"touch-native-relevance-fixture-v1"
GENESIS = b"touch-genesis-fixture-v1"
DIGEST_PHYSICAL = receipt_sha256(PHYSICAL)
DIGEST_B = receipt_sha256(RELEVANCE)
DIGEST_C = receipt_sha256(GENESIS)


def registry(*payloads: bytes) -> ReceiptRegistry:
    return ReceiptRegistry.from_payloads(
        profile_payload=PROFILE,
        receipt_payloads=(PHYSICAL, RELEVANCE, GENESIS, *payloads),
    )


def calibration(port_id: str, kind: PortKind) -> NativePortCalibration:
    values = dict(
        sense=Sense.TOUCH,
        transducer_id="touch-array-1",
        port_id=port_id,
        port_kind=kind,
        physical_unit="native_current",
        raw_scale=F(1, 10),
        raw_offset=F(-1, 2),
        phase_kappa=F(3, 2),
        calibration_id=f"cal-{port_id}",
        physical_profile_receipt_sha256=DIGEST_PHYSICAL,
        relevance_operator_id=f"native-{port_id}-operator-v1",
        relevance_receipt_sha256=DIGEST_B,
    )
    payload = native_port_calibration_receipt_payload(**values)
    return NativePortCalibration(
        **values,
        calibration_receipt_sha256=receipt_sha256(payload),
    )


def state(cal: NativePortCalibration) -> NativePortState:
    return NativePortState(
        calibration_id=cal.calibration_id,
        source_epoch="epoch-1",
        last_sample_index=-1,
        last_timestamp=F(0),
        phase_turns=F(1, 7),
        genesis_receipt_sha256=DIGEST_C,
    )


def samples(raw_codes=(5, 7), relevances=(F(1, 3), F(2, 3))):
    return tuple(
        NativePortSample(
            source_epoch="epoch-1",
            sample_index=index,
            timestamp=F(index + 1),
            raw_code=raw,
            native_relevance=relevance,
        )
        for index, (raw, relevance) in enumerate(zip(raw_codes, relevances, strict=True))
    )


def batch(cal: NativePortCalibration, values=None, batch_id="batch-1"):
    value_tuple = tuple(samples() if values is None else values)
    return NativeSampleBatch.from_samples(
        batch_id=batch_id,
        calibration_id=cal.calibration_id,
        port_id=cal.port_id,
        samples=value_tuple,
    )


def test_exact_calibration_and_phase_are_rational_and_persistent():
    cal = calibration("dynamic-neurite", PortKind.PHASIC)
    sample_batch, batch_payload = batch(cal)

    result = couple_native_port(
        cal,
        sample_batch,
        state(cal),
        registry(cal.canonical_receipt_payload(), batch_payload),
    )

    assert result.failure is None
    assert result.evidence is not None
    assert tuple(sample.signal for sample in result.evidence.samples) == (F(0), F(1, 5))
    assert tuple(sample.relevance for sample in result.evidence.samples) == (F(1, 3), F(2, 3))
    assert result.evidence.samples[0].phase_turns == F(1, 7)
    assert result.evidence.samples[1].phase_turns == F(1, 7) + F(3, 10)
    assert result.state.phase_turns == result.evidence.samples[-1].phase_turns


def test_multiple_native_ports_remain_independent_and_in_declared_order():
    dynamic = calibration("dynamic-neurite", PortKind.PHASIC)
    static = calibration("static-merkel", PortKind.TONIC)
    dynamic_batch, dynamic_payload = batch(
        dynamic,
        samples((5, 7), (F(1, 4), F(1, 2))),
        "dynamic-batch",
    )
    static_batch, static_payload = batch(
        static,
        samples((6, 6), (F(3, 4), F(3, 4))),
        "static-batch",
    )

    results = couple_mounted_sense(
        (dynamic, static),
        {
            "dynamic-neurite": dynamic_batch,
            "static-merkel": static_batch,
        },
        {"dynamic-neurite": state(dynamic), "static-merkel": state(static)},
        registry(
            dynamic.canonical_receipt_payload(),
            static.canonical_receipt_payload(),
            dynamic_payload,
            static_payload,
        ),
    )

    assert tuple(result.evidence.port_id for result in results if result.evidence) == (
        "dynamic-neurite",
        "static-merkel",
    )
    assert results[0].evidence is not None and results[1].evidence is not None
    assert results[0].evidence.samples != results[1].evidence.samples
    assert results[0].evidence.port_kind == "phasic"
    assert results[1].evidence.port_kind == "tonic"


def test_mounted_sense_rejects_missing_or_undeclared_ports():
    dynamic = calibration("dynamic-neurite", PortKind.PHASIC)
    static = calibration("static-merkel", PortKind.TONIC)
    dynamic_batch, dynamic_payload = batch(dynamic)

    with pytest.raises(ReceiptError, match="exactly match"):
        couple_mounted_sense(
            (dynamic, static),
            {"dynamic-neurite": dynamic_batch},
            {"dynamic-neurite": state(dynamic), "static-merkel": state(static)},
            registry(
                dynamic.canonical_receipt_payload(),
                static.canonical_receipt_payload(),
                dynamic_payload,
            ),
        )


def test_invalid_sample_advances_orderable_source_time_without_phase_and_latches():
    cal = calibration("dynamic-neurite", PortKind.PHASIC)
    initial = state(cal)
    bad = NativePortSample(
        source_epoch="epoch-1",
        sample_index=0,
        timestamp=F(5),
        raw_code=5,
        native_relevance=F(0),
        valid=False,
        fault="sensor_crc",
    )
    sample_batch, batch_payload = batch(cal, (bad,), "bad-batch")

    result = couple_native_port(
        cal,
        sample_batch,
        initial,
        registry(cal.canonical_receipt_payload(), batch_payload),
    )

    assert result.evidence is None
    assert result.failure is not None
    assert result.failure.reason == "invalid_sample:sensor_crc"
    assert result.state.last_timestamp == F(5)
    assert result.state.last_sample_index == 0
    assert result.state.phase_turns == initial.phase_turns
    assert result.state.disrupted is True


def test_sample_gap_is_a_failure_not_time_compression():
    cal = calibration("dynamic-neurite", PortKind.PHASIC)
    gap = NativePortSample(
        source_epoch="epoch-1",
        sample_index=2,
        timestamp=F(3),
        raw_code=5,
        native_relevance=F(1),
    )
    sample_batch, batch_payload = batch(cal, (gap,), "gap-batch")

    result = couple_native_port(
        cal,
        sample_batch,
        state(cal),
        registry(cal.canonical_receipt_payload(), batch_payload),
    )

    assert result.evidence is None
    assert result.failure is not None
    assert result.failure.reason == "nonconsecutive_sample_index"
    assert result.state.disrupted is True


def test_out_of_range_calibration_fails_without_clamping():
    cal = calibration("dynamic-neurite", PortKind.PHASIC)
    sample_batch, batch_payload = batch(
        cal, samples((100,), (F(1),)), "range-batch"
    )

    result = couple_native_port(
        cal,
        sample_batch,
        state(cal),
        registry(cal.canonical_receipt_payload(), batch_payload),
    )

    assert result.evidence is None
    assert result.failure is not None
    assert result.failure.reason.startswith("calibration_fault:")
    assert result.state.phase_turns == F(1, 7)


def test_missing_or_malformed_receipt_is_rejected():
    with pytest.raises(ReceiptError, match="64 lowercase"):
        NativePortCalibration(
            sense=Sense.SIGHT,
            transducer_id="rod-1",
            port_id="glutamate-release",
            port_kind=PortKind.TONIC,
            physical_unit="vesicles_per_second",
            raw_scale=F(1),
            raw_offset=F(0),
            phase_kappa=F(1),
            calibration_id="rod-cal-v1",
            physical_profile_receipt_sha256=DIGEST_PHYSICAL,
            calibration_receipt_sha256="missing",
            relevance_operator_id="rod-release-v1",
            relevance_receipt_sha256=DIGEST_B,
        )


def test_digest_shaped_string_without_mounted_bytes_is_not_authority():
    cal = calibration("dynamic-neurite", PortKind.PHASIC)
    unmounted = NativePortCalibration(
        sense=cal.sense,
        transducer_id=cal.transducer_id,
        port_id=cal.port_id,
        port_kind=cal.port_kind,
        physical_unit=cal.physical_unit,
        raw_scale=cal.raw_scale,
        raw_offset=cal.raw_offset,
        phase_kappa=cal.phase_kappa,
        calibration_id=cal.calibration_id,
        physical_profile_receipt_sha256=cal.physical_profile_receipt_sha256,
        calibration_receipt_sha256="d" * 64,
        relevance_operator_id=cal.relevance_operator_id,
        relevance_receipt_sha256=cal.relevance_receipt_sha256,
    )
    sample_batch, batch_payload = batch(unmounted)

    with pytest.raises(ReceiptError, match="not mounted"):
        couple_native_port(unmounted, sample_batch, state(cal), registry(batch_payload))


def test_changing_calibration_field_under_same_digest_fails_closed():
    original = calibration("dynamic-neurite", PortKind.PHASIC)
    changed = replace(original, raw_scale=F(1, 9))
    sample_batch, batch_payload = batch(changed)

    with pytest.raises(ReceiptError, match="fields do not match"):
        couple_native_port(
            changed,
            sample_batch,
            state(changed),
            registry(original.canonical_receipt_payload(), batch_payload),
        )


def test_changing_native_relevance_under_same_batch_digest_fails_closed():
    cal = calibration("dynamic-neurite", PortKind.PHASIC)
    original_batch, original_payload = batch(cal)
    changed_samples = (
        replace(original_batch.samples[0], native_relevance=F(9, 10)),
        *original_batch.samples[1:],
    )
    changed_batch = replace(original_batch, samples=changed_samples)

    with pytest.raises(ReceiptError, match="values do not match"):
        couple_native_port(
            cal,
            changed_batch,
            state(cal),
            registry(cal.canonical_receipt_payload(), original_payload),
        )
