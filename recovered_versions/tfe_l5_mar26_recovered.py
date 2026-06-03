#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class L5BaselineFilter:
    min_d_k: float = 0.0
    required_rev_k: int = 0
    min_m_k: float = 0.0
    min_close: float = 5.0
    min_gate_count: int = 10
    max_raw_x_m: float = 0.50
    max_f_n: float = 1.65

    REQUIRED_COLUMNS = (
        "D_k",
        "Rev_k",
        "B_k",
        "prev_B_k",
        "M_k",
        "Close",
        "Gate_Count",
        "raw_x_m",
        "F_n",
    )

    def apply_canonical_filter(self, df: pd.DataFrame) -> pd.DataFrame:
        missing = [column for column in self.REQUIRED_COLUMNS if column not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        mask = (
            (df["D_k"] >= self.min_d_k)
            & (df["Rev_k"] == self.required_rev_k)
            & (df["B_k"] > df["prev_B_k"])
            & (df["M_k"] >= self.min_m_k)
            & (df["Close"] >= self.min_close)
            & (df["Gate_Count"] >= self.min_gate_count)
            & (df["raw_x_m"] <= self.max_raw_x_m)
            & (df["F_n"] <= self.max_f_n)
        )
        return df.loc[mask].copy()


def apply_canonical_filter(df: pd.DataFrame) -> pd.DataFrame:
    return L5BaselineFilter().apply_canonical_filter(df)
