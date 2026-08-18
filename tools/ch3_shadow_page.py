"""Render the authoritative CH3 paper book as a read-only static page."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from tools.channel_static_page import ChannelPage, ClosedRow, OpenRow, ROOT, run_cli  # noqa: E402


BOOK_PATH = ROOT / "artifacts" / "vtvr_observer" / "ch3_shadow_log.json"


def recorded_shares(trade: dict[str, object]) -> int:
    shares = trade.get("shares")
    if shares is not None and int(shares) > 0:
        return int(shares)
    entry_price = float(trade["entry_px"])
    notional = float(trade.get("notional") or 0)
    return int(round(notional / entry_price)) if entry_price > 0 else 0


def build_page() -> ChannelPage:
    with BOOK_PATH.open("r", encoding="utf-8") as handle:
        book = json.load(handle)
    account = book["book"]
    opens: list[OpenRow] = []
    closed: list[ClosedRow] = []
    for trade in book["finds"]:
        shares = recorded_shares(trade)
        if trade["status"] == "OPEN":
            opens.append(
                OpenRow(
                    symbol=str(trade["symbol"]),
                    side=int(trade["side"]),
                    shares=shares,
                    entry_price=float(trade["entry_px"]),
                    notional=float(trade["notional"]),
                    entered_at=str(trade["date"]),
                )
            )
            continue
        closed.append(
            ClosedRow(
                symbol=str(trade["symbol"]),
                side=int(trade["side"]),
                shares=shares,
                entry_price=float(trade["entry_px"]),
                exit_price=float(trade["exit_px"]) if trade.get("exit_px") is not None else None,
                pnl=float(trade.get("pnl") or 0),
                return_pct=float(trade.get("ret_pct") or 0),
                entered_at=str(trade["date"]),
                exited_at=str(trade.get("resolved") or ""),
                reason=str(trade["status"]),
            )
        )
    return ChannelPage(
        code="CH3",
        title="CH3 — Shadow Hunter",
        engine=str(book.get("engine") or "unknown"),
        starting_capital=float(account.get("start") or 100_000),
        cash=float(account["cash"]),
        opens=tuple(opens),
        closed=tuple(closed),
        rules=(
            "This is a reduced paper L5 projection, not full joint-field evaluation, and it creates no real orders.",
            "Entry requires a completed-close gain of at least 8%, volume at least three times the preceding 20-session mean, price at least $5, and explicit same-day gband=0 herd evidence. Missing herd evidence is refused.",
            "Harvest occurs at the first completed close at least 5% below entry; the fifth completed session is the time backstop.",
            "The anomaly cut is triggered by the first completed close at least 20% above entry. Gaps can cross the trigger.",
            "After an anomaly cut, the symbol remains refuted until a later completed close returns to or below the original entry. The cut bar cannot be re-entered.",
            "Declared gross exposure is capped at twice starting capital. Borrow costs are not modeled.",
        ),
    )


if __name__ == "__main__":
    run_cli(build_page)
