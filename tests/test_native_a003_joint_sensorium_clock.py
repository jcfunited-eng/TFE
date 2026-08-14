"""A-003 proof that production senses share one exact native occurrence."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


def test_production_roster_is_one_joint_clock_not_separate_sense_batches() -> None:
    repository = Path(__file__).resolve().parents[1]
    environment = dict(os.environ)
    environment.update(
        {
            "GUALA_CHEMORECEPTION": "1",
            "GUALA_COCHLEAR_EARS": "1",
            "GUALA_NATIVE_ORGANISM_IDENTITY": (
                "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
            ),
            "GUALA_TOUCH_RECEPTORS": "1",
            "GUALA_VESTIBULAR": "1",
            "GUALA_WORLD": "1",
            "PYTHONPATH": str(repository),
        }
    )
    probe = r'''from fractions import Fraction
import json
from dsf_ai_service import native_production_app as production

times = production._quiescent_hop_times()
episode = production._whole_roster_hop_episode(
    "a003-joint-clock-proof",
    times,
    (0.5,) * production.CARD_SURFACE_PORT_COUNT,
    (0.0,) * len(times),
    tasted=(Fraction(0),) * production.TASTE_SITE_COUNT,
    smelled=(Fraction(0),) * production.SMELL_SITE_COUNT,
)
print(json.dumps({
    "group_sizes": [len(group) for group in production._lesson_port_groups()],
    "lesson_occurrence_count": production.LESSON_OCCURRENCE_COUNT,
    "occurrence_count": episode.occurrence_count,
    "occurrence_frame_count": episode.occurrence_frame_count,
    "port_count": episode.port_count,
    "python_callback_count": episode.python_callback_count,
    "schema": episode.schema,
    "source_sample_count": episode.source_sample_count,
    "times": [[value.numerator, value.denominator] for value in times],
}))
'''
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=repository,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    evidence = json.loads(completed.stdout)

    assert evidence["schema"] == "guala.native.exact_joint_source_episode.v2"
    assert evidence["group_sizes"] == [27, 2, 16, 16, 27, 5, 8, 4, 4]
    assert evidence["port_count"] == 109
    assert evidence["lesson_occurrence_count"] == 1
    assert evidence["occurrence_count"] == 1
    assert evidence["occurrence_frame_count"] == 26
    assert evidence["source_sample_count"] == 109 * 26
    assert evidence["python_callback_count"] == 0
    assert evidence["times"][0] == [0, 1]
    assert evidence["times"][-1] == [1, 4]
