"""Focused live-boundary proof for core and cutaneous thermoreceptors."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_exact_thermal_body_reaches_neurons_and_cold_restores(
    tmp_path: Path,
) -> None:
    program = r'''
import json
from dsf_ai_service import native_production_app as p

p._startup()
times = p._quiescent_hop_times()
episode = p._whole_roster_hop_episode(
    "thermal-body-first",
    times,
    (0.0,) * p.CARD_SURFACE_PORT_COUNT,
    (0.0,) * len(times),
)
result = p._perform_admitted_intake(
    [(episode, [(p.INTAKE_HOP_MILLISECONDS, 1000)])],
    "thermal-body-first",
)
before = p._native_record()
temperature_before = p._temperature_record(before)
p._persist_world(p._world())
p._world_authority = None
p._startup()
after = p._native_record()
temperature_after = p._temperature_record(after)
print(json.dumps({
    "body_layer_before": dict(before["reached_neuron_count_by_layer"]).get(5, 0),
    "body_layer_after": dict(after["reached_neuron_count_by_layer"]).get(5, 0),
    "core_sites": p._runtime()[0].organism.observe_reached_source_site_count(
        p.THERMAL_SENSOR_ID, "temperature-core"
    ),
    "cutaneous_sites": p._runtime()[0].organism.observe_reached_source_site_count(
        p.THERMAL_SENSOR_ID, "temperature-cutaneous-shell"
    ),
    "first_dsf": result["totals"]["dsf_delivery_count"],
    "first_transitions": result["totals"]["physically_transitioned_neuron_count"],
    "port_count": episode.port_count,
    "python_callbacks": after["python_callback_count"],
    "state_before": before["state_sha256"],
    "state_after": after["state_sha256"],
    "temperature_before": temperature_before,
    "temperature_after": temperature_after,
}))
'''
    environment = os.environ.copy()
    environment.update(
        {
            "GUALA_CHEMORECEPTION": "0",
            "GUALA_COCHLEAR_EARS": "0",
            "GUALA_TOUCH_RECEPTORS": "0",
            "GUALA_UNATTENDED_TIME": "0",
            "GUALA_VESTIBULAR": "0",
            "GUALA_WORLD": "1",
            "GUALA_NATIVE_ORGANISM_IDENTITY": (
                "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
            ),
            "GUALA_NATIVE_ORGANISM_ROOT": str(tmp_path),
            "PYTHONPATH": str(ROOT),
        }
    )
    completed = subprocess.run(
        [sys.executable, "-c", program],
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    evidence = json.loads(completed.stdout)

    assert evidence["port_count"] == 35
    assert evidence["core_sites"] == evidence["cutaneous_sites"] == 1
    assert evidence["body_layer_before"] == evidence["body_layer_after"] == 6
    assert evidence["first_dsf"] > 0
    assert evidence["first_transitions"] > 0
    assert evidence["python_callbacks"] == 0
    assert evidence["state_before"] == evidence["state_after"]
    assert evidence["temperature_before"] == evidence["temperature_after"]
    assert evidence["temperature_after"]["available"] is True
    assert evidence["temperature_after"]["native_neuronal_participation"] is True
