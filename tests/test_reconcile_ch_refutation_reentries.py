from copy import deepcopy

from tools.reconcile_ch_refutation_reentries import reconcile_ch3, reconcile_ch6


HISTORY = {"WETO": (["2026-08-14", "2026-08-17"], [8.22, 24.59])}
CUT_TIME = "2026-08-17T16:46:00+00:00"
RECONCILED_TIME = "2026-08-18T00:00:00+00:00"


def test_ch3_voids_invalid_reentry_once_and_restores_notional() -> None:
    book = {
        "book": {"cash": -81_096.14},
        "finds": [
            {
                "symbol": "WETO",
                "status": "ANOMALY-CUT",
                "entry_px": 8.22,
                "resolved": CUT_TIME,
            },
            {
                "symbol": "WETO",
                "status": "OPEN",
                "entry_px": 24.59,
                "notional": 1_499.99,
                "date": "2026-08-17",
            },
        ],
    }
    assert reconcile_ch3(book, HISTORY, RECONCILED_TIME) == ["WETO"]
    assert book["book"]["cash"] == -79_596.15
    assert book["finds"][-1]["status"] == "VOID-REFUTATION-REENTRY"
    assert book["finds"][-1]["pnl"] == 0
    assert reconcile_ch3(book, HISTORY, RECONCILED_TIME) == []


def test_ch6_voids_invalid_reentry_once_and_preserves_closed_audit_row() -> None:
    book = {
        "cash": 65_564.72,
        "positions": {
            "WETO": {
                "side": -1,
                "shares": 81,
                "entry_px": 24.59,
                "notional": 1_991.79,
                "entry_date": "2026-08-17",
            }
        },
        "closed": [
            {
                "symbol": "WETO",
                "reason": "ANOMALY-CUT",
                "entry_px": 8.22,
                "exit_at": CUT_TIME,
            }
        ],
    }
    original_cut = deepcopy(book["closed"][0])
    assert reconcile_ch6(book, HISTORY, RECONCILED_TIME) == ["WETO"]
    assert book["cash"] == 67_556.51
    assert book["positions"] == {}
    assert book["closed"][0] == original_cut
    assert book["closed"][-1]["reason"] == "VOID-REFUTATION-REENTRY"
    assert book["closed"][-1]["pnl"] == 0
    assert reconcile_ch6(book, HISTORY, RECONCILED_TIME) == []
