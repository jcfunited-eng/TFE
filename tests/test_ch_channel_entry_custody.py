import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from ch3_reveal_fade import candidate_events  # noqa: E402
from ch6_fast_harvest import qualifying_events  # noqa: E402


def event_market() -> tuple[pd.DataFrame, np.ndarray, pd.Timestamp]:
    days = pd.bdate_range("2026-07-20", periods=22)
    closes = [10.0 + ((index % 3) - 1) * 0.1 for index in range(21)] + [12.2]
    volumes = [100.0] * 21 + [1_000.0]
    market = pd.DataFrame(
        {
            "Date": days,
            "Symbol": ["WETO"] * len(days),
            "Close": closes,
            "Volume": volumes,
        }
    )
    return market, days.to_numpy(), pd.Timestamp(days[-1])


def test_ch3_refuses_missing_herd_evidence() -> None:
    market, days, latest = event_market()

    events, unknown, refuted = candidate_events(
        market=market,
        days=days,
        latest=latest,
        herd_state={},
        anomaly_cuts=[],
    )

    assert events == []
    assert unknown == 1
    assert refuted == 0


def test_ch6_refuses_missing_herd_evidence() -> None:
    market, days, latest = event_market()

    events, unknown, refuted = qualifying_events(
        market=market,
        days=[pd.Timestamp(day) for day in days],
        latest=latest,
        herd_state={},
        anomaly_cuts=[],
    )

    assert events == []
    assert unknown == 1
    assert refuted == 0


def test_both_channels_refuse_same_day_anomaly_reentry() -> None:
    market, days, latest = event_market()
    latest_s = latest.strftime("%Y-%m-%d")
    ch3_cut = {
        "symbol": "WETO",
        "status": "ANOMALY-CUT",
        "resolved": f"{latest_s}T16:46:09Z",
        "entry_px": 8.22,
    }
    ch6_cut = {
        "symbol": "WETO",
        "reason": "ANOMALY-CUT",
        "exit_at": f"{latest_s}T16:46:09Z",
        "entry_px": 8.22,
    }

    ch3_events, _, ch3_refuted = candidate_events(
        market=market,
        days=days,
        latest=latest,
        herd_state={"WETO": 0},
        anomaly_cuts=[ch3_cut],
    )
    ch6_events, _, ch6_refuted = qualifying_events(
        market=market,
        days=[pd.Timestamp(day) for day in days],
        latest=latest,
        herd_state={"WETO": 0},
        anomaly_cuts=[ch6_cut],
    )

    assert ch3_events == []
    assert ch6_events == []
    assert ch3_refuted == 1
    assert ch6_refuted == 1


def test_explicit_low_herd_without_refutation_is_eligible() -> None:
    market, days, latest = event_market()

    ch3_events, ch3_unknown, ch3_refuted = candidate_events(
        market=market,
        days=days,
        latest=latest,
        herd_state={"WETO": 0},
        anomaly_cuts=[],
    )
    ch6_events, ch6_unknown, ch6_refuted = qualifying_events(
        market=market,
        days=[pd.Timestamp(day) for day in days],
        latest=latest,
        herd_state={"WETO": 0},
        anomaly_cuts=[],
    )

    assert [event["symbol"] for event in ch3_events] == ["WETO"]
    assert [event["symbol"] for event in ch6_events] == ["WETO"]
    assert (ch3_unknown, ch3_refuted, ch6_unknown, ch6_refuted) == (0, 0, 0, 0)
