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
            "This is a reduced paper L5 projection, not full joint-field evaluation, and it creates no real orders.",
            "Entry requires a completed-close gain of at least 8%, volume at least three times the preceding 20-session mean, price at least $5, and explicit same-day gband=0 herd evidence. Missing herd evidence is refused.",
            "A winner arms at 5%, tracks its best observed gain, and harvests after giving back more than one percentage point; the completed-close sweep harvests positions still at 5% or better.",
            "The anomaly cut is triggered by the first five-minute mark or completed close at least 20% against entry. Marks and gaps can cross the trigger.",
            "The fifth completed session is the time backstop.",
            "After an anomaly cut, the symbol remains refuted until a later completed close returns to or below the original entry. The cut bar cannot be re-entered. Borrow costs are not modeled.",
        ),
    )


if __name__ == "__main__":
    run_cli(build_page)
