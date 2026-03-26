#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor


UNKNOWN_SECTOR = "Unknown"
MAX_ATTEMPTS = 3
ACTIVE_EPOCHS: dict[str, float] = {
    "RATES_PRESSURE": 0.8,
    "CONSUMER_STRESS": 0.6,
    "WAR_GEOPOLITICS": 0.7,
}
SECTOR_SENSITIVITY_MATRIX: dict[str, dict[str, float]] = {
    "Communication Services": {
        "RATES_PRESSURE": -0.2,
        "CONSUMER_STRESS": -0.3,
        "WAR_GEOPOLITICS": -0.1,
    },
    "Consumer Discretionary": {
        "RATES_PRESSURE": -0.5,
        "CONSUMER_STRESS": -1.0,
        "WAR_GEOPOLITICS": -0.2,
    },
    "Consumer Staples": {
        "RATES_PRESSURE": 0.1,
        "CONSUMER_STRESS": 0.4,
        "WAR_GEOPOLITICS": -0.1,
    },
    "Energy": {
        "RATES_PRESSURE": 0.0,
        "CONSUMER_STRESS": -0.2,
        "WAR_GEOPOLITICS": 0.9,
    },
    "Financials": {
        "RATES_PRESSURE": 0.2,
        "CONSUMER_STRESS": -0.5,
        "WAR_GEOPOLITICS": -0.2,
    },
    "Health Care": {
        "RATES_PRESSURE": 0.0,
        "CONSUMER_STRESS": 0.3,
        "WAR_GEOPOLITICS": 0.1,
    },
    "Industrials": {
        "RATES_PRESSURE": -0.2,
        "CONSUMER_STRESS": -0.3,
        "WAR_GEOPOLITICS": 0.2,
    },
    "Information Technology": {
        "RATES_PRESSURE": -0.4,
        "CONSUMER_STRESS": -0.3,
        "WAR_GEOPOLITICS": 0.0,
    },
    "Materials": {
        "RATES_PRESSURE": -0.1,
        "CONSUMER_STRESS": -0.3,
        "WAR_GEOPOLITICS": 0.3,
    },
    "Real Estate": {
        "RATES_PRESSURE": -1.0,
        "CONSUMER_STRESS": -0.5,
        "WAR_GEOPOLITICS": 0.0,
    },
    "Utilities": {
        "RATES_PRESSURE": -0.3,
        "CONSUMER_STRESS": 0.2,
        "WAR_GEOPOLITICS": 0.1,
    },
}


@dataclass(frozen=True)
class ShadowDecision:
    ticker: str
    decision: str
    reason: str
    sector: str
    market_cap: float


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except Exception:
        return None


def _get_db_connection():
    return psycopg2.connect(
        host=str(os.environ.get("PGHOST", "")).strip(),
        database=str(os.environ.get("PGDATABASE", "")).strip(),
        user=str(os.environ.get("PGUSER", "")).strip(),
        password=str(os.environ.get("PGPASSWORD", "")).strip(),
    )


def _fetch_candidate_rows() -> list[dict[str, Any]]:
    query = """
        SELECT
            ticker,
            sector,
            gross_profit,
            current_ratio,
            free_cash_flow,
            gross_margin,
            long_term_debt,
            market_cap,
            operating_cash_flow,
            revenues,
            attempt_count
        FROM l5_fundamentals_normalized
        WHERE sector <> 'Unknown'
          AND COALESCE(attempt_count, 0) < %s
        ORDER BY COALESCE(market_cap, 0) DESC, ticker ASC
    """
    with _get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, (MAX_ATTEMPTS,))
            return list(cur.fetchall())


def _evaluate_sector_epoch(sector: str) -> tuple[bool, str]:
    normalized_sector = str(sector or "").strip()
    if normalized_sector not in SECTOR_SENSITIVITY_MATRIX:
        return False, f"Unknown sector: {sector}"

    sector_vector = SECTOR_SENSITIVITY_MATRIX[normalized_sector]
    epoch_pressure = sum(
        float(ACTIVE_EPOCHS[epoch_name]) * float(sector_vector.get(epoch_name, 0.0))
        for epoch_name in ACTIVE_EPOCHS
    )
    if epoch_pressure <= -0.5:
        return False, f"Adverse Epoch Pressure: {epoch_pressure}"
    return True, "Epoch Favorable/Neutral"


def _fundamental_decision(row: dict[str, Any]) -> tuple[str, str]:
    sector = str(row.get("sector") or "").strip() or UNKNOWN_SECTOR
    if sector == UNKNOWN_SECTOR:
        return "Avoid", "Unknown sector: Unknown"

    current_ratio = _to_float(row.get("current_ratio"))
    free_cash_flow = _to_float(row.get("free_cash_flow"))
    gross_margin = _to_float(row.get("gross_margin"))
    gross_profit = _to_float(row.get("gross_profit"))
    market_cap = _to_float(row.get("market_cap")) or 0.0
    operating_cash_flow = _to_float(row.get("operating_cash_flow"))
    revenues = _to_float(row.get("revenues"))

    required_metrics = {
        "current_ratio": current_ratio,
        "free_cash_flow": free_cash_flow,
        "gross_margin": gross_margin,
        "gross_profit": gross_profit,
        "operating_cash_flow": operating_cash_flow,
        "revenues": revenues,
    }
    missing = [name for name, value in required_metrics.items() if value is None]
    if missing:
        return "Avoid", f"Missing normalized metric(s): {', '.join(missing)}"

    if revenues <= 0:
        return "Avoid", "Domain C Failure: revenues missing or nonpositive"

    if market_cap >= 200_000_000_000:
        assigned_tier = "Tier 1"
        current_ratio_floor = 0.75
    elif market_cap >= 2_000_000_000:
        assigned_tier = "Tier 2"
        current_ratio_floor = 1.0
    else:
        assigned_tier = "Tier 3"
        current_ratio_floor = 1.2

    if current_ratio <= current_ratio_floor:
        return "Avoid", f"Domain A Failure: {assigned_tier} requires Current Ratio > {current_ratio_floor}"

    if free_cash_flow <= 0:
        return "Avoid", "Domain B Failure: Free Cash Flow <= 0"

    if gross_margin <= 0:
        return "Avoid", "Domain C Failure: Gross Margin <= 0"

    if gross_profit <= 0:
        return "Avoid", "Domain C Failure: Gross Profit <= 0"

    if operating_cash_flow <= 0:
        return "Avoid", "Domain B Failure: Operating Cash Flow <= 0"

    epoch_ok, epoch_reason = _evaluate_sector_epoch(sector)
    if not epoch_ok:
        return "Avoid", epoch_reason

    return "Accumulate", "Passed normalized fundamentals and Epoch constraints."


def evaluate_rows(rows: list[dict[str, Any]]) -> list[ShadowDecision]:
    decisions: list[ShadowDecision] = []
    for row in rows:
        ticker = str(row.get("ticker") or "").strip() or "UNKNOWN"
        sector = str(row.get("sector") or "").strip() or UNKNOWN_SECTOR
        decision, reason = _fundamental_decision(row)
        decisions.append(
            ShadowDecision(
                ticker=ticker,
                decision=decision,
                reason=reason,
                sector=sector,
                market_cap=_to_float(row.get("market_cap")) or 0.0,
            )
        )
    return decisions


def run() -> int:
    rows = _fetch_candidate_rows()
    decisions = evaluate_rows(rows)
    accumulate_count = sum(1 for item in decisions if item.decision == "Accumulate")
    print(f"ACCUMULATE_COUNT {accumulate_count}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the database-only L5 shadow pipeline.")
    parser.parse_args()
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
