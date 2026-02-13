import streamlit as st
import pandas as pd
import numpy as np

from uf_snapshot_cache import load_snapshot
from tfe_portfolio_api import get_portfolio_df


# ============================================================
# UF-LINKED ADVISOR VIEW (NO LIVE CALLS)
# ============================================================

st.set_page_config(layout="wide")
st.title("🧠 Advisor View — UF Structural Guidance (Snapshot Only)")

snapshot_rows = load_snapshot()
if not snapshot_rows:
    st.error("No UF snapshot found. Run UF snapshot generation first.")
    st.stop()

snap_df = pd.DataFrame(snapshot_rows)
if "ticker" not in snap_df.columns:
    st.error("UF snapshot malformed: missing 'ticker' field.")
    st.stop()

snap_df["ticker"] = snap_df["ticker"].astype(str).str.upper()

for c in ["S_UF", "R_UF", "stability_score", "max_dd", "regime"]:
    if c not in snap_df.columns:
        snap_df[c] = np.nan

portfolio_df = get_portfolio_df()
if portfolio_df is None or portfolio_df.empty:
    st.warning("Your portfolio is empty.")
    st.stop()

portfolio_df = portfolio_df.copy()
portfolio_df["ticker"] = portfolio_df["ticker"].astype(str).str.upper()


# ============================================================
# SIMPLE UF-BASED ACTION RULE
# ============================================================

def uf_action_from_row(row: pd.Series) -> dict:
    """
    Map UF snapshot fields to a human-readable action.

    Inputs (row fields):
        S_UF, R_UF, max_dd, stability_score

    Output:
        { action, confidence, reason }
    """
    S = float(row.get("S_UF", 0.0) or 0.0)
    R = float(row.get("R_UF", 0.0) or 0.0)
    max_dd = float(row.get("max_dd", row.get("max_drawdown", 0.0)) or 0.0)
    stab = float(row.get("stability_score", 0.0) or 0.0)

    # Composite score similar to uf_rank_universe
    score = 0.4 * S + 0.3 * R + 0.3 * max(0.0, stab)

    # Confidence heuristic
    confidence = max(0.0, min(1.0, (score + 1.0) / 2.0))

    # Basic rule-set
    if score > 0.8 and max_dd > -0.5:
        action = "ACCUMULATE"
        reason = "Strong UF structure with acceptable drawdown."
    elif score > 0.5 and max_dd > -0.6:
        action = "HOLD"
        reason = "Healthy UF structure; maintain position."
    elif score > 0.2 or max_dd > -0.7:
        action = "TRIM"
        reason = "Mixed UF structure or drawdown; consider reducing."
    else:
        action = "AVOID"
        reason = "Weak UF structure and/or deep drawdown."

    return {
        "action": action,
        "confidence": confidence,
        "reason": reason,
    }


# ============================================================
# BUILD ADVISOR TABLE
# ============================================================

rows = []

merged = portfolio_df.merge(snap_df, how="left", on="ticker", suffixes=("", "_snap"))

for _, r in merged.iterrows():
    ticker = r["ticker"]

    if pd.isna(r["S_UF"]) or pd.isna(r["R_UF"]):
        rows.append({
            "Ticker": ticker,
            "Price": r.get("price", np.nan),
            "UF Action": "NO DATA",
            "Confidence": np.nan,
            "Reason": "No UF snapshot entry for this asset.",
            "Regime": r.get("regime", None),
            "S_UF": r.get("S_UF", np.nan),
            "R_UF": r.get("R_UF", np.nan),
            "Stability": r.get("stability_score", np.nan),
            "MaxDD %": float(r.get("max_dd", r.get("max_drawdown", 0.0)) or 0.0) * 100.0,
        })
        continue

    decision = uf_action_from_row(r)

    rows.append({
        "Ticker": ticker,
        "Price": r.get("price", np.nan),
        "UF Action": decision["action"],
        "Confidence": decision["confidence"],
        "Reason": decision["reason"],
        "Regime": r.get("regime", None),
        "S_UF": r.get("S_UF", np.nan),
        "R_UF": r.get("R_UF", np.nan),
        "Stability": r.get("stability_score", np.nan),
        "MaxDD %": float(r.get("max_dd", r.get("max_drawdown", 0.0)) or 0.0) * 100.0,
    })

advisor_df = pd.DataFrame(rows)


# ============================================================
# DISPLAY ADVISOR TABLE
# ============================================================

st.header("📊 UF Structural Metrics & Actions")

st.dataframe(
    advisor_df[
        [
            "Ticker",
            "Price",
            "UF Action",
            "Confidence",
            "S_UF",
            "R_UF",
            "Stability",
            "MaxDD %",
            "Regime",
        ]
    ],
    use_container_width=True,
)


# ============================================================
# SUGGESTED ACTIONS (TEXT)
# ============================================================

st.header("📌 Suggested Actions (UF L5-derived)")

for _, r in advisor_df.iterrows():
    t = r["Ticker"]
    action = r["UF Action"]
    reason = r["Reason"]

    if action == "ACCUMULATE":
        st.markdown(f"🟢 **{t} — ACCUMULATE**  •  _{reason}_")
    elif action == "HOLD":
        st.markdown(f"🔵 **{t} — HOLD**  •  _{reason}_")
    elif action == "TRIM":
        st.markdown(f"🟠 **{t} — TRIM**  •  _{reason}_")
    elif action == "AVOID":
        st.markdown(f"🔴 **{t} — AVOID**  •  _{reason}_")
    else:
        st.markdown(f"⚪ **{t} — NO DATA**")
