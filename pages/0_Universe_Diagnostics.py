"""
0_Universe_Diagnostics.py

Temporary diagnostic page to verify that:
- Index universe loads correctly
- Crypto universe loads correctly
- JSON universe cache files can be read/written

No rebuild is triggered.
No UF-Core activity.
"""

from __future__ import annotations

import streamlit as st
import os
import json

from massive_universe_index import get_index_tickers_from_universe
from massive_universe_crypto import get_crypto_tickers_from_universe


st.title("Universe Diagnostics (Temporary)")

# ------------------------------------------------------------
# INDEX
# ------------------------------------------------------------
st.subheader("Index Universe")

try:
    index_ticks = get_index_tickers_from_universe()
    st.success(f"Loaded {len(index_ticks)} index symbols: {index_ticks}")
except Exception as exc:
    st.error(f"Index universe FAILED: {exc}")

# Check JSON file presence
if os.path.exists("massive_universe_index.json"):
    st.info("massive_universe_index.json exists.")
    try:
        with open("massive_universe_index.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        st.info(f"JSON content: {data}")
    except Exception as exc:
        st.error(f"Error reading index JSON: {exc}")
else:
    st.warning("massive_universe_index.json is missing.")


# ------------------------------------------------------------
# CRYPTO
# ------------------------------------------------------------
st.subheader("Crypto Universe")

try:
    crypto_ticks = get_crypto_tickers_from_universe()
    st.success(f"Loaded {len(crypto_ticks)} crypto symbols: {crypto_ticks}")
except Exception as exc:
    st.error(f"Crypto universe FAILED: {exc}")

# Check JSON file presence
if os.path.exists("massive_universe_crypto.json"):
    st.info("massive_universe_crypto.json exists.")
    try:
        with open("massive_universe_crypto.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        st.info(f"JSON content: {data}")
    except Exception as exc:
        st.error(f"Error reading crypto JSON: {exc}")
else:
    st.warning("massive_universe_crypto.json is missing.")


st.markdown("---")
st.info("If both universes load successfully, you may proceed to the full UF rebuild.")
