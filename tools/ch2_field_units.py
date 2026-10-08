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


class FeedError(RuntimeError):
    """The kernel is being fed wrong — refuse to produce results."""


def check_feed(F: np.ndarray, r: pd.DataFrame | None = None, max_share: float = 0.60,
               max_pinned: float = 0.95, outputs=("D_k", "M_k", "URF_k"), min_gate_bars: int = 5) -> None:
    """Joe's rule (10-08, after a year of it): no variance is impossible; if it
    appears, the FEED is wrong. Refuse when one channel carries more than
    max_share of the typical daily displacement, or when a direction/motion
    output sits on one value on more than max_pinned of readings."""
    F = F[np.isfinite(F).all(axis=1)]
    dF = np.abs(np.diff(F, axis=0))
    share = np.median(dF / np.maximum(dF.sum(axis=1, keepdims=True), 1e-12), axis=0)
    if share.max() > max_share:
        raise FeedError(f"channel {int(share.argmax())} carries {share.max():.0%} of the daily move — mixed units in the field")
    if r is not None and len(r) > 2:
        # 2026-10-08: a q98 own-resolution run scored 174k "gates" whose median
        # length was ONE bar — boundaries cluster while the 20-bar variance stays
        # high. A structure must have length to be read as structure.
        g = np.diff(r["t"].values)
        if np.median(g) < min_gate_bars:
            raise FeedError(f"median gate is {np.median(g):.0f} bar(s) — boundaries are clustering, no structure to read")
        for c in outputs:
            top = r[c].round(6).value_counts(normalize=True).iloc[0]
            if top > max_pinned:
                raise FeedError(f"{c} sits on one value on {top:.0%} of readings — the kernel is not seeing the data")
