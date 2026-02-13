import json
import time
import requests
import csv
from pathlib import Path

# === CONFIG ===

# Massive BTC daily aggregates URL
# Replace YOUR_KEY_HERE with your real Massive REST API key
MASSIVE_BTC_URL = "https://api.massive.com/v2/aggs/ticker/X:BTCUSD/range/1/day/2020-12-01/2025-12-01?adjusted=true&sort=asc&limit=50000&apiKey=s2Tpv2VaUIMBThbRgzjKy3Y19aJHhEuc"

# Output CSV path
OUTPUT_CSV = Path(r"C:\Users\joeta\OneDrive\Desktop\Tao_Financial_Engine\market_data\BTC.csv")


def fetch_btc_json() -> dict:
    """Fetch BTC daily aggregates JSON from Massive."""
    resp = requests.get(MASSIVE_BTC_URL, timeout=30)
    resp.raise_for_status()
    return resp.json()


def write_btc_csv(data: dict, output_path: Path) -> None:
    """Convert BTC aggregates to CSV format."""
    results = data.get("results", [])
    if not results:
        print("No results found in JSON. Nothing to write.")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "Open", "High", "Low", "Close", "Volume"])

        for bar in results:
            t_ms = bar.get("t")
            if t_ms is None:
                continue
            dt = time.strftime("%Y-%m-%d", time.gmtime(t_ms / 1000))

            writer.writerow([
                dt,
                bar.get("o"),
                bar.get("h"),
                bar.get("l"),
                bar.get("c"),
                int(bar.get("v")) if bar.get("v") is not None else ""
            ])


def main():
    print("Fetching BTC daily aggregates from Massive...")
    data = fetch_btc_json()
    print("Writing BTC.csv...")
    write_btc_csv(data, OUTPUT_CSV)
    print(f"Done. CSV written to: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
