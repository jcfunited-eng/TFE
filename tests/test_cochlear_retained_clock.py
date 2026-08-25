"""The mounted cochlea retains its own physical observation clock."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from fractions import Fraction


ROOT = Path(__file__).resolve().parents[1]


def test_authorized_cochlea_does_not_repeat_envelopes_on_pcm_grid() -> None:
    program = r'''
import json
from fractions import Fraction
from dsf_ai_service import native_production_app as production
from guala_core import exact_articulatory_interval_trajectory

observed_filter_input_lengths = []
real_filter = production.auditory_gammatone_field

def measured_filter(signal, *args):
    observed_filter_input_lengths.append(len(signal))
    return real_filter(signal, *args)

production.auditory_gammatone_field = measured_filter
samples = (0,) * production.COCHLEAR_SAMPLE_RATE_HZ
pcm_hops = production._pcm_hops(
    samples,
    production.COCHLEAR_SAMPLE_RATE_HZ,
)
cochlear_hops = production._cochlear_hops(
    samples,
    production.COCHLEAR_SAMPLE_RATE_HZ,
)
sample_rate_hz, pressure, body, *_ = exact_articulatory_interval_trajectory(
    intervals=((16_000, ((0, 8),)),)
)
body_hops = production._articulatory_body_hops(
    body,
    len(pressure),
    sample_rate_hz,
)
body_pcm_hops = production._pcm_hops(pressure, sample_rate_hz)
quiet = production._quiescent_hop_times()
print(json.dumps({
    "pcm_clocks": [[(v.numerator, v.denominator) for v in times] for times, _ in pcm_hops],
    "cochlear_clocks": [[(v.numerator, v.denominator) for v in times] for times, _ in cochlear_hops],
    "body_widths": [[len(channel) for channel in hop] for hop in body_hops],
    "body_pcm_widths": [len(times) for times, _ in body_pcm_hops],
    "quiet": [(v.numerator, v.denominator) for v in quiet],
    "filter_input_lengths": observed_filter_input_lengths,
}))
'''
    environment = os.environ.copy()
    environment.update(
        {
            "GUALA_COCHLEAR_EARS": "1",
            "GUALA_TOUCH_RECEPTORS": "1",
            "GUALA_INTEROCEPTION": "0",
            "GUALA_CHEMORECEPTION": "1",
            "GUALA_VESTIBULAR": "1",
            "GUALA_WORLD": "1",
            "PYTHONPATH": str(ROOT),
        }
    )
    completed = subprocess.run(
        [sys.executable, "-c", program],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout)
    expected_clock = [
        [Fraction(index, 100).numerator, Fraction(index, 100).denominator]
        for index in range(26)
    ]
    assert result["pcm_clocks"] == [expected_clock] * 4
    assert result["cochlear_clocks"] == [expected_clock] * 4
    assert result["quiet"] == expected_clock
    assert result["body_pcm_widths"] == [26] * len(result["body_widths"])
    assert all(widths == [26] * 4 for widths in result["body_widths"])
    assert result["filter_input_lengths"][0] == 16_160


def test_roster_without_cochlea_keeps_bounded_pcm_transport_grid() -> None:
    program = r'''
import json
from dsf_ai_service import native_production_app as production

samples = (0,) * production.COCHLEAR_SAMPLE_RATE_HZ
hops = production._pcm_hops(samples, production.COCHLEAR_SAMPLE_RATE_HZ)
quiet = production._quiescent_hop_times()
print(json.dumps({
    "hop_widths": [len(times) for times, _ in hops],
    "quiet_width": len(quiet),
}))
'''
    environment = os.environ.copy()
    environment.update(
        {
            "GUALA_COCHLEAR_EARS": "0",
            "PYTHONPATH": str(ROOT),
        }
    )
    completed = subprocess.run(
        [sys.executable, "-c", program],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout)
    assert result == {
        "hop_widths": [251, 251, 251, 251],
        "quiet_width": 251,
    }
