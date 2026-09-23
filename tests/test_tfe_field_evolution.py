import gzip
import json

import pandas as pd
import pytest

from tools import tfe_field_evolution as evolution
from tools.tfe_field_receipt import capture


def test_each_observation_is_its_own_complete_prefix(tmp_path):
    frame = pd.DataFrame({"Symbol": "X", "Date": pd.date_range("2026-01-01", periods=16),
                          "Close": [1., 100.] * 8})
    path = tmp_path / "tape.jsonl.gz"
    result = evolution.write_evolution(frame, "X", "2026-01-12", "2026-01-14", path)
    with gzip.open(path, "rt") as stream:
        receipts = [json.loads(line) for line in stream]
    assert result["observations"] == 3
    assert [r["input_bars"] for r in receipts] == [12, 13, 14]
    for receipt in receipts:
        assert receipt == capture(frame, "X", receipt["as_of"])
    before = path.read_bytes()
    with pytest.raises(FileExistsError):
        evolution.write_evolution(frame, "X", "2026-01-12", "2026-01-14", path)
    assert path.read_bytes() == before


def test_midstream_failure_never_publishes_partial_history(tmp_path, monkeypatch):
    frame = pd.DataFrame({"Symbol": "X", "Date": pd.date_range("2026-01-01", periods=3),
                          "Close": [1., 2., 3.]})
    def fail_on_second(frame, symbol, date):
        if date.day == 2:
            raise ValueError("invalid kernel output")
        return {"kernel_sha256": evolution.kernel_hashes(), "gate_history": []}
    monkeypatch.setattr(evolution, "capture", fail_on_second)
    with pytest.raises(ValueError, match="invalid kernel"):
        evolution.write_evolution(frame, "X", "2026-01-01", "2026-01-03", tmp_path / "tape.gz")
    assert list(tmp_path.iterdir()) == []
