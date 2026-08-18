"""Shared deterministic refutation-reset law for CH3 and CH6 shorts."""

from __future__ import annotations

from datetime import date, datetime
from math import isfinite
from typing import Iterable, Mapping, Sequence


def _day(value: object) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None


def has_unreset_refutation(
    *,
    symbol: str,
    candidate_day: object,
    anomaly_cuts: Iterable[Mapping[str, object]],
    history_days: Sequence[object],
    history_closes: Sequence[object],
) -> bool:
    """Return whether the latest anomaly cut still forbids a new short.

    A cut declares the fade thesis refuted. It resets only after a later
    completed daily close returns to or below that cut's original entry.
    The candidate bar cannot reset its own refutation.
    """

    candidate = _day(candidate_day)
    if candidate is None or len(history_days) != len(history_closes):
        raise ValueError("candidate day and aligned daily history are required")

    normalized_symbol = str(symbol).strip().upper()
    latest: tuple[date, float] | None = None
    for raw in anomaly_cuts:
        if str(raw.get("symbol") or raw.get("sym") or "").strip().upper() != normalized_symbol:
            continue
        if str(raw.get("reason") or raw.get("status") or "").strip().upper() != "ANOMALY-CUT":
            continue
        cut_day = _day(raw.get("exit_at") or raw.get("resolved") or raw.get("exit_date"))
        try:
            entry = float(raw.get("entry_px"))
        except (TypeError, ValueError):
            continue
        if cut_day is None or cut_day > candidate or not isfinite(entry) or entry <= 0:
            continue
        if latest is None or cut_day > latest[0]:
            latest = (cut_day, entry)

    if latest is None:
        return False

    cut_day, entry = latest
    for raw_day, raw_close in zip(history_days, history_closes):
        observed_day = _day(raw_day)
        try:
            close = float(raw_close)
        except (TypeError, ValueError):
            continue
        if (
            observed_day is not None
            and cut_day < observed_day < candidate
            and isfinite(close)
            and close <= entry
        ):
            return False
    return True
