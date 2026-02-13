from datetime import date, timedelta
import numpy as np
import pandas as pd

from tfe_market_data import get_unified_market_data
from tfe_market_data_service import HistoryRequest
from uf_core.layer0 import compute_sev_series
from uf_core.layer1 import segment_gates
from uf_core.layer2 import interpret_gates
from uf_core.layer3 import compute_resonance
from uf_core.config import KERNEL_THRESHOLDS

# Same control-group symbols you already used
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


def run_deltaR_diagnostics(symbol: str) -> None:
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

    # L0–L3 pipeline
    sev_list = compute_sev_series(df, field_col="Close")
    gates = segment_gates(sev_list)
    interps = interpret_gates(sev_list, gates)
    resonance = compute_resonance(interps)

    if not resonance or len(resonance) < 2:
        print(f"\n=== {symbol}: INSUFFICIENT GATES FOR ΔR ===")
        return

    # URF_k (effective resonance)
    urf = np.array([float(r.URF_k) for r in resonance], dtype=float)

    # ΔR sequence
    delta_R = np.diff(urf)
    abs_delta = np.abs(delta_R)

    # Adaptive epsilon_D_eff as defined in layer4
    epsilon_D = getattr(KERNEL_THRESHOLDS, "epsilon_D", 0.01)
    alpha_eps = getattr(KERNEL_THRESHOLDS, "epsilon_D_alpha", 1.0)

    sigma_delta_R = float(np.std(delta_R)) if delta_R.size > 0 else 0.0
    epsilon_eff = float(epsilon_D * (1.0 + alpha_eps * sigma_delta_R))

    max_abs = float(abs_delta.max()) if abs_delta.size > 0 else 0.0
    mean_abs = float(abs_delta.mean()) if abs_delta.size > 0 else 0.0
    std_abs = float(abs_delta.std()) if abs_delta.size > 0 else 0.0

    if epsilon_eff > 0.0:
        pct_active = float((abs_delta > epsilon_eff).mean())
    else:
        pct_active = 0.0

    print(f"\n=== ΔR DIAGNOSTICS ===")
    print(f"Symbol: {symbol}")
    print(f"Number of gates: {len(gates)}")
    print(f"epsilon_D base: {epsilon_D}")
    print(f"sigma_delta_R: {sigma_delta_R}")
    print(f"epsilon_D_eff: {epsilon_eff}")
    print(f"max |ΔR|: {max_abs}")
    print(f"mean |ΔR|: {mean_abs}")
    print(f"std  |ΔR|: {std_abs}")
    print(f"fraction(|ΔR| > epsilon_D_eff): {pct_active}")


if __name__ == "__main__":
    for sym in SYMBOLS:
        run_deltaR_diagnostics(sym)
