import os
import json
import requests

# We use python-dotenv to load MASSIVE_API_KEY from your .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("[ERROR] python-dotenv is not installed. Install it with:")
    print("        pip install python-dotenv")
    raise

api_key = os.getenv("MASSIVE_API_KEY")

if not api_key:
    print("[ERROR] MASSIVE_API_KEY not found in environment or .env file.")
    raise SystemExit(1)

# This URL may differ depending on Massive's docs; this is our best known path
url = "https://api.massive.com/v3/reference/tickers"

params = {
    "active": "true",
    "market": "stocks",
    "limit": 1000,
}

headers = {
    "Authorization": f"Bearer {api_key}",
    "Accept": "application/json",
}

print("[INFO] Requesting:", url)
resp = requests.get(url, headers=headers, params=params)
print("[INFO] HTTP status:", resp.status_code)

try:
    data = resp.json()
except Exception as e:
    print("[ERROR] Could not parse JSON:", e)
    print("Raw text:", resp.text[:500])
    raise

# Write full JSON to file so you don't have to deal with huge output in the console
out_path = "massive_tickers_raw.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, sort_keys=True)

print(f"[INFO] Wrote full JSON response to {out_path}")
print("[INFO] Now open massive_tickers_raw.json in Notepad and search for:")
print("       'next', 'next_url', 'page', or 'cursor' keys.")
