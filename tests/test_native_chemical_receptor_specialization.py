"""Small end-to-end proof of the mounted smell/taste receptor path."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_exact_chemical_roster_reaches_and_cold_restores(tmp_path: Path) -> None:
    program = r'''
import json
from fractions import Fraction
from dsf_ai_service import native_production_app as p

p._startup()
times = p._quiescent_hop_times()

def occurrence(name):
    return p._whole_roster_hop_episode(
        name,
        times,
        (0.0,) * p.CARD_SURFACE_PORT_COUNT,
        (0.0,) * len(times),
        tasted=(Fraction(1,2), Fraction(1,4), Fraction(3,4), Fraction(1,8), Fraction(1)),
        smelled=(Fraction(1,8), Fraction(1,4), Fraction(3,8), Fraction(1,2),
                 Fraction(5,8), Fraction(3,4), Fraction(7,8), Fraction(1)),
    )

first = p._perform_admitted_intake(
    [(occurrence("chemical-first"), [(p.INTAKE_HOP_MILLISECONDS, 1000)])],
    "chemical-first",
)
first_record = p._native_record()
first_sha = first_record["state_sha256"]
p._startup()
restored = p._native_record()
repeat = p._perform_admitted_intake(
    [(occurrence("chemical-repeat"), [(p.INTAKE_HOP_MILLISECONDS, 1000)])],
    "chemical-repeat",
)
after = p._native_record()
print(json.dumps({
    "first_layers": first_record["reached_neuron_count_by_layer"],
    "restored_layers": restored["reached_neuron_count_by_layer"],
    "after_layers": after["reached_neuron_count_by_layer"],
    "first_sha": first_sha,
    "restored_sha": restored["state_sha256"],
    "first_neurons": first_record["complete_neuron_count"],
    "after_neurons": after["complete_neuron_count"],
    "first_resting": first_record["developmental_resting_neuron_count"],
    "after_resting": after["developmental_resting_neuron_count"],
    "first_dsf": first["totals"]["dsf_delivery_count"],
    "first_transitions": first["totals"]["physically_transitioned_neuron_count"],
    "first_ingress": first["receptor_ingress"],
    "python_callbacks": after["python_callback_count"],
    "state_bytes": after["state_bytes"],
    "max_fabric_bytes": after["resource_admission"]["max_fabric_bytes"],
    "repeat_mosaics": after["cognitive_mosaic_count"],
    "repeat_dsf": repeat["totals"]["dsf_delivery_count"],
}))
'''
    environment = os.environ.copy()
    environment.update(
        {
            "GUALA_CHEMORECEPTION": "1",
            "GUALA_COCHLEAR_EARS": "0",
            "GUALA_TOUCH_RECEPTORS": "0",
            "GUALA_VESTIBULAR": "0",
            "GUALA_WORLD": "0",
            "GUALA_UNATTENDED_TIME": "0",
            "GUALA_NATIVE_ORGANISM_ROOT": str(tmp_path),
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
    expected_layers = [[0, 27], [3, 8], [4, 5], [6, 40], [7, 1]]
    assert result["first_layers"] == expected_layers
    assert result["restored_layers"] == expected_layers
    assert result["after_layers"] == expected_layers
    assert result["first_sha"] == result["restored_sha"]
    assert result["first_neurons"] == result["after_neurons"] == 81
    assert result["first_resting"] == result["after_resting"]
    assert result["first_dsf"] == result["repeat_dsf"] == 43
    assert result["first_transitions"] > 0
    assert result["first_ingress"] == {
        "changing_count": 0,
        "quiescent_count": 42,
        "sense_counts": {
            "sight": 27,
            "sound": 2,
            "touch": 0,
            "smell": 8,
            "taste": 5,
            "body": 0,
        },
        "source_hop_count": 1,
    }
    assert result["python_callbacks"] == 0
    assert result["repeat_mosaics"] == 0
    assert result["state_bytes"] <= result["max_fabric_bytes"]
