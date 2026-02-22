"""
tfe_bar_integrity.py

Canonical daily-bar integrity filtering for TFE/UF pipelines.

Strict rules enforced:
- finite OHLC
- positive OHLC
- OHLC structural consistency
- minimum price floor on all OHLC fields
- duplicate timestamp collapse (last bar wins)
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Any, Dict, Iterable, List, Tuple


DEFAULT_MIN_PRICE_FLOOR: float = 0.10


def sanitize_daily_bars(
    raw_bars: Iterable[Any],
    min_price_floor: float = DEFAULT_MIN_PRICE_FLOOR,
) -> Tuple[List[Any], Dict[str, int]]:
    """
    Apply strict integrity filtering to daily bars.

    Returns:
        (clean_bars_sorted, dropped_reason_counts)

    Dropped reason keys:
        parse_error
        missing_timestamp
        non_finite_ohlc
        non_positive_ohlc
        micro_price_bar
        ohlc_inconsistent
        duplicate_timestamp
    """

    dropped = Counter()
    by_timestamp: Dict[Any, Any] = {}

    for bar in raw_bars:
        try:
            ts = getattr(bar, "timestamp", None)
            o = float(getattr(bar, "open"))
            h = float(getattr(bar, "high"))
            l = float(getattr(bar, "low"))
            c = float(getattr(bar, "close"))
        except Exception:
            dropped["parse_error"] += 1
            continue

        if ts is None:
            dropped["missing_timestamp"] += 1
            continue

        if not (math.isfinite(o) and math.isfinite(h) and math.isfinite(l) and math.isfinite(c)):
            dropped["non_finite_ohlc"] += 1
            continue

        if (o <= 0.0) or (h <= 0.0) or (l <= 0.0) or (c <= 0.0):
            dropped["non_positive_ohlc"] += 1
            continue

        if (o < min_price_floor) or (h < min_price_floor) or (l < min_price_floor) or (c < min_price_floor):
            dropped["micro_price_bar"] += 1
            continue

        if h < l:
            dropped["ohlc_inconsistent"] += 1
            continue

        if (h < max(o, c)) or (l > min(o, c)):
            dropped["ohlc_inconsistent"] += 1
            continue

        if ts in by_timestamp:
            dropped["duplicate_timestamp"] += 1

        by_timestamp[ts] = bar

    clean = sorted(by_timestamp.values(), key=lambda b: b.timestamp)
    return clean, dict(dropped)
