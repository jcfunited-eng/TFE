import pandas as pd
from datetime import date, timedelta

from uf_core.uf_structural_engine import compute_uf_structural_state

from uf_core.layer0 import compute_sev_series
from uf_core.layer1 import segment_gates
from uf_core.layer3 import compute_resonance
from uf_core.layer4 import compute_directional_signal  # <-- DSF SOURCE

from tfe_market_data import get_unified_market_data
from tfe_market_data_service import HistoryRequest, Timespan


SYMBOLS = [
    "F",
    "AAPL",
    "AAL",
    "AAT",
    "ABL",
    "ABTS",
    "EQIX",
    "NOC",
    "AFJK",
    "NCPL",
    "TWG",
    "YAAS",
]


# --------------------------------------------------------
# LOAD MARKET HISTORY
# --------------------------------------------------------
def load_history(symbol, lookback_days=400):
    mds = get_unified_market_data()
    end = date.today()
    start = end - timedelta(days=lookback_days)

    req = HistoryRequest(
        symbol=symbol,
        start=start,
        end=end,
        timespan=Timespan.DAY,
        limit=5000,
    )

    try:
        hist = mds.get_history(req)
    except Exception:
        return None

    if hist is None or len(hist.bars) == 0:
        return None

    ts = [b.timestamp for b in hist.bars]
    px = [b.close for b in hist.bars]

    df = pd.DataFrame({"Close": px}, index=pd.to_datetime(ts))
    df = df.sort_index()
    return df


# --------------------------------------------------------
# TRUE RAW L4 DSF (ONLY VALID SOURCE)
# --------------------------------------------------------
def compute_raw_L4(df):
    sev = compute_sev_series(df, field_col="Close")
    gates = segment_gates(sev)
    res = compute_resonance(sev, gates)
    dsf = compute_directional_signal(sev, gates, res)

    if len(dsf) == 0:
        return None

    last = dsf[-1]   # <-- contains D_k, M_k, R_rev_k, U_star_k, P_k, B_k

    return [
        float(last.D_k),
        float(last.M_k),
        float(last.R_rev_k),
        float(last.U_star_k),
        float(last.P_k),
        float(last.B_k),
    ]


# --------------------------------------------------------
# PER-SYMBOL BACKTEST
# --------------------------------------------------------
def backtest_symbol(symbol):
    df = load_history(symbol)
    if df is None:
        print(f"[NO DATA] {symbol}")
        return None

    raw_vec = compute_raw_L4(df)
    state = compute_uf_structural_state(df["Close"])

    governed_vec = state.level5.get("decision_vector")
    regime = state.level3.get("regime")
    S_UF = state.level4.get("S_UF")
    R_UF = state.level4.get("R_UF")
    stability = state.level4.get("stability_score")
    mdd = state.level4.get("max_drawdown")

    print("\n====================================================")
    print(f"RAW vs GOVERNED DECISION: {symbol}")
    print("====================================================")
    print(f"Regime:          {regime}")
    print(f"S_UF:            {S_UF}")
    print(f"R_UF:            {R_UF}")
    print(f"Stability score: {stability}")

    print("\nRAW UF DECISION (TRUE L4 DSF):")
    print(f"  {raw_vec}")

    print("\nGOVERNED DECISION:")
    print(f"  {governed_vec}")

    print("====================================================\n")

    return {
        "symbol": symbol,
        "raw": raw_vec,
        "governed": governed_vec,
        "regime": regime,
        "S_UF": S_UF,
        "R_UF": R_UF,
        "stability": stability,
        "max_drawdown": mdd,
    }


# --------------------------------------------------------
# MAIN
# --------------------------------------------------------
if __name__ == "__main__":
    for sym in SYMBOLS:
        backtest_symbol(sym)
