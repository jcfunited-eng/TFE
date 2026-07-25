"""Exact rollback and retry identity for one continuous auditory chunk."""

from __future__ import annotations

import math
import struct
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    build_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.auditory_incremental_terminal import (
    MAX_ACTIVE_TRACKERS,
    MAX_EVENT_HOPS,
    AuditoryIncrementalTerminalRegistry,
    AuditoryIncrementalTerminalOwner,
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
    MAX_PATH_BRANCHES_PER_CLASS,
    MAX_RECIPROCAL_CLASSES_PER_KIND,
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
    AuditoryFullFieldStream,
)
from dsf_ai_service.v4.gualaloom_v5_engine import Guala


SOURCE_EPOCH_NS = 1_000_000_000


def _tone(sample_count: int, frequency_hz: int = 440) -> bytes:
    values = tuple(
        round(
            8_000
            * math.sin(
                2 * math.pi * frequency_hz * index / PCM_SAMPLE_RATE_HZ
            )
        )
        for index in range(sample_count)
    )
    return struct.pack(f"<{len(values)}h", *values)


class _MountedAuthorities:
    def __init__(self) -> None:
        self.transport_owner = AuditoryPCMStreamRegistry()
        self.stream_id = self.transport_owner.open()["stream_id"]
        self.cochlear_owner = AuditoryFullFieldStream()
        self.l5_owner = AuditoryL5Owner(
            log_event=lambda *_args, **_kwargs: None
        )
        self.causal_owner = ExactCausalExperienceOwner(
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
        accepted = self.transport_owner.accept(
            stream_id=self.stream_id,
            sequence=sequence,
            first_sample_index=first_sample_index,
            sample_rate_hz=PCM_SAMPLE_RATE_HZ,
            source_epoch_start_ns=SOURCE_EPOCH_NS,
            pcm_s16le=pcm_s16le,
        )
        capture, cochlear = self.cochlear_owner.advance(
            pcm_s16le, accepted.receipt
        )
        epoch = Fraction(SOURCE_EPOCH_NS, 1_000_000_000)
        start = accepted.receipt.first_sample_index
        end = accepted.receipt.last_sample_index_exclusive
        built = build_six_sense_full_field(
            assembly_id=f"chunk-transaction-{self.stream_id}-{sequence}",
            source_time_start=epoch + Fraction(start, PCM_SAMPLE_RATE_HZ),
            source_time_end=epoch + Fraction(end, PCM_SAMPLE_RATE_HZ),
            observed_substreams={
                PhysicalSense.SOUND: auditory_kernel_component_inputs(
                    capture, source_anchor=epoch
                )
            },
            states={
                sense: (
                    SenseBoundaryState.OBSERVED
                    if sense is PhysicalSense.SOUND
                    else SenseBoundaryState.SENSOR_UNAVAILABLE
                )
                for sense in SENSE_ORDER
            },
        )
        auditory_l5 = self.l5_owner.settle(
            built, event_boundary=event_boundary
        )
        assert auditory_l5 is not None
        causal = self.causal_owner.settle(
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


def _learned_reciprocity() -> AuditoryReciprocityOwner:
    witness_mount = _MountedAuthorities()
    witness = witness_mount.mount(
        _tone(6_400),
        sequence=0,
        first_sample_index=0,
        event_boundary="utterance",
    )["auditory_l5"]
    owner = AuditoryReciprocityOwner(
        log_event=lambda *_args, **_kwargs: None,
        tutor_authority=AuditoryTutorAuthority.unrequired(),
    )
    owner.teach(
        witness,
        kind=AuditoryReciprocityKind.SPOKEN_FORM,
        tutor_label="transaction-witness",
    )
    return owner


def _terminal_authorities(values: dict[str, object]) -> dict[str, object]:
    return {
        name: values[name]
        for name in (
            "pcm_s16le",
            "capture",
            "auditory_l5",
            "transport",
            "cochlear",
            "joint_settlement",
        )
    }


def test_append_failure_restores_exact_owner_and_same_chunk_retries(
        monkeypatch):
    owner = AuditoryIncrementalTerminalOwner(
        reciprocity_owner=_learned_reciprocity()
    )
    mounted = _MountedAuthorities()
    authorities = mounted.mount(
        _tone(3_200), sequence=0, first_sample_index=0
    )
    before = owner._transaction_checkpoint()
    original_append = owner._append_pcm
    calls = 0

    def fail_once(*args):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("injected append failure")
        return original_append(*args)

    monkeypatch.setattr(owner, "_append_pcm", fail_once)
    with pytest.raises(RuntimeError, match="injected append failure"):
        owner.advance(**_terminal_authorities(authorities))
    assert owner._transaction_checkpoint() == before

    committed = owner.advance(**_terminal_authorities(authorities))
    committed.verify()
    assert owner._last_committed_receipt_sha256 == authorities[
        "transport"
    ].receipt_sha256
    assert owner.advance(**_terminal_authorities(authorities)) is committed

    changed_pcm = b"\x00\x00" * authorities["transport"].sample_count
    with pytest.raises(ValueError, match="PCM differs from transport"):
        owner.advance(**{
            **_terminal_authorities(authorities),
            "pcm_s16le": changed_pcm,
        })


def test_verified_capability_prevents_duplicate_full_graph_verification(
        monkeypatch):
    mounted = _MountedAuthorities()
    authorities = mounted.mount(
        _tone(3_200), sequence=0, first_sample_index=0
    )
    capability = AuditoryIncrementalTerminalOwner.prepare_verified_settlement(
        pcm_s16le=authorities["pcm_s16le"],
        capture=authorities["capture"],
        auditory_l5=authorities["auditory_l5"],
        transport=authorities["transport"],
        cochlear=authorities["cochlear"],
        causal_settlement=authorities["causal_settlement"],
    )

    def duplicate_verification(*_args, **_kwargs):
        raise AssertionError("verified auditory graph was traversed twice")

    monkeypatch.setattr(
        type(authorities["transport"]),
        "verify",
        duplicate_verification,
    )
    monkeypatch.setattr(
        type(authorities["cochlear"]),
        "verify",
        duplicate_verification,
    )
    monkeypatch.setattr(
        type(capability.joint_settlement),
        "verify",
        duplicate_verification,
    )
    monkeypatch.setattr(
        type(authorities["auditory_l5"]),
        "verify",
        duplicate_verification,
    )

    owner = AuditoryIncrementalTerminalOwner(
        reciprocity_owner=AuditoryReciprocityOwner(
            log_event=lambda *_args, **_kwargs: None,
            tutor_authority=AuditoryTutorAuthority.unrequired(),
        )
    )
    transaction_authorities = _terminal_authorities(authorities)
    transaction_authorities["joint_settlement"] = (
        capability.joint_settlement
    )
    result = owner.advance(
        **transaction_authorities,
        verified_capability=capability,
    )
    result.verify()


def test_failure_after_native_step_restores_prior_chunk_not_prior_result(
        monkeypatch):
    owner = AuditoryIncrementalTerminalOwner(
        reciprocity_owner=_learned_reciprocity()
    )
    mounted = _MountedAuthorities()
    first = mounted.mount(
        _tone(3_200), sequence=0, first_sample_index=0
    )
    first_result = owner.advance(**_terminal_authorities(first))
    checkpoint = owner._transaction_checkpoint()
    assert checkpoint.native_active_tracker_count > 0

    second = mounted.mount(
        _tone(3_200), sequence=1, first_sample_index=3_200
    )
    original_process = owner._process_frame
    calls = 0

    def fail_after_native(*args):
        nonlocal calls
        value = original_process(*args)
        calls += 1
        if calls == 1:
            raise RuntimeError("injected post-native failure")
        return value

    monkeypatch.setattr(owner, "_process_frame", fail_after_native)
    with pytest.raises(RuntimeError, match="injected post-native failure"):
        owner.advance(**_terminal_authorities(second))
    assert owner._transaction_checkpoint() == checkpoint

    monkeypatch.setattr(owner, "_process_frame", original_process)
    second_result = owner.advance(**_terminal_authorities(second))
    second_result.verify()
    assert second_result is not first_result
    assert owner._last_committed_receipt_sha256 == second[
        "transport"
    ].receipt_sha256


def test_worst_cardinality_rollback_restores_bounded_native_checkpoint_without_replay(
        monkeypatch):
    clone_calls = []

    class NativeStateProbe:
        def __init__(self, *, checkpoint=False):
            self.active_starts = tuple(range(MAX_EVENT_HOPS))
            self.active_tracker_count = MAX_ACTIVE_TRACKERS
            self.is_checkpoint = checkpoint

        def checkpoint_state(self):
            clone_calls.append(self)
            return NativeStateProbe(checkpoint=True)

        def step(self, *_args, **_kwargs):
            raise AssertionError("rollback replayed retained native history")

    owner = AuditoryIncrementalTerminalOwner(
        reciprocity_owner=AuditoryReciprocityOwner(
            log_event=lambda *_args, **_kwargs: None,
            tutor_authority=AuditoryTutorAuthority.unrequired(),
        )
    )
    maximum_cells = (
        MAX_RECIPROCAL_CLASSES_PER_KIND
        * MAX_PATH_BRANCHES_PER_CLASS
        * (MAX_PATH_BRANCHES_PER_CLASS + 1)
        // 2
    )
    owner._cells = (object(),) * maximum_cells
    owner._frames = [object()] * MAX_EVENT_HOPS
    owner._native_proposals = NativeStateProbe()
    checkpoint = owner._transaction_checkpoint()

    def forbidden_reconstruction():
        raise AssertionError("rollback reconstructed the native proposal owner")

    monkeypatch.setattr(
        owner,
        "_new_native_proposal_owner",
        forbidden_reconstruction,
    )
    owner._native_proposals = NativeStateProbe()
    owner._restore_transaction_checkpoint(checkpoint)

    assert maximum_cells == 640
    assert len(checkpoint.frames) == MAX_EVENT_HOPS == 800
    assert checkpoint.native_active_tracker_count == MAX_ACTIVE_TRACKERS
    assert len(clone_calls) == 1
    assert owner._native_proposals is checkpoint.native_state
    assert owner._native_proposals.is_checkpoint


def test_full_gate_exception_restores_empty_owner_for_same_chunk_retry(
        monkeypatch):
    owner = AuditoryIncrementalTerminalOwner(
        reciprocity_owner=_learned_reciprocity()
    )
    mounted = _MountedAuthorities()
    authorities = mounted.mount(
        _tone(6_400), sequence=0, first_sample_index=0
    )
    before = owner._transaction_checkpoint()
    original_full_gate = owner._full_gate
    calls = 0

    def fail_once(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("injected full-gate failure")
        return original_full_gate(*args, **kwargs)

    monkeypatch.setattr(owner, "_full_gate", fail_once)
    with pytest.raises(RuntimeError, match="injected full-gate failure"):
        owner.advance(**_terminal_authorities(authorities))
    assert calls == 1
    assert owner._transaction_checkpoint() == before

    monkeypatch.setattr(owner, "_full_gate", original_full_gate)
    result = owner.advance(**_terminal_authorities(authorities))
    result.verify()
    assert owner._last_committed_receipt_sha256 == authorities[
        "transport"
    ].receipt_sha256


def test_registry_failure_removes_uncommitted_epoch_then_exact_duplicate_reuses(
        monkeypatch):
    registry = AuditoryIncrementalTerminalRegistry(
        reciprocity_owner=AuditoryReciprocityOwner(
            log_event=lambda *_args, **_kwargs: None,
            tutor_authority=AuditoryTutorAuthority.unrequired()
        )
    )
    mounted = _MountedAuthorities()
    authorities = mounted.mount(
        _tone(3_200), sequence=0, first_sample_index=0
    )
    original_advance = AuditoryIncrementalTerminalOwner.advance
    calls = 0

    def fail_after_owner_commit(self, **values):
        nonlocal calls
        result = original_advance(self, **values)
        calls += 1
        if calls == 1:
            raise RuntimeError("injected registry commit failure")
        return result

    monkeypatch.setattr(
        AuditoryIncrementalTerminalOwner,
        "advance",
        fail_after_owner_commit,
    )
    with pytest.raises(RuntimeError, match="injected registry commit failure"):
        registry.advance(**_terminal_authorities(authorities))
    assert registry.status()["active_streams"] == 0

    committed = registry.advance(**_terminal_authorities(authorities))
    committed.verify()
    assert registry.status()["active_streams"] == 1
    assert registry.advance(**_terminal_authorities(authorities)) is committed


def test_registry_does_not_restore_twice_after_owner_rolls_back_late_failure(
        monkeypatch):
    registry = AuditoryIncrementalTerminalRegistry(
        reciprocity_owner=_learned_reciprocity()
    )
    mounted = _MountedAuthorities()
    first = mounted.mount(
        _tone(3_200), sequence=0, first_sample_index=0
    )
    registry.advance(**_terminal_authorities(first))
    owner = registry._streams[first["transport"].stream_id].owner
    before = owner._transaction_checkpoint()
    second = mounted.mount(
        _tone(3_200), sequence=1, first_sample_index=3_200
    )
    original_process = owner._process_frame
    original_restore = owner._restore_transaction_checkpoint
    restore_calls = 0
    process_calls = 0

    def fail_after_native(*args):
        nonlocal process_calls
        value = original_process(*args)
        process_calls += 1
        if process_calls == 1:
            raise RuntimeError("injected late owner failure")
        return value

    def count_restore(checkpoint):
        nonlocal restore_calls
        restore_calls += 1
        return original_restore(checkpoint)

    monkeypatch.setattr(owner, "_process_frame", fail_after_native)
    monkeypatch.setattr(owner, "_restore_transaction_checkpoint", count_restore)
    with pytest.raises(RuntimeError, match="injected late owner failure"):
        registry.advance(**_terminal_authorities(second))

    assert restore_calls == 1
    assert owner._transaction_checkpoint() == before


def test_engine_joint_failure_retains_capture_and_l5_for_exact_retry(
        monkeypatch):
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("WAVE_SUMMARY_ENQUEUE_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    engine = Guala()
    try:
        mounted = _MountedAuthorities()
        authorities = mounted.mount(
            _tone(3_200), sequence=0, first_sample_index=0
        )
        transport = authorities["transport"]
        settlement = authorities["causal_settlement"]
        capture_authority = (
            transport,
            authorities["capture"],
            authorities["cochlear"],
            authorities["pcm_s16le"],
        )
        verified_capability = (
            AuditoryIncrementalTerminalOwner.prepare_verified_settlement(
                pcm_s16le=authorities["pcm_s16le"],
                capture=authorities["capture"],
                auditory_l5=authorities["auditory_l5"],
                transport=transport,
                cochlear=authorities["cochlear"],
                causal_settlement=settlement,
            )
        )
        engine._auditory_capture_authorities[
            transport.receipt_sha256
        ] = capture_authority
        engine._auditory_l5_by_assembly[
            settlement.assembly_id
        ] = authorities["auditory_l5"]
        engine._auditory_prediction_joint_by_transport[
            transport.receipt_sha256
        ] = verified_capability.joint_settlement
        engine._auditory_verified_capability_by_transport[
            transport.receipt_sha256
        ] = verified_capability
        prior_joint = engine._latest_auditory_stream_settlement_receipt
        prior_advance = engine._latest_auditory_incremental_advance
        original_advance = engine._auditory_incremental_terminals.advance
        calls = 0

        def fail_once(**values):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RuntimeError("injected joint advance failure")
            return original_advance(**values)

        monkeypatch.setattr(
            engine._auditory_incremental_terminals, "advance", fail_once
        )
        with pytest.raises(RuntimeError, match="injected joint advance failure"):
            engine.advance_continuous_auditory_terminal(
                pcm_s16le=authorities["pcm_s16le"],
                transport=transport,
                settlement=settlement,
            )
        assert engine._auditory_capture_authorities[
            transport.receipt_sha256
        ] is capture_authority
        assert engine._auditory_l5_by_assembly[
            settlement.assembly_id
        ] is authorities["auditory_l5"]
        assert engine._latest_auditory_stream_settlement_receipt is prior_joint
        assert engine._latest_auditory_incremental_advance is prior_advance

        joint, result = engine.advance_continuous_auditory_terminal(
            pcm_s16le=authorities["pcm_s16le"],
            transport=transport,
            settlement=settlement,
        )
        joint.verify()
        result.verify()
        assert transport.receipt_sha256 not in (
            engine._auditory_capture_authorities
        )
        assert transport.receipt_sha256 not in (
            engine._auditory_prediction_joint_by_transport
        )
        assert transport.receipt_sha256 not in (
            engine._auditory_verified_capability_by_transport
        )
        assert settlement.assembly_id not in engine._auditory_l5_by_assembly
        assert engine._latest_auditory_stream_settlement_receipt is joint
        assert engine._latest_auditory_incremental_advance is result
    finally:
        engine.strict_shutdown(timeout=30.0)
