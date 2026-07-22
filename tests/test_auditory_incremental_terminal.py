from __future__ import annotations

import math
import struct
from fractions import Fraction

import dsf_ai_service.substrate.auditory_incremental_terminal as terminal_module
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    NativeSensorySubstreamInput,
    build_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.auditory_incremental_terminal import (
    AuditoryIncrementalTerminalRegistry,
    AuditoryIncrementalStatus,
    AuditoryIncrementalTerminalOwner,
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
from dsf_ai_service.substrate.auditory_tutor_authority import (
    AuditoryTutorAuthority,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    AUDITORY_CHANNELS,
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
        ports = tuple(
            NativeSensorySubstreamInput(
                sense=PhysicalSense.SOUND,
                sensor_id="microphone-gammatone-cochlear-field",
                substream_id=channel.definition.name,
                topology_index=topology_index,
                coordinates=(
                    NativeAxisCoordinate(
                        "cochlear-channel", channel.definition.name
                    ),
                    NativeAxisCoordinate(
                        "centre-hz", str(channel.definition.centre_hz)
                    ),
                    NativeAxisCoordinate(
                        "erb-width-hz", str(channel.definition.erb_width_hz)
                    ),
                    NativeAxisCoordinate("gammatone-order", "4"),
                    NativeAxisCoordinate(
                        "observation-hop-samples",
                        str(OBSERVATION_HOP_SAMPLES),
                    ),
                ),
                physical_quantity="cochlear-pressure-envelope",
                physical_unit="full-scale-pressure",
                source_times=tuple(
                    epoch + Fraction(value, 1_000_000_000)
                    for value in channel.causal_offsets_ns
                ),
                normalized_signal=channel.pressure_envelope_full_scale,
                phase_turns=tuple(
                    Fraction.from_float(value)
                    for value in channel.carrier_phase_turns
                ),
            )
            for topology_index, channel in enumerate(capture.channels)
        )
        assert tuple(port.substream_id for port in ports) == tuple(
            value.name for value in AUDITORY_CHANNELS
        )
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
        auditory_l5 = self.l5.settle(
            built, event_boundary=event_boundary
        )
        assert auditory_l5 is not None
        causal = self.causal.settle(
            built,
            routing_chis=(),
            source_tags=(),
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
        }


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
        extents.append((
            event.source_sample_start,
            event.source_sample_end,
            event.tutor_label,
        ))
    assert extents == [(offset, offset + LEARNED_SAMPLES, "learned-form")] * 3


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
    return terminal_module._PendingTerminal(
        start=start,
        end=end,
        tutor_label=label,
        structural_fingerprint="1" * 64,
        l5_authority_receipt_sha256="2" * 64,
        transport_receipt_sha256s=("3" * 64,),
        cochlear_receipt_sha256s=("4" * 64,),
        joint_settlement_receipt_sha256s=("5" * 64,),
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
            field_sample_limit=2_000,
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
            field_sample_limit=2_000,
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
    one_field = LEARNED_SAMPLES // OBSERVATION_HOP_SAMPLES * 16
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
    registry = AuditoryIncrementalTerminalRegistry(
        reciprocity_owner=_learned_owner()
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
