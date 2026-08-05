from __future__ import annotations

import copy
import math
import struct
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from fractions import Fraction

import pytest

import dsf_ai_service.substrate.auditory_incremental_terminal as terminal_module
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    build_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.auditory_incremental_terminal import (
    AuditoryIncrementalTerminalBatch,
    AuditoryIncrementalTerminalRegistry,
    AuditoryIncrementalTerminalEvent,
    AuditoryIncrementalStatus,
    AuditoryIncrementalTerminalOwner,
)
from dsf_ai_service.substrate.auditory_kernel_mount import (
    AUDITORY_KERNEL_COMPONENT_COUNT,
    auditory_kernel_component_inputs,
)
from dsf_ai_service.substrate.auditory_l5 import AuditoryL5Owner
from dsf_ai_service.substrate.auditory_pcm_stream import (
    AuditoryPCMStreamRegistry,
    PCM_SAMPLE_RATE_HZ,
)
from dsf_ai_service.substrate.auditory_reciprocity import (
    AuditoryRecognitionState,
    AuditoryReciprocityKind,
    AuditoryReciprocityOwner,
)
from dsf_ai_service.substrate.auditory_stream_settlement import (
    bind_auditory_stream_settlement,
)
from dsf_ai_service.substrate.auditory_tutor_authority import (
    AuditoryTutorAuthority,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    OBSERVATION_HOP_SAMPLES,
    AuditoryFullFieldStream,
)


SOURCE_EPOCH_NS = 1_000_000_000
LEARNED_SAMPLES = 6_400
TRAILING_SAMPLES = 3_200


def _tone_values(sample_count: int, frequency_hz: int) -> tuple[int, ...]:
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


def _learned_owner(
    *, labels: tuple[str, ...] = ("learned-form",)
) -> AuditoryReciprocityOwner:
    mounted = _MountedStream()
    taught = mounted.mount(
        _pcm(_tone_values(LEARNED_SAMPLES, 440)),
        sequence=0,
        first_sample_index=0,
        event_boundary="utterance",
    )["auditory_l5"]
    owner = AuditoryReciprocityOwner(
        log_event=lambda *_args, **_kwargs: None,
        tutor_authority=AuditoryTutorAuthority.unrequired(),
    )
    for label in labels:
        owner.teach(
            taught,
            kind=AuditoryReciprocityKind.SPOKEN_FORM,
            tutor_label=label,
        )
    return owner


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
        self.last_built = None
        self.last_causal = None

    def mount(
        self,
        pcm_s16le: bytes,
        *,
        sequence: int,
        first_sample_index: int,
        event_boundary: str = "ambient",
    ):
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
        ports = auditory_kernel_component_inputs(
            capture,
            source_anchor=epoch,
        )
        assert len(ports) == AUDITORY_KERNEL_COMPONENT_COUNT
        start = accepted.receipt.first_sample_index
        end = accepted.receipt.last_sample_index_exclusive
        built = build_six_sense_full_field(
            assembly_id=f"incremental-test-{self.stream_id}-{sequence}",
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
        self.last_built = built
        auditory_l5 = self.l5.settle(
            built, event_boundary=event_boundary
        )
        assert auditory_l5 is not None
        causal = self.causal.settle(
            built,
            routing_chis=(),
            source_tags=(),
        )
        self.last_causal = causal
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
        }


def test_incremental_frames_consume_provider_settled_phase_advance() -> None:
    mounted = _MountedStream().mount(
        _pcm(_tone_values(LEARNED_SAMPLES, 440)),
        sequence=0,
        first_sample_index=0,
    )
    frames = AuditoryIncrementalTerminalOwner._frame_values(
        mounted["capture"],
        mounted["auditory_l5"],
    )

    assert len(frames) == mounted["capture"].frame_count
    for frame_index, frame in enumerate(frames):
        assert frame[2] == tuple(
            channel.carrier_phase_advance_turns[frame_index]
            for channel in mounted["capture"].channels
        )
        assert frame[3] == tuple(
            channel.carrier_phase_advance_nyquist_fraction[frame_index]
            for channel in mounted["capture"].channels
        )
    assert any(
        advance != absolute
        for channel in mounted["capture"].channels
        for advance, absolute in zip(
            channel.carrier_phase_advance_turns,
            channel.carrier_phase_turns,
            strict=True,
        )
    )


def test_full_gate_establishes_only_event_local_phase_genesis() -> None:
    offset = 3_200
    mounted = _MountedStream().mount(
        _pcm(
            (0,) * offset
            + _tone_values(LEARNED_SAMPLES, 440)
            + (0,) * OBSERVATION_HOP_SAMPLES
        ),
        sequence=0,
        first_sample_index=0,
    )
    values = AuditoryIncrementalTerminalOwner._frame_values(
        mounted["capture"],
        mounted["auditory_l5"],
    )
    selected = tuple(
        terminal_module._Frame(*value)
        for value in values
        if offset < value[0] <= offset + LEARNED_SAMPLES
    )
    assert selected
    assert any(value != 0.0 for value in selected[0].phase_advance)

    for channel_index in range(len(mounted["capture"].channels)):
        advances, normalized = terminal_module._event_local_phase_component(
            selected,
            channel_index,
        )
        assert advances[0] == 0.0
        assert normalized[0] == 0.0
        assert advances[1:] == tuple(
            frame.phase_advance[channel_index] for frame in selected[1:]
        )
        assert normalized[1:] == tuple(
            frame.phase_advance_nyquist_fraction[channel_index]
            for frame in selected[1:]
        )


def test_incremental_owner_rejects_legacy_reciprocity_v4(
    monkeypatch,
) -> None:
    owner = _learned_owner()
    monkeypatch.setattr(
        owner,
        "snapshot",
        lambda: {
            "schema": (
                terminal_module.LEGACY_AUDITORY_RECIPROCITY_SNAPSHOT_SCHEMA
            )
        },
    )

    with pytest.raises(ValueError, match="rejects reciprocity v4"):
        AuditoryIncrementalTerminalOwner(reciprocity_owner=owner)


def test_incremental_owner_requires_both_complete_l4_banks(
    monkeypatch,
) -> None:
    owner = _learned_owner()
    snapshot = copy.deepcopy(owner.snapshot())
    snapshot["classes"][0]["branches"][0][
        "carrier_phase_advance_l4_field_tuples"
    ][0] = []
    monkeypatch.setattr(owner, "snapshot", lambda: snapshot)

    with pytest.raises(ValueError, match="phase L4 channel 0 is incomplete"):
        AuditoryIncrementalTerminalOwner(reciprocity_owner=owner)


def _run(
    *,
    offset_samples: int,
    cuts: tuple[int, ...],
    reciprocity: AuditoryReciprocityOwner | None = None,
):
    learned = reciprocity or _learned_owner()
    terminal = AuditoryIncrementalTerminalOwner(
        reciprocity_owner=learned
    )
    signal = (
        (0,) * offset_samples
        + _tone_values(LEARNED_SAMPLES, 440)
        + (0,) * TRAILING_SAMPLES
    )
    assert cuts[-1] == len(signal)
    mounted = _MountedStream()
    results = []
    start = 0
    for sequence, end in enumerate(cuts):
        chunk = _pcm(signal[start:end])
        authorities = mounted.mount(
            chunk,
            sequence=sequence,
            first_sample_index=start,
        )
        results.append(terminal.advance(**authorities))
        start = end
    replies = [
        result.reply_candidate for result in results
        if result.reply_candidate is not None
    ]
    return terminal, results, replies


def test_same_terminal_is_found_at_137_seconds_across_chunk_partitions() -> None:
    offset = 21_920
    total = offset + LEARNED_SAMPLES + TRAILING_SAMPLES
    variants = (
        (total,),
        (5_003, 12_892, total),
        (8_321, 17_777, 24_111, total),
    )
    extents = []
    for cuts in variants:
        _owner, _results, replies = _run(
            offset_samples=offset,
            cuts=cuts,
        )
        assert len(replies) == 1
        event = replies[0]
        event.verify()
        assert event.recognition_occurrence is not None
        event.recognition_occurrence.verify()
        assert (
            event.recognition_occurrence.l5_authority_receipt_sha256
            == event.l5_authority_receipt_sha256
        )
        assert len(
            event.recognition_occurrence
            .candidate_class_authority_receipts
        ) == 1
        assert (
            event.recognition_occurrence
            .selected_class_authority_receipt_sha256
            == event.recognition_occurrence
            .candidate_class_authority_receipts[0]
        )
        extents.append((
            event.source_sample_start,
            event.source_sample_end,
            event.tutor_label,
        ))
    assert extents == [(offset, offset + LEARNED_SAMPLES, "learned-form")] * 3


def _two_terminal_signal() -> tuple[int, ...]:
    return (
        (0,) * 3_200
        + _tone_values(LEARNED_SAMPLES, 440)
        + (0,) * 3_200
        + _tone_values(LEARNED_SAMPLES, 440)
        + (0,) * TRAILING_SAMPLES
    )


def test_one_advance_keeps_causally_changed_repeat_distinct() -> None:
    owner = AuditoryIncrementalTerminalOwner(
        reciprocity_owner=_learned_owner()
    )
    mounted = _MountedStream()
    result = owner.advance(**mounted.mount(
        _pcm(_two_terminal_signal()),
        sequence=0,
        first_sample_index=0,
    ))

    result.verify()
    assert result.status is AuditoryIncrementalStatus.RELEASED_UNIQUE
    assert result.reply_candidate is result.released_terminals[0]
    assert len(result.released_terminals) == 1
    assert tuple(
        (event.source_sample_start, event.source_sample_end)
        for event in result.released_terminals
    ) == ((3_200, 3_200 + LEARNED_SAMPLES),)
    assert all(
        event.recognition_occurrence is not None
        and event.recognition_occurrence.state
        is AuditoryRecognitionState.UNIQUE
        for event in result.released_terminals
    )
    assert len(owner._released_full_fields) == 1


def test_rephased_repeat_does_not_erase_prior_cochlear_state() -> None:
    first_start = 3_200
    second_start = first_start + LEARNED_SAMPLES + 3_231
    signal = (
        (0,) * first_start
        + _tone_values(LEARNED_SAMPLES, 440)
        + (0,) * 3_231
        + _tone_values(LEARNED_SAMPLES, 440)
        + (0,) * TRAILING_SAMPLES
    )
    owner = AuditoryIncrementalTerminalOwner(
        reciprocity_owner=_learned_owner()
    )
    mounted = _MountedStream()

    result = owner.advance(**mounted.mount(
        _pcm(signal),
        sequence=0,
        first_sample_index=0,
    ))

    result.verify()
    assert result.status is AuditoryIncrementalStatus.RELEASED_UNIQUE
    terminals = tuple(
        (
            event.source_sample_start,
            event.source_sample_end,
            event.tutor_label,
        )
        for event in result.released_terminals
    )
    assert terminals == (
        (
            first_start,
            first_start + LEARNED_SAMPLES,
            "learned-form",
        ),
    )
    assert all(event[0] != second_start for event in terminals)


def test_rephase_search_cannot_turn_an_unknown_later_sound_into_a_terminal(
) -> None:
    first_start = 3_200
    second_start = first_start + LEARNED_SAMPLES + 3_231
    signal = (
        (0,) * first_start
        + _tone_values(LEARNED_SAMPLES, 440)
        + (0,) * 3_231
        + _tone_values(LEARNED_SAMPLES, 1_700)
        + (0,) * TRAILING_SAMPLES
    )
    owner = AuditoryIncrementalTerminalOwner(
        reciprocity_owner=_learned_owner()
    )
    mounted = _MountedStream()

    result = owner.advance(**mounted.mount(
        _pcm(signal),
        sequence=0,
        first_sample_index=0,
    ))

    result.verify()
    assert tuple(
        (event.source_sample_start, event.source_sample_end)
        for event in result.released_terminals
    ) == ((first_start, first_start + LEARNED_SAMPLES),)
    assert all(
        event.source_sample_start != second_start
        for event in result.released_terminals
    )


def test_registry_issues_only_the_verified_continuous_field() -> None:
    registry = AuditoryIncrementalTerminalRegistry(
        reciprocity_owner=_learned_owner(),
        terminal_authority_capacity=2,
    )
    mounted = _MountedStream()
    result = registry.advance(**mounted.mount(
        _pcm(_two_terminal_signal()),
        sequence=0,
        first_sample_index=0,
    ))

    assert len(result.released_terminals) == 1
    assert registry.status()["issued_terminal_authorities"] == 1
    assert registry._authority_order == [
        event.event_id for event in result.released_terminals
    ]
    batch = registry.materialize_batch(result)
    assert isinstance(batch, AuditoryIncrementalTerminalBatch)
    batch.verify()
    assert tuple(entry.event for entry in batch.entries) == (
        result.released_terminals
    )
    assert tuple(
        entry.auditory_l5.authority_receipt_sha256
        for entry in batch.entries
    ) == tuple(
        event.l5_authority_receipt_sha256
        for event in result.released_terminals
    )
    for entry in batch.entries:
        assert len(entry.auditory_l5.channels) == 16
        assert all(
            channel.pressure.l4_field_tuples
            and channel.carrier_phase_advance.l4_field_tuples
            for channel in entry.auditory_l5.channels
        )

    before = (
        registry.authority_counts(),
        tuple(registry._issued.items()),
        tuple(registry._authority_order),
        registry.batch_claim_count(),
    )
    assert registry.materialize_batch(result) == batch
    other_field = _MountedStream().mount(
        _pcm(_tone_values(LEARNED_SAMPLES, 1_700)),
        sequence=0,
        first_sample_index=0,
        event_boundary="utterance",
    )["auditory_l5"]
    mismatched = replace(
        batch,
        entries=(
            replace(
                batch.entries[0],
                auditory_l5=other_field,
            ),
        ),
    )
    with pytest.raises(ValueError, match="terminal and full field disagree"):
        registry.claim_batch(mismatched)
    tampered = replace(batch, authority_receipt_sha256="0" * 64)
    with pytest.raises(ValueError, match="batch receipt was altered"):
        registry.claim_batch(tampered)
    unauthenticated = replace(batch, authority_hmac_sha256="0" * 64)
    with pytest.raises(ValueError, match="owner authentication changed"):
        registry.claim_batch(unauthenticated)
    assert (
        registry.authority_counts(),
        tuple(registry._issued.items()),
        tuple(registry._authority_order),
        registry.batch_claim_count(),
    ) == before

    def attempt_claim():
        try:
            return registry.claim_batch(batch)
        except ValueError as error:
            return error

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = tuple(
            executor.map(lambda _value: attempt_claim(), range(2))
        )
    claims = tuple(
        value for value in outcomes if not isinstance(value, Exception)
    )
    failures = tuple(
        value for value in outcomes if isinstance(value, Exception)
    )
    assert len(claims) == 1
    assert len(failures) == 1
    assert isinstance(failures[0], ValueError)
    assert registry.verify_batch_claim(claims[0]) == batch
    assert registry.authority_counts() == {
        "issued_terminal_authorities": 0,
        "in_flight_terminal_authorities": 1,
    }
    assert registry.batch_claim_count() == 1

    registry.rollback_batch(claims[0])
    for _index in range(8):
        repeated = registry.claim_batch(batch)
        registry.rollback_batch(repeated)
        assert registry.authority_counts() == {
            "issued_terminal_authorities": 1,
            "in_flight_terminal_authorities": 0,
        }
        assert registry.batch_claim_count() == 0
        assert registry._authority_order == [
            entry.event.event_id for entry in batch.entries
        ]

    claim = registry.claim_batch(batch)

    def fail_commit() -> None:
        raise RuntimeError("downstream settlement failed")

    with pytest.raises(RuntimeError, match="downstream settlement failed"):
        registry.consume_batch(claim, commit_batch=fail_commit)
    assert registry.verify_batch_claim(claim) == batch
    assert registry.consume_batch(claim) == batch
    assert registry.authority_counts() == {
        "issued_terminal_authorities": 0,
        "in_flight_terminal_authorities": 0,
    }
    assert registry._authority_order == []
    assert registry.batch_claim_count() == 0


def test_registry_capacity_admits_one_verified_continuous_field(
) -> None:
    registry = AuditoryIncrementalTerminalRegistry(
        reciprocity_owner=_learned_owner(),
        terminal_authority_capacity=1,
    )
    mounted = _MountedStream()
    authorities = mounted.mount(
        _pcm(_two_terminal_signal()),
        sequence=0,
        first_sample_index=0,
    )

    result = registry.advance(**authorities)
    status = registry.status()
    assert len(result.released_terminals) == 1
    assert status["issued_terminal_authorities"] == 1
    assert status["in_flight_terminal_authorities"] == 0
    assert status["active_streams"] == 1


def test_same_terminal_is_found_at_642_seconds_across_chunk_partitions() -> None:
    offset = 102_720
    total = offset + LEARNED_SAMPLES + TRAILING_SAMPLES
    variants = (
        (total,),
        (31_337, 79_111, total),
        (22_403, 54_719, 91_027, total),
    )
    for cuts in variants:
        owner, _results, replies = _run(
            offset_samples=offset,
            cuts=cuts,
        )
        assert len(replies) == 1
        assert (
            replies[0].source_sample_start,
            replies[0].source_sample_end,
        ) == (offset, offset + LEARNED_SAMPLES)
        assert owner.retained_sample_count <= 8 * PCM_SAMPLE_RATE_HZ


def test_music_and_noise_do_not_create_reply_candidates() -> None:
    for values in (
        _tone_values(16_000, 1_700),
        tuple(((index * 7_919) % 16_001) - 8_000 for index in range(16_000)),
    ):
        learned = _learned_owner()
        terminal = AuditoryIncrementalTerminalOwner(
            reciprocity_owner=learned
        )
        mounted = _MountedStream()
        result = terminal.advance(**mounted.mount(
            _pcm(values), sequence=0, first_sample_index=0
        ))
        assert result.reply_candidate is None
        assert terminal.close_stream().reply_candidate is None


def test_ambiguous_full_field_gate_releases_nothing() -> None:
    reciprocity = _learned_owner(labels=("first", "second"))
    offset = 21_920
    total = offset + LEARNED_SAMPLES + TRAILING_SAMPLES
    owner, results, replies = _run(
        offset_samples=offset,
        cuts=(7_333, 19_001, total),
        reciprocity=reciprocity,
    )
    assert replies == []
    assert any(
        result.status is AuditoryIncrementalStatus.AMBIGUOUS
        for result in results
    )
    assert owner.close_stream().reply_candidate is None


def test_discontinuity_discards_provisional_terminal() -> None:
    learned = _learned_owner()
    terminal = AuditoryIncrementalTerminalOwner(reciprocity_owner=learned)
    first_stream = _MountedStream()
    learned_pcm = _pcm(_tone_values(LEARNED_SAMPLES, 440))
    first = terminal.advance(**first_stream.mount(
        learned_pcm,
        sequence=0,
        first_sample_index=0,
    ))
    assert first.status is AuditoryIncrementalStatus.CONTINUING
    assert first.reply_candidate is None

    second_stream = _MountedStream()
    second = terminal.advance(**second_stream.mount(
        _pcm((0,) * 1_600),
        sequence=0,
        first_sample_index=0,
    ))
    assert second.status is AuditoryIncrementalStatus.DISCONTINUITY
    assert second.reply_candidate is None
    assert terminal.close_stream().reply_candidate is None


def test_tracker_overflow_is_typed_indeterminate_and_releases_nothing() -> None:
    learned = _learned_owner(labels=("first", "second"))
    terminal = AuditoryIncrementalTerminalOwner(
        reciprocity_owner=learned,
        max_active_trackers=1,
    )
    mounted = _MountedStream()
    result = terminal.advance(**mounted.mount(
        _pcm(_tone_values(1_600, 440)),
        sequence=0,
        first_sample_index=0,
    ))
    assert result.status is AuditoryIncrementalStatus.INDETERMINATE_RESOURCE
    assert result.reply_candidate is None
    assert terminal.active_tracker_count == 0


def test_exact_structural_closure_does_not_repeat_the_full_field_gate(
    monkeypatch,
) -> None:
    learned = _learned_owner()
    terminal = AuditoryIncrementalTerminalOwner(reciprocity_owner=learned)
    mounted = _MountedStream()
    offset = 21_920
    signal = (
        (0,) * offset
        + _tone_values(LEARNED_SAMPLES, 440)
        + (0,) * TRAILING_SAMPLES
    )
    full_gate_calls = []
    full_gate = terminal._full_gate

    def counted_full_gate(start, end, *, max_work):
        full_gate_calls.append((start, end, max_work))
        return full_gate(start, end, max_work=max_work)

    monkeypatch.setattr(terminal, "_full_gate", counted_full_gate)
    monkeypatch.setattr(
        terminal_module,
        "MAX_REACHABILITY_CELLS_PER_RECOGNITION",
        2_000,
    )
    monkeypatch.setattr(
        terminal_module,
        "MAX_FULL_GATE_WORK_PER_ADVANCE",
        2_000,
    )
    result = terminal.advance(**mounted.mount(
        _pcm(signal), sequence=0, first_sample_index=0
    ))

    assert [value[:2] for value in full_gate_calls] == [
        (offset, offset + LEARNED_SAMPLES),
    ]
    assert full_gate_calls[0][2] == 2_000
    assert result.status is AuditoryIncrementalStatus.RELEASED_UNIQUE
    assert result.reply_candidate is not None
    assert terminal.active_tracker_count == 0
    assert terminal.close_stream().reply_candidate is None


class _NativeProposalStub:
    def __init__(self, spans, active_starts=()):
        self.spans = list(spans)
        self._active_starts = set(active_starts)

    def step(self, *_args):
        return (
            list(self.spans),
            [],
            False,
            False,
            0,
            len(self._active_starts),
            sorted(self._active_starts),
        )

    @property
    def active_starts(self):
        return sorted(self._active_starts)

    @property
    def active_tracker_count(self):
        return len(self._active_starts)

    def discard_starts(self, starts):
        self._active_starts.difference_update(starts)

    def retain_at_or_after(self, boundary):
        self._active_starts = {
            start for start in self._active_starts if start >= boundary
        }

    def clear(self):
        self._active_starts.clear()


def _pending_terminal(start, end, label):
    mounted = _MountedStream().mount(
        _pcm(_tone_values(LEARNED_SAMPLES, 440)),
        sequence=0,
        first_sample_index=0,
        event_boundary="utterance",
    )
    auditory_l5 = mounted["auditory_l5"]
    return terminal_module._PendingTerminal(
        start=start,
        end=end,
        tutor_label=label,
        structural_fingerprint=auditory_l5.structural_fingerprint,
        l5_authority_receipt_sha256=(
            auditory_l5.authority_receipt_sha256
        ),
        transport_receipt_sha256s=("3" * 64,),
        cochlear_receipt_sha256s=("4" * 64,),
        joint_settlement_receipt_sha256s=("5" * 64,),
        auditory_l5=auditory_l5,
    )


def test_same_completion_requires_every_full_field_candidate(monkeypatch) -> None:
    terminal = AuditoryIncrementalTerminalOwner(
        reciprocity_owner=_learned_owner()
    )
    terminal._native_proposals = _NativeProposalStub(
        ((0, LEARNED_SAMPLES), (160, LEARNED_SAMPLES)),
        active_starts=(0, 160),
    )
    calls = []

    def full_gate(start, end, *, max_work):
        calls.append((start, end))
        assert max_work >= 1
        return (
            terminal_module.AuditoryRecognitionState.UNIQUE,
            _pending_terminal(start, end, f"identity-{start}"),
            1,
        )

    monkeypatch.setattr(terminal, "_full_gate", full_gate)
    chosen, ambiguous, resource = terminal._process_frame(
        LEARNED_SAMPLES,
        (1.0,) * 16,
        (0.0,) * 16,
        terminal_module._AdvanceFullGateWorkLedger(
            reachability_limit=2,
            field_sample_limit=(
                2
                * LEARNED_SAMPLES
                // OBSERVATION_HOP_SAMPLES
                * AUDITORY_KERNEL_COMPONENT_COUNT
            ),
        ),
    )

    assert calls == [(0, LEARNED_SAMPLES), (160, LEARNED_SAMPLES)]
    assert chosen is None
    assert ambiguous is False
    assert resource is False


def test_overlapping_identity_cannot_be_preempted_by_proposal_order(
        monkeypatch) -> None:
    terminal = AuditoryIncrementalTerminalOwner(
        reciprocity_owner=_learned_owner()
    )
    terminal._pending[0] = _pending_terminal(0, LEARNED_SAMPLES, "first")
    terminal._native_proposals = _NativeProposalStub(
        ((0, LEARNED_SAMPLES + 160), (160, LEARNED_SAMPLES + 160)),
        active_starts=(160,),
    )
    calls = []

    def full_gate(start, end, *, max_work):
        calls.append((start, end))
        assert max_work >= 1
        if start == 0:
            return terminal_module.AuditoryRecognitionState.UNKNOWN, None, 1
        return (
            terminal_module.AuditoryRecognitionState.UNIQUE,
            _pending_terminal(start, end, "second"),
            1,
        )

    monkeypatch.setattr(terminal, "_full_gate", full_gate)
    chosen, ambiguous, resource = terminal._process_frame(
        LEARNED_SAMPLES + 160,
        (1.0,) * 16,
        (0.0,) * 16,
        terminal_module._AdvanceFullGateWorkLedger(
            reachability_limit=2,
            field_sample_limit=(
                (
                    LEARNED_SAMPLES // OBSERVATION_HOP_SAMPLES
                    + (LEARNED_SAMPLES + OBSERVATION_HOP_SAMPLES)
                    // OBSERVATION_HOP_SAMPLES
                )
                * AUDITORY_KERNEL_COMPONENT_COUNT
            ),
        ),
    )

    assert calls == [
        (0, LEARNED_SAMPLES + 160),
        (160, LEARNED_SAMPLES + 160),
    ]
    assert chosen is None
    assert ambiguous is True
    assert resource is False
    assert terminal._pending == {}


def test_zero_reachability_matches_cannot_bypass_field_rebuild_boundary(
        monkeypatch) -> None:
    terminal = AuditoryIncrementalTerminalOwner(
        reciprocity_owner=_learned_owner()
    )
    terminal._native_proposals = _NativeProposalStub(
        ((0, LEARNED_SAMPLES), (160, LEARNED_SAMPLES)),
        active_starts=(0, 160),
    )
    calls = []

    def exact_full_gate(start, end, *, max_work):
        calls.append((start, end, max_work))
        return (
            terminal_module.AuditoryRecognitionState.UNIQUE,
            _pending_terminal(start, end, "same-identity"),
            0,
        )

    monkeypatch.setattr(terminal, "_full_gate", exact_full_gate)
    one_field = (
        LEARNED_SAMPLES
        // OBSERVATION_HOP_SAMPLES
        * AUDITORY_KERNEL_COMPONENT_COUNT
    )
    chosen, ambiguous, resource = terminal._process_frame(
        LEARNED_SAMPLES,
        (1.0,) * 16,
        (0.0,) * 16,
        terminal_module._AdvanceFullGateWorkLedger(
            reachability_limit=2,
            field_sample_limit=one_field,
        ),
    )

    assert calls == [(0, LEARNED_SAMPLES, 2)]
    assert chosen is None
    assert ambiguous is False
    assert resource is True
    assert terminal._pending == {}


def test_registry_keeps_interleaved_stream_epochs_physically_independent() -> None:
    registry = AuditoryIncrementalTerminalRegistry(
        reciprocity_owner=_learned_owner()
    )
    streams = (_MountedStream(), _MountedStream())
    signal = (
        (0,) * 21_920
        + _tone_values(LEARNED_SAMPLES, 440)
        + (0,) * TRAILING_SAMPLES
    )
    cut = 17_777
    results = []
    for mounted in streams:
        results.append(registry.advance(**mounted.mount(
            _pcm(signal[:cut]), sequence=0, first_sample_index=0
        )))
    for mounted in streams:
        results.append(registry.advance(**mounted.mount(
            _pcm(signal[cut:]), sequence=1, first_sample_index=cut
        )))

    replies = [
        value.reply_candidate for value in results
        if value.reply_candidate is not None
    ]
    assert len(replies) == 2
    assert {value.stream_id for value in replies} == {
        value.stream_id for value in streams
    }
    assert registry.status()["active_streams"] == 2


def test_registry_reject_discards_but_graceful_close_releases_terminal() -> None:
    now = [0.0]
    registry = AuditoryIncrementalTerminalRegistry(
        reciprocity_owner=_learned_owner(),
        clock=lambda: now[0],
        idle_seconds=1,
    )
    learned_pcm = _pcm(_tone_values(LEARNED_SAMPLES, 440))

    rejected = _MountedStream()
    first = registry.advance(**rejected.mount(
        learned_pcm, sequence=0, first_sample_index=0
    ))
    assert first.status is AuditoryIncrementalStatus.CONTINUING
    assert registry.close(
        rejected.stream_id, release_terminal=False
    ) is None

    completed = _MountedStream()
    second = registry.advance(**completed.mount(
        learned_pcm, sequence=0, first_sample_index=0
    ))
    assert second.status is AuditoryIncrementalStatus.CONTINUING
    released = registry.close(
        completed.stream_id, release_terminal=True
    )
    assert released is not None
    assert released.status is AuditoryIncrementalStatus.RELEASED_UNIQUE
    assert released.reply_candidate is not None
    assert registry.status()["issued_terminal_authorities"] == 1

    altered_record = released.reply_candidate.as_record()
    altered_record["tutor_label"] = "altered-label"
    receipt_payload = dict(altered_record)
    del receipt_payload["authority_receipt_sha256"]
    altered_record["authority_receipt_sha256"] = terminal_module._digest(
        receipt_payload
    )
    altered = AuditoryIncrementalTerminalEvent.from_record(altered_record)
    with pytest.raises(ValueError, match="differs from owner authority"):
        registry.claim(altered)
    assert registry.status()["issued_terminal_authorities"] == 1

    # Neither stream-idle expiry nor a later teaching refresh can invalidate a
    # terminal already admitted to the bounded reply door.  The owner retains
    # at most stream_capacity events until one is consumed or discarded.
    registry.refresh_learning()
    now[0] = 2.0
    assert registry.status()["issued_terminal_authorities"] == 1
    claim = registry.claim(released.reply_candidate)
    assert registry.verify_claim(claim) == released.reply_candidate
    assert registry.status()["issued_terminal_authorities"] == 0
    with pytest.raises(ValueError, match="not issued or was already consumed"):
        registry.claim(released.reply_candidate)


def test_registry_close_capacity_failure_restores_the_exact_pending_stream(
) -> None:
    registry = AuditoryIncrementalTerminalRegistry(
        reciprocity_owner=_learned_owner(),
        terminal_authority_capacity=1,
    )
    learned_pcm = _pcm(_tone_values(LEARNED_SAMPLES, 440))

    first_stream = _MountedStream()
    first_advance = registry.advance(**first_stream.mount(
        learned_pcm, sequence=0, first_sample_index=0
    ))
    assert first_advance.status is AuditoryIncrementalStatus.CONTINUING
    first_release = registry.close(
        first_stream.stream_id, release_terminal=True
    )
    assert first_release is not None
    assert first_release.reply_candidate is not None

    second_stream = _MountedStream()
    second_advance = registry.advance(**second_stream.mount(
        learned_pcm, sequence=0, first_sample_index=0
    ))
    assert second_advance.status is AuditoryIncrementalStatus.CONTINUING
    with pytest.raises(RuntimeError, match="authority capacity is full"):
        registry.close(second_stream.stream_id, release_terminal=True)
    failed_status = registry.status()
    assert failed_status["active_streams"] == 1
    assert failed_status["issued_terminal_authorities"] == 1

    assert registry.discard_unadmitted(first_release.reply_candidate)
    retried = registry.close(second_stream.stream_id, release_terminal=True)
    assert retried is not None
    assert retried.reply_candidate is not None
    assert registry.status()["issued_terminal_authorities"] == 1


def test_claim_completion_rejects_a_different_event_local_field() -> None:
    registry = AuditoryIncrementalTerminalRegistry(
        reciprocity_owner=_learned_owner(),
    )
    mounted = _MountedStream()
    first = registry.advance(**mounted.mount(
        _pcm(_tone_values(LEARNED_SAMPLES, 440)),
        sequence=0,
        first_sample_index=0,
    ))
    assert first.status is AuditoryIncrementalStatus.CONTINUING
    released = registry.close(mounted.stream_id, release_terminal=True)
    assert released is not None
    assert released.reply_candidate is not None
    assert mounted.last_causal is not None
    current_record = released.reply_candidate.as_record()
    assert current_record["schema"] == (
        terminal_module.AUDITORY_INCREMENTAL_EVENT_SCHEMA_V3
    )
    assert current_record["l5_schema"] == "guala.auditory_l5.full_field.v4"
    assert current_record["reciprocity_snapshot_schema"] == (
        "guala.auditory.causal_path.v5"
    )
    assert current_record["recognition_operator"] == (
        "auditory_joint_causal_path_contains.v2"
    )
    assert AuditoryIncrementalTerminalEvent.from_record(current_record) == (
        released.reply_candidate
    )
    legacy_record = dict(current_record)
    legacy_record["schema"] = (
        terminal_module.AUDITORY_INCREMENTAL_EVENT_SCHEMA_V2
    )
    del legacy_record["l5_schema"]
    del legacy_record["recognition_operator"]
    del legacy_record["reciprocity_snapshot_schema"]
    del legacy_record["authority_receipt_sha256"]
    legacy_record["authority_receipt_sha256"] = terminal_module._digest(
        legacy_record
    )
    legacy = AuditoryIncrementalTerminalEvent.from_record(legacy_record)
    with pytest.raises(ValueError, match="audit record cannot be claimed"):
        registry.claim(legacy)

    claim = registry.claim(released.reply_candidate)
    with pytest.raises(
        ValueError,
        match="auditory causal settlement reduced the exact field",
    ):
        registry.complete_claim(claim, mounted.last_causal)
    registry.rollback_claim(claim)
    assert registry.status()["issued_terminal_authorities"] == 1
