from __future__ import annotations

import hashlib
import math
import struct

from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    REQUIRED_SAMPLE_RATE_HZ,
)
from tools.probe_auditory_bilateral_cross_receptor_resonance_trajectory import (
    EDGE_COUNT,
    L4_SUPPORT_COUNT,
    TrajectoryState,
    _transduce_pcm,
    build_trajectory,
    relate_trajectories,
)


SAMPLE_COUNT = 1_600


def _tone(frequency: int, *, gain: int = 1) -> bytes:
    values = tuple(
        gain * int(
            2_000 * math.sin(
                2.0
                * math.pi
                * frequency
                * index
                / REQUIRED_SAMPLE_RATE_HZ
            )
        )
        for index in range(SAMPLE_COUNT)
    )
    return struct.pack(f"<{len(values)}h", *values)


def _trajectory(left: bytes, right: bytes, *, identity: str):
    supports = tuple(
        hashlib.sha256(
            f"{identity}:support:{index}".encode("ascii")
        ).hexdigest()
        for index in range(L4_SUPPORT_COUNT)
    )
    return build_trajectory(
        left_capture=_transduce_pcm(left),
        right_capture=_transduce_pcm(right),
        l4_support_receipt_sha256s=supports,
        source_receipt_sha256s=(
            hashlib.sha256(left).hexdigest(),
            hashlib.sha256(right).hexdigest(),
        ),
    )


def test_complete_bilateral_topology_retains_every_edge_and_l4_support():
    left = _tone(440)
    right = bytes(8) + left[:-8]
    trajectory = _trajectory(left, right, identity="complete")

    trajectory.verify()
    assert trajectory.state is TrajectoryState.OBSERVED
    assert trajectory.spatially_resolved is True
    assert len(trajectory.edge_facts) == EDGE_COUNT == 496
    assert len(trajectory.l4_support_receipt_sha256s) == 64
    assert trajectory.edge_facts[0].left_vertex == "left:erb_00"
    assert trajectory.edge_facts[-1].right_vertex == "right:erb_15"


def test_identical_ears_are_explicitly_spatially_unresolved():
    signal = _tone(440)
    trajectory = _trajectory(signal, signal, identity="mono-control")

    trajectory.verify()
    assert trajectory.spatially_resolved is False


def test_relation_uses_edge_facts_not_scalar_meet_or_support_receipts():
    left = _tone(440)
    right = bytes(8) + left[:-8]
    first = _trajectory(left, right, identity="first")
    second = _trajectory(left, right, identity="second")

    assert first.authority_receipt_sha256 != second.authority_receipt_sha256
    relation = relate_trajectories(first, second)
    assert relation["relation_locked"] is True
    assert relation["exact_matching_edge_fact_count"] == EDGE_COUNT
    assert relation["scalar_meet_used"] is False


def test_distinct_physical_tones_do_not_exactly_lock():
    first_pcm = _tone(440)
    second_pcm = _tone(880)
    first = _trajectory(
        first_pcm,
        bytes(8) + first_pcm[:-8],
        identity="tone-440",
    )
    second = _trajectory(
        second_pcm,
        bytes(8) + second_pcm[:-8],
        identity="tone-880",
    )

    relation = relate_trajectories(first, second)
    assert relation["relation_locked"] is False
    assert relation["exact_matching_edge_fact_count"] < EDGE_COUNT
