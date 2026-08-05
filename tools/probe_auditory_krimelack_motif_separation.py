"""Measure whether auditory L4 commitments support Krimelack motif order.

This is a read-only architecture diagnostic.  It maps every exact L4 tuple
back to the causal 10 ms cochlear hops it governs, then converts each field
value only to its balanced-ternary commitment sign for the scoring rule in the
original Krimelack paper.  It does not grant recognition authority, alter
L0-L4, or propose that this reduced view replace the authoritative full field.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from dsf_ai_service.glew_runtime.exact_field_executor import (
    start_exact_field_executor,
    stop_exact_field_executor,
)
from dsf_ai_service.substrate.auditory_l4_causal_support import (
    mount_auditory_l4_causal_support,
)
from dsf_ai_service.substrate.auditory_l5 import AuditoryL5Owner
from tools.probe_auditory_surrounded_event_recognition import _experience


RECORDINGS = (
    Path("/workspaces/Tao_Financial_Engine/harness/Hello Guala.mp3"),
    Path("/workspaces/Tao_Financial_Engine/harness/hello guala 1.mp3"),
    Path("/workspaces/Tao_Financial_Engine/harness/hello guala 2.mp3"),
    Path("/workspaces/Tao_Financial_Engine/docs/Daddy says Hello.mp3"),
    Path("/workspaces/Tao_Financial_Engine/docs/Your Name is Guala.mp3"),
)


def _sign(value: object) -> int:
    return 1 if value > 0 else -1 if value < 0 else 0


def _motifs(experience):
    support = mount_auditory_l4_causal_support(experience)
    frame_count = len(experience.channels[0].pressure.samples)
    field_names = tuple(
        name
        for name, _value in support.components[0].tuples[0].fields
    )
    by_component = []
    for component in support.components:
        by_frame = [None] * frame_count
        for field_tuple in component.tuples:
            motif = tuple(_sign(value) for _name, value in field_tuple.fields)
            for index in range(
                field_tuple.source_index_start,
                field_tuple.source_index_end + 1,
            ):
                if by_frame[index] is not None:
                    raise RuntimeError("L4 causal support overlapped one hop")
                by_frame[index] = motif
        if any(value is None for value in by_frame):
            raise RuntimeError("L4 causal support omitted one hop")
        by_component.append(tuple(by_frame))
    return field_names, tuple(
        tuple(
            value
            for component in by_component
            for value in component[index]
        )
        for index in range(frame_count)
    )


def _motif_id(motif) -> str:
    return hashlib.sha256(bytes(value + 1 for value in motif)).hexdigest()


def _ngrams(motifs, width: int):
    ids = tuple(_motif_id(value) for value in motifs)
    return {
        ids[index:index + width]
        for index in range(len(ids) - width + 1)
    }


def _overlap(left, right, width: int) -> dict[str, object]:
    left_ngrams = _ngrams(left, width)
    right_ngrams = _ngrams(right, width)
    shared = left_ngrams & right_ngrams
    return {
        "width": width,
        "left_unique": len(left_ngrams),
        "right_unique": len(right_ngrams),
        "shared": len(shared),
        "left_fraction": (
            len(shared) / len(left_ngrams) if left_ngrams else 0.0
        ),
        "right_fraction": (
            len(shared) / len(right_ngrams) if right_ngrams else 0.0
        ),
    }


def main() -> None:
    executor = start_exact_field_executor()
    executor.assert_healthy()
    owner = AuditoryL5Owner(log_event=lambda *_args, **_kwargs: None)
    try:
        experiences = []
        for ordinal, path in enumerate(RECORDINGS):
            experience, report = _experience(path, ordinal, owner)
            experiences.append(experience)
            print(
                "settled",
                path.name,
                "event_frames",
                report["event_frame_count"],
                flush=True,
            )
    finally:
        stop_exact_field_executor()

    motifs = []
    for path, experience in zip(RECORDINGS, experiences, strict=True):
        field_names, recording_motifs = _motifs(experience)
        motifs.append(recording_motifs)
        print(
            "motif",
            path.name,
            "fields",
            field_names,
            "frames",
            len(recording_motifs),
            "unique_motifs",
            len(set(recording_motifs)),
            "trits_per_frame",
            len(recording_motifs[0]),
        )

    print("PAIR_ORDERED_EXACT_MOTIF_NGRAM_OVERLAP")
    for left in range(len(RECORDINGS)):
        for right in range(left + 1, len(RECORDINGS)):
            print(
                RECORDINGS[left].name,
                "VS",
                RECORDINGS[right].name,
                tuple(
                    _overlap(motifs[left], motifs[right], width)
                    for width in (1, 2, 3, 4, 6, 8)
                ),
            )


if __name__ == "__main__":
    main()
