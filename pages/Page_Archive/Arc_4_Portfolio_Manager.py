import streamlit as st
import pandas as pd

from engine import get_portfolio_and_prices, get_history_with_indicators


# ==========================
# LOAD & SAVE HELPERS
# ==========================

def load_portfolio_df() -> pd.DataFrame:
    df = pd.read_csv("portfolio.csv")
    df.columns = [c.lower().strip() for c in df.columns]

    required = {"ticker", "quantity", "cost_basis"}
    if not required.issubset(df.columns):
        st.error("portfolio.csv must contain: ticker, quantity, cost_basis")
        st.stop()

    # Ensure asset_type exists
    if "asset_type" not in df.columns:
        df["asset_type"] = "equity"

    # Normalize types
    df["asset_type"] = df["asset_type"].apply(
        lambda v: "equity"
        if str(v).lower() in ("stock", "etf", "shares")
        else str(v).lower()
    )

    return df


def save_portfolio_df(df: pd.DataFrame):
    df.to_csv("portfolio.csv", index=False)


# ==========================
# PAGE CONTENT
# ==========================

st.title("🧺 Portfolio Manager")
st.write("Add, remove, or update assets in your portfolio.")


df = load_portfolio_df()
tickers = list(df["ticker"])

tab_add, tab_remove, tab_update = st.tabs(
    ["➕ Add Asset", "🗑 Remove Asset", "✏️ Update Asset"]
)


# -------------------------
# ADD ASSET
# -------------------------
with tab_add:
    st.subheader("Add Asset")

    new_ticker = st.text_input("Ticker (e.g., AAPL, BTC-USD):", key="add_ticker").upper().strip()
    new_qty = st.number_input("Quantity", min_value=0.0, format="%.4f", key="add_qty")
    new_cost = st.number_input("Cost Basis ($/unit)", min_value=0.0, format="%.4f", key="add_cost")
    new_type = st.selectbox("Asset Type", ["equity", "crypto", "etf", "index"], key="add_type")

    if st.button("Add to Portfolio", key="add_btn"):
        if new_ticker == "":
            st.error("Ticker cannot be empty.")
        else:
            new_row = pd.DataFrame([{
                "ticker": new_ticker,
                "quantity": new_qty,
                "cost_basis": new_cost,
                "asset_type": new_type
            }])
            df = pd.concat([df, new_row], ignore_index=True)
            save_portfolio_df(df)
            st.success(f"Added {new_ticker}")
            st.experimental_rerun()


# -------------------------
# REMOVE ASSET
# -------------------------
with tab_remove:
    st.subheader("Remove Asset")

    if not tickers:
        st.info("Portfolio is empty.")
    else:
        rm = st.selectbox("Select asset to remove", tickers, key="rm_selector")

        if st.button("Remove Asset", key="rm_btn"):
            df = df[df["ticker"] != rm]
            save_portfolio_df(df)
            st.success(f"Removed {rm}")
            st.experimental_rerun()


# -------------------------
# UPDATE ASSET
# -------------------------
with tab_update:
    st.subheader("Update Asset")

    if not tickers:
        st.info("Portfolio is empty.")
    else:
        up = st.selectbox("Select asset", tickers, key="up_selector")

        row = df[df["ticker"] == up].iloc[0]

        upd_qty = st.number_input(
            "Quantity", 
            min_value=0.0, 
            value=float(row["quantity"]), 
            format="%.4f",
            key="up_qty"
        )
        upd_cost = st.number_input(
            "Cost Basis ($/unit)", 
            min_value=0.0, 
            value=float(row["cost_basis"]), 
            format="%.4f",
            key="up_cost"
        )
        upd_type = st.selectbox(
            "Asset Type",
            ["equity", "crypto", "etf", "index"],
            index=["equity","crypto","etf","index"].index(str(row["asset_type"])),
            key="up_type"
        )

        if st.button("Save Changes", key="update_btn"):
            df.loc[df["ticker"] == up, "quantity"] = upd_qty
            df.loc[df["ticker"] == up, "cost_basis"] = upd_cost
            df.loc[df["ticker"] == up, "asset_type"] = upd_type
            save_portfolio_df(df)
            st.success(f"Updated {up}")
            st.experimental_rerun()
