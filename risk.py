from typing import Dict, Tuple

import numpy as np
import pandas as pd


def daily_returns(prices: pd.Series) -> pd.Series:
    """Simple percentage daily returns from a price series."""
    return prices.pct_change().dropna()


def annualized_volatility(
    returns: pd.Series,
    periods_per_year: int = 252,
) -> float:
    """
    Annualized volatility (standard deviation of returns).
    """
    if returns.empty:
        return 0.0
    return float(returns.std(ddof=1) * np.sqrt(periods_per_year))


def sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """
    Basic Sharpe ratio using arithmetic mean of returns.
    risk_free_rate is annualized (e.g., 0.02 = 2%).
    """
    if returns.empty:
        return 0.0

    mean_return = float(returns.mean()) * periods_per_year
    excess_return = mean_return - risk_free_rate
    vol = annualized_volatility(returns, periods_per_year=periods_per_year)
    if vol == 0:
        return 0.0
    return excess_return / vol


def max_drawdown(equity_curve: pd.Series) -> Tuple[float, float]:
    """
    Maximum drawdown and duration.

    Returns:
        (max_drawdown_pct, max_drawdown_duration_days)
    """
    if equity_curve.empty:
        return 0.0, 0.0

    running_max = equity_curve.cummax()
    drawdowns = equity_curve / running_max - 1.0

    max_dd = float(drawdowns.min())

    # Duration in days of the worst drawdown
    underwater = drawdowns < 0
    max_duration = 0
    current = 0
    for is_under in underwater:
        if is_under:
            current += 1
            max_duration = max(max_duration, current)
        else:
            current = 0

    return max_dd, float(max_duration)


def beta(
    asset_returns: pd.Series,
    benchmark_returns: pd.Series,
) -> float:
    """
    Beta of an asset (or portfolio) vs a benchmark.
    """
    aligned = pd.concat([asset_returns, benchmark_returns], axis=1).dropna()
    if aligned.shape[0] < 2:
        return 0.0

    cov = np.cov(aligned.iloc[:, 0], aligned.iloc[:, 1])[0][1]
    var = np.var(aligned.iloc[:, 1])
    if var == 0:
        return 0.0
    return float(cov / var)


def var_lite(
    returns: pd.Series,
    confidence: float = 0.95,
) -> float:
    """
    Very simple historical Value-at-Risk estimate.
    Negative value indicates potential loss.
    """
    if returns.empty:
        return 0.0

    alpha = 1.0 - confidence
    return float(np.quantile(returns, alpha))
