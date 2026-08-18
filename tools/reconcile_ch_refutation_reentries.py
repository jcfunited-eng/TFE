#!/usr/bin/env python3
"""Void paper entries opened while an anomaly refutation was still active."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.ch_short_refutation import has_unreset_refutation  # noqa: E402


CH3_PATH = ROOT / "artifacts" / "vtvr_observer" / "ch3_shadow_log.json"
CH6_PATH = ROOT / "artifacts" / "vtvr_observer" / "ch6_book.json"
ROSTER_PATH = ROOT / "ch4_live_store.parquet"
TAIL_PATH = ROOT / "ch3_supply_tail.parquet"
VOID_REASON = "VOID-REFUTATION-REENTRY"


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain one JSON object")
    return value


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(value, indent=1) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def market_history() -> dict[str, tuple[list[object], list[object]]]:
    roster = pd.read_parquet(ROSTER_PATH, columns=["Date", "Symbol", "Close"])
    roster["Date"] = pd.to_datetime(roster["Date"])
    frames = [roster]
    if TAIL_PATH.exists():
        tail = pd.read_parquet(TAIL_PATH, columns=["Date", "Symbol", "Close"])
        tail["Date"] = pd.to_datetime(tail["Date"])
        frames.append(tail)
    market = pd.concat(frames, ignore_index=True).drop_duplicates(["Date", "Symbol"], keep="last")
    result: dict[str, tuple[list[object], list[object]]] = {}
    for symbol, rows in market.groupby("Symbol"):
        ordered = rows.sort_values("Date")
        result[str(symbol)] = (ordered["Date"].tolist(), ordered["Close"].tolist())
    return result


def is_invalid_reentry(
    *,
    symbol: str,
    entry_day: object,
    cuts: list[dict[str, object]],
    history: dict[str, tuple[list[object], list[object]]],
) -> bool:
    days, closes = history.get(symbol, ([], []))
    return has_unreset_refutation(
        symbol=symbol,
        candidate_day=entry_day,
        anomaly_cuts=cuts,
        history_days=days,
        history_closes=closes,
    )


def reconcile_ch3(
    book: dict[str, Any],
    history: dict[str, tuple[list[object], list[object]]],
    now: str,
) -> list[str]:
    finds = book.get("finds")
    account = book.get("book")
    if not isinstance(finds, list) or not isinstance(account, dict):
        raise ValueError("CH3 book schema is invalid")
    cuts = [row for row in finds if isinstance(row, dict) and row.get("status") == "ANOMALY-CUT"]
    voided: list[str] = []
    for row in finds:
        if not isinstance(row, dict) or row.get("status") != "OPEN":
            continue
        symbol = str(row.get("symbol", ""))
        if not is_invalid_reentry(symbol=symbol, entry_day=row.get("date"), cuts=cuts, history=history):
            continue
        account["cash"] = round(float(account["cash"]) + float(row["notional"]), 2)
        row.update(
            status=VOID_REASON,
            resolved=now,
            exit_px=float(row["entry_px"]),
            ret_pct=0.0,
            pnl=0.0,
            void_reason="entry opened before the latest anomaly refutation reset",
        )
        voided.append(symbol)
    return voided


def reconcile_ch6(
    book: dict[str, Any],
    history: dict[str, tuple[list[object], list[object]]],
    now: str,
) -> list[str]:
    open_positions = book.get("positions")
    closed = book.get("closed")
    if not isinstance(open_positions, dict) or not isinstance(closed, list):
        raise ValueError("CH6 book schema is invalid")
    cuts = [row for row in closed if isinstance(row, dict) and row.get("reason") == "ANOMALY-CUT"]
    voided: list[str] = []
    for symbol in sorted(list(open_positions)):
        row = open_positions[symbol]
        if not isinstance(row, dict):
            continue
        if not is_invalid_reentry(symbol=symbol, entry_day=row.get("entry_date"), cuts=cuts, history=history):
            continue
        book["cash"] = round(float(book["cash"]) + float(row["notional"]), 2)
        closed.append(
            {
                "symbol": symbol,
                "side": int(row["side"]),
                "shares": int(row["shares"]),
                "entry_px": float(row["entry_px"]),
                "exit_px": float(row["entry_px"]),
                "entry_date": row["entry_date"],
                "exit_at": now,
                "ret_pct": 0.0,
                "pnl": 0.0,
                "reason": VOID_REASON,
                "void_reason": "entry opened before the latest anomaly refutation reset",
            }
        )
        del open_positions[symbol]
        voided.append(symbol)
    return voided


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    history = market_history()
    ch3 = read_json(CH3_PATH)
    ch6 = read_json(CH6_PATH)
    now = datetime.now(timezone.utc).isoformat()
    ch3_voided = reconcile_ch3(ch3, history, now)
    ch6_voided = reconcile_ch6(ch6, history, now)
    mode = "APPLY" if args.apply else "DRY"
    print(f"[{mode}] CH3 voided {len(ch3_voided)}: {', '.join(ch3_voided) or 'none'}")
    print(f"[{mode}] CH6 voided {len(ch6_voided)}: {', '.join(ch6_voided) or 'none'}")
    if args.apply:
        atomic_json(CH3_PATH, ch3)
        atomic_json(CH6_PATH, ch6)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
