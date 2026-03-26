import os

import psycopg2
import requests

# Use verified live environment variables
PGHOST = os.getenv("PGHOST")
PGDATABASE = os.getenv("PGDATABASE")
PGUSER = os.getenv("PGUSER")
PGPASSWORD = os.getenv("PGPASSWORD")
POLYGON_API_KEY = os.getenv("MASSIVE_API_KEY") or os.getenv("POLYGON_API_KEY")

# Deterministic SIC-to-Sector Map
SIC_TO_MACRO_MAP = {
    "SERVICES-BUSINESS SERVICES, NEC": "Information Technology",
    "INSURANCE CARRIERS": "Financials",
}


def get_db_connection():
    return psycopg2.connect(
        host=PGHOST,
        database=PGDATABASE,
        user=PGUSER,
        password=PGPASSWORD,
    )


def fetch_normalized_data(ticker):
    data = {"ticker": ticker, "sector": "Unknown", "gross_profit": 0.0, "market_cap": 0.0}
    try:
        poly_url = f"https://api.polygon.io/v3/reference/tickers/{ticker}?apiKey={POLYGON_API_KEY}"
        res = requests.get(poly_url).json()
        if res.get("status") == "OK":
            results = res.get("results", {})
            raw_sic = results.get("sic_description", "")
            data["sector"] = SIC_TO_MACRO_MAP.get(raw_sic, "Unknown")
            data["market_cap"] = results.get("market_cap", 0.0)
    except Exception as e:
        print(f"Error normalizing {ticker}: {e}")
    return data


def run_etl():
    conn = get_db_connection()
    cur = conn.cursor()

    # Corrected source columns: symbol + s_uf
    cur.execute("SELECT symbol FROM l4_snapshot_rows WHERE s_uf >= 0.6466")
    tickers = [row[0] for row in cur.fetchall()]

    print(f"Starting Normalization for {len(tickers)} tickers...")

    for i, ticker in enumerate(tickers):
        norm_data = fetch_normalized_data(ticker)
        upsert_query = """
            INSERT INTO l5_fundamentals_normalized (ticker, sector, market_cap)
            VALUES (%(ticker)s, %(sector)s, %(market_cap)s)
            ON CONFLICT (ticker) DO UPDATE SET
                sector = EXCLUDED.sector,
                market_cap = EXCLUDED.market_cap,
                updated_at = CURRENT_TIMESTAMP;
        """
        cur.execute(upsert_query, norm_data)
        if i % 100 == 0:
            conn.commit()
            print(f"Committed {i} records...")

    conn.commit()
    cur.close()
    conn.close()
    print("ETL Run Complete.")


if __name__ == "__main__":
    run_etl()
