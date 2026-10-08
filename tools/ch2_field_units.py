"""Field units for the canon kernel (MINE, 2026-10-08) — the data-entry fix.
Raw O,H,L,C,V puts dollars and shares in one vector: volume is ~100% of the
displacement, so price never reaches the kernel (HRB: C_k=3 on 100% of days,
B_k at floor 93-99%, regime VOLATILE 98-99%). Each channel enters relative to
its OWN trailing normal (median of the prior 252 bars, expanding in year one,
shift 1 = causal): prices / normal close, volume / normal volume. Dimensionless,
same order of magnitude, knowable at the close. Kernel untouched."""
import numpy as np, pandas as pd

def unit_field(df: pd.DataFrame) -> np.ndarray:
    c = df.Close.astype(float); v = df.Volume.astype(float)
    nc = c.shift(1).rolling(252, min_periods=20).median()
    nv = v.shift(1).rolling(252, min_periods=20).median()
    F = np.column_stack([df.Open / nc, df.High / nc, df.Low / nc, c / nc, v / nv])
    return F


def move_unit_field(df: pd.DataFrame) -> np.ndarray:
    """Each channel in units of its OWN typical daily move (trailing 252-bar
    median of |daily change|, shift 1, causal): a normal day moves every
    channel ~1, so price and volume enter the kernel at the same size."""
    cols = [df.Open, df.High, df.Low, df.Close, df.Volume.astype(float)]
    out = []
    for x in cols:
        x = x.astype(float)
        s = x.diff().abs().shift(1).rolling(252, min_periods=20).median()
        out.append(x / s)
    return np.column_stack(out)
