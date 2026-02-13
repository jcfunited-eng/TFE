import json
import time
import requests
import csv
from pathlib import Path

# === CONFIGURATION ===

# Massive SPY daily aggregates URL (use EXACT URL you tested with Invoke-WebRequest)
# IMPORTANT: Replace ONLY YOUR_KEY_HERE with your real API key, leave everything else identical.
MASSIVE_SPY_URL = "https://api.massive.com/v2/aggs/ticker/SPY/range/1/day/2020-12-01/2025-12-01?adjusted=true&sort=asc&limit=50000&apiKey=s2Tpv2VaUIMBThbRgzjKy3Y19aJHhEuc"

# Output CSV path
OUTPUT_CSV = Path(r"C:\Users\joeta\OneDrive\Desktop\Tao_Financial_Engine\market_data\SPY.csv")


def fetch_spy_json() -> dict:
    """Fetch SPY daily aggregates JSON from Massive."""
    resp = requests.get(MASSIVE_SPY_URL, timeout=30)
    resp.raise_for_status()
    return resp.json()


def write_spy_csv(data: dict, output_path: Path) -> None:
    """
    Convert Massive SPY aggregates JSON to CSV with columns:
    Date,Open,High,Low,Close,Volume
    """
    results = data.get("results", [])
    if not results:
        print("No results found in JSON. Nothing to write.")
        return

    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "Open", "High", "Low", "Close", "Volume"])

        for bar in results:
            # Massive / Polygon time is in milliseconds since epoch
            t_ms = bar.get("t")
            if t_ms is None:
                continue
            dt = time.strftime("%Y-%m-%d", time.gmtime(t_ms / 1000))

            o = bar.get("o")
            h = bar.get("h")
            l = bar.get("l")
            c = bar.get("c")
            v = bar.get("v")

            writer.writerow([dt, o, h, l, c, int(v) if v is not None else ""])


def main():
    print("Fetching SPY daily aggregates from Massive...")
    data = fetch_spy_json()
    print("Writing SPY.csv...")
    write_spy_csv(data, OUTPUT_CSV)
    print(f"Done. CSV written to: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
