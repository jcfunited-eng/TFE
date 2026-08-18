from tools.ch_short_refutation import has_unreset_refutation


def cut(exit_at: str, entry_px: float, symbol: str = "WETO") -> dict[str, object]:
    return {
        "symbol": symbol,
        "reason": "ANOMALY-CUT",
        "exit_at": exit_at,
        "entry_px": entry_px,
    }


def test_weto_same_day_reentry_is_refused() -> None:
    assert has_unreset_refutation(
        symbol="WETO",
        candidate_day="2026-08-17",
        anomaly_cuts=[cut("2026-08-17T16:46:09Z", 8.22)],
        history_days=["2026-08-14", "2026-08-17"],
        history_closes=[8.22, 24.59],
    )


def test_refutation_stays_active_while_completed_closes_remain_above_entry() -> None:
    assert has_unreset_refutation(
        symbol="WETO",
        candidate_day="2026-08-20",
        anomaly_cuts=[cut("2026-08-17T16:46:09Z", 8.22)],
        history_days=["2026-08-18", "2026-08-19", "2026-08-20"],
        history_closes=[18.0, 12.0, 16.0],
    )


def test_later_completed_relaxation_resets_refutation() -> None:
    assert not has_unreset_refutation(
        symbol="WETO",
        candidate_day="2026-08-20",
        anomaly_cuts=[cut("2026-08-17T16:46:09Z", 8.22)],
        history_days=["2026-08-18", "2026-08-19", "2026-08-20"],
        history_closes=[18.0, 8.0, 16.0],
    )


def test_latest_refutation_controls_after_an_older_one_reset() -> None:
    assert has_unreset_refutation(
        symbol="WETO",
        candidate_day="2026-08-23",
        anomaly_cuts=[
            cut("2026-08-10T20:00:00Z", 10.0),
            cut("2026-08-22T20:00:00Z", 20.0),
        ],
        history_days=["2026-08-11", "2026-08-21", "2026-08-23"],
        history_closes=[9.0, 25.0, 30.0],
    )


def test_symbol_without_anomaly_cut_is_not_blocked() -> None:
    assert not has_unreset_refutation(
        symbol="FGI",
        candidate_day="2026-08-17",
        anomaly_cuts=[cut("2026-08-17T16:46:09Z", 8.22)],
        history_days=["2026-08-14", "2026-08-17"],
        history_closes=[11.15, 10.30],
    )
