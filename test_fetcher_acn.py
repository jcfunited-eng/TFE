#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path

from tfe_fundamental_fetcher import FundamentalCorpora


def load_env_file() -> None:
    env_path = Path("/workspaces/Tao_Financial_Engine/.env")
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line or line.startswith("export "):
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value

    massive_key = str(os.environ.get("MASSIVE_API_KEY", "")).strip()
    if massive_key and not str(os.environ.get("POLYGON_API_KEY", "")).strip():
        os.environ["POLYGON_API_KEY"] = massive_key


def main() -> None:
    load_env_file()
    result = FundamentalCorpora().evaluate_ticker("ACN", sector_hint="Unknown")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
