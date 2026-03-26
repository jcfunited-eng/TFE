#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path

import requests


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
    api_key = str(os.environ.get("POLYGON_API_KEY") or os.environ.get("MASSIVE_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("Missing POLYGON_API_KEY/MASSIVE_API_KEY in environment.")

    polygon_url = f"https://api.polygon.io/v3/reference/tickers/ACN?apiKey={api_key}"
    polygon_resp = requests.get(polygon_url, timeout=30)
    print(f"POLYGON_STATUS={polygon_resp.status_code}")
    try:
        polygon_json = polygon_resp.json()
        print("POLYGON_JSON_BEGIN")
        print(json.dumps(polygon_json, indent=2, sort_keys=True))
        print("POLYGON_JSON_END")
    except Exception:
        print("POLYGON_RAW_BEGIN")
        print(polygon_resp.text)
        print("POLYGON_RAW_END")

    yahoo_url = "https://finance.yahoo.com/quote/ACN/profile"
    yahoo_resp = requests.get(
        yahoo_url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            )
        },
        timeout=30,
    )
    print(f"YAHOO_STATUS={yahoo_resp.status_code}")
    if yahoo_resp.status_code == 200:
        text = yahoo_resp.text
        idx = text.find("Sector")
        print(f"YAHOO_SECTOR_INDEX={idx}")
        if idx >= 0:
            start = max(0, idx - 100)
            end = min(len(text), idx + 300)
            print("YAHOO_SNIPPET_BEGIN")
            print(text[start:end])
            print("YAHOO_SNIPPET_END")


if __name__ == "__main__":
    main()
