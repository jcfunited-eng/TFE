#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from publication_identity import stamp_active_snapshot_and_quote_artifacts


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    result = stamp_active_snapshot_and_quote_artifacts(
        output_path=root / 'web' / 'data' / 'screener-quote-cache.json',
        failures_path=root / 'web' / 'data' / 'screener-quote-cache.failures.json',
        snapshot_path=root / 'uf_snapshot.json',
        require_aligned=False,
    )
    import json
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
