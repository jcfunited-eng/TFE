"""Permanent sustained-capture proof for production-sized W1 hearing."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_eight_full_five_second_binaural_experiences_remain_bounded() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.probe_w1_sustained_five_second_binaural_authority",
        ],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=90,
    )
    report = json.loads(completed.stdout)

    assert report["capture_count"] == 8
    assert report["deadline_met_for_every_capture"] is True
    assert report["exact_final_restore"] is True
    assert report["raw_media_zero_after_every_commit"] is True
    assert all(
        capture["compact_authority_bytes"]
        <= report["compact_authority_limit_bytes"]
        and capture["snapshot_bytes"]
        <= report["snapshot_limit_bytes"]
        and capture["transition_relations"]
        <= report["transition_capacity"]
        for capture in report["captures"]
    )
    saturated = report["captures"][4:]
    assert all(
        capture["transition_relations"] == report["transition_capacity"]
        for capture in saturated
    )
