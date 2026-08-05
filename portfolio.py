# portfolio.py
# Unified Portfolio Snapshot Engine for Tao Financial Engine (TFE)

import pandas as pd
import numpy as np


class PortfolioSnapshot:
    """
    A consistent structure for sharing portfolio statistics across
    Dashboard, Insights, Recommendations, Watchlist, and Advisor View.
    """

    def __init__(self, positions, latest_prices):
        self.positions = positions
        self.latest_prices = latest_prices

        # Compute everything once
        self.current_values = self._compute_current_values()
        self.total_value = self.current_values.sum()

        self.cost_basis_value = (positions["quantity"] * positions["cost_basis"]).sum()
        self.unrealized_pl = self.total_value - self.cost_basis_value
        self.unrealized_pl_percent = (
            (self.unrealized_pl / self.cost_basis_value) * 100
            if self.cost_basis_value > 0 else 0
        )

        # exposure weights
        self.weights = self._compute_weights()

        # diversification score (simple entropy-based measure)
        self.diversification = self._compute_diversification()

    # -----------------------------------------------------
    # INTERNAL: compute the current value per position
    # -----------------------------------------------------
    def _compute_current_values(self):
        rows = []
        for _, row in self.positions.iterrows():
            ticker = row["ticker"]
            qty = float(row["quantity"])
            price = self.latest_prices.get(ticker, 0)

            if price is None:
                price = 0

            rows.append(qty * price)

        return pd.Series(rows)

    # -----------------------------------------------------
    # INTERNAL: compute position weights
    # -----------------------------------------------------
    def _compute_weights(self):
        if self.total_value <= 0:
            return {t: 0 for t in self.positions["ticker"].tolist()}

        result = {}
        for i, row in self.positions.iterrows():
            ticker = row["ticker"]
            current_val = self.current_values.iloc[i]
            result[ticker] = float(current_val / self.total_value)

        return result

    # -----------------------------------------------------
    # INTERNAL: diversification
    # -----------------------------------------------------
    def _compute_diversification(self):
        w = np.array(list(self.weights.values()))

        if len(w) == 0:
            return 0.0

        w = w[w > 0]
        entropy = -np.sum(w * np.log(w))
        max_entropy = np.log(len(w))
        return float(entropy / max_entropy if max_entropy > 0 else 0)


# ---------------------------------------------------------
# EXPORTED FUNCTION (used by utils → every page)
# ---------------------------------------------------------
def compute_portfolio_snapshot(positions, latest_prices):
    """
    Compatibility wrapper — do NOT delete.
    Older pages call compute_portfolio_snapshot().
    It now simply returns the new class.
    """
    return PortfolioSnapshot(positions, latest_prices)
