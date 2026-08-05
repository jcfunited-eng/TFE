"""Lossless bounded closure proofs for the complete auditory DSF field."""

from __future__ import annotations

import io
import json
import math
import struct
import wave
from dataclasses import replace
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.model import ReceiptError
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    build_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.compact_auditory_field_authority import (
    MAX_COMPACT_AUDITORY_FIELD_BYTES,
    compact_auditory_field_from_causal_settlement,
    decode_compact_auditory_field,
    maximum_full_field_payload_bytes,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.w1_audiovisual_physical_evidence import (
    _sound_inputs,
)


from tests.native_joint_occurrence_support import joint_occurrences_for
SAMPLE_RATE = 16_000


def _wav() -> bytes:
    values = tuple(
        int(
            9_000
            * math.sin(2.0 * math.pi * 440.0 * index / SAMPLE_RATE)
            + 3_000
            * math.sin(2.0 * math.pi * 733.0 * index / SAMPLE_RATE)
        )
        for index in range(SAMPLE_RATE)
    )
    payload = io.BytesIO()
    with wave.open(payload, "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(SAMPLE_RATE)
        stream.writeframes(struct.pack(f"<{len(values)}h", *values))
    return payload.getvalue()


@pytest.fixture(scope="module")
def compact_authority():
    with wave.open(io.BytesIO(_wav()), "rb") as stream:
        pcm = stream.readframes(stream.getnframes())
    sound_inputs = _sound_inputs(
        ear="left",
        topology_index=0,
        pcm=pcm,
        source_time_start=Fraction(4),
    )
    observed = {
        PhysicalSense.SOUND: tuple(sound_inputs),
    }
    built = build_six_sense_full_field(
        assembly_id="compact-authority-test",
        source_time_start=Fraction(4),
        source_time_end=Fraction(5),
        observed_substreams=observed,
        occurrences=joint_occurrences_for(observed),
        states={
            sense: (
                SenseBoundaryState.OBSERVED
                if sense is PhysicalSense.SOUND
                else SenseBoundaryState.SENSOR_UNAVAILABLE
            )
            for sense in SENSE_ORDER
        },
    )
    settlement = ExactCausalExperienceOwner(
        on_settlement=lambda _settlement: None,
        log_event=lambda *_args, **_kwargs: None,
    ).settle(
        built,
        routing_chis=(),
        source_tags=(),
    )
    sound = next(
        value
        for value in settlement.interpretations
        if value.sense == "sound"
    )
    authority = compact_auditory_field_from_causal_settlement(
        settlement
    )
    return settlement, sound, authority


def test_real_full_field_round_trips_every_field_and_interval_exactly(
    compact_authority,
) -> None:
    _settlement, sound, authority = compact_authority
    encoded = authority.encoded()
    restored = decode_compact_auditory_field(encoded)

    assert restored == authority
    assert restored.encoded() == encoded
    assert len(encoded) < MAX_COMPACT_AUDITORY_FIELD_BYTES
    for compact, source, causal in zip(
        restored.components,
        sound.substreams,
        sound.substreams,
        strict=True,
    ):
        assert compact.source_sample_count == source.source_sample_count
        assert len(compact.tuples) == len(source.field_tuples)
        for closed, exact, exact_support in zip(
            compact.tuples,
            source.field_tuples,
            causal.field_tuples,
            strict=True,
        ):
            assert closed.tuple_index == exact.tuple_index
            assert closed.fields == exact.fields
            assert tuple(name for name, _value in closed.fields) == (
                DSF_FIELD_ORDER
            )
            assert closed.source_index_start == (
                exact_support.source_index_start
            )
            assert closed.source_index_end == (
                exact_support.source_index_end
            )


def test_durable_authority_retains_no_raw_sample_array(
    compact_authority,
) -> None:
    _experience, _support, authority = compact_authority
    encoded = authority.encoded()
    metadata_length = struct.unpack(">I", encoded[8:12])[0]
    metadata = json.loads(encoded[12:12 + metadata_length])

    assert "samples" not in metadata
    for component in metadata["components"]:
        assert "samples" not in component
        assert "signal" not in component
        assert "phase_turns" not in component
        assert component["source_sample_count"] > 0
        assert len(component["source_sample_commitment_sha256"]) == 64


def test_payload_and_digest_tampering_are_rejected(
    compact_authority,
) -> None:
    _experience, _support, authority = compact_authority
    encoded = authority.encoded()
    payload_tamper = bytearray(encoded)
    payload_tamper[-33] ^= 1
    digest_tamper = bytearray(encoded)
    digest_tamper[-1] ^= 1

    with pytest.raises(ReceiptError):
        decode_compact_auditory_field(bytes(payload_tamper))
    with pytest.raises(ReceiptError):
        decode_compact_auditory_field(bytes(digest_tamper))


def test_non_binary64_field_is_rejected_instead_of_rounded(
    compact_authority,
) -> None:
    _experience, _support, authority = compact_authority
    component = authority.components[0]
    field_tuple = component.tuples[0]
    changed_tuple = replace(
        field_tuple,
        fields=(
            (DSF_FIELD_ORDER[0], Fraction(1, 3)),
            *field_tuple.fields[1:],
        ),
    )

    with pytest.raises(
        ReceiptError,
        match="outside the exact binary64 kernel receipt domain",
    ):
        changed_tuple.verify(
            expected_tuple_index=0,
            source_sample_count=component.source_sample_count,
        )


def test_two_ear_worst_case_field_payload_fits_declared_boundary() -> None:
    assert maximum_full_field_payload_bytes() == 1_920_000
    assert (
        maximum_full_field_payload_bytes()
        < MAX_COMPACT_AUDITORY_FIELD_BYTES
    )
    assert (
        MAX_COMPACT_AUDITORY_FIELD_BYTES
        - maximum_full_field_payload_bytes()
        == 177_152
    )


def test_two_ear_causal_settlement_closes_into_same_lossless_boundary() -> None:
    sample_count = 960

    def pcm(frequency_hz: int) -> bytes:
        values = tuple(
            int(
                10_000
                * math.sin(
                    2.0
                    * math.pi
                    * frequency_hz
                    * index
                    / SAMPLE_RATE
                )
            )
            for index in range(sample_count)
        )
        return struct.pack(f"<{sample_count}h", *values)

    start = Fraction(0)
    left = _sound_inputs(
        ear="left",
        topology_index=0,
        pcm=pcm(440),
        source_time_start=start,
    )
    right = _sound_inputs(
        ear="right",
        topology_index=len(left),
        pcm=pcm(660),
        source_time_start=start,
    )
    observed = {
        PhysicalSense.SOUND: (*left, *right),
    }
    built = build_six_sense_full_field(
        assembly_id="compact-two-ear-test",
        source_time_start=start,
        source_time_end=Fraction(sample_count, SAMPLE_RATE),
        observed_substreams=observed,
        occurrences=joint_occurrences_for(observed),
        states={
            sense: (
                SenseBoundaryState.OBSERVED
                if sense is PhysicalSense.SOUND
                else SenseBoundaryState.SENSOR_UNAVAILABLE
            )
            for sense in SENSE_ORDER
        },
    )
    owner = ExactCausalExperienceOwner(
        on_settlement=lambda _settlement: None,
        log_event=lambda *_args, **_kwargs: None,
    )
    settlement = owner.settle(
        built,
        routing_chis=(),
        source_tags=(),
    )
    authority = compact_auditory_field_from_causal_settlement(
        settlement
    )
    restored = decode_compact_auditory_field(authority.encoded())

    assert restored == authority
    assert len(restored.components) == 64
    assert len(authority.encoded()) < MAX_COMPACT_AUDITORY_FIELD_BYTES
    sound = next(
        value
        for value in settlement.interpretations
        if value.sense == "sound"
    )
    for compact, source in zip(
        restored.components,
        sound.substreams,
        strict=True,
    ):
        assert tuple(value.fields for value in compact.tuples) == tuple(
            value.fields for value in source.field_tuples
        )
