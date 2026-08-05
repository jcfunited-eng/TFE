from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.language import (
    MountedTypedLanguageKernelBinding,
    TypedLanguageEvent,
    TypedLanguageState,
    build_typed_language_frozen_kernel_input,
    encode_balanced_ternary_scalar,
    typed_interface_receipt_payload,
    typed_language_event_receipt_payload,
    typed_language_kernel_binding_receipt_payload,
    typed_phase_calibration_receipt_payload,
)
from dsf_ai_service.glew_runtime.model import (
    ReceiptError,
    ReceiptRegistry,
    receipt_sha256,
)


def _environment(scalar: str = "I"):
    profile = b'{"schema":"test.typed_language_kernel_profile.v1"}'
    interface_id = "typed-recall-interface"
    interface_payload = typed_interface_receipt_payload(interface_id)
    phase_id = "typed-recall-phase"
    phase_kappa = Fraction(1, 7)
    phase_payload = typed_phase_calibration_receipt_payload(
        phase_id,
        phase_kappa,
    )
    genesis_payload = b'{"schema":"test.typed_language_genesis.v1"}'
    derivation_payload = (
        b'{"derivation":"F=1+s/2;inverse s=2*(F-1)",'
        b'"schema":"test.typed_language_kernel_derivation.v1"}'
    )
    binding_payload = typed_language_kernel_binding_receipt_payload(
        adapter_id="typed-recall-frozen-kernel-adapter",
        interface_id=interface_id,
        interface_receipt_sha256=receipt_sha256(interface_payload),
        phase_calibration_receipt_sha256=receipt_sha256(phase_payload),
        derivation_receipt_sha256=receipt_sha256(derivation_payload),
    )
    binding = MountedTypedLanguageKernelBinding(
        adapter_id="typed-recall-frozen-kernel-adapter",
        interface_id=interface_id,
        interface_receipt_sha256=receipt_sha256(interface_payload),
        phase_calibration_receipt_sha256=receipt_sha256(phase_payload),
        derivation_receipt_sha256=receipt_sha256(derivation_payload),
        authority_receipt_sha256=receipt_sha256(binding_payload),
    )
    valid_count = sum(
        value.valid for value in encode_balanced_ternary_scalar(ord(scalar))
    )
    times = tuple(Fraction(index + 1) for index in range(valid_count))
    event_payload = typed_language_event_receipt_payload(
        text=scalar,
        event_id="typed-recall-scalar-event",
        interface_id=interface_id,
        source_epoch="typed-recall-epoch",
        valid_sample_times=times,
    )
    event = TypedLanguageEvent.from_text(
        text=scalar,
        event_id="typed-recall-scalar-event",
        interface_id=interface_id,
        source_epoch="typed-recall-epoch",
        valid_sample_times=times,
        interface_receipt_sha256=receipt_sha256(interface_payload),
        event_receipt_sha256=receipt_sha256(event_payload),
        phase_calibration_id=phase_id,
        phase_kappa=phase_kappa,
        phase_calibration_receipt_sha256=receipt_sha256(phase_payload),
    )
    state = TypedLanguageState(
        phase_calibration_id=phase_id,
        source_epoch="typed-recall-epoch",
        last_source_index=-1,
        last_timestamp=Fraction(0),
        phase_turns=Fraction(0),
        genesis_receipt_sha256=receipt_sha256(genesis_payload),
    )
    registry = ReceiptRegistry.from_payloads(
        profile_payload=profile,
        receipt_payloads=(
            interface_payload,
            phase_payload,
            genesis_payload,
            derivation_payload,
            binding_payload,
            event_payload,
        ),
    )
    return event, state, binding, registry


def test_typed_scalar_is_receipt_bound_to_frozen_kernel_without_relevance_flattening():
    event, state, binding, registry = _environment("I")

    result = build_typed_language_frozen_kernel_input(
        event=event,
        initial_state=state,
        kernel_binding=binding,
        receipt_registry=registry,
    )

    result.verify()
    assert result.stream.lane_id == "language"
    assert tuple(value.relevance for value in result.stream.samples) == tuple(
        Fraction(1) for _ in result.stream.samples
    )
    assert tuple(
        value.dimensionless_field for value in result.kernel_input.samples
    ) == tuple(
        Fraction(1) + value.signal / 2 for value in result.stream.samples
    )
    restarted = replace(
        result,
        receipt_registry=ReceiptRegistry(
            result.receipt_registry.profile_binding_sha256,
            tuple(result.receipt_registry.records),
        ),
    )
    restarted.verify()


def test_complete_14_place_grid_preserves_valid_zero_and_padding_boundary():
    event, state, binding, registry = _environment("b")
    complete_times = tuple(Fraction(index + 1) for index in range(14))

    result = build_typed_language_frozen_kernel_input(
        event=event,
        initial_state=state,
        kernel_binding=binding,
        receipt_registry=registry,
        complete_grid_times=complete_times,
    )

    result.verify()
    assert len(result.stream.samples) == 14
    assert result.final_state.last_source_index == 13
    assert result.final_state.last_timestamp == Fraction(14)
    observed = tuple(
        (trit.valid, trit.value, sample.relevance)
        for trit, sample in zip(
            event.trits,
            result.stream.samples,
            strict=True,
        )
    )
    assert any(
        valid and value == 0 and relevance == Fraction(1)
        for valid, value, relevance in observed
    )
    assert all(
        relevance == (Fraction(1) if valid else Fraction(0))
        for valid, _value, relevance in observed
    )
    assert tuple(
        value.l0_relevance for value in result.kernel_input.samples
    ) == tuple(
        value.relevance for value in result.stream.samples
    )


def test_typed_kernel_map_tamper_fails_closed():
    event, state, binding, registry = _environment("I")
    result = build_typed_language_frozen_kernel_input(
        event=event,
        initial_state=state,
        kernel_binding=binding,
        receipt_registry=registry,
    )
    first = result.kernel_input.samples[0]
    changed = replace(
        result.kernel_input,
        samples=(
            replace(
                first,
                dimensionless_field=first.dimensionless_field - Fraction(1, 9),
            ),
            *result.kernel_input.samples[1:],
        ),
    )

    with pytest.raises(ReceiptError):
        replace(result, kernel_input=changed).verify()
