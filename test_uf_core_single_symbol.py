from datetime import date, timedelta
import pandas as pd

from tfe_market_data import get_unified_market_data
from tfe_market_data_service import HistoryRequest, Timespan
from uf_core.uf_structural_engine import compute_uf_structural_state
from uf_core.layer3 import compute_resonance
from uf_core.layer2 import interpret_gates
from uf_core.layer1 import segment_gates
from uf_core.layer0 import compute_sev_series


# Symbol control group – from your recent runs
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


def run_single(symbol: str) -> None:
    mds = get_unified_market_data()

    end = date.today()
    start = end - timedelta(days=400)

    req = HistoryRequest(symbol=symbol, start=start, end=end)
    hist = mds.get_history(req)
    bars = hist.bars

    if not bars:
        print(f"\n=== {symbol}: NO DATA ===")
        return

    close = pd.Series(
        [b.close for b in bars],
        index=[b.timestamp for b in bars],
    ).sort_index()

    # ---- UF-L0..L3 manual probe ----
    df = pd.DataFrame({"Close": close})
    sev_list = compute_sev_series(df, field_col="Close")
    gates = segment_gates(sev_list)
    interp = interpret_gates(sev_list, gates)
    resonance = compute_resonance(interp)

    print("\n=== RESONANCE DIAGNOSTICS ===")
    print(f"Symbol: {symbol}")
    print(f"Number of gates: {len(gates)}")
    print("R_k sequence (raw L3 R_k):")
    print([float(r.R_k) for r in resonance])
    print("URF_k sequence (g_k * R_k):")
    print([float(r.URF_k) for r in resonance])
    print("Hyst_k sequence:")
    print([int(r.Hyst_k) for r in resonance])
    print("U_k sequence (L2 uncertainty):")
    print([float(r.interpretation.U_k) for r in resonance])
    print("IAS_k sequence:")
    print([int(r.interpretation.IAS_k) for r in resonance])

    # ---- Full engine summary ----
    state = compute_uf_structural_state(close)

    print("\n=== UF-Core Single Symbol Test ===")
    print(f"Symbol: {symbol}")
    print("Regime:", state.level3.get("regime"))
    print("S_UF:", state.level4.get("S_UF"))
    print("R_UF:", state.level4.get("R_UF"))
    print("Stability Score:", state.level4.get("stability_score"))
    print("Decision Vector:", state.level5.get("decision_vector"))
    print("Max Drawdown:", state.level4.get("max_drawdown"))


if __name__ == "__main__":
    for sym in SYMBOLS:
        run_single(sym)
