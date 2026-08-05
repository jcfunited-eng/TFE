from __future__ import annotations

import json
import math
from dataclasses import replace
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.model import (
    ReceiptError,
    ReceiptRegistry,
    receipt_sha256,
)
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    MAX_NATIVE_SAMPLES_PER_SUBSTREAM,
    NativeSensorySubstreamInput,
    build_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
    SETTLEMENT_PROFILE_PAYLOAD,
    SETTLEMENT_SCHEMA,
    causal_experience_settlement_receipt_payload,
    source_evidence_sample_commitment_sha256,
)
from dsf_ai_service.substrate.native_evidence_custody import (
    NativeEvidenceCustodyOwner,
    NativeEvidenceCustodyWitness,
)


def _boundary(
    assembly_id: str,
    *,
    frequency: int = 8,
    coordinate: str = "center",
    physical_unit: str = "normalized-intensity",
):
    sample_count = 96
    signal = tuple(
        math.sin(2 * math.pi * frequency * index / 200)
        for index in range(sample_count)
    )
    sight = NativeSensorySubstreamInput(
        sense=PhysicalSense.SIGHT,
        sensor_id="test-camera",
        substream_id="fixation-0",
        topology_index=0,
        coordinates=(NativeAxisCoordinate("fixation", coordinate),),
        physical_quantity="light-intensity",
        physical_unit=physical_unit,
        source_times=tuple(Fraction(index, 200)
                           for index in range(sample_count)),
        normalized_signal=signal,
        phase_turns=tuple(Fraction(index // 12)
                          for index in range(sample_count)),
    )
    states = {
        sense: (
            SenseBoundaryState.OBSERVED
            if sense is PhysicalSense.SIGHT
            else SenseBoundaryState.SENSOR_UNAVAILABLE
        )
        for sense in SENSE_ORDER
    }
    return build_six_sense_full_field(
        assembly_id=assembly_id,
        source_time_start=Fraction(0),
        source_time_end=Fraction(sample_count, 200),
        observed_substreams={PhysicalSense.SIGHT: (sight,)},
        states=states,
    )


def test_exact_identity_excludes_chi_source_and_event_bookkeeping() -> None:
    accepted = []
    owner = ExactCausalExperienceOwner(
        on_settlement=accepted.append,
        log_event=lambda *_args, **_kwargs: None,
    )

    first = owner.settle(
        _boundary("capture-one"),
        routing_chis=(3,),
        source_tags=("joe_voice",),
    )
    repeated = owner.settle(
        _boundary("capture-two"),
        routing_chis=(91,),
        source_tags=("ambient",),
    )

    assert first.structural_fingerprint == repeated.structural_fingerprint
    assert first.event_id != repeated.event_id
    assert first.routing_chis != repeated.routing_chis
    assert first.source_tags != repeated.source_tags
    assert repeated.interpretations[0].relation == "recurrence"
    first.verify()
    repeated.verify()
    assert len(first.receipt_registry.records) == (
        len(first.native_evidence_witness.receipt_records) + 3
    )
    assert owner.status()["settled"] == 2
    assert accepted == [first, repeated]


def test_settlement_builds_registry_from_one_verified_native_witness(
    monkeypatch,
) -> None:
    settlement = ExactCausalExperienceOwner(
        on_settlement=lambda _settlement: None,
        log_event=lambda *_args, **_kwargs: None,
    ).settle(
        _boundary("one-verified-native-witness"),
        routing_chis=(),
        source_tags=(),
    )
    witness_type = type(settlement.native_evidence_witness)
    original_verify = witness_type.verify
    calls = 0

    def counted_verify(value):
        nonlocal calls
        calls += 1
        return original_verify(value)

    monkeypatch.setattr(witness_type, "verify", counted_verify)
    object.__setattr__(settlement, "_verified_integrity", None)
    settlement.verify()
    settlement.verify()

    assert calls == 1


def test_native_witness_full_verification_is_retained_by_exact_object(
    monkeypatch,
) -> None:
    witness = NativeEvidenceCustodyWitness.from_built(
        _boundary("one-full-native-verification")
    )
    port_type = type(witness.ports[0])
    original_verify = port_type.verify
    calls = 0

    def counted_verify(value, registry):
        nonlocal calls
        calls += 1
        return original_verify(value, registry)

    monkeypatch.setattr(port_type, "verify", counted_verify)
    object.__setattr__(witness, "_verified_integrity", None)
    witness.verify()
    witness.verify()

    assert calls == len(witness.ports)


def test_native_transition_full_verification_is_retained_by_exact_object(
    monkeypatch,
) -> None:
    transition = NativeEvidenceCustodyWitness.from_built(
        _boundary("one-full-native-transition-verification")
    ).transition_index()
    port_type = type(transition.ports[0])
    original_verify_index = port_type.verify_index
    calls = 0

    def counted_verify_index(value):
        nonlocal calls
        calls += 1
        return original_verify_index(value)

    monkeypatch.setattr(
        port_type,
        "verify_index",
        counted_verify_index,
    )
    object.__setattr__(transition, "_verified_integrity", None)
    transition.verify()
    transition.verify()

    assert calls == len(transition.ports)


def test_repeated_native_content_keeps_current_construction_tuple() -> None:
    owner = ExactCausalExperienceOwner(
        on_settlement=lambda _settlement: None,
        log_event=lambda *_args, **_kwargs: None,
    )
    first_built = _boundary("same-physical-construction")
    first = owner.settle(
        first_built,
        routing_chis=(),
        source_tags=(),
    )
    second_built = _boundary("same-physical-construction")

    second = owner.settle(
        second_built,
        routing_chis=(),
        source_tags=(),
    )

    assert (
        first.native_evidence_witness.authority_receipt_sha256
        == second.native_evidence_witness.authority_receipt_sha256
    )
    assert (
        second.native_evidence_witness.receipt_records
        is second_built.receipt_registry.records
    )
    second.verify()


def test_one_exact_field_change_is_structural_change() -> None:
    owner = ExactCausalExperienceOwner(
        on_settlement=lambda _settlement: None,
        log_event=lambda *_args, **_kwargs: None,
    )
    owner.settle(
        _boundary("capture-one", frequency=8),
        routing_chis=(),
        source_tags=(),
    )
    changed = owner.settle(
        _boundary("capture-two", frequency=9),
        routing_chis=(),
        source_tags=(),
    )

    assert changed.interpretations[0].relation == "structural_change"


def test_physical_topology_is_structural_but_capture_source_is_not() -> None:
    owner = ExactCausalExperienceOwner(
        on_settlement=lambda _settlement: None,
        log_event=lambda *_args, **_kwargs: None,
    )
    first = owner.settle(
        _boundary("capture-one"),
        routing_chis=(7,),
        source_tags=("camera-a",),
    )
    moved = owner.settle(
        _boundary("capture-two", coordinate="upper-left"),
        routing_chis=(91,),
        source_tags=("camera-b",),
    )
    unit_changed = owner.settle(
        _boundary("capture-three", coordinate="upper-left", physical_unit="lux"),
        routing_chis=(3,),
        source_tags=("camera-c",),
    )

    assert first.structural_fingerprint != moved.structural_fingerprint
    assert moved.structural_fingerprint != unit_changed.structural_fingerprint
    assert moved.interpretations[0].relation == "structural_change"
    assert unit_changed.interpretations[0].relation == "structural_change"


def test_one_oversized_native_substream_is_rejected_before_receipt_growth() -> None:
    count = MAX_NATIVE_SAMPLES_PER_SUBSTREAM + 1
    with pytest.raises(ValueError, match="settlement sample boundary"):
        NativeSensorySubstreamInput(
            sense=PhysicalSense.SOUND,
            sensor_id="test-microphone",
            substream_id="band-0",
            topology_index=0,
            coordinates=(NativeAxisCoordinate("frequency", "440-hz"),),
            physical_quantity="sound-pressure",
            physical_unit="normalized-amplitude",
            source_times=tuple(Fraction(index, 200) for index in range(count)),
            normalized_signal=(0.0,) * count,
            phase_turns=(Fraction(0),) * count,
        )


def test_settlement_retains_bounded_exact_source_evidence_commitment() -> None:
    built = _boundary("source-commitment")
    settlement = ExactCausalExperienceOwner(
        on_settlement=lambda _settlement: None,
        log_event=lambda *_args, **_kwargs: None,
    ).settle(built, routing_chis=(), source_tags=())
    substream = settlement.interpretations[0].substreams[0]
    source_digest = (
        built.boundary.boundaries[0]
        .substreams[0]
        .profile.physical_derivation_receipt_sha256
    )
    samples = tuple(
        (
            index,
            Fraction(index, 200),
            Fraction.from_float(
                math.sin(2 * math.pi * 8 * index / 200)
            ),
            Fraction(1),
            Fraction(index // 12),
        )
        for index in range(96)
    )

    assert substream.source_evidence_stream_receipt_sha256 == source_digest
    assert substream.source_sample_count == len(samples)
    assert substream.source_sample_commitment_sha256 == (
        source_evidence_sample_commitment_sha256(samples)
    )
    assert substream.matches_source_claim(
        source_evidence_stream_receipt_sha256=source_digest,
        samples=samples,
    )
    assert not hasattr(substream, "samples")

    authority = json.loads(settlement.receipt_registry.resolve(
        settlement.authority_receipt_sha256
    ))
    authority_substream = authority["interpretations"][0]["substreams"][0]
    assert authority["schema"] == SETTLEMENT_SCHEMA
    assert authority_substream["source_evidence_stream_receipt_sha256"] == (
        source_digest
    )
    assert authority_substream["source_sample_count"] == len(samples)
    assert authority_substream["source_sample_commitment_sha256"] == (
        substream.source_sample_commitment_sha256
    )


def test_settlement_cold_witness_retains_raw_native_trace_and_n_gate() -> None:
    settlement = ExactCausalExperienceOwner(
        on_settlement=lambda _settlement: None,
        log_event=lambda *_args, **_kwargs: None,
    ).settle(
        _boundary("lossless-native-witness"),
        routing_chis=(),
        source_tags=(),
    )
    witness = settlement.native_evidence_witness
    cold = NativeEvidenceCustodyWitness.from_record(witness.record())
    assert cold == witness
    assert cold.total_receipt_bytes == sum(
        len(value.payload) for value in cold.receipt_records
    )
    assert len(cold.ports) == 1
    port = cold.ports[0]
    samples = port.verify(cold.registry())
    assert tuple(value[1] for value in samples) == tuple(
        Fraction(index, 200) for index in range(96)
    )
    trace = json.loads(cold.registry().resolve(
        port.complete_l0_l4_trace_receipt_sha256
    ))
    assert port.n_gates == tuple(
        value["N_gate"] for value in trace["L1_GateL1State"]
    )
    assert settlement.receipt_registry.resolve(
        port.source_evidence_stream_receipt_sha256
    ) == cold.registry().resolve(
        port.source_evidence_stream_receipt_sha256
    )
    settlement.verify()


def test_native_witness_rejects_n_gate_bytes_and_count_tampering() -> None:
    witness = ExactCausalExperienceOwner(
        on_settlement=lambda _settlement: None,
        log_event=lambda *_args, **_kwargs: None,
    ).settle(
        _boundary("native-witness-tamper"),
        routing_chis=(),
        source_tags=(),
    ).native_evidence_witness

    changed_gate = json.loads(json.dumps(witness.record()))
    changed_gate["ports"][0]["n_gates"][0] += 1
    with pytest.raises(ReceiptError, match="N_gate evidence changed"):
        NativeEvidenceCustodyWitness.from_record(changed_gate)

    changed_bytes = json.loads(json.dumps(witness.record()))
    encoded = changed_bytes["receipt_records"][0]["payload_base64"]
    changed_bytes["receipt_records"][0]["payload_base64"] = (
        ("A" if encoded[0] != "A" else "B") + encoded[1:]
    )
    with pytest.raises(ReceiptError, match="does not match"):
        NativeEvidenceCustodyWitness.from_record(changed_bytes)

    with pytest.raises(ReceiptError, match="byte custody changed"):
        replace(
            witness,
            total_receipt_bytes=witness.total_receipt_bytes + 1,
        ).verify()


def test_settlement_rejects_dropped_native_registry_dependencies() -> None:
    settlement = ExactCausalExperienceOwner(
        on_settlement=lambda _settlement: None,
        log_event=lambda *_args, **_kwargs: None,
    ).settle(
        _boundary("native-dependency-drop"),
        routing_chis=(),
        source_tags=(),
    )
    payload = settlement.receipt_registry.resolve(
        settlement.authority_receipt_sha256
    )
    dropped = replace(
        settlement,
        receipt_registry=ReceiptRegistry.from_payloads(
            profile_payload=SETTLEMENT_PROFILE_PAYLOAD,
            receipt_payloads=(payload,),
        ),
    )
    with pytest.raises(
        ReceiptError,
        match="receipt dependency custody changed",
    ):
        dropped.verify()


def test_repeated_native_experience_keeps_one_raw_content_window() -> None:
    owner = ExactCausalExperienceOwner(
        on_settlement=lambda _settlement: None,
        log_event=lambda *_args, **_kwargs: None,
    )
    first = owner.settle(
        _boundary("bounded-native-window-0"),
        routing_chis=(),
        source_tags=(),
    )
    raw_record_bytes = len(json.dumps(
        first.native_evidence_witness.record(),
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8"))
    transition_bytes = len(json.dumps(
        first.native_evidence_witness.transition_index().record(),
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8"))
    assert transition_bytes < raw_record_bytes

    for index in range(1, 24):
        owner.settle(
            _boundary(f"bounded-native-window-{index}"),
            routing_chis=(),
            source_tags=(),
        )
    custody = owner.status()["native_evidence_custody"]
    assert custody["retained_witnesses"] == 1
    assert custody["retired_witnesses"] == 23
    assert custody["raw_receipt_bytes"] <= (
        custody["max_receipt_bytes_per_witness"]
    )
    assert custody["raw_receipt_bytes"] <= custody[
        "max_total_receipt_bytes"
    ]


def test_failed_direct_settlement_leaves_no_native_evidence() -> None:
    def fail_after_verification(_settlement) -> None:
        raise RuntimeError("injected direct causal callback failure")

    owner = ExactCausalExperienceOwner(
        on_settlement=fail_after_verification,
        log_event=lambda *_args, **_kwargs: None,
    )
    before = owner.status()

    with pytest.raises(
        RuntimeError,
        match="injected direct causal callback failure",
    ):
        owner.settle(
            _boundary("failed-direct-native-custody"),
            routing_chis=(),
            source_tags=(),
        )

    assert owner.status() == before


def test_discarded_reservation_leaves_no_native_evidence() -> None:
    owner = ExactCausalExperienceOwner(
        on_settlement=lambda _settlement: None,
        log_event=lambda *_args, **_kwargs: None,
    )
    before = owner.status()
    settlement = owner.settle(
        _boundary("discarded-native-custody-reservation"),
        routing_chis=(),
        source_tags=(),
        commit=False,
        reserve=True,
    )
    prepared = owner.status()["native_evidence_custody"]
    assert prepared["prepared_admissions"] == 1
    assert prepared["retained_witnesses"] == 0

    owner.discard_prepared(settlement)

    assert owner.status() == before


def test_prepared_native_evidence_bytes_are_bounded() -> None:
    witness = NativeEvidenceCustodyWitness.from_built(
        _boundary("bounded-prepared-native-evidence")
    )
    custody = NativeEvidenceCustodyOwner(
        max_retained_witnesses=1,
        max_total_receipt_bytes=witness.total_receipt_bytes,
        max_receipt_bytes_per_witness=witness.total_receipt_bytes,
    )
    before = custody.status()
    prepared = custody.prepare_admission(witness)

    with pytest.raises(
        ReceiptError,
        match="prepared byte capacity is full",
    ):
        custody.prepare_admission(witness)

    custody.discard_prepared_admission(prepared)
    assert custody.status() == before


def test_verified_native_witness_capability_is_bound_to_exact_object() -> None:
    witness, capability = (
        NativeEvidenceCustodyWitness.verified_from_built(
            _boundary("verified-native-object-identity")
        )
    )
    custody = NativeEvidenceCustodyOwner()
    copied_witness = replace(witness)

    with pytest.raises(
        ReceiptError,
        match="changed construction identity",
    ):
        custody.prepare_admission(
            copied_witness,
            verified_capability=capability,
        )

    prepared = custody.prepare_admission(
        witness,
        verified_capability=capability,
    )
    custody.discard_prepared_admission(prepared)


def test_prepared_causal_capability_is_bound_to_owner_held_object() -> None:
    owner = ExactCausalExperienceOwner(
        on_settlement=lambda _settlement: None,
        log_event=lambda *_args, **_kwargs: None,
    )
    settlement = owner.settle(
        _boundary("verified-causal-object-identity"),
        routing_chis=(),
        source_tags=(),
        commit=False,
        reserve=True,
    )
    capability = owner.prepared_transaction_capability(settlement)
    copied_settlement = replace(settlement)

    with pytest.raises(
        ReceiptError,
        match="changed transaction identity",
    ):
        capability.verify_linkage(copied_settlement)
    with pytest.raises(
        ReceiptError,
        match="changed transaction identity",
    ):
        owner.commit_prepared(
            copied_settlement,
            verified_capability=capability,
        )

    owner.discard_prepared(settlement)


def test_source_commitment_rejects_each_changed_l5_sample_field() -> None:
    built = _boundary("source-claim-comparison")
    settlement = ExactCausalExperienceOwner(
        on_settlement=lambda _settlement: None,
        log_event=lambda *_args, **_kwargs: None,
    ).settle(built, routing_chis=(), source_tags=())
    substream = settlement.interpretations[0].substreams[0]
    source_digest = substream.source_evidence_stream_receipt_sha256
    samples = tuple(
        (
            index,
            Fraction(index, 200),
            Fraction.from_float(
                math.sin(2 * math.pi * 8 * index / 200)
            ),
            Fraction(1),
            Fraction(index // 12),
        )
        for index in range(96)
    )

    changed_time = list(samples)
    index, timestamp, signal, relevance, phase = changed_time[1]
    changed_time[1] = (
        index,
        timestamp + Fraction(1, 1000),
        signal,
        relevance,
        phase,
    )
    changed_signal = list(samples)
    index, timestamp, signal, relevance, phase = changed_signal[1]
    changed_signal[1] = (
        index,
        timestamp,
        signal + Fraction(1, 1000),
        relevance,
        phase,
    )
    changed_relevance = list(samples)
    index, timestamp, signal, relevance, phase = changed_relevance[1]
    changed_relevance[1] = (
        index,
        timestamp,
        signal,
        relevance - Fraction(1, 1000),
        phase,
    )
    changed_phase = list(samples)
    index, timestamp, signal, relevance, phase = changed_phase[1]
    changed_phase[1] = (
        index,
        timestamp,
        signal,
        relevance,
        phase + Fraction(1, 1000),
    )

    for changed in (
        changed_time,
        changed_signal,
        changed_relevance,
        changed_phase,
    ):
        assert not substream.matches_source_claim(
            source_evidence_stream_receipt_sha256=source_digest,
            samples=tuple(changed),
        )

    changed_index = list(samples)
    _, timestamp, signal, relevance, phase = changed_index[0]
    changed_index[0] = (1, timestamp, signal, relevance, phase)
    with pytest.raises(ReceiptError, match="indices are not contiguous"):
        substream.matches_source_claim(
            source_evidence_stream_receipt_sha256=source_digest,
            samples=tuple(changed_index),
        )


def test_identical_samples_match_across_assembly_local_source_receipts() -> None:
    owner = ExactCausalExperienceOwner(
        on_settlement=lambda _settlement: None,
        log_event=lambda *_args, **_kwargs: None,
    )
    first = owner.settle(
        _boundary("cross-assembly-one"),
        routing_chis=(),
        source_tags=(),
    ).interpretations[0].substreams[0]
    second = owner.settle(
        _boundary("cross-assembly-two"),
        routing_chis=(),
        source_tags=(),
    ).interpretations[0].substreams[0]
    samples = tuple(
        (
            index,
            Fraction(index, 200),
            Fraction.from_float(
                math.sin(2 * math.pi * 8 * index / 200)
            ),
            Fraction(1),
            Fraction(index // 12),
        )
        for index in range(96)
    )

    assert first.source_evidence_stream_receipt_sha256 != (
        second.source_evidence_stream_receipt_sha256
    )
    assert first.source_sample_commitment_sha256 == (
        second.source_sample_commitment_sha256
    )
    assert first.matches_source_claim(
        source_evidence_stream_receipt_sha256=(
            second.source_evidence_stream_receipt_sha256
        ),
        samples=samples,
    )


def test_v3_settlement_profile_and_claim_shape_are_rejected() -> None:
    settlement = ExactCausalExperienceOwner(
        on_settlement=lambda _settlement: None,
        log_event=lambda *_args, **_kwargs: None,
    ).settle(_boundary("reject-v3"), routing_chis=(), source_tags=())
    raw = json.loads(settlement.receipt_registry.resolve(
        settlement.authority_receipt_sha256
    ))
    raw["schema"] = "guala.exact_causal_experience.settlement.v3"
    for sense in raw["interpretations"]:
        for substream in sense["substreams"]:
            substream.pop("source_evidence_stream_receipt_sha256")
            substream.pop("source_sample_count")
            substream.pop("source_sample_commitment_sha256")
    legacy_payload = json.dumps(
        raw,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    legacy = replace(
        settlement,
        authority_receipt_sha256=receipt_sha256(legacy_payload),
        receipt_registry=ReceiptRegistry.from_payloads(
            profile_payload=(
                b"guala.exact_causal_experience.settlement.profile.v3"
            ),
            receipt_payloads=(legacy_payload,),
        ),
    )

    with pytest.raises(ReceiptError, match="settlement profile changed"):
        legacy.verify()


def _reseal_settlement(settlement, **changes):
    candidate = replace(settlement, **changes)
    payload = causal_experience_settlement_receipt_payload(
        event_id=candidate.event_id,
        structural_fingerprint=candidate.structural_fingerprint,
        assembly_id=candidate.assembly_id,
        source_time_start=candidate.source_time_start,
        source_time_end=candidate.source_time_end,
        interpretations=candidate.interpretations,
        language_events=candidate.language_events,
        native_evidence_witness=candidate.native_evidence_witness,
        routing_chis=candidate.routing_chis,
        source_tags=candidate.source_tags,
        assembly_receipt_sha256=candidate.assembly_receipt_sha256,
    )
    return replace(
        candidate,
        authority_receipt_sha256=receipt_sha256(payload),
        receipt_registry=ReceiptRegistry.from_payloads(
            profile_payload=SETTLEMENT_PROFILE_PAYLOAD,
            receipt_payloads=(
                *(
                    record.payload
                    for record in candidate.native_evidence_witness
                    .receipt_records
                ),
                candidate.native_evidence_witness.authority_payload(),
                payload,
            ),
        ),
    )


def test_verify_rejects_resealed_reduced_or_internally_false_field() -> None:
    settlement = ExactCausalExperienceOwner(
        on_settlement=lambda _settlement: None,
        log_event=lambda *_args, **_kwargs: None,
    ).settle(_boundary("semantic-verification"), routing_chis=(), source_tags=())
    sight = settlement.interpretations[0]
    substream = sight.substreams[0]
    first_tuple = substream.field_tuples[0]

    cases = (
        (
            {"interpretations": tuple(reversed(settlement.interpretations))},
            "six senses in canonical order",
        ),
        (
            {
                "interpretations": (
                    replace(sight, state="unknown"),
                    *settlement.interpretations[1:],
                )
            },
            "unobserved causal sense carries observed field structure",
        ),
        (
            {
                "interpretations": (
                    replace(
                        sight,
                        substreams=(replace(substream, topology_index=1),),
                    ),
                    *settlement.interpretations[1:],
                )
            },
            "topology is not complete and ordered",
        ),
        (
            {
                "interpretations": (
                    replace(
                        sight,
                        substreams=(replace(
                            substream,
                            field_tuples=(replace(
                                first_tuple,
                                fields=tuple(reversed(first_tuple.fields)),
                            ), *substream.field_tuples[1:]),
                        ),),
                    ),
                    *settlement.interpretations[1:],
                )
            },
            "L4 field order changed",
        ),
        (
            {
                "interpretations": (
                    replace(
                        sight,
                        substreams=(replace(
                            substream,
                            field_tuples=(replace(
                                first_tuple,
                                tuple_index=1,
                            ), *substream.field_tuples[1:]),
                        ),),
                    ),
                    *settlement.interpretations[1:],
                )
            },
            "L4 tuple indices are not contiguous",
        ),
        (
            {
                "interpretations": (
                    replace(
                        sight,
                        substreams=(replace(substream, field_tuples=()),),
                    ),
                    *settlement.interpretations[1:],
                )
            },
            "L4 tuple cardinality is invalid",
        ),
        (
            {
                "interpretations": (
                    replace(sight, structural_fingerprint="0" * 64),
                    *settlement.interpretations[1:],
                )
            },
            "causal sense structural fingerprint changed",
        ),
        (
            {"structural_fingerprint": "0" * 64},
            "causal settlement structural fingerprint changed",
        ),
        (
            {"event_id": "0" * 64},
            "causal settlement event identity changed",
        ),
    )

    for changes, message in cases:
        altered = _reseal_settlement(settlement, **changes)
        with pytest.raises(ReceiptError, match=message):
            altered.verify()
