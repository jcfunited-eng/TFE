from __future__ import annotations

from typing import Any, Dict, List, Tuple

import streamlit as st

from uf_snapshot_cache import (
    load_snapshot,
    load_filtered_snapshot,
    refresh_snapshot_full,
)


# ------------------------------------------------------------
# MDG v0.1 – classification and ranking (long‑only, no TA)
# ------------------------------------------------------------


def _extract_decision_vector(row: Dict[str, Any]) -> Tuple[float, float, float, float, float, float]:
    """
    decision_vector is stored as [D, M, R_rev, U_star, P, B].

    This helper makes the unpacking explicit and robust.
    """
    dv = row.get("decision_vector") or []
    if not isinstance(dv, (list, tuple)) or len(dv) != 6:
        # Fallback: neutral fields
        return 0.0, 0.0, 0.0, 0.5, 0.0, 0.0

    try:
        D, M, R_rev, U_star, P, B = map(float, dv)
    except Exception:
        return 0.0, 0.0, 0.0, 0.5, 0.0, 0.0

    return D, M, R_rev, U_star, P, B


def classify_from_row(row: Dict[str, Any]) -> str:
    """
    MDG v0.1 mapping from UF structural state → {BUY, HOLD, AVOID}.

    Rules (long‑only, aligned with your regime diagnostics):

        • Use UF as a field evaluator, not a TA signal.
        • S_UF ≥ 0.30 => structure present (coherence gate).
        • D_k > 0  => up‑phase (long side).
        • D_k ≤ 0  => no new long; treat as HOLD / EXIT region.
        • Shorts (D_k < 0) are not executed; they are not SELLs.

    We do NOT:
        • introduce TA indicators,
        • invent extra heuristics beyond S_UF, D_k, regime.
    """
    S_UF = float(row.get("S_UF") or 0.0)
    regime = (row.get("regime") or "").upper()

    D_k, M_k, R_rev_k, U_star, P_k, B_k = _extract_decision_vector(row)

    # 1) No coherent structure → avoid as a decision target.
    if S_UF < 0.30:
        return "AVOID"

    # 2) Coherent structure but DSF not pointing up → HOLD (no new long).
    if D_k <= 0.0:
        return "HOLD"

    # 3) Coherent + up‑phase → BUY candidates.
    #    Regime influences *strength* but not the discrete label here.
    if regime in ("TRANSITIONAL", "STABLE"):
        return "BUY"

    # 4) Fallback for unknown regime: treat as weak BUY.
    return "BUY"


def structural_score(row: Dict[str, Any]) -> float:
    """
    Ranking score (UF structural) — no TA.

    Simple, transparent weighting:

        score = 0.5 * S_UF + 0.5 * R_UF

    This prefers symbols that are both structurally coherent and robust
    under perturbation. No magical thresholds, no domain‑specific TA.
    """
    S_UF = float(row.get("S_UF") or 0.0)
    R_UF = float(row.get("R_UF") or 0.0)
    return 0.5 * S_UF + 0.5 * R_UF


# ------------------------------------------------------------
# Page UI
# ------------------------------------------------------------

st.title("Tao Financial Engine — UF-Core Market Recommendations")

snapshot_rows: List[Dict[str, Any]] = load_snapshot()
st.markdown(
    f"UF snapshot loaded for **{len(snapshot_rows)} symbols** "
    "(snapshot-only, no live API calls performed here)."
)

# ---------------- Asset type + band controls ----------------
col_asset, col_min, col_max = st.columns([1, 1, 1])

with col_asset:
    asset_type_label = st.selectbox(
        "Asset type",
        ["Stocks", "ETFs", "Index", "Crypto"],
        index=0,
    )

asset_type_map: Dict[str, Tuple[str, ...]] = {
    "Stocks": ("stock",),
    "ETFs": ("etf",),
    "Index": ("index",),
    "Crypto": ("crypto",),
}

asset_types = asset_type_map[asset_type_label]

with col_min:
    min_price = st.number_input("Min price", value=0.0, min_value=0.0)

with col_max:
    max_price = st.number_input("Max price", value=100000.0, min_value=0.0)

# ---------------- Admin controls ----------------
st.markdown("### Admin Snapshot Controls (UF + local cache)")

col_reload, col_rebuild = st.columns(2)

with col_reload:
    if st.button("Re-load UF snapshot from disk"):
        # Streamlit's recommended way to force a fresh read.
        if hasattr(st, "experimental_rerun"):
            st.experimental_rerun()
        else:
            st.info("Snapshot reload will occur on next page refresh.")

with col_rebuild:
    if st.button("Rebuild FULL UF snapshot (stocks + ETFs + index + crypto)"):
        st.info("Running rebuild… this may take time.")
        refresh_snapshot_full(("stock", "etf", "index", "crypto"))
        st.success("Full UF snapshot rebuilt. Please refresh the page (F5).")

# ---------------- Filter + classification ----------------
filtered_rows: List[Dict[str, Any]] = load_filtered_snapshot(
    min_price=min_price,
    max_price=max_price,
    asset_types=asset_types,
)

for r in filtered_rows:
    r["classification"] = classify_from_row(r)
    r["score"] = structural_score(r)

# Sort by structural score (best first)
filtered_rows.sort(key=lambda r: r.get("score", 0.0), reverse=True)

st.markdown(f"### Filtered results ({len(filtered_rows)} symbols)")

# ---------------- Top 5 Hot Picks under $30 (Stocks only) ----------------
st.markdown("#### Top 5 Hot Picks — Stocks under $30 (BUY only)")

hot_rows: List[Dict[str, Any]] = [
    r
    for r in snapshot_rows
    if r.get("asset_type") == "stock"
    and r.get("price") is not None
    and float(r["price"]) < 30.0
]

for r in hot_rows:
    r["classification"] = classify_from_row(r)
    r["score"] = structural_score(r)

hot_rows = [r for r in hot_rows if r["classification"] == "BUY"]
hot_rows.sort(key=lambda r: r.get("score", 0.0), reverse=True)
hot_rows = hot_rows[:5]

if hot_rows:
    hot_table = [
        {
            "ticker": r.get("ticker"),
            "price": r.get("price"),
            "regime": r.get("regime"),
            "S_UF": r.get("S_UF"),
            "R_UF": r.get("R_UF"),
        }
        for r in hot_rows
    ]
    st.table(hot_table)
else:
    st.info("No BUY candidates under $30 at this time.")

# ---------------- Top 10 BUYs in current asset type ----------------
st.markdown(f"#### Top 10 BUYs in {asset_type_label}")

buy_rows = [r for r in filtered_rows if r.get("classification") == "BUY"]
top10 = buy_rows[:10]

if top10:
    top_table = [
        {
            "ticker": r.get("ticker"),
            "price": r.get("price"),
            "regime": r.get("regime"),
            "S_UF": r.get("S_UF"),
            "R_UF": r.get("R_UF"),
        }
        for r in top10
    ]
    st.table(top_table)
else:
    st.info("No BUY candidates in the current asset type and band.")

# ---------------- Full result table ----------------
st.markdown("#### Full ranked list (structural)")

if filtered_rows:
    cols = [
        "ticker",
        "asset_type",
        "price",
        "classification",
        "regime",
        "S_UF",
        "R_UF",
    ]
    table = [{c: r.get(c) for c in cols} for r in filtered_rows]
    # Streamlit 1.41: use width='stretch' instead of use_container_width
    st.dataframe(table, width="stretch")
else:
    st.info("No symbols match the current filters.")
