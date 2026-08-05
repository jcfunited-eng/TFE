from __future__ import annotations

import hashlib
import json
from dataclasses import fields, is_dataclass
from pathlib import Path

import pandas as pd

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from uf_core.layer0 import compute_sev_series
from uf_core.layer1 import build_gate_l1_state, segment_gates
from uf_core.layer2 import interpret_gates
from uf_core.layer3 import compute_resonance
from uf_core.layer4 import compute_directional_signal, compute_dsf


_ROOT = Path(__file__).resolve().parents[1]
_BASELINE_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "uf_kernel_backward_compatibility_baseline_v1.json"
)
_FIXTURES = {
    "financial_positive": [
        100, 100.1, 100.2, 100.15, 100.4, 101.0, 100.7, 100.72,
        100.73, 99.9, 99.5, 99.8, 100.4, 100.45, 101.8, 101.7,
        101.71, 102.5, 101.9, 102.1, 103.0, 102.8, 103.5, 103.6,
    ],
    "thermal_positive": [
        300, 300, 300.01, 300.02, 300.02, 300.5, 301.0, 301.5,
        301.49, 301.48, 300.0, 299.5, 299.7, 300.2, 302.0, 304.0,
        303.0, 302.5, 302.51, 302.52, 305.0, 304.0, 304.2, 304.3,
    ],
    "physiological_positive": [
        1.0, 1.02, 0.99, 1.01, 1.00, 1.08, 0.94, 1.03,
        0.98, 1.04, 0.97, 1.05, 0.96, 1.06, 0.95, 1.07,
        1.00, 1.01, 1.02, 0.99, 1.0, 1.12, 0.9, 1.0,
    ],
    "adapted_signed_sensor": [
        1 + value / 2
        for value in (
            0, .1, .2, -.1, -.4, .8, -.8, .3, -.2, .9, -.9, .5,
            -.5, .25, -.25, .75, -.75, .05, -.05, .6, -.6, .4,
            -.4, 0,
        )
    ],
    "quiescent": [2.0] * 24,
}


def _normalize(value: object) -> object:
    if isinstance(value, float):
        return value.hex()
    if is_dataclass(value):
        return {
            item.name: _normalize(getattr(value, item.name))
            for item in fields(value)
        }
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {
            key: _normalize(item)
            for key, item in sorted(value.items())
        }
    return value


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")).hexdigest()


def _run_case(values: list[float]) -> tuple[str, int, int]:
    sev = compute_sev_series(
        pd.DataFrame({"signal": values}),
        field_col="signal",
    )
    gates = segment_gates(sev)
    layer1 = build_gate_l1_state(sev, gates)
    layer2 = interpret_gates(sev, gates)
    layer3 = compute_resonance(layer2)
    layer4 = compute_dsf(compute_directional_signal(layer3))
    record = {
        "gates": _normalize(gates),
        "input": [float(value).hex() for value in values],
        "l1": _normalize(layer1),
        "l2": _normalize(layer2),
        "l3": _normalize(layer3),
        "l4": _normalize(layer4),
        "sev": _normalize(sev),
    }
    return _digest(record), len(gates), len(layer4)


def test_canonical_kernel_sources_match_frozen_v1_hashes() -> None:
    baseline = json.loads(_BASELINE_PATH.read_text(encoding="utf-8"))
    actual = []
    for expected in baseline["canonical_sources"]:
        encoded = (_ROOT / expected["path"]).read_bytes()
        row = {
            "bytes": len(encoded),
            "path": expected["path"],
            "sha256": hashlib.sha256(encoded).hexdigest(),
        }
        assert row == expected
        # Machine-independent rows only: the v1 bundle digest embedded the
        # absolute checkout path, so it could never pass outside the machine
        # that froze it. The per-file sha256 asserts above are the real guard.
        actual.append({
            "relative_path": expected["path"],
            "sha256": row["sha256"],
            "size_bytes": row["bytes"],
        })
    assert _digest(actual) == baseline["canonical_source_bundle_v2_sha256"]


def test_default_profile_is_bit_exact_for_non_auditory_domains() -> None:
    baseline = json.loads(_BASELINE_PATH.read_text(encoding="utf-8"))
    actual = {}
    for name, values in _FIXTURES.items():
        digest, gate_count, dsf_count = _run_case(values)
        actual[name] = {
            "dsf_count": dsf_count,
            "gate_count": gate_count,
            "sha256": digest,
        }
    assert actual == baseline["behavior_cases"]
    assert _digest(actual) == baseline["behavior_bundle_sha256"]


def test_default_profile_preserves_complete_ordered_dsf_surface() -> None:
    baseline = json.loads(_BASELINE_PATH.read_text(encoding="utf-8"))
    assert list(DSF_FIELD_ORDER) == baseline["dsf_field_order"]
    assert baseline["complete_trace_schemas"] == [
        "glew.provider.complete_signed_port_l0_l4_trace.v3",
        "glew.provider.complete_physical_port_l0_l4_trace.v4",
    ]
