#!/usr/bin/env python3
"""tests/test_combinatorial_chains_monitor.py — Combinatorial Chain & Trajectory Monitor Tests.

Physics & Verification Invariants:
1. Acoustic Drive Invariance: Acoustic formant tuples (p, f1, f2) map deterministically to phonemes.
2. Topological Region Invariance: Continuous 2D coordinates map to exact 10 home world room manifolds.
3. Temporal Clustering: Syllable emissions within delta_tick <= 50 cluster into multi-beat chains.
4. Information Entropy & Syntactic Mutual Information: Quantifies phonemic diversity and transition syntax.
5. Non-Ergodic Discovery: Measures expansion rate of unique combinatorial chain repertoire.
6. Cryptographic Ledger Idempotency: SHA-256 receipt tracking prevents duplicate ledger appends.
7. Universal Physics Floor: Validates that live developmental telemetry satisfies composite score >= 0.85.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from tools.monitor_combinatorial_chains import (
    DRIVE_TO_SYLLABLE,
    PHYSICS_FLOOR,
    REGION_BOUNDS,
    SpatialTrajectory,
    VocalChain,
    append_chains_to_ledger,
    compute_non_ergodicity_expansion,
    compute_spatial_trajectory_metrics,
    compute_vocal_chain_entropy_and_mutual_info,
    extract_spatial_trajectories_from_text,
    extract_vocal_chains_from_text,
    point_to_region,
    run_combinatorial_monitor,
)


def test_drive_to_syllable_mapping() -> None:
    """Verify acoustic formant drives map deterministically to canonical syllable tokens."""
    # 1. Register 0 (pitch 3450)
    assert DRIVE_TO_SYLLABLE.get((3450, 0, 0)) == "ah0"
    assert DRIVE_TO_SYLLABLE.get((3450, 2, 3)) == "dee0"

    # 2. Register 1 (pitch 3600)
    assert DRIVE_TO_SYLLABLE.get((3600, 2, 3)) == "dee1"
    assert DRIVE_TO_SYLLABLE.get((3600, 1, 9)) == "neh1"

    # 3. Register 2 (pitch 3750)
    assert DRIVE_TO_SYLLABLE.get((3750, 4, 8)) == "loo2"
    assert DRIVE_TO_SYLLABLE.get((3750, 3, 6)) == "toh2"

    # 4. Total phonemic space
    assert len(DRIVE_TO_SYLLABLE) >= 220


def test_point_to_region_bounds() -> None:
    """Verify continuous coordinates map to the 10 topological region manifolds."""
    test_cases = [
        (2_500, 7_500, "her-room"),
        (7_000, 7_500, "hallway"),
        (11_000, 7_500, "library"),
        (16_000, 7_500, "tv-room"),
        (3_500, 2_500, "kitchen"),
        (9_500, 2_500, "dining"),
        (14_000, 2_500, "daddys-room"),
        (18_000, 2_500, "wcs-room"),
        (10_000, 13_000, "backyard"),
        (10_000, 19_000, "walkway"),
    ]
    for x, y, expected_reg in test_cases:
        assert point_to_region(x, y) == expected_reg, f"Coord ({x}, {y}) should be in {expected_reg}"


def test_extract_vocal_chains_from_synthetic_events() -> None:
    """Verify temporal clustering groups emissions into multi-beat chains with SHA-256 receipts."""
    # Sample log lines with known timestamps
    synthetic_log = """
    2026-09-20T01:00:00Z echo: echoed her syllable drive=[3600, 2, 3] from person-body-1 at tick 100
    2026-09-20T01:00:10Z echo: echoed her syllable drive=[3600, 1, 9] from person-body-1 at tick 120
    2026-09-20T01:00:20Z echo: echoed her syllable drive=[3600, 0, 3] from person-body-1 at tick 140
    2026-09-20T01:05:00Z echo: echoed her syllable drive=[3750, 4, 8] from person-body-1 at tick 500
    2026-09-20T01:05:10Z echo: echoed her syllable drive=[3750, 3, 6] from person-body-1 at tick 525
    2026-09-20T01:10:00Z echo: echoed her syllable drive=[3450, 0, 0] from person-body-1 at tick 1000
    """
    chains, events = extract_vocal_chains_from_text(synthetic_log, max_tick_delta=50)

    assert len(events) == 6
    assert len(chains) == 2  # tick 100-140 (3 beats) and tick 500-525 (2 beats); tick 1000 is isolated

    # Chain 1: dee1 -> neh1 -> dah1 (3 beats, duration 40 ticks)
    c1 = chains[0]
    assert c1.syllables == ("dee1", "neh1", "dah1")
    assert c1.length == 3
    assert c1.duration_ticks == 40
    assert len(c1.receipt_sha256) == 64

    # Chain 2: loo2 -> toh2 (2 beats, duration 25 ticks)
    c2 = chains[1]
    assert c2.syllables == ("loo2", "toh2")
    assert c2.length == 2
    assert c2.duration_ticks == 25


def test_vocal_entropy_and_mutual_information() -> None:
    """Verify calculation of vocabulary entropy H(S) and transition constraint mutual information."""
    synthetic_log = """
    echo: drive=[3600, 2, 3] at tick 100
    echo: drive=[3600, 1, 9] at tick 120
    echo: drive=[3600, 0, 3] at tick 140
    echo: drive=[3750, 4, 8] at tick 500
    echo: drive=[3750, 3, 6] at tick 520
    echo: drive=[3600, 2, 3] at tick 700
    echo: drive=[3600, 1, 9] at tick 720
    """
    chains, events = extract_vocal_chains_from_text(synthetic_log)
    metrics = compute_vocal_chain_entropy_and_mutual_info(events, chains)

    assert metrics["total_syllable_tokens"] == 7
    assert metrics["unique_syllables"] >= 4
    assert metrics["shannon_entropy_bits"] > 1.5
    assert metrics["entropy_ratio"] > 0.70
    assert metrics["total_chains"] == 3
    assert metrics["max_chain_length"] == 3


def test_spatial_trajectory_extraction_and_crossings() -> None:
    """Verify extraction of continuous coordinates and detection of portal transitions."""
    synthetic_log = """
    housekeeping: returning displaced pillow from (2500, 7500) to her bed
    housekeeping: returning displaced pillow from (4500, 7500) to her bed
    housekeeping: returning displaced pillow from (6500, 7500) to her bed
    housekeeping: returning displaced pillow from (7500, 7500) to her bed
    housekeeping: returning displaced pillow from (9500, 7500) to her bed
    """
    trajs = extract_spatial_trajectories_from_text(synthetic_log)
    assert len(trajs) >= 1

    t = trajs[0]
    # Path: her-room (2500, 4500) -> hallway (6500, 7500) -> library (9500)
    assert "her-room" in t.regions
    assert "hallway" in t.regions
    assert "library" in t.regions
    assert t.portal_crossings >= 2

    metrics = compute_spatial_trajectory_metrics(trajs)
    assert metrics["total_portal_crossings"] >= 2
    assert "hallway" in metrics["regions_visited"]
    assert metrics["score"] >= PHYSICS_FLOOR


def test_non_ergodicity_expansion_metric() -> None:
    """Verify non-ergodicity metric quantifies repertoire growth rate."""
    rec = "a" * 64
    c1 = VocalChain(("ah0", "bah0"), 1, 20, 19, rec)
    c2 = VocalChain(("dah0", "gah0"), 30, 50, 20, rec)
    c3 = VocalChain(("ah0", "bah0"), 60, 80, 20, rec)  # duplicate
    c4 = VocalChain(("lah0", "nah0"), 90, 110, 20, rec)

    metrics = compute_non_ergodicity_expansion([c1, c2, c3, c4])
    assert metrics["total_chains"] == 4
    assert metrics["unique_chains"] == 3
    assert metrics["cumulative_growth_ratio"] == 0.75
    assert metrics["non_ergodic_expansion"] is True
    assert metrics["score"] == 1.0


def test_ledger_append_and_idempotency(tmp_path: Path) -> None:
    """Verify newly emergent chains append atomically to the cryptographic JSONL ledger without duplicates."""
    ledger_file = tmp_path / "test_chains.jsonl"
    rec1 = "11" * 32
    rec2 = "22" * 32
    c1 = VocalChain(("ah0", "bah0"), 100, 130, 30, rec1)
    c2 = VocalChain(("dah0", "gah0"), 200, 230, 30, rec2)

    # First append: 2 entries
    count1 = append_chains_to_ledger([c1, c2], [], ledger_path=ledger_file)
    assert count1 == 2

    # Verify content
    lines = [json.loads(l) for l in ledger_file.read_text().strip().split("\n")]
    assert len(lines) == 2
    assert lines[0]["receipt_sha256"] == rec1
    assert lines[1]["receipt_sha256"] == rec2

    # Second append with same receipts: 0 new entries (idempotent)
    count2 = append_chains_to_ledger([c1, c2], [], ledger_path=ledger_file)
    assert count2 == 0

    # Append one new chain: 1 new entry
    rec3 = "33" * 32
    c3 = VocalChain(("lah0", "nah0"), 300, 330, 30, rec3)
    count3 = append_chains_to_ledger([c1, c3], [], ledger_path=ledger_file)
    assert count3 == 1
    assert len(ledger_file.read_text().strip().split("\n")) == 3


def test_run_combinatorial_monitor_with_live_log(tmp_path: Path) -> None:
    """Verify complete combinatorial monitor against actual developmental caretaker logs."""
    test_ledger = tmp_path / "live_test_ledger.jsonl"
    report = run_combinatorial_monitor(ledger_path=test_ledger, append_ledger=True)

    # 1. Physics Floor Invariant
    assert report["composite_score"] >= PHYSICS_FLOOR
    assert report["overall_pass"] is True

    # 2. Vocal Chains Verified
    vm = report["vocal_combinatorial_metrics"]
    assert vm["total_chains"] > 50
    assert vm["max_chain_length"] >= 3
    assert vm["shannon_entropy_bits"] > 5.0
    assert vm["entropy_ratio"] >= 0.85

    # 3. Spatial Exploration Verified
    sm = report["spatial_trajectory_metrics"]
    assert sm["total_trajectories"] > 10
    assert len(sm["regions_visited"]) >= 2
    assert sm["total_portal_crossings"] >= 5

    # 4. Non-Ergodicity Verified
    em = report["non_ergodicity_expansion"]
    assert em["unique_chains"] > 50
    assert em["cumulative_growth_ratio"] > 0.80

    # 5. Cryptographic Ledger Output
    assert test_ledger.exists()
    assert report["ledger_entries_appended"] > 0
