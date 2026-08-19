"""Render the authoritative CH6 paper book as a read-only static page."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from tools.channel_static_page import ChannelPage, ClosedRow, OpenRow, ROOT, run_cli  # noqa: E402


BOOK_PATH = ROOT / "artifacts" / "vtvr_observer" / "ch6_book.json"


def build_page() -> ChannelPage:
    with BOOK_PATH.open("r", encoding="utf-8") as handle:
        book = json.load(handle)
    opens = tuple(
        OpenRow(
            symbol=str(symbol),
            side=int(trade["side"]),
            shares=int(trade["shares"]),
            entry_price=float(trade["entry_px"]),
            notional=float(trade["notional"]),
            entered_at=str(trade["entry_date"]),
            armed=bool(trade.get("armed")),
        )
        for symbol, trade in book["positions"].items()
    )
    closed = tuple(
        ClosedRow(
            symbol=str(trade["symbol"]),
            side=int(trade["side"]),
            shares=int(trade["shares"]),
            entry_price=float(trade["entry_px"]),
            exit_price=float(trade["exit_px"]) if trade.get("exit_px") is not None else None,
            pnl=float(trade.get("pnl") or 0),
            return_pct=float(trade.get("ret_pct") or 0),
            entered_at=str(trade["entry_date"]),
            exited_at=str(trade.get("exit_at") or ""),
            reason=str(trade["reason"]),
        )
        for trade in book["closed"]
    )
    return ChannelPage(
        code="CH6",
        title="CH6 — Fast Harvest",
        engine=str(book.get("engine") or "unknown"),
        starting_capital=float(book.get("start") or 100_000),
        cash=float(book["cash"]),
        opens=opens,
        closed=closed,
        rules=(
            "This is a paper channel: a reduced event projection plus a whole-life kernel reading at entry. It is not full joint-field evaluation and it creates no real orders.",
            "Entry layer 1 (projection): completed-close gain of at least 8%, volume at least three times the preceding 20-session mean, price at least $5, and explicit same-day gband=0 herd evidence. Missing herd evidence is refused.",
            "Entry layer 2 (the reading, laws v2-20260819): every surviving candidate's whole life runs through the canonical v2 chain. Laws in force are Joseph's — desk floor (no-borrow, uptick, halt-prone), fillability ($2k must hide inside 1% of a normal day), the suicide-pill shell ban (lifetime peak 1000x today's price), never short a sound company. The complete reading is filed daily under docs/readings/.",
            "No structural entry law is in force. Two candidates — the charging-vehicle conjunction and the extinction-presence law — were falsified on the filed decade record and retired. Readings file; they do not veto (Rule 10: caps, cut line, clock and the premarket pass are the protection).",
            "Holdings governance: once per day every open position is re-read whole-life. A position refused by the shell ban or the sound-structure law, or that has become unreadable, is cut at the next available mark. The book does not hold what it cannot read.",
            "A winner arms at 5%, tracks its best observed gain, and harvests after giving back more than one percentage point; the completed-close sweep harvests positions still at 5% or better.",
            "The anomaly cut is triggered by the first five-minute mark or completed close at least 20% against entry. Marks and gaps can cross the trigger: the realized bound per position is the slice times the worst gap, not 20% (realized so far: WETO -112.5%, IPST -195.8%, TNON -58.7%).",
            "The fifth completed session is the time backstop.",
            "After an anomaly cut, the symbol remains refuted until a later completed close returns to or below the original entry. The cut bar cannot be re-entered. Borrow and slippage carry costs are charged on every close.",
        ) + _kill_test_line(),
    )


def _kill_test_line() -> tuple:
    """One honest line on where CH6 stands against its armed kill test."""
    try:
        kill = json.loads((ROOT / "artifacts" / "ch4_uf" /
                           "ch3_kill_test.json").read_text())
        sample = kill["samples"]["harvest_engine_v3"]
        return (
            f"Kill test (armed at the {kill['kill_threshold_pctl']:g}th "
            f"percentile of the decade object): CH6's live mean of "
            f"{sample['live_mean_pct']:+.2f}% over {sample['n_closures']} "
            f"closures sits at percentile {sample['live_mean_percentile']:.2f} "
            f"as of {str(kill.get('ran_at_utc', ''))[:10]}. "
            + ("BROKEN." if sample.get("broken") else "Inside the object."),
        )
    except Exception:  # noqa: BLE001 — the page renders without the line
        return ("Kill test artifact unreadable — position unknown.",)


if __name__ == "__main__":
    run_cli(build_page)
