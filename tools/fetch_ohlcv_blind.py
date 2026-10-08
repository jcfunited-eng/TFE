"""Blind universe for the BUILD-state confirmation (declared 2026-10-08): 1,500 names
NOT in artifacts/ch2_life/ohlcv_pool.parquet, drawn with seed 11 from names that have
>= 1,000 closes in ch4_live_store.parquet AND herd state in herd_state_live.parquet.
Same fetch as tools/fetch_ohlcv_pool.py. Output artifacts/ch2_life/ohlcv_blind.parquet."""
import os, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np, pandas as pd
sys.path.insert(0, "tools"); sys.path.insert(0, ".")
from fetch_ohlcv_pool import fetch
pool = set(pd.read_parquet("artifacts/ch2_life/ohlcv_pool.parquet", columns=["Symbol"]).Symbol.unique())
st = pd.read_parquet("ch4_live_store.parquet", columns=["Symbol"]).Symbol.value_counts()
herd = set(pd.read_parquet("artifacts/ch4_uf/herd_state_live.parquet", columns=["sym"]).sym.unique())
cand = sorted(s for s in st[st >= 1000].index if s not in pool and s in herd)
names = list(np.random.default_rng(11).choice(cand, min(1500, len(cand)), replace=False))
print("candidates", len(cand), "drawn", len(names), flush=True)
key = os.environ.get("MASSIVE_API_KEY") or os.environ.get("POLYGON_API_KEY")
rows, failed = [], []
with ThreadPoolExecutor(8) as ex:
    for f in as_completed([ex.submit(fetch, s, key) for s in names]):
        s, out = f.result()
        if isinstance(out, list): rows += out
        else: failed.append(s)
df = pd.DataFrame(rows, columns=["Date", "Symbol", "Open", "High", "Low", "Close", "Volume"])
df["Date"] = pd.to_datetime(df.Date); df.sort_values(["Symbol", "Date"]).to_parquet("artifacts/ch2_life/ohlcv_blind.parquet", index=False)
print("wrote", df.Symbol.nunique(), "symbols", len(df), "bars; failed", len(failed), flush=True)
