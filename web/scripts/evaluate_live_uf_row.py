#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from uf_mdg_snapshot import evaluate_symbol_snapshot
except Exception as exc:
    print(json.dumps({"error": f"Failed to import uf_mdg_snapshot.evaluate_symbol_snapshot: {exc}"}))
    raise SystemExit(1)


def normalize_asset_type(raw: str, ticker: str) -> str:
    value = str(raw or "").strip().lower()
    if value:
        return value

    symbol = ticker.upper().strip()
    if symbol.startswith("X:"):
        return "crypto"
    if symbol.startswith("I:"):
        return "index"
    return "stock"


def sanitize_json(value: Any) -> Any:
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        return value

    if isinstance(value, dict):
        return {str(k): sanitize_json(v) for k, v in value.items()}

    if isinstance(value, list):
        return [sanitize_json(item) for item in value]

    if isinstance(value, tuple):
        return [sanitize_json(item) for item in value]

    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate one ticker with live UF-Core row construction.")
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--asset-type", default="")
    args = parser.parse_args()

    ticker = str(args.ticker).strip().upper()
    if not ticker:
        print(json.dumps({"error": "Ticker is required."}))
        return 2

    asset_type = normalize_asset_type(str(args.asset_type), ticker)

    try:
        row = evaluate_symbol_snapshot(ticker, asset_type=asset_type)
    except Exception as exc:
        print(json.dumps({"error": f"Live UF evaluation failed for {ticker}: {exc}"}))
        return 1

    payload = {
        "ticker": ticker,
        "assetType": asset_type,
        "row": sanitize_json(row),
    }

    print(json.dumps(payload, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
