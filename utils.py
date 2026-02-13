# utils.py
# Shared constants + helpers used by all Streamlit pages

import pandas as pd
import data_loader
import portfolio

from engine import (
    get_history_range,
    latest_price_single,
    get_portfolio_and_prices as engine_portfolio_loader,
)


# ============================================================
# COLOR + THEME CONSTANTS
# ============================================================

UP_COLOR = "#00B050"
DOWN_COLOR = "#C00000"
PLOTLY_TEMPLATE = "plotly_dark"


# ============================================================
# PORTFOLIO LOADING (wrapper used by pages)
# ============================================================

def get_portfolio_and_prices():
    """
    Simple pass-through wrapper to engine.get_portfolio_and_prices()
    """
    return engine_portfolio_loader()


# ============================================================
# HISTORY RANGE (Ticker Lookup uses this)
# ============================================================

def history_range(code: str):
    return get_history_range(code)


# ============================================================
# LATEST PRICE FOR SINGLE TICKER
# ============================================================

def latest_price(ticker: str):
    return latest_price_single(ticker)
