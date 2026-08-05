"""Prove one production-sized W1 binaural experience end to end."""

from __future__ import annotations

import json
import math
import resource
import struct
import time

from dsf_ai_service.substrate.embodiment_world import (
    MAX_VOCAL_SAMPLE_COUNT,
    PORT_ID,
    SECOND_BODY_PORT_ID,
    EmbodiedBody,
    EmbodimentPort,
    EmbodimentWorldAuthority,
    PoseMM,
    PositionMM,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
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
    W1BinauralAuditoryL5Owner,
)
from dsf_ai_service.substrate.w1_companion_vocal_experience import (
    W1CompanionVocalExperienceAuthority,
)


SAMPLE_RATE_HZ = 16_000


def _five_second_pcm() -> bytes:
    values = tuple(
        int(
            8_000
            * math.sin(2 * math.pi * 223 * index / SAMPLE_RATE_HZ)
            + 4_000
            * math.sin(2 * math.pi * 659 * index / SAMPLE_RATE_HZ)
            + 2_000
            * math.sin(2 * math.pi * 1_231 * index / SAMPLE_RATE_HZ)
        )
        for index in range(MAX_VOCAL_SAMPLE_COUNT)
    )
    return struct.pack(f"<{len(values)}h", *values)


def _world() -> EmbodimentWorldAuthority:
    return EmbodimentWorldAuthority(
        authority_key=b"w" * 32,
        bodies=(
            EmbodiedBody(
                "guala-body-1",
                PoseMM(PositionMM(1_000, 1_000, 0), 0),
                250,
                800,
            ),
            EmbodiedBody(
                "companion-body",
                PoseMM(PositionMM(3_500, 2_500, 0), 180_000),
                200,
                600,
            ),
        ),
        actor_ports=(
            EmbodimentPort(PORT_ID, "guala-body-1"),
            EmbodimentPort(SECOND_BODY_PORT_ID, "companion-body"),
        ),
    )


def main() -> None:
    world = _world()
    causal = ExactCausalExperienceOwner(
        on_settlement=lambda _settlement: None,
        log_event=lambda *_args, **_kwargs: None,
    )
    auditory = W1BinauralAuditoryL5Owner(max_transitions=4)
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
                max_transitions=4,
            )
        ),
    )
    companion = W1CompanionVocalExperienceAuthority(
        authority_key=b"c" * 32,
        world_authority=world,
        physical_authority=physical,
    )
    pcm = _five_second_pcm()
    start = time.perf_counter()
    prepared = companion.prepare(pcm_s16le=pcm)
    prepare_seconds = time.perf_counter() - start
    experience = prepared.physical_mount.binaural_auditory_l5
    if experience is None:
        raise RuntimeError("five-second W1 experience omitted binaural L5")
    compact = experience.compact_full_field
    encoded = compact.encoded()
    start = time.perf_counter()
    companion.commit(prepared)
    commit_seconds = time.perf_counter() - start
    snapshot = auditory.encoded_snapshot()
    restored = W1BinauralAuditoryL5Owner(max_transitions=4)
    restored.restore_encoded(snapshot)
    if (
        restored.encoded_snapshot() != snapshot
        or restored.latest != auditory.latest
    ):
        raise RuntimeError("five-second W1 authority changed on restore")
    print(json.dumps({
        "auditory_snapshot_bytes": len(snapshot),
        "compact_authority_bytes": len(encoded),
        "compact_authority_limit_bytes": (
            MAX_W1_BINAURAL_AUDITORY_L5_BYTES
        ),
        "component_count": len(compact.components),
        "commit_seconds": commit_seconds,
        "full_field_tuple_count": sum(
            len(component.tuples) for component in compact.components
        ),
        "maximum_resident_kib": resource.getrusage(
            resource.RUSAGE_SELF
        ).ru_maxrss,
        "prepare_seconds": prepare_seconds,
        "retained_raw_media_bytes": physical.status()[
            "retained_raw_media_bytes"
        ],
        "sample_count": MAX_VOCAL_SAMPLE_COUNT,
        "schema": "guala.audit.w1_five_second_binaural_authority.v1",
        "source_hop_count_per_component": (
            compact.components[0].source_sample_count
        ),
        "state_round_trip_exact": True,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
