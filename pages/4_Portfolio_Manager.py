import streamlit as st
import pandas as pd

from tfe_market_data import get_unified_market_data
from tfe_market_data_service import TickerInfo

from tfe_portfolio_api import (
    get_portfolio_df,
    save_portfolio_df,
)


# ============================================================
# PAGE HEADER
# ============================================================

st.title("🧺 Portfolio Manager")
st.write("Add, remove, or update assets in your portfolio (SES-Core encrypted storage).")

mds = get_unified_market_data()

# Load the SES-Core portfolio
df = get_portfolio_df()
tickers = list(df["ticker"]) if not df.empty else []


# ============================================================
# VALIDATION HELPER
# ============================================================

def is_valid_ticker(t: str) -> bool:
    """
    Validate tickers using unified market data service.
    """
    info = mds.get_ticker_info(t)
    return info is not None


# ============================================================
# TABS
# ============================================================

tab_add, tab_remove, tab_update = st.tabs(
    ["➕ Add Asset", "🗑 Remove Asset", "✏️ Update Asset"]
)


# ============================================================
# TAB: ADD ASSET
# ============================================================

with tab_add:
    st.subheader("➕ Add Asset")

    new_ticker = st.text_input("Ticker (e.g., AAPL, BTC-USD)", key="add_ticker").upper().strip()
    qty = st.number_input("Quantity", min_value=0.0, step=0.01, key="add_qty")
    cost = st.number_input("Cost Basis ($ per unit)", min_value=0.0, step=0.01, key="add_cost")
    a_type = st.selectbox("Asset Type", ["equity", "crypto", "index", "etf"], key="add_type")

    if st.button("Add to Portfolio", key="add_button"):
        if new_ticker == "":
            st.error("Ticker cannot be empty.")
        elif new_ticker in tickers:
            st.error("Ticker already exists.")
        elif not is_valid_ticker(new_ticker):
            st.error(f"{new_ticker} is not recognized by Massive/Alpaca data providers.")
        else:
            new_row = pd.DataFrame([{
                "ticker": new_ticker,
                "quantity": qty,
                "cost_basis": cost,
                "asset_type": a_type,
            }])

            if df.empty:
                new_df = new_row
            else:
                new_df = pd.concat([df, new_row], ignore_index=True)

            save_portfolio_df(new_df)
            st.success(f"{new_ticker} added successfully.")
            st.rerun()


# ============================================================
# TAB: REMOVE ASSET
# ============================================================

with tab_remove:
    st.subheader("🗑 Remove Asset")

    if not tickers:
        st.info("Portfolio is empty.")
    else:
        rem_ticker = st.selectbox("Select Ticker to Remove", tickers, key="remove_ticker")

        if st.button("Remove Asset", key="remove_button"):
            new_df = df[df["ticker"] != rem_ticker]
            save_portfolio_df(new_df)
            st.success(f"{rem_ticker} removed successfully.")
            st.rerun()


# ============================================================
# TAB: UPDATE ASSET
# ============================================================

with tab_update:
    st.subheader("✏️ Update Asset")

    if not tickers:
        st.info("Portfolio is empty.")
        st.stop()

    upd_ticker = st.selectbox("Select Ticker", tickers, key="update_ticker")

    row = df[df["ticker"] == upd_ticker].iloc[0]

    new_qty = st.number_input(
        "Quantity",
        min_value=0.0,
        step=0.01,
        value=float(row["quantity"]),
        key="upd_qty"
    )

    new_cost = st.number_input(
        "Cost Basis ($ per unit)",
        min_value=0.0,
        step=0.01,
        value=float(row["cost_basis"]),
        key="upd_cost"
    )

    new_type = st.selectbox(
        "Asset Type",
        ["equity", "crypto", "index", "etf"],
        index=["equity", "crypto", "index", "etf"].index(row["asset_type"]),
        key="upd_type"
    )

    if st.button("Update Asset", key="update_button"):
        new_df = df.copy()
        new_df.loc[new_df["ticker"] == upd_ticker, "quantity"] = new_qty
        new_df.loc[new_df["ticker"] == upd_ticker, "cost_basis"] = new_cost
        new_df.loc[new_df["ticker"] == upd_ticker, "asset_type"] = new_type

        save_portfolio_df(new_df)
        st.success(f"{upd_ticker} updated successfully.")
        st.rerun()
