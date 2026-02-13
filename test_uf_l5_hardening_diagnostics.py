from datetime import date, timedelta
import pandas as pd

from tfe_market_data import get_unified_market_data
from tfe_market_data_service import HistoryRequest

from uf_core.uf_structural_engine import compute_uf_structural_state


# Same control group you’ve been using
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


def run_l5_hardening_diagnostics(symbol: str) -> None:
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

    # MAIN UF PIPELINE (includes L5, hardening, safemode)
    uf_state = compute_uf_structural_state(close)

    level3 = uf_state.level3
    level4 = uf_state.level4
    level5 = uf_state.level5

    decision_vector = level5.get("decision_vector", [])
    hardening = level5.get("hardening", {})
    safemode = level5.get("safemode", {})

    flags = hardening.get("flags", {})
    raw_metrics = hardening.get("raw_metrics", {})
    notes = hardening.get("notes", [])

    print("\n====================================================")
    print(f"L5 / HARDENING DIAGNOSTICS: {symbol}")
    print("====================================================")

    # Basic UF summary
    print(f"Regime:          {level3.get('regime')}")
    print(f"S_UF:            {level4.get('S_UF')}")
    print(f"R_UF:            {level4.get('R_UF')}")
    print(f"Stability score: {level4.get('stability_score')}")
    print(f"Max Drawdown:    {level4.get('max_drawdown')}")

    # Decision vector actually delivered to TFE
    print(f"\nFinal decision_vector (from UFStructuralState.level5):")
    print(f"  {decision_vector}")

    # Hardening flags (what HA-1 / HA-2 / HA-3 saw)
    print("\n--- HARDENING FLAGS (htc_result.flags) ---")
    if flags:
        for k, v in flags.items():
            print(f"  {k}: {v}")
    else:
        print("  <no flags>")

    # Raw metrics that hardening controller used
    print("\n--- HARDENING RAW METRICS (htc_result.raw_metrics) ---")
    if raw_metrics:
        for k, v in raw_metrics.items():
            print(f"  {k}: {v}")
    else:
        print("  <no raw_metrics>")

    # Notes from hardening evaluation
    print("\n--- HARDENING NOTES ---")
    if notes:
        for n in notes:
            print(f"  - {n}")
    else:
        print("  <no notes>")

    # Safemode state summary
    print("\n--- SAFEMODE STATE ---")
    print(f"  safe_mode:    {safemode.get('safe_mode')}")
    print(f"  entry_step:   {safemode.get('entry_step')}")
    print(f"  entry_reasons:{safemode.get('entry_reasons')}")


if __name__ == "__main__":
    for sym in SYMBOLS:
        run_l5_hardening_diagnostics(sym)
