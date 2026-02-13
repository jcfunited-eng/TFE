from datetime import date, timedelta
import pandas as pd

from tfe_market_data import get_unified_market_data
from tfe_market_data_service import HistoryRequest

from uf_core.layer0 import compute_sev_series
from uf_core.layer1 import segment_gates
from uf_core.layer2 import interpret_gates
from uf_core.layer3 import compute_resonance
from uf_core.layer4 import compute_directional_signal, compute_dsf
from uf_core.uf_structural_engine import compute_uf_structural_state

# Control-group symbols you've been using
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


def run_raw_vs_governed(symbol: str) -> None:
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

    df = pd.DataFrame({"Close": close})

    # ---- UF-Core L0..L3 to reconstruct raw DSF ----
    sev_list = compute_sev_series(df, field_col="Close")
    gates = segment_gates(sev_list)
    interps = interpret_gates(sev_list, gates)
    resonance = compute_resonance(interps)

    if not resonance:
        print(f"\n=== {symbol}: NO GATES / NO RESONANCE ===")
        return

    # L4 DSF sequence
    decision_states = compute_directional_signal(resonance)
    dsf_list = compute_dsf(decision_states)

    last_dsf = dsf_list[-1]

    # Raw kernel decision vector (pre-hardening, pre-safemode)
    raw_decision_vector = [
        float(last_dsf.D_k),
        float(last_dsf.M_k),
        float(last_dsf.R_rev_k),
        float(last_dsf.U_star_k),
        float(last_dsf.P_k),
        float(last_dsf.B_k),
    ]

    # ---- Full UF engine (with hardening + safemode) ----
    state = compute_uf_structural_state(close)

    regime = state.level3.get("regime")
    S_UF = state.level4.get("S_UF")
    R_UF = state.level4.get("R_UF")
    stability_score = state.level4.get("stability_score")
    governed_decision_vector = state.level5.get("decision_vector")

    print("\n====================================================")
    print(f"RAW vs GOVERNED DECISION: {symbol}")
    print("====================================================")
    print(f"Regime:          {regime}")
    print(f"S_UF:            {S_UF}")
    print(f"R_UF:            {R_UF}")
    print(f"Stability score: {stability_score}")
    print(f"Num gates:       {len(gates)}")

    print("\nRAW UF DECISION (L4 DSF, last gate, pre-hardening):")
    print(f"  [D, M, R_rev, U*, P, B] = {raw_decision_vector}")

    print("\nGOVERNED DECISION (post-hardening + safemode):")
    print(f"  decision_vector = {governed_decision_vector}")
    print("====================================================\n")


if __name__ == "__main__":
    for sym in SYMBOLS:
        run_raw_vs_governed(sym)
