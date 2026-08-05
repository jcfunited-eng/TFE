from __future__ import annotations

from dataclasses import replace

import pytest

from dsf_ai_service.substrate.auditory_pcm_stream import (
    AuditoryPCMStreamRegistry,
    PCM_SAMPLE_RATE_HZ,
)
from dsf_ai_service.substrate.visual_exposure_epoch import (
    MAX_VISUAL_EXPOSURE_EPOCH_STATE_BYTES,
    VisualExposureEpochAuthority,
)


KEY = b"visual-exposure-epoch-test-key-32-bytes"


def _auditory(registry, stream_id, sequence):
    return registry.accept(
        stream_id=stream_id,
        sequence=sequence,
        first_sample_index=sequence * 8,
        sample_rate_hz=PCM_SAMPLE_RATE_HZ,
        source_epoch_start_ns=1_000_000_000,
        pcm_s16le=b"\0\0" * 8,
    ).receipt


def _frames(prefix):
    return tuple(f"{prefix + index:064x}" for index in range(4))


def test_successive_pcm_chunks_produce_predecessor_evidence_not_identity():
    auditory = AuditoryPCMStreamRegistry()
    stream_id = auditory.open()["stream_id"]
    authority = VisualExposureEpochAuthority(authority_key=KEY)

    first = authority.prepare(
        auditory=_auditory(auditory, stream_id, 0),
        frame_receipt_sha256s=_frames(1),
        preparation_receipt_sha256="a" * 64,
    )
    assert first.relation == "first_in_epoch"
    authority.commit(first)

    second = authority.prepare(
        auditory=_auditory(auditory, stream_id, 1),
        frame_receipt_sha256s=_frames(10),
        preparation_receipt_sha256="b" * 64,
    )
    assert second.relation == "authenticated_predecessor_evidence"
    assert second.authenticated_predecessor_epoch_receipt_sha256 == (
        first.authority_receipt_sha256
    )
    assert second.authenticated_predecessor_terminal_frame_sha256 == (
        first.current_terminal_frame_sha256
    )
    assert authority.status()["identity_authority"] is False


def test_missing_visual_sequence_rebases_instead_of_bridging_gap():
    auditory = AuditoryPCMStreamRegistry()
    stream_id = auditory.open()["stream_id"]
    authority = VisualExposureEpochAuthority(authority_key=KEY)
    first = authority.prepare(
        auditory=_auditory(auditory, stream_id, 0),
        frame_receipt_sha256s=_frames(1),
        preparation_receipt_sha256="a" * 64,
    )
    authority.commit(first)
    _auditory(auditory, stream_id, 1)
    after_gap = authority.prepare(
        auditory=_auditory(auditory, stream_id, 2),
        frame_receipt_sha256s=_frames(20),
        preparation_receipt_sha256="c" * 64,
    )
    assert after_gap.relation == "first_in_epoch"
    assert after_gap.authenticated_predecessor_epoch_receipt_sha256 is None


def test_state_is_bounded_transient_authenticated_and_clearable():
    auditory = AuditoryPCMStreamRegistry()
    authority = VisualExposureEpochAuthority(authority_key=KEY)
    stream_ids = []
    for index in range(4):
        stream_id = auditory.open()["stream_id"]
        stream_ids.append(stream_id)
        evidence = authority.prepare(
            auditory=_auditory(auditory, stream_id, 0),
            frame_receipt_sha256s=_frames(index * 10 + 1),
            preparation_receipt_sha256=f"{index + 1:064x}",
        )
        authority.commit(evidence)
    encoded = authority.snapshot_encoded()
    assert len(encoded) < MAX_VISUAL_EXPOSURE_EPOCH_STATE_BYTES
    assert authority.status() == {
        "active_streams": 4,
        "stream_capacity": 4,
        "retained_raw_frame_bytes": 0,
        "persistence": "disabled",
        "identity_authority": False,
    }
    restored = VisualExposureEpochAuthority(authority_key=KEY)
    restored.rollback_encoded(encoded)
    assert restored.status()["active_streams"] == 4
    stream_id = stream_ids[0]
    assert restored.clear(stream_id) is True
    assert restored.clear(stream_id) is False

    altered = bytearray(encoded)
    altered[len(altered) // 2] ^= 1
    with pytest.raises(ValueError):
        restored.rollback_encoded(bytes(altered))
    assert restored.status()["active_streams"] == 3


def test_evidence_tampering_and_stale_commit_fail_closed():
    auditory = AuditoryPCMStreamRegistry()
    stream_id = auditory.open()["stream_id"]
    authority = VisualExposureEpochAuthority(authority_key=KEY)
    auditory_receipt = _auditory(auditory, stream_id, 0)
    first = authority.prepare(
        auditory=auditory_receipt,
        frame_receipt_sha256s=_frames(1),
        preparation_receipt_sha256="a" * 64,
    )
    with pytest.raises(ValueError, match="HMAC"):
        authority.verify(replace(first, current_terminal_frame_sha256="f" * 64))

    competing = authority.prepare(
        auditory=auditory_receipt,
        frame_receipt_sha256s=_frames(30),
        preparation_receipt_sha256="d" * 64,
    )
    authority.commit(first)
    with pytest.raises(RuntimeError, match="changed before commit"):
        authority.commit(competing)
    assert authority.status()["active_streams"] == 1


def test_idle_epoch_expires_and_cannot_create_false_predecessor():
    now = [0.0]
    auditory = AuditoryPCMStreamRegistry(
        clock=lambda: now[0], idle_seconds=30
    )
    stream_id = auditory.open()["stream_id"]
    authority = VisualExposureEpochAuthority(
        authority_key=KEY,
        clock=lambda: now[0],
        idle_seconds=30,
    )
    first = authority.prepare(
        auditory=_auditory(auditory, stream_id, 0),
        frame_receipt_sha256s=_frames(1),
        preparation_receipt_sha256="a" * 64,
    )
    authority.commit(first)
    now[0] = 31.0
    assert authority.status()["active_streams"] == 0
