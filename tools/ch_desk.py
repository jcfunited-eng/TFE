"""
ch_desk.py — the ONE copy of shared desk-floor law used by both books.
Created by Rule 11's first review (2026-08-19): carry_costs existed as
two verbatim copies fed different day-counts; the fee schedule now
lives here alone, and days held are CALENDAR days in both books.
"""
from __future__ import annotations

from datetime import date


def carry_costs(notional: float, normal_day: float, days_held: int) -> float:
    """Borrow fee by liquidity class (annualized, calendar days) plus
    round-trip slippage for thin names. Positive dollars to subtract."""
    if normal_day >= 5_000_000:
        rate, slip = 0.01, 0.0005
    elif normal_day >= 1_000_000:
        rate, slip = 0.10, 0.002
    else:
        rate, slip = 0.50, 0.005
    return round(notional * (rate * max(1, days_held) / 365 + slip), 2)


def calendar_days(entry_iso: str, exit_iso: str) -> int:
    """Calendar days between two ISO dates; raises loudly on garbage
    rather than silently defaulting (review finding: masked fallback)."""
    d0 = date.fromisoformat(str(entry_iso)[:10])
    d1 = date.fromisoformat(str(exit_iso)[:10])
    return max(1, (d1 - d0).days)
