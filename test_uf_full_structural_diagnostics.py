from datetime import date, timedelta
import numpy as np
import pandas as pd

from tfe_market_data import get_unified_market_data
from tfe_market_data_service import HistoryRequest

from uf_core.layer0 import compute_sev_series
from uf_core.layer1 import segment_gates
from uf_core.layer2 import interpret_gates
from uf_core.layer3 import compute_resonance
from uf_core.layer4 import compute_directional_signal, compute_dsf
from uf_core.config import KERNEL_THRESHOLDS

SYMBOLS = [
    "F","AAPL","AAL","AAT","ABL",
    "ABTS","EQIX","NOC","AFJK","NCPL",
    "TWG","YAAS"
]


def run_structural_diagnostics(symbol: str):

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

    # --------------------------
    # L0–L3 pipeline
    # --------------------------

    sev_list = compute_sev_series(df, field_col="Close")
    gates = segment_gates(sev_list)
    interps = interpret_gates(sev_list, gates)
    resonance = compute_resonance(interps)

    if len(resonance) < 2:
        print(f"\n=== {symbol}: insufficient gates for deep diagnostics ===")
        return

    # Effective resonance = URF_k
    urf = np.array([float(r.URF_k) for r in resonance])
    delta_R = np.diff(urf)

    # Adaptive epsilon_D_eff
    eps_base = float(getattr(KERNEL_THRESHOLDS, "epsilon_D", 0.00073))
    alpha_eps = float(getattr(KERNEL_THRESHOLDS, "epsilon_D_alpha", 1.0))
    sigma = float(np.std(delta_R)) if delta_R.size else 0.0
    eps_eff = eps_base * (1.0 + alpha_eps * sigma)

    # --------------------------
    # L4 DSF full sequence
    # --------------------------
    ds_states = compute_directional_signal(resonance)
    dsf_full = compute_dsf(ds_states)

    print("\n====================================================")
    print(f"FULL STRUCTURAL DIAGNOSTICS: {symbol}")
    print("====================================================")
    print(f"Number of gates: {len(gates)}")
    print(f"epsilon_D base: {eps_base}")
    print(f"sigma_delta_R: {sigma}")
    print(f"epsilon_D_eff: {eps_eff}")
    print("")

    print("--- SECTION 1: L4 DSF DUMP (ALL GATES) ---")
    for k in range(len(resonance)):
        if k == 0:
            dR = 0.0
        else:
            dR = delta_R[k-1]

        r = resonance[k]
        ds = ds_states[k]
        dsf = dsf_full[k]

        print(f"\nGate {k}:")
        print(f"  ΔR:                 {dR}")
        print(f"  eps_D_eff:          {eps_eff}")
        print(f"  D_k:                {ds.D_k}")
        print(f"  M_k:                {ds.M_k}")
        print(f"  R_rev_k:            {ds.R_rev_k}")
        print(f"  U_star_k:           {ds.U_star_k}")
        print(f"  P_k:                {ds.P_k}")
        print(f"  B_k:                {ds.B_k}")
        print(f"  Raw R_k:            {r.R_k}")
        print(f"  URF_k:              {r.URF_k}")
        print(f"  U_k:                {r.U_k}")
        print(f"  IAS_k:              {r.IAS_k}")
        print(f"  Hyst_k:             {r.Hyst_k}")

    # --------------------------
    # SECTION 2: L5 suppression trace
    # --------------------------

    print("\n--- SECTION 2: L5 DECISION PIPELINE ---")

    print("NOTE:")
    print("L5 takes the *last gate’s* DSF and reliability fields.")
    print("If earlier DSF has structure but the last gate is neutral,")
    print("the delivered decision_vector will appear silent.")

    # Summary of last gate
    last = ds_states[-1]
    print("\nLAST GATE DSF:")
    print(f"  D:  {last.D_k}")
    print(f"  M:  {last.M_k}")
    print(f"  Rr: {last.R_rev_k}")
    print(f"  U*: {last.U_star_k}")
    print(f"  P:  {last.P_k}")
    print(f"  B:  {last.B_k}")

    # --------------------------
    # SECTION 3: Semantic divergence analysis
    # --------------------------

    print("\n--- SECTION 3: SEMANTIC INVARIANCE ---")

    for k, r in enumerate(resonance):
        cv_norm = np.linalg.norm(interps[k].CV_k)
        S_k = float(interps[k].S_k)
        U_k = float(interps[k].U_k)
        regime = interps[k].regime

        if k == 0:
            dR = 0.0
        else:
            dR = delta_R[k-1]

        # Semantic divergence score
        gamma_k = cv_norm + S_k - U_k

        print(f"\nGate {k}:")
        print(f"  ΔR: {dR}")
        print(f"  CV_norm: {cv_norm}")
        print(f"  S_k: {S_k}")
        print(f"  U_k: {U_k}")
        print(f"  regime: {regime}")
        print(f"  Γ_k (semantic divergence): {gamma_k}")

    # --------------------------
    # SECTION 4: Structural summary
    # --------------------------

    D_all = np.array([ds.D_k for ds in ds_states])
    pct_nonzero = float((D_all != 0).mean())

    print("\n--- SECTION 4: STRUCTURAL SUMMARY ---")
    print(f"Fraction of gates with D_k ≠ 0:  {pct_nonzero}")
    print(f"Mean |ΔR|: {np.mean(np.abs(delta_R))}")
    print(f"Mean semantic divergence Γ: {np.mean([np.linalg.norm(ip.CV_k)+ip.S_k-ip.U_k for ip in interps])}")


if __name__ == "__main__":
    for sym in SYMBOLS:
        run_structural_diagnostics(sym)
