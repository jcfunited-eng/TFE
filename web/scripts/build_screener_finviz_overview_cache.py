#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "web" / "data" / "screener-finviz-overview-cache.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Write an empty screener overview cache. Finviz scraping is permanently disabled.",
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--base-url", default="")
    parser.add_argument("--max-pages", type=int, default=0)
    parser.add_argument("--timeout-sec", type=int, default=0)
    parser.add_argument("--sleep-ms", type=int, default=0)
    parser.add_argument("--retry-limit", type=int, default=0)
    parser.add_argument("--save-every", type=int, default=0)
    args = parser.parse_args()

    output_path = Path(args.output).resolve()
    started_at_utc = _utc_now()
    payload = {
        "status": "disabled",
        "generated_at_utc": _utc_now(),
        "started_at_utc": started_at_utc,
        "source_base_url": None,
        "total_detected": 0,
        "pages_fetched": 0,
        "row_count": 0,
        "rows": {},
        "reason": "Finviz overview scraper disabled by Native Engine UI backend teardown.",
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    print(
        json.dumps(
            {
                "status": "ok",
                "output": str(output_path),
                "pages_fetched": 0,
                "rows": 0,
                "reason": "finviz_disabled",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
