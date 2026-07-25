"""Focused acceptance tests for the isolated source-identity experiment."""

from __future__ import annotations

import json
import importlib.util
from pathlib import Path
import sys

import numpy as np
import pytest

_PROBE_PATH = (
    Path(__file__).resolve().parents[1]
    / "tools"
    / "full_field_source_identity_probe.py"
)
_PROBE_SPEC = importlib.util.spec_from_file_location(
    "full_field_source_identity_probe", _PROBE_PATH
)
assert _PROBE_SPEC is not None and _PROBE_SPEC.loader is not None
_PROBE = importlib.util.module_from_spec(_PROBE_SPEC)
sys.modules[_PROBE_SPEC.name] = _PROBE
_PROBE_SPEC.loader.exec_module(_PROBE)

FIELD_NAMES = _PROBE.FIELD_NAMES
FREQUENCY_LANES_HZ = _PROBE.FREQUENCY_LANES_HZ
NYQUIST_HZ = _PROBE.NYQUIST_HZ
SAMPLE_RATE_HZ = _PROBE.SAMPLE_RATE_HZ
build_report = _PROBE.build_report
build_stimuli = _PROBE.build_stimuli
frequency_time_lanes = _PROBE.frequency_time_lanes


@pytest.fixture(scope="module")
def report():
    return build_report()


def test_controlled_stimuli_are_deterministic_distinct_and_full_spectrum():
    first = build_stimuli()
    second = build_stimuli()

    assert tuple(first) == (
        "source_a_utterance_one",
        "source_a_utterance_two",
        "source_b_utterance_one",
        "music",
        "mixture",
    )
    for name in first:
        np.testing.assert_array_equal(first[name], second[name])
        assert first[name].dtype == np.float64
        assert np.isfinite(first[name]).all()

    assert not np.array_equal(
        first["source_a_utterance_one"], first["source_a_utterance_two"]
    )
    assert not np.array_equal(
        first["source_a_utterance_one"], first["source_b_utterance_one"]
    )
    assert FREQUENCY_LANES_HZ[0][0] == 0
    assert FREQUENCY_LANES_HZ[-1][1] == SAMPLE_RATE_HZ // 2 == NYQUIST_HZ
    assert all(
        left[1] == right[0]
        for left, right in zip(FREQUENCY_LANES_HZ, FREQUENCY_LANES_HZ[1:])
    )

    for signal in first.values():
        lanes = frequency_time_lanes(signal)
        assert len(lanes) == len(FREQUENCY_LANES_HZ)
        assert all(np.isfinite(values).all() for values in lanes.values())
        assert all(np.all(values > 0.0) for values in lanes.values())


def test_every_lane_preserves_canonical_upstream_and_all_l4_fields(report):
    assert report["scope"] == {
        "isolated": True,
        "production_code_modified": False,
        "machine_learning_used": False,
        "fitted_threshold_used": False,
        "l0_l4_modified": False,
    }
    assert report["kernel_contract"]["retained_l4_fields"] == list(FIELD_NAMES)
    assert report["kernel_contract"]["authority_relevance_mode"] == "legacy_unit"
    assert report["kernel_contract"]["diagnostic_relevance_mode"] == (
        "structural_activity_diagnostic"
    )
    assert report["kernel_contract"]["diagnostic_is_production_authority"] is False

    for case in report["cases"].values():
        authority = case["authority_l0_l4"]
        diagnostic = case["diagnostic_only_l0_l4"]
        assert tuple(authority) == tuple(diagnostic)
        for lane_name in authority:
            for result, expected_mode in (
                (authority[lane_name], "legacy_unit"),
                (diagnostic[lane_name], "structural_activity_diagnostic"),
            ):
                assert result["relevance_mode"] == expected_mode
                assert result["l0_sev"]
                assert result["l1_gates"]
                assert result["l2_interpretations"]
                assert result["l3_resonance"]
                assert result["l4_dsf"]
                for field in result["l4_dsf"]:
                    assert set(FIELD_NAMES).issubset(field)
                    assert all(np.isfinite(field[name]) for name in FIELD_NAMES)


def test_current_authority_does_not_force_source_identity(report):
    separation = report["authority_separation"]
    assert separation["all_fields_strictly_separated"] is False
    assert not any(
        separation["within_strictly_below_both_between_by_field"].values()
    )
    # The same-source second utterance is structurally closer to the wrong
    # exemplar in every retained field.  The experiment must therefore reject
    # identity instead of adding a fitted threshold to rescue the answer.
    same_source_query = separation["exemplar_queries"][
        "source_a_utterance_two"
    ]
    assert same_source_query["candidate"] == "source_b"
    assert report["identity_decision"]["status"] == "identity_not_decidable"
    assert report["identity_decision"]["chi_or_ternary_used_as_authority"] is False
    assert report["identity_decision"][
        "diagnostic_relevance_used_as_authority"
    ] is False


def test_secondary_recurrence_reports_collision_and_unknown(report):
    recurrence = report["isolated_living_atlas_recurrence"]
    assert recurrence["authority"] is False
    assert recurrence["atlas_isolated"] is True
    assert recurrence["forced_collision_check"]["status"] == "collision_unknown"
    assert recurrence["forced_collision_check"]["candidate_motif_ids"] == [1, 2]
    assert recurrence["queries"]["source_a_utterance_two"]["status"] == (
        "no_recurrence_unknown"
    )
    assert recurrence["queries"]["mixture"]["status"] == (
        "no_recurrence_unknown"
    )
    # The naturally identical chi for different sources is preserved as a
    # collision, demonstrating why chi cannot be promoted to identity authority.
    secondary_a = report["cases"]["source_a_utterance_one"][
        "secondary_structure"
    ]
    secondary_b = report["cases"]["source_b_utterance_one"][
        "secondary_structure"
    ]
    assert secondary_a["chi"] == secondary_b["chi"]
    assert secondary_a["authority"] is False
    assert secondary_b["authority"] is False


def test_report_is_machine_readable_and_measures_resources(report):
    encoded = json.dumps(report, allow_nan=False, sort_keys=True)
    decoded = json.loads(encoded)
    assert decoded["schema"] == "tfe.experiment.full_field_source_identity.v1"
    assert decoded["resources"]["runtime_ms"] > 0.0
    assert decoded["resources"]["tracemalloc_peak_bytes"] > 0
    assert decoded["resources"]["audio_input_bytes"] > 0
    assert all(case["runtime_ms"] > 0.0 for case in decoded["cases"].values())
