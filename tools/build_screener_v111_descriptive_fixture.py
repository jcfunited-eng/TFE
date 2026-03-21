#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

FILTER_LABEL_TO_TFE_KEY = {
    "Exchange": "exchange",
    "Index": "index",
    "Sector": "sector",
    "Industry": "industry",
    "Country": "country",
    "Market Cap.": "marketCap",
    "Dividend Yield": "dividendYield",
    "Short Float": "shortFloat",
    "Analyst Recom.": "analystRecom",
    "Option/Short": "optionShort",
    "Earnings Date": "earningsDate",
    "Average Volume": "avgVolume",
    "Relative Volume": "relVolume",
    "Current Volume": "currentVolume",
    "Trades": "trades",
    "Price $": "priceBand",
    "Target Price": "targetPrice",
    "IPO Date": "ipoDate",
    "Shares Outstanding": "sharesOutstanding",
    "Float": "float",
    "Theme": "theme",
    "Sub-theme": "subTheme",
}

ALL_TFE_KEYS = [
    "exchange",
    "index",
    "sector",
    "industry",
    "country",
    "marketCap",
    "dividendYield",
    "shortFloat",
    "analystRecom",
    "optionShort",
    "earningsDate",
    "avgVolume",
    "relVolume",
    "currentVolume",
    "trades",
    "priceBand",
    "targetPrice",
    "ipoDate",
    "sharesOutstanding",
    "float",
    "theme",
    "subTheme",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    schema_path = Path(args.schema).resolve()
    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    data = json.loads(schema_path.read_text(encoding="utf-8"))
    views = data.get("views", [])
    v111 = next((v for v in views if str(v.get("view_v")) == "111"), None)
    if not isinstance(v111, dict):
        raise RuntimeError("v=111 view not found in schema")

    selects = v111.get("filter_selects", [])

    by_key: dict[str, list[dict[str, Any]]] = {k: [] for k in ALL_TFE_KEYS}
    unmapped_labels: list[str] = []

    for item in selects:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label", "")).strip()
        key = FILTER_LABEL_TO_TFE_KEY.get(label)
        if not key:
            unmapped_labels.append(label)
            continue
        options = item.get("options", [])
        if isinstance(options, list):
            by_key[key] = [
                {
                    "value": str(opt.get("value", "")),
                    "label": str(opt.get("label", "")),
                    "elite_only": bool(opt.get("elite_only", False)),
                }
                for opt in options
                if isinstance(opt, dict)
            ]

    payload = {
        "source_schema": str(schema_path),
        "generated_at_utc": data.get("generated_at_utc"),
        "keys": by_key,
        "unmapped_filter_labels": sorted(set(unmapped_labels)),
    }

    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
