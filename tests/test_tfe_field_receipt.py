import numpy as np
import pandas as pd
import pytest

from tools.tfe_field_receipt import FIELDS, capture


def bars():
    return pd.DataFrame({"Symbol": "X", "Date": pd.date_range("2026-01-01", periods=80),
                         "Close": np.where(np.arange(80) % 2, 100.0, 1.0)})


def test_future_prices_cannot_change_a_prior_receipt():
    original = bars()
    cutoff = original.Date.iloc[59].date().isoformat()
    changed = original.copy()
    changed.loc[60:, "Close"] *= 10
    first, second = capture(original, "X", cutoff), capture(changed, "X", cutoff)
    assert first == second
    assert first["input_bars"] == 60
    assert first["l4_adapter_exact_match"] is True
    assert len(first["gate_history"]) > 1
    assert all(set(FIELDS) <= set(g["l4"]) for g in first["gate_history"])


def test_duplicate_and_missing_input_are_refused():
    original = bars()
    with pytest.raises(ValueError, match="duplicate"):
        capture(pd.concat([original, original.iloc[:1]]), "X", "2026-02-01")
    with pytest.raises(ValueError, match="exact cutoff"):
        capture(original, "X", "2027-01-01")


def test_nonfinite_input_is_not_silently_skipped():
    original = bars()
    original.loc[2, "Close"] = np.nan
    with pytest.raises(ValueError, match="invalid raw"):
        capture(original, "X", "2026-02-01")
