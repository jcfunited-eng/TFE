import numpy as np
import pandas as pd
import pytest

from uf_core.layer0 import RelevanceMode, compute_sev_series
from uf_core.config import KERNEL_THRESHOLDS
from uf_core.layer1 import build_gate_l1_state, segment_gates


def _frame(values):
    return pd.DataFrame(
        {"signal": np.asarray(values, dtype=float)},
        index=np.arange(len(values)),
    )


def test_legacy_relevance_default_is_unchanged():
    sev = compute_sev_series(_frame(np.ones(32)), "signal")

    assert all(sample.relevance == 1.0 for sample in sev)


def test_structural_activity_relevance_uses_canonical_deviation_growth():
    values = 2.0 + 0.25 * np.sin(np.linspace(0.0, 4.0 * np.pi, 64))
    sev = compute_sev_series(
        _frame(values),
        "signal",
        relevance_mode=RelevanceMode.STRUCTURAL_ACTIVITY_DIAGNOSTIC,
    )

    for sample in sev:
        deviation = (
            KERNEL_THRESHOLDS.alpha1 * abs(sample.dF)
            + KERNEL_THRESHOLDS.alpha2 * sample.sigma
            + KERNEL_THRESHOLDS.alpha3 * sample.kappa
        )
        expected = (
            0.0
            if sample.N == 1
            else deviation / (deviation + KERNEL_THRESHOLDS.tau_D)
        )
        assert sample.relevance == expected

    assert any(0.0 < sample.relevance < 1.0 for sample in sev)


def test_constant_field_reaches_canonical_negative_space_gate():
    sev = compute_sev_series(
        _frame(np.ones(64)),
        "signal",
        relevance_mode=RelevanceMode.STRUCTURAL_ACTIVITY_DIAGNOSTIC,
    )
    gates = segment_gates(sev)
    l1 = build_gate_l1_state(sev, gates)

    assert len(l1) == 1
    assert all(sample.N == 1 for sample in sev)
    assert all(sample.relevance == 0.0 for sample in sev)
    assert l1[0].tvr[1] < KERNEL_THRESHOLDS.theta_V
    assert l1[0].tvr[2] == 0.0
    assert l1[0].N_gate == 1


def test_unsupported_relevance_mode_fails_loudly():
    with pytest.raises(ValueError, match="Unsupported relevance_mode"):
        compute_sev_series(
            _frame(np.ones(8)),
            "signal",
            relevance_mode="unratified-mode",
        )
