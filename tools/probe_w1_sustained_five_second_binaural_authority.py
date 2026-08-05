"""Measure sustained production-sized W1 binaural experience settlement."""

from __future__ import annotations

import gc
import json
import math
import os
from pathlib import Path
import resource
import struct
import time

from dsf_ai_service.substrate.embodiment_world import (
    MAX_VOCAL_SAMPLE_COUNT,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.glew_runtime.exact_field_executor import (
    start_exact_field_executor,
    stop_exact_field_executor,
)
from dsf_ai_service.substrate.w1_acoustic_emitter import (
    W1AcousticEmitterAuthority,
)
from dsf_ai_service.substrate.w1_anonymous_audiovisual_continuity import (
    W1AnonymousAudiovisualContinuityOwner,
)
from dsf_ai_service.substrate.w1_audiovisual_physical_evidence import (
    W1AudiovisualPhysicalEvidenceAuthority,
)
from dsf_ai_service.substrate.w1_binaural_auditory_l5 import (
    MAX_W1_BINAURAL_AUDITORY_L5_BYTES,
    MAX_W1_BINAURAL_AUDITORY_L5_STATE_BYTES,
    W1BinauralAuditoryL5Owner,
)
from dsf_ai_service.substrate.w1_companion_vocal_experience import (
    W1CompanionVocalExperienceAuthority,
)
from tools.probe_w1_five_second_binaural_authority import (
    SAMPLE_RATE_HZ,
    _world,
)


CAPTURE_COUNT = 8
CAPTURE_DEADLINE_SECONDS = 5.0
TRANSITION_CAPACITY = 4


def _pcm(ordinal: int) -> bytes:
    base_hz = 181 + ordinal * 29
    values = tuple(
        int(
            7_000
            * math.sin(
                2 * math.pi * base_hz * index / SAMPLE_RATE_HZ
            )
            + 3_500
            * math.sin(
                2 * math.pi * (base_hz + 337) * index / SAMPLE_RATE_HZ
            )
            + 1_500
            * math.sin(
                2 * math.pi * (base_hz + 911) * index / SAMPLE_RATE_HZ
            )
        )
        for index in range(MAX_VOCAL_SAMPLE_COUNT)
    )
    return struct.pack(f"<{len(values)}h", *values)


def _resident_kib() -> int:
    fields = Path("/proc/self/statm").read_text(
        encoding="ascii"
    ).split()
    if len(fields) < 2:
        raise RuntimeError("Linux resident-memory evidence is unavailable")
    return int(fields[1]) * os.sysconf("SC_PAGE_SIZE") // 1024


def main() -> None:
    exact_field_owner = start_exact_field_executor()
    exact_field_owner.assert_healthy()
    world = _world()
    causal = ExactCausalExperienceOwner(
        on_settlement=lambda _settlement: None,
        log_event=lambda *_args, **_kwargs: None,
    )
    auditory = W1BinauralAuditoryL5Owner(
        max_transitions=TRANSITION_CAPACITY,
    )
    physical = W1AudiovisualPhysicalEvidenceAuthority(
        authority_key=b"p" * 32,
        world_authority=world,
        causal_owner=causal,
        acoustic_emitter=W1AcousticEmitterAuthority(
            authority_key=b"a" * 32,
            world_authority=world,
        ),
        binaural_auditory_l5_owner=auditory,
        anonymous_av_continuity_owner=(
            W1AnonymousAudiovisualContinuityOwner(
                authority_key=b"v" * 32,
                physical_authority_key=b"p" * 32,
                max_transitions=TRANSITION_CAPACITY,
            )
        ),
    )
    companion = W1CompanionVocalExperienceAuthority(
        authority_key=b"c" * 32,
        world_authority=world,
        physical_authority=physical,
    )
    baseline_resident_kib = _resident_kib()
    captures = []
    for ordinal in range(CAPTURE_COUNT):
        start = time.perf_counter()
        prepared = companion.prepare(pcm_s16le=_pcm(ordinal))
        prepare_seconds = time.perf_counter() - start
        experience = prepared.physical_mount.binaural_auditory_l5
        if experience is None:
            raise RuntimeError("sustained W1 capture omitted binaural L5")
        compact = experience.compact_full_field
        compact_bytes = len(compact.encoded())
        start = time.perf_counter()
        companion.commit(prepared)
        commit_seconds = time.perf_counter() - start
        current_before_collection_kib = _resident_kib()
        gc.collect()
        current_after_collection_kib = _resident_kib()
        snapshot_bytes = len(auditory.encoded_snapshot())
        status = auditory.status()
        captures.append({
            "capture": ordinal + 1,
            "commit_seconds": commit_seconds,
            "compact_authority_bytes": compact_bytes,
            "full_field_tuple_count": sum(
                len(component.tuples)
                for component in compact.components
            ),
            "prepare_seconds": prepare_seconds,
            "resident_after_collection_kib": (
                current_after_collection_kib
            ),
            "resident_before_collection_kib": (
                current_before_collection_kib
            ),
            "retained_raw_media_bytes": physical.status()[
                "retained_raw_media_bytes"
            ],
            "snapshot_bytes": snapshot_bytes,
            "transition_relations": status["transition_relations"],
        })
    encoded = auditory.encoded_snapshot()
    restored = W1BinauralAuditoryL5Owner(
        max_transitions=TRANSITION_CAPACITY,
    )
    restored.restore_encoded(encoded)
    exact_restore = (
        restored.encoded_snapshot() == encoded
        and restored.latest == auditory.latest
    )
    report = {
        "baseline_resident_kib": baseline_resident_kib,
        "capture_count": CAPTURE_COUNT,
        "capture_deadline_seconds": CAPTURE_DEADLINE_SECONDS,
        "captures": captures,
        "compact_authority_limit_bytes": (
            MAX_W1_BINAURAL_AUDITORY_L5_BYTES
        ),
        "deadline_met_for_every_capture": all(
            value["prepare_seconds"] < CAPTURE_DEADLINE_SECONDS
            for value in captures
        ),
        "exact_final_restore": exact_restore,
        "maximum_resident_kib": resource.getrusage(
            resource.RUSAGE_SELF
        ).ru_maxrss,
        "raw_media_zero_after_every_commit": all(
            value["retained_raw_media_bytes"] == 0
            for value in captures
        ),
        "schema": (
            "guala.audit.w1_sustained_five_second_binaural_authority.v1"
        ),
        "snapshot_limit_bytes": (
            MAX_W1_BINAURAL_AUDITORY_L5_STATE_BYTES
        ),
        "transition_capacity": TRANSITION_CAPACITY,
    }
    stop_exact_field_executor()
    print(json.dumps(report, indent=2, sort_keys=True))
    if (
        not report["deadline_met_for_every_capture"]
        or not exact_restore
        or not report["raw_media_zero_after_every_commit"]
        or any(
            value["compact_authority_bytes"]
            > MAX_W1_BINAURAL_AUDITORY_L5_BYTES
            or value["snapshot_bytes"]
            > MAX_W1_BINAURAL_AUDITORY_L5_STATE_BYTES
            or value["transition_relations"] > TRANSITION_CAPACITY
            for value in captures
        )
    ):
        raise RuntimeError(
            "sustained five-second W1 authority proof failed"
        )


if __name__ == "__main__":
    main()
