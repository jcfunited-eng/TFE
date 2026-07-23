from __future__ import annotations

import hashlib
import json
import math
import struct
from dataclasses import replace
from fractions import Fraction

import pytest

import dsf_ai_service.substrate.auditory_stream_settlement as joint_module
import dsf_ai_service.substrate.auditory_token_sequence as token_module
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    build_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.auditory_batch_causal_intake import (
    AuditoryBatchCausalIntakeAuthority,
    AuditoryBatchCausalIntakeReceipt,
)
from dsf_ai_service.substrate.auditory_incremental_terminal import (
    AuditoryIncrementalTerminalRegistry,
)
from dsf_ai_service.substrate.auditory_kernel_mount import (
    auditory_kernel_component_inputs,
)
from dsf_ai_service.substrate.auditory_l5 import AuditoryL5Owner
from dsf_ai_service.substrate.auditory_pcm_stream import (
    AuditoryPCMStreamRegistry,
    PCM_SAMPLE_RATE_HZ,
)
from dsf_ai_service.substrate.auditory_reciprocity import (
    AuditoryReciprocityKind,
    AuditoryReciprocityOwner,
)
from dsf_ai_service.substrate.auditory_stream_settlement import (
    bind_auditory_stream_settlement,
)
from dsf_ai_service.substrate.auditory_token_sequence import (
    AuditoryTokenSequenceAuthority,
    AuditoryTokenSequenceReceipt,
    OrderedAuditoryTokenOccurrence,
)
from dsf_ai_service.substrate.auditory_tutor_authority import (
    AuditoryTutorAuthority,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    AuditoryFullFieldStream,
)


SOURCE_EPOCH_NS = 1_000_000_000
LEARNED_SAMPLES = 6_400
TRAILING_SAMPLES = 3_200
INTAKE_KEY = b"auditory-batch-causal-intake-test-key" * 2
TOKEN_KEY = b"auditory-batch-causal-token-test-key" * 2


def _tone(sample_count: int, frequency_hz: int = 440) -> tuple[int, ...]:
    return tuple(
        round(
            8_000
            * math.sin(
                2 * math.pi * frequency_hz * index / PCM_SAMPLE_RATE_HZ
            )
        )
        for index in range(sample_count)
    )


def _pcm(values: tuple[int, ...]) -> bytes:
    return struct.pack(f"<{len(values)}h", *values)


def _two_terminal_signal() -> tuple[int, ...]:
    return (
        (0,) * 3_200
        + _tone(LEARNED_SAMPLES)
        + (0,) * 3_200
        + _tone(LEARNED_SAMPLES)
        + (0,) * TRAILING_SAMPLES
    )


class _MountedStream:
    def __init__(self) -> None:
        self.transport = AuditoryPCMStreamRegistry()
        self.stream_id = self.transport.open()["stream_id"]
        self.cochlea = AuditoryFullFieldStream()
        self.l5 = AuditoryL5Owner(
            log_event=lambda *_args, **_kwargs: None
        )
        self.causal = ExactCausalExperienceOwner(
            on_settlement=lambda _value: None,
            log_event=lambda *_args, **_kwargs: None,
        )

    def mount(
        self,
        pcm_s16le: bytes,
        *,
        sequence: int,
        first_sample_index: int,
        event_boundary: str = "ambient",
    ) -> dict[str, object]:
        accepted = self.transport.accept(
            stream_id=self.stream_id,
            sequence=sequence,
            first_sample_index=first_sample_index,
            sample_rate_hz=PCM_SAMPLE_RATE_HZ,
            source_epoch_start_ns=SOURCE_EPOCH_NS,
            pcm_s16le=pcm_s16le,
        )
        capture, cochlear = self.cochlea.advance(
            accepted.pcm_s16le, accepted.receipt
        )
        epoch = Fraction(SOURCE_EPOCH_NS, 1_000_000_000)
        ports = auditory_kernel_component_inputs(capture, source_anchor=epoch)
        start = accepted.receipt.first_sample_index
        end = accepted.receipt.last_sample_index_exclusive
        built = build_six_sense_full_field(
            assembly_id=f"intake-test-{self.stream_id}-{sequence}",
            source_time_start=epoch + Fraction(start, PCM_SAMPLE_RATE_HZ),
            source_time_end=epoch + Fraction(end, PCM_SAMPLE_RATE_HZ),
            observed_substreams={PhysicalSense.SOUND: ports},
            states={
                sense: (
                    SenseBoundaryState.OBSERVED
                    if sense is PhysicalSense.SOUND
                    else SenseBoundaryState.SENSOR_UNAVAILABLE
                )
                for sense in SENSE_ORDER
            },
        )
        auditory_l5 = self.l5.settle(
            built, event_boundary=event_boundary
        )
        assert auditory_l5 is not None
        causal = self.causal.settle(
            built, routing_chis=(), source_tags=()
        )
        joint = bind_auditory_stream_settlement(
            transport=accepted.receipt,
            cochlear=cochlear,
            auditory_l5=auditory_l5,
            causal_settlement=causal,
        )
        return {
            "pcm_s16le": pcm_s16le,
            "capture": capture,
            "auditory_l5": auditory_l5,
            "transport": accepted.receipt,
            "cochlear": cochlear,
            "joint_settlement": joint,
            "causal_settlement": causal,
        }


def _learned_owner() -> AuditoryReciprocityOwner:
    mounted = _MountedStream()
    taught = mounted.mount(
        _pcm(_tone(LEARNED_SAMPLES)),
        sequence=0,
        first_sample_index=0,
        event_boundary="utterance",
    )["auditory_l5"]
    owner = AuditoryReciprocityOwner(
        log_event=lambda *_args, **_kwargs: None,
        tutor_authority=AuditoryTutorAuthority.unrequired(),
    )
    owner.teach(
        taught,
        kind=AuditoryReciprocityKind.SPOKEN_FORM,
        tutor_label="must-never-enter-intake",
    )
    return owner


def _claim_sequence(
    registry: AuditoryIncrementalTerminalRegistry,
    advance,
    tokens: AuditoryTokenSequenceAuthority,
):
    batch = registry.materialize_batch(advance)
    claim = registry.claim_batch(batch)
    admitted = tuple(
        tokens.admit(entry.event, entry.auditory_l5)
        for entry in batch.entries
    )
    return claim, tokens.settle_sequence(admitted)


def _same_window():
    registry = AuditoryIncrementalTerminalRegistry(
        reciprocity_owner=_learned_owner(),
        terminal_authority_capacity=2,
    )
    mounted = _MountedStream()
    authorities = mounted.mount(
        _pcm(_two_terminal_signal()),
        sequence=0,
        first_sample_index=0,
    )
    advance = registry.advance(**{
        key: authorities[key]
        for key in (
            "pcm_s16le",
            "capture",
            "auditory_l5",
            "transport",
            "cochlear",
            "joint_settlement",
        )
    })
    tokens = AuditoryTokenSequenceAuthority(authority_secret=TOKEN_KEY)
    claim, sequence = _claim_sequence(registry, advance, tokens)
    return {
        "registry": registry,
        "claim": claim,
        "advance": advance,
        "tokens": tokens,
        "sequence": sequence,
        "joint": authorities["joint_settlement"],
        "settlement": authorities["causal_settlement"],
    }


def _resign_sequence(
    sequence: AuditoryTokenSequenceReceipt,
    authority: AuditoryTokenSequenceAuthority,
    occurrences: tuple[OrderedAuditoryTokenOccurrence, ...],
    *,
    stream_id: str | None = None,
) -> AuditoryTokenSequenceReceipt:
    actual_stream = stream_id or sequence.stream_id
    base = {
        "binding_state_sha256": sequence.binding_state_sha256,
        "occurrences": [value.as_record() for value in occurrences],
        "schema": token_module.TOKEN_SEQUENCE_SCHEMA,
        "stream_id": actual_stream,
    }
    sequence_id = token_module._digest(base)
    provisional = AuditoryTokenSequenceReceipt(
        sequence_id=sequence_id,
        stream_id=actual_stream,
        binding_state_sha256=sequence.binding_state_sha256,
        occurrences=occurrences,
        authority_hmac_sha256="",
    )
    return replace(
        provisional,
        authority_hmac_sha256=token_module._hmac(
            authority._sequence_key, provisional.payload()
        ),
    )


def _bind(authority, values, **overrides):
    arguments = {
        "registry": values["registry"],
        "claim": values["claim"],
        "advance": values["advance"],
        "token_authority": values["tokens"],
        "sequence": values["sequence"],
        "joint_settlement": values["joint"],
        "causal_settlement": values["settlement"],
    }
    arguments.update(overrides)
    return authority.bind(**arguments)


def test_live_batch_intake_is_exact_stateless_and_contains_no_semantic_data(
) -> None:
    values = _same_window()
    authority = AuditoryBatchCausalIntakeAuthority(
        authority_key=INTAKE_KEY
    )
    first = _bind(authority, values)
    assert first.state == "unique"
    assert first.reason == "causal_intake_authenticated"
    assert first.intake is not None
    authority.verify_for_episode(
        intake=first.intake,
        sequence=values["sequence"],
        settlement=values["settlement"],
    )
    assert authority.retained_intake_count == 0
    for _index in range(32):
        repeated = _bind(authority, values)
        assert repeated.intake == first.intake
        assert authority.retained_intake_count == 0

    record = first.intake.as_record()
    restored = AuditoryBatchCausalIntakeReceipt.from_record(record)
    authority.verify_intake(restored)
    encoded = json.dumps(record, sort_keys=True).lower()
    assert all(
        forbidden not in encoded
        for forbidden in (
            "tutor_label",
            "token_form",
            "token_candidates",
            "transcript",
            "recognized_text",
            "source_tags",
            "routing_chis",
            "atlas",
        )
    )


@pytest.mark.parametrize(
    "field",
    (
        "advance_authority_receipt_sha256",
        "batch_authority_receipt_sha256",
        "token_sequence_id",
        "joint_settlement_authority_receipt_sha256",
        "causal_settlement_authority_receipt_sha256",
        "authority_hmac_sha256",
    ),
)
def test_persistent_intake_receipt_rejects_every_authority_link_tamper(
    field: str,
) -> None:
    values = _same_window()
    authority = AuditoryBatchCausalIntakeAuthority(
        authority_key=INTAKE_KEY
    )
    intake = _bind(authority, values).intake
    changed = replace(intake, **{field: "0" * 64})
    with pytest.raises(ValueError, match="identity changed|authority changed"):
        authority.verify_intake(changed)


def test_bind_rejects_occurrence_order_field_time_stream_and_advance_changes(
) -> None:
    values = _same_window()
    authority = AuditoryBatchCausalIntakeAuthority(
        authority_key=INTAKE_KEY
    )
    sequence = values["sequence"]
    tokens = values["tokens"]

    reversed_sequence = _resign_sequence(
        sequence,
        tokens,
        tuple(replace(value, ordinal=index) for index, value in enumerate(
            reversed(sequence.occurrences)
        )),
    )
    with pytest.raises(ValueError, match="physical order changed"):
        _bind(authority, values, sequence=reversed_sequence)

    changed_l5 = replace(
        sequence.occurrences[0],
        l5_authority_receipt_sha256="0" * 64,
    )
    changed_sequence = _resign_sequence(
        sequence,
        tokens,
        (changed_l5, *sequence.occurrences[1:]),
    )
    with pytest.raises(ValueError, match="batch and token occurrence disagree"):
        _bind(authority, values, sequence=changed_sequence)

    changed_time = replace(
        sequence.occurrences[0],
        source_time_start=sequence.occurrences[0].source_time_start
        + Fraction(1, PCM_SAMPLE_RATE_HZ),
        source_time_end=sequence.occurrences[0].source_time_end
        + Fraction(1, PCM_SAMPLE_RATE_HZ),
    )
    timed_sequence = _resign_sequence(
        sequence,
        tokens,
        (changed_time, *sequence.occurrences[1:]),
    )
    with pytest.raises(ValueError, match="batch and token occurrence disagree"):
        _bind(authority, values, sequence=timed_sequence)

    other_stream = _resign_sequence(
        sequence,
        tokens,
        sequence.occurrences,
        stream_id="another-stream",
    )
    with pytest.raises(ValueError, match="crosses stream epochs"):
        _bind(authority, values, sequence=other_stream)

    changed_advance = replace(
        values["advance"], authority_receipt_sha256="0" * 64
    )
    with pytest.raises(ValueError, match="advance receipt was altered"):
        _bind(authority, values, advance=changed_advance)


def test_bind_rejects_wrong_joint_evidence_assembly_and_causal_settlement(
) -> None:
    values = _same_window()
    authority = AuditoryBatchCausalIntakeAuthority(
        authority_key=INTAKE_KEY
    )
    joint = values["joint"]
    wrong_sequence = replace(
        joint,
        sequence=joint.sequence + 1,
        prior_transport_receipt_sha256="a" * 64,
        prior_cochlear_state_receipt_sha256="b" * 64,
        authority_receipt_sha256="0" * 64,
    )
    wrong_sequence = replace(
        wrong_sequence,
        authority_receipt_sha256=joint_module._digest(
            wrong_sequence.payload()
        ),
    )
    with pytest.raises(ValueError, match="lacks current joint settlement evidence"):
        _bind(authority, values, joint_settlement=wrong_sequence)

    wrong_assembly = replace(
        joint,
        assembly_id="another-assembly",
        authority_receipt_sha256="0" * 64,
    )
    wrong_assembly = replace(
        wrong_assembly,
        authority_receipt_sha256=joint_module._digest(
            wrong_assembly.payload()
        ),
    )
    with pytest.raises(ValueError, match="joint settlement changed"):
        _bind(authority, values, joint_settlement=wrong_assembly)

    other = _MountedStream().mount(
        _pcm(_tone(LEARNED_SAMPLES)),
        sequence=0,
        first_sample_index=0,
    )["causal_settlement"]
    with pytest.raises(ValueError, match="joint settlement changed"):
        _bind(authority, values, causal_settlement=other)


def test_cross_chunk_terminal_is_explicitly_not_forced_into_current_window(
) -> None:
    registry = AuditoryIncrementalTerminalRegistry(
        reciprocity_owner=_learned_owner()
    )
    mounted = _MountedStream()
    signal = (0,) * 3_200 + _tone(LEARNED_SAMPLES) + (0,) * TRAILING_SAMPLES
    cut = 5_000
    first_authorities = mounted.mount(
        _pcm(signal[:cut]), sequence=0, first_sample_index=0
    )
    first = registry.advance(**{
        key: first_authorities[key]
        for key in (
            "pcm_s16le",
            "capture",
            "auditory_l5",
            "transport",
            "cochlear",
            "joint_settlement",
        )
    })
    assert not first.released_terminals
    second_authorities = mounted.mount(
        _pcm(signal[cut:]), sequence=1, first_sample_index=cut
    )
    second = registry.advance(**{
        key: second_authorities[key]
        for key in (
            "pcm_s16le",
            "capture",
            "auditory_l5",
            "transport",
            "cochlear",
            "joint_settlement",
        )
    })
    assert len(second.released_terminals) == 1
    tokens = AuditoryTokenSequenceAuthority(authority_secret=TOKEN_KEY)
    claim, sequence = _claim_sequence(registry, second, tokens)
    result = AuditoryBatchCausalIntakeAuthority(
        authority_key=INTAKE_KEY
    ).bind(
        registry=registry,
        claim=claim,
        advance=second,
        token_authority=tokens,
        sequence=sequence,
        joint_settlement=second_authorities["joint_settlement"],
        causal_settlement=second_authorities["causal_settlement"],
    )
    assert result.state == "unknown"
    assert result.reason == "multi_settlement_window_required"
    assert result.intake is None
    assert registry.verify_batch_claim(claim) == claim.batch
