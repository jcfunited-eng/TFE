from dataclasses import replace
from fractions import Fraction as F

import pytest

from dsf_ai_service.glew_runtime import (
    ReceiptError,
    ReceiptRegistry,
    TypedLanguageEvent,
    TypedLanguageState,
    capture_typed_language,
    encode_balanced_ternary_scalar,
    receipt_sha256,
    typed_interface_receipt_payload,
    typed_language_event_receipt_payload,
    typed_phase_calibration_receipt_payload,
)


PROFILE = b"glew-profile-fixture-v1"
INTERFACE = typed_interface_receipt_payload("typed-keyboard-1")
PHASE = typed_phase_calibration_receipt_payload("typed-phase-v1", F(1, 3))
GENESIS = b"typed-genesis-fixture-v1"
DIGEST_A = receipt_sha256(INTERFACE)
DIGEST_B = receipt_sha256(PHASE)
DIGEST_C = receipt_sha256(GENESIS)


def registry(*payloads: bytes) -> ReceiptRegistry:
    return ReceiptRegistry.from_payloads(
        profile_payload=PROFILE,
        receipt_payloads=(INTERFACE, PHASE, GENESIS, *payloads),
    )


def test_balanced_ternary_round_trip_and_padding_validity():
    for scalar in (0, ord("A"), 0x10FFFF):
        trits = encode_balanced_ternary_scalar(scalar)
        reconstructed = sum(trit.value * 3**trit.place for trit in trits if trit.valid)
        assert reconstructed == scalar
        first_padding = next((trit.place for trit in trits if not trit.valid), 14)
        assert all(not trit.valid for trit in trits[first_padding:])


def _event(text: str = "A") -> TypedLanguageEvent:
    normalized = __import__("unicodedata").normalize("NFC", text)
    valid_count = sum(
        trit.valid
        for index, scalar in enumerate(normalized)
        for trit in encode_balanced_ternary_scalar(ord(scalar), index)
    )
    times = tuple(F(index + 1) for index in range(valid_count))
    event_payload = typed_language_event_receipt_payload(
        text=text,
        event_id="typed-event-1",
        interface_id="typed-keyboard-1",
        source_epoch="keyboard-epoch-1",
        valid_sample_times=times,
    )
    return TypedLanguageEvent.from_text(
        text=text,
        event_id="typed-event-1",
        interface_id="typed-keyboard-1",
        source_epoch="keyboard-epoch-1",
        valid_sample_times=times,
        interface_receipt_sha256=DIGEST_A,
        event_receipt_sha256=receipt_sha256(event_payload),
        phase_calibration_id="typed-phase-v1",
        phase_kappa=F(1, 3),
        phase_calibration_receipt_sha256=DIGEST_B,
    )


def _state() -> TypedLanguageState:
    return TypedLanguageState(
        phase_calibration_id="typed-phase-v1",
        source_epoch="keyboard-epoch-1",
        last_source_index=-1,
        last_timestamp=F(0),
        phase_turns=F(0),
        genesis_receipt_sha256=DIGEST_C,
    )


def test_typed_text_is_nfc_preserved_as_artificial_unit_events_not_chemistry():
    event = _event("e\u0301")

    evidence, final_state = capture_typed_language(
        event, _state(), registry(event.canonical_event_payload())
    )

    assert event.original_utf8 == "e\u0301".encode("utf-8")
    assert event.normalized_text == "é"
    assert evidence.lane_id == "language"
    assert evidence.port_id == "typed-keyboard-1"
    assert evidence.evidence_id == "typed-event-1"
    assert evidence.port_kind == "artificial_interface_event"
    assert evidence.physical_unit == "valid_balanced_trit_event"
    assert all(sample.relevance == F(1) for sample in evidence.samples)
    assert final_state.phase_turns == evidence.samples[-1].phase_turns


def test_valid_zero_trit_is_a_real_interface_event_with_separate_signal_and_relevance():
    event = _event("\x00")

    evidence, _ = capture_typed_language(
        event, _state(), registry(event.canonical_event_payload())
    )

    assert len(evidence.samples) == 1
    assert evidence.samples[0].signal == 0
    assert evidence.samples[0].relevance == 1


def test_typed_event_does_not_invent_source_timestamps():
    with pytest.raises(ReceiptError, match="one exact source timestamp"):
        TypedLanguageEvent.from_text(
            text="A",
            event_id="typed-event-1",
            interface_id="typed-keyboard-1",
            source_epoch="keyboard-epoch-1",
            valid_sample_times=(),
            interface_receipt_sha256=DIGEST_A,
            event_receipt_sha256="d" * 64,
            phase_calibration_id="typed-phase-v1",
            phase_kappa=F(1),
            phase_calibration_receipt_sha256=DIGEST_B,
        )


def test_empty_text_is_not_silently_converted_to_zero_relevance():
    with pytest.raises(ReceiptError, match="nonempty"):
        TypedLanguageEvent.from_text(
            text="",
            event_id="typed-event-1",
            interface_id="typed-keyboard-1",
            source_epoch="keyboard-epoch-1",
            valid_sample_times=(),
            interface_receipt_sha256=DIGEST_A,
            event_receipt_sha256="d" * 64,
            phase_calibration_id="typed-phase-v1",
            phase_kappa=F(1),
            phase_calibration_receipt_sha256=DIGEST_B,
        )


def test_changing_typed_event_under_same_digest_fails_closed():
    original = _event("A")
    changed_payload = typed_language_event_receipt_payload(
        text="B",
        event_id=original.event_id,
        interface_id=original.interface_id,
        source_epoch=original.source_epoch,
        valid_sample_times=original.valid_sample_times,
    )
    changed = TypedLanguageEvent.from_text(
        text="B",
        event_id=original.event_id,
        interface_id=original.interface_id,
        source_epoch=original.source_epoch,
        valid_sample_times=original.valid_sample_times,
        interface_receipt_sha256=original.interface_receipt_sha256,
        event_receipt_sha256=original.event_receipt_sha256,
        phase_calibration_id=original.phase_calibration_id,
        phase_kappa=original.phase_kappa,
        phase_calibration_receipt_sha256=original.phase_calibration_receipt_sha256,
    )
    assert changed.canonical_event_payload() == changed_payload

    with pytest.raises(ReceiptError, match="event values do not match"):
        capture_typed_language(
            changed,
            _state(),
            registry(original.canonical_event_payload()),
        )


def test_changing_phase_kappa_under_same_receipt_fails_closed():
    original = _event("A")
    changed = replace(original, phase_kappa=F(2, 3))

    with pytest.raises(ReceiptError, match="phase fields do not match"):
        capture_typed_language(
            changed,
            _state(),
            registry(original.canonical_event_payload()),
        )
