"""Test causal two-unit path composition across a transport boundary.

Each half is independently settled through exact L0--L4 and auditory L5.
The diagnostic then preserves their physical order, composes only their
Krimelack motifs, and applies the same hierarchical reciprocal L6 relation.
It does not fabricate a combined L5 field or receipt.
"""

from __future__ import annotations

import json
from pathlib import Path

from dsf_ai_service.glew_runtime.exact_field_executor import (
    start_exact_field_executor,
    stop_exact_field_executor,
)
from dsf_ai_service.substrate.auditory_krimelack_kind import (
    _matching_locked_motifs,
    mount_auditory_krimelack_path,
)
from dsf_ai_service.substrate.auditory_l5 import AuditoryL5Owner
from dsf_ai_service.substrate.language_fact_strand import (
    canonical_l6_direction,
)
from tools.probe_auditory_krimelack_continuous_chunk import (
    _continuous_experience,
    _event_pcm,
)
from tools.probe_auditory_surrounded_event_recognition import _experience


TUTOR = Path(
    "/workspaces/Tao_Financial_Engine/harness/Hello Guala.mp3"
)
QUERY = Path(
    "/workspaces/Tao_Financial_Engine/harness/hello guala 2.mp3"
)


def main() -> None:
    executor = start_exact_field_executor()
    executor.assert_healthy()
    owner = AuditoryL5Owner(log_event=lambda *_args, **_kwargs: None)
    try:
        tutor = mount_auditory_krimelack_path(
            _experience(TUTOR, 0, owner)[0]
        )
        pcm = _event_pcm(QUERY)
        midpoint = len(pcm) // 4 * 2
        first = mount_auditory_krimelack_path(
            _continuous_experience(
                pcm[:midpoint],
                offset=26_640,
                ordinal=1,
                owner=owner,
            )
        )
        second = mount_auditory_krimelack_path(
            _continuous_experience(
                pcm[midpoint:],
                offset=0,
                ordinal=2,
                owner=owner,
            )
        )
    finally:
        stop_exact_field_executor()
    query_frames = (*first.frames, *second.frames)
    settled = sum(
        any(value != 0 for value in frame)
        for frame in query_frames
    )
    matching = _matching_locked_motifs(
        tutor.frames,
        query_frames,
    )
    tutor_l6 = canonical_l6_direction(
        dimensions=tutor.settled_motifs,
        matching_non_null=matching,
        matching_quiescent=0,
    )
    query_l6 = canonical_l6_direction(
        dimensions=settled,
        matching_non_null=matching,
        matching_quiescent=0,
    )
    print(json.dumps({
        "component_path_receipts": [
            first.authority_receipt_sha256,
            second.authority_receipt_sha256,
        ],
        "matching_locked_motifs": matching,
        "query_l6_locked": query_l6.locked,
        "query_settled_motifs": settled,
        "schema": (
            "guala.audit.auditory_krimelack_composite_boundary.v1"
        ),
        "structurally_locked": tutor_l6.locked and query_l6.locked,
        "tutor_l6_locked": tutor_l6.locked,
        "tutor_settled_motifs": tutor.settled_motifs,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
