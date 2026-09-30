"""Joe, 2026-09-30: "for any 3 month period — draw a 10 line graph — 1 line
for price and 9 for each tuple at the end day for any ticker symbol."

Each day's reading is the production adapter run on the closes through
that day (uf_core.uf_structural_engine.compute_uf_structural_state), the
kernel as it is in production (tau_D 0.20, nothing changed). The nine:
D_k, M_k, R_rev_k, U*_k, C_k, P_k, B_k (level 5) and S_UF, R_UF (level 4).

Usage: python3 tools/ch2_draw_nine.py SYMBOL --end 2026-09-29 [--months 3]
Writes artifacts/ch2_life/<SYMBOL>_nine_<start>_<end>.png and .csv
"""
import argparse, sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
NINE = ["D_k", "M_k", "R_rev_k", "U_star_k", "C_k", "P_k", "B_k", "S_UF", "R_UF"]


def readings(close: pd.Series, start: int) -> pd.DataFrame:
    from uf_core.uf_structural_engine import compute_uf_structural_state
    rows = []
    for t in range(start, len(close)):
        st = compute_uf_structural_state(close.iloc[: t + 1])
        l5, l4 = st.level5, st.level4
        rows.append([close.index[t], float(close.iloc[t])] + [l5.get(k) for k in NINE[:7]] + [l4.get("S_UF"), l4.get("R_UF")])
    return pd.DataFrame(rows, columns=["date", "close"] + NINE)


def draw(symbol: str, df: pd.DataFrame, path: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(18, 9))
    x = np.arange(len(df))
    colors = ["tab:blue", "tab:orange", "tab:red", "tab:purple", "tab:cyan", "tab:gray", "tab:brown", "tab:green", "tab:olive"]
    for k, c in zip(NINE, colors):
        ax.plot(x, df[k].astype(float).values, lw=1.4, color=c, label=k, drawstyle="steps-post")
    ax.set_ylabel("tuple value (full value, no scaling)")
    ax.grid(alpha=0.25)
    ax2 = ax.twinx()
    ax2.plot(x, df.close.values, color="black", lw=2.4, label="price (close)")
    ax2.set_ylabel("price")
    ticks = np.linspace(0, len(df) - 1, 12).astype(int)
    ax.set_xticks(ticks); ax.set_xticklabels([str(df.date.iloc[t].date()) for t in ticks], rotation=30, fontsize=8)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=9, ncol=5)
    ax.set_title(f"{symbol}  {df.date.iloc[0].date()} → {df.date.iloc[-1].date()}   production kernel, each day's reading on the closes through that day", fontsize=11)
    fig.tight_layout(); fig.savefig(path, dpi=90); plt.close(fig)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("symbol"); ap.add_argument("--end", default=None)
    ap.add_argument("--months", type=float, default=3.0); a = ap.parse_args()
    store = pd.read_parquet(ROOT / "ch4_live_store.parquet", columns=["Date", "Symbol", "Close"])
    g = store[store.Symbol == a.symbol].sort_values("Date")
    close = pd.Series(g.Close.values.astype(float), index=pd.to_datetime(g.Date.values))
    end_idx = len(close) - 1 if a.end is None else int(np.searchsorted(close.index.values, np.datetime64(a.end), side="right") - 1)
    close = close.iloc[: end_idx + 1]
    start = max(0, len(close) - int(a.months * 21))
    df = readings(close, start)
    out = ROOT / "artifacts" / "ch2_life"
    tag = f"{a.symbol}_nine_{df.date.iloc[0].date()}_{df.date.iloc[-1].date()}"
    df.to_csv(out / f"{tag}.csv", index=False)
    draw(a.symbol, df, out / f"{tag}.png")
    pd.set_option("display.width", 200); pd.set_option("display.max_rows", 200)
    print(df.to_string(index=False))
    print("wrote", out / f"{tag}.png")


if __name__ == "__main__":
    main()
