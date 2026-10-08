#!/usr/bin/env python3
"""CH2 field governance — the nightly reading, inside production, off the
production database. Same computation as tools/ch2_field_nightly.py
(verified against the backtest), with production's own bars.

Joe, 2026-09-30: "as long as it's a positive move go for it." One system:
this is CH2's entry law from the deploy that carries it (FIELD-R1), not a
book beside it.

INPUT  daily_bars (ticker, bar_date, open, high, low, close, volume) — the
       refresh pipeline's bar cache, full OHLCV since 2021-04-12.
       The pool: names in runtime_decisions_latest for the latest run with
       asset_type stock and price x avg_volume >= $2M (the live ENTRY-R5 /
       ENTRY-R11 pool), plus SPY for the record.
       ch2_filings (ticker, filing_date) — see tools/ch2_filings_sync.py.
STATE  releasing share, storing share, phase, day polarity of releases,
       20-day polarity, slow polarity (120-day mean), temperature, epic
       window; bear regime with hysteresis (enter < 0.48, leave > 0.52).
LAW    field_long = epic window OR field-wide down-release OR charging &
       quiet, and NOT 20-day polarity UP; in the bear regime: epic only.
       priority: epic 0, down-release 1, charging & quiet 2.
       eligible name: tradeable (price >= 5, 20-day median $ volume >= $2M,
       no pump-and-dump window, not a zombie, >= 252 bars), 61–95 days
       since its last filing, not 96–130 (late), not 0–3 days after.
OUTPUT ch2_field_state (as_of DATE PRIMARY KEY, state JSONB, computed_at)
       ch2_field_eligible (as_of DATE, ticker TEXT, dsl INT, age INT,
       priority INT, PRIMARY KEY (as_of, ticker))
Usage: python3 tools/ch2_field_nightly_db.py [--asof YYYY-MM-DD] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(HERE))

W = 20
C = 3.77
LATTICES = ((1.0, 1.0, 1.0), (2.0, 2.0, 2.0), (4.0, 4.0, 4.0))


# ---------------------------------------------------------------- database
def connect():
    import psycopg2
    kw = {"host": os.environ["PGHOST"], "port": int(os.environ.get("PGPORT", "5432")), "dbname": os.environ["PGDATABASE"],
          "user": os.environ["PGUSER"], "password": os.environ["PGPASSWORD"], "connect_timeout": 10}
    sslmode = os.environ.get("PGSSLMODE", "require")
    if sslmode and sslmode != "disable":
        kw["sslmode"] = sslmode
        cert = os.environ.get("PGSSLROOTCERT", "/app/certs/rds-global-bundle.pem")
        if Path(cert).exists():
            kw["sslrootcert"] = cert
    return psycopg2.connect(**kw)


def ensure_tables(conn):
    with conn.cursor() as cur:
        cur.execute("""CREATE TABLE IF NOT EXISTS ch2_field_state (as_of DATE PRIMARY KEY, state JSONB NOT NULL, computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW())""")
        cur.execute("""CREATE TABLE IF NOT EXISTS ch2_field_eligible (as_of DATE NOT NULL, ticker TEXT NOT NULL, dsl INTEGER, age INTEGER, priority INTEGER NOT NULL,
                       PRIMARY KEY (as_of, ticker))""")
        cur.execute("ALTER TABLE ch2_field_eligible ADD COLUMN IF NOT EXISTS energy INTEGER")
        cur.execute("""CREATE TABLE IF NOT EXISTS ch2_filings (ticker TEXT NOT NULL, filing_date DATE NOT NULL, period_end DATE, timeframe TEXT, PRIMARY KEY (ticker, filing_date))""")
    conn.commit()


def load_pool(conn):
    q = """SELECT r.ticker FROM runtime_decisions_latest r
           LEFT JOIN runtime_metrics_latest m ON m.ticker = r.ticker
           WHERE r.run_id = (SELECT run_id FROM runtime_decisions_latest ORDER BY generated_at_utc DESC LIMIT 1)
             AND LOWER(TRIM(COALESCE(r.snapshot_row_json->>'asset_type',''))) = 'stock'
             AND CAST(NULLIF(r.snapshot_row_json->>'price','') AS DOUBLE PRECISION) * COALESCE(m.avg_volume, 0) >= 2000000"""
    with conn.cursor() as cur:
        cur.execute(q); rows = cur.fetchall()
    return sorted({r[0] for r in rows} | {"SPY"})


def load_bars(conn, tickers, asof, min_bars=300):
    """One (dates, O,H,L,C,V float32 arrays) per ticker, streamed with a server-side cursor — no wide frame."""
    q = """SELECT ticker, bar_date, open, high, low, close, volume FROM daily_bars
           WHERE ticker = ANY(%s) AND bar_date <= %s AND open IS NOT NULL AND high IS NOT NULL AND low IS NOT NULL AND close > 0
           ORDER BY ticker, bar_date"""
    out, cur_sym, buf = {}, None, []
    def flush():
        if cur_sym is not None and len(buf) >= min_bars:
            a = np.array([[float(x) for x in b[2:]] for b in buf], dtype=np.float64)          # open, high, low, close, volume
            out[cur_sym] = (np.array([b[1] for b in buf], dtype="datetime64[D]"), a)
    with conn.cursor(name="ch2_field_bars") as cur:
        cur.itersize = 50000
        cur.execute(q, (list(tickers), asof))
        for row in cur:
            if row[0] != cur_sym:
                flush(); cur_sym, buf = row[0], []
            buf.append(row)
        flush()
    return out


# ---------------------------------------------------------------- the kernel (canon, causal) — copied verbatim from tools/canon_kernel_causal.py
def readings(F, tau, r=None):
    from uf_core.config import KERNEL_THRESHOLDS as KT
    n = len(F)
    dF = np.zeros_like(F); dF[1:] = F[1:] - F[:-1]
    ndF = np.linalg.norm(dF, axis=1)
    sigma = np.zeros(n)
    for t in range(n):
        win = F[max(0, t - W + 1): t + 1]; sigma[t] = float(np.mean(np.sum((win - win.mean(axis=0)) ** 2, axis=1)))
    kappa = np.zeros(n); kappa[1:-1] = np.linalg.norm(F[2:] - 2 * F[1:-1] + F[:-2], axis=1)
    N = ((sigma < 1e-6) & (ndF < 1e-6) & (kappa < 1e-6)).astype(int)
    D = ndF + sigma + kappa
    tau = np.where(np.isfinite(tau), tau, np.inf)
    bounds = [t for t in range(1, n) if D[t] >= tau[t]]
    if not bounds or bounds[-1] != n - 1:
        bounds.append(n - 1)
    rows = []; t_a = 0
    chi_max = cv_max = d_max = 0.0; R_prev = 0.0; URF_prev = URF_prev2 = 0.0; D_prev = 0; B_prev = 0.0; mu_prev = np.zeros(3)
    Z = KT.lambda1 + KT.lambda2 + KT.lambda3 + KT.lambda4 + KT.lambda5
    for t_b in bounds:
        if t_b <= t_a: continue
        sl = slice(t_a, t_b); T = float(t_b - t_a)
        V = float(np.sum(ndF[sl] + sigma[sl] + kappa[sl])); Rr = float(np.sum(r[sl])) if r is not None else T
        P_list = [(int(T // h1), int(V // h2), int(Rr // h3)) for h1, h2, h3 in LATTICES]; Ck = len(set(P_list))
        mu = np.array([ndF[sl].mean(), sigma[sl].mean(), kappa[sl].mean()]); delta_g = float(np.linalg.norm(mu - mu_prev)); N_gate = int(N[sl].all())
        chi = V / max(T, 1e-12); chi_max = max(chi_max, chi); w = min(1.0, max(0.0, chi / chi_max)) if chi_max > 0 else 0.0
        cvn = float(np.linalg.norm(np.array([T, V, Rr]) - mu)); cv_max = max(cv_max, cvn); psi = min(1.0, max(0.0, cvn / cv_max)) if cv_max > 0 else 0.0
        d_max = max(d_max, delta_g)
        S = min(1.0, max(0.0, KT.gamma1 * w + KT.gamma2 * psi + KT.gamma3 / (1.0 + Ck)))
        U = min(1.0, max(0.0, KT.lambda_u1 * (Ck - 1) / 2 + KT.lambda_u2 * (delta_g / d_max if d_max > 0 else 0.0) + KT.lambda_u3 * N_gate))
        IAS = int(U > KT.U_max)
        Rk = min(1.0, max(0.0, (KT.lambda1 * w + KT.lambda2 * psi + KT.lambda3 * S + KT.lambda4 / (1.0 + Ck) + KT.lambda5 * (1.0 - U)) / Z))
        Hyst = int(abs(Rk - R_prev) > KT.h_max) if rows else 0
        g = int(U <= KT.U_max and IAS == 0 and Hyst == 0); URF = g * Rk
        dR = URF - URF_prev if rows else 0.0
        Dk = (1 if dR > KT.epsilon_D else -1 if dR < -KT.epsilon_D else 0) if rows else 0
        B = float(np.clip(B_prev + KT.breath_xi * (1.0 - min(1.0, U + KT.eta_H * Hyst + KT.eta_IAS * IAS)) * dR - KT.breath_chi * min(1.0, U + KT.eta_H * Hyst + KT.eta_IAS * IAS), KT.B_min, KT.B_max))
        rows.append((t_b, T, V, Rk, Dk))
        R_prev = Rk; URF_prev2 = URF_prev; URF_prev = URF; D_prev = Dk; B_prev = B; mu_prev = mu; t_a = t_b
    return pd.DataFrame(rows, columns=["t", "T_k", "V_k", "R_k", "D_k"])


def l0_D(g, cols):
    F = g[list(cols)].astype(float); dF = F.diff().fillna(0.0)
    ndF = np.sqrt((dF ** 2).sum(axis=1)).values; sigma = F.rolling(W, min_periods=1).var(ddof=0).sum(axis=1).values
    kap = np.zeros(len(F)); Fv = F.values; kap[1:-1] = np.linalg.norm(Fv[2:] - 2 * Fv[1:-1] + Fv[:-2], axis=1)
    return sigma, ndF + sigma + kap


def band3(x):
    q1 = x.quantile(0.25, axis=1); q3 = x.quantile(0.75, axis=1)
    return (x.gt(q1, axis=0).astype(int) + x.gt(q3, axis=0).astype(int)).where(x.notna())


def tradeable_flags(df):
    close, vol, high, low = df.Close.astype(float), df.Volume.astype(float), df.High.astype(float), df.Low.astype(float)
    ret = close.pct_change().abs(); dv20 = (close * vol).rolling(20, min_periods=20).median()
    zero60 = (vol <= 0).astype(int).rolling(60, min_periods=1).sum(); hist = pd.Series(np.arange(len(df)), index=df.index)
    doubled20 = close.rolling(20, min_periods=20).max() / close.rolling(20, min_periods=20).min() > 2.0
    big60 = (ret > 0.30).astype(int).rolling(60, min_periods=1).sum() > 0
    spike = (vol > 8 * vol.rolling(60, min_periods=20).median()) & (ret > 0.15); spike_block = spike.astype(int).rolling(60, min_periods=1).sum() > 0
    rng60 = (high.rolling(60, min_periods=60).max() - low.rolling(60, min_periods=60).min()) / close
    return (hist >= 252) & (close >= 5.0) & (dv20 >= 2_000_000) & (zero60 <= 3) & ~(doubled20.fillna(False) | big60 | spike_block) & (rng60 >= 0.05)


def band_trailing(x, lo=0.2, hi=0.8):
    prev = x.shift(1); q_hi = prev.rolling(252, min_periods=60).quantile(hi); q_lo = prev.rolling(252, min_periods=60).quantile(lo)
    return pd.Series(np.where(x >= q_hi, "HI", np.where(x <= q_lo, "LO", "MID")), index=x.index).where(q_hi.notna())


# ---------------------------------------------------------------- the stock's own energy (FIELD-R2, 2026-10-08)
# One kernel per ticker on the whole bar (Joe: "all inputs are per ticker through 1
# kernel"), each channel in units of its own 100-bar movement (Joe: "scale ... at least 50
# bar"; tools/ch2_field_units.path_unit_field), own resolution 3.77 x trailing median D
# (HIS), relevance psi_r on the close channel (standalone_truth_kernel.py). Returns D_k of
# the latest structure known at the last close (gate ending t_b known at close t_b+1), or
# None when the feed is unreadable (mixed units / clustering / pinned outputs).
# Book receipt: tools/ch2_book_sim_energy.py / _release.py / _blind.py (energy-first beat
# random-fill in every run, +4..+7 pts over 2022-26).
def energy_of(A):
    X = pd.DataFrame(A, columns=["O", "H", "L", "C", "V"])
    s = X.diff().abs().rolling(100).sum().shift(1).rolling(252, min_periods=60).median()
    F = (X / s).to_numpy(np.float64); ok = np.isfinite(F).all(axis=1)
    if ok.sum() < 300: return None
    F = F[np.argmax(ok):]
    if not np.isfinite(F).all(): return None
    n = len(F)
    dF = np.zeros_like(F); dF[1:] = F[1:] - F[:-1]
    Fd = pd.DataFrame(F); sig = sum(Fd[c].rolling(W, min_periods=1).var(ddof=0) for c in Fd.columns).values
    kap = np.zeros(n); kap[1:-1] = np.linalg.norm(F[2:] - 2 * F[1:-1] + F[:-2], axis=1)
    D = np.linalg.norm(dF, axis=1) + sig + kap
    tau = pd.Series(D).shift(1).rolling(252, min_periods=20).median().values * 3.77
    cc = pd.Series(F[:, 3]); rr = np.where(cc > cc.rolling(10, min_periods=1).mean(), 1.0, 0.5)
    r = readings(F, tau, r=rr)
    if len(r) < 3: return None
    g = np.diff(r.t.values); cover = g[g >= 5].sum() / max(g.sum(), 1)
    share = np.median(np.abs(dF[1:]) / np.maximum(np.abs(dF[1:]).sum(axis=1, keepdims=True), 1e-12), axis=0)
    if cover < 0.80 or share.max() > 0.60 or r.D_k.value_counts(normalize=True).iloc[0] > 0.95: return None
    known = r[r.t.values + 1 <= n - 1]
    return int(known.D_k.iloc[-1]) if len(known) else None


# ---------------------------------------------------------------- the field
def l0_arrays(A):
    """A: (n, 5) float64 O,H,L,C,V. Returns sigma, D on the price 4-vector, and rel (volume relevance)."""
    F = A[:, :4]; n = len(F)
    dF = np.zeros_like(F); dF[1:] = F[1:] - F[:-1]; ndF = np.linalg.norm(dF, axis=1)
    csum = np.cumsum(np.vstack([np.zeros((1, 4)), F]), axis=0); csq = np.cumsum(np.vstack([np.zeros((1, 4)), F ** 2]), axis=0)
    idx = np.arange(n); lo = np.maximum(0, idx - W + 1); cnt = (idx - lo + 1)[:, None]
    mean = (csum[idx + 1] - csum[lo]) / cnt; var = (csq[idx + 1] - csq[lo]) / cnt - mean ** 2
    sigma = np.maximum(var, 0.0).sum(axis=1)
    kap = np.zeros(n); kap[1:-1] = np.linalg.norm(F[2:] - 2 * F[1:-1] + F[:-2], axis=1)
    v = A[:, 4]; mv = pd.Series(v).rolling(W, min_periods=1).median().values
    rel = np.where(mv > 0, v / np.where(mv > 0, mv, 1.0), 1.0)
    return sigma, ndF + sigma + kap, rel


def tradeable_arrays(A):
    df = pd.DataFrame(A, columns=["Open", "High", "Low", "Close", "Volume"])
    return tradeable_flags(df).values


def compute(bars: dict, filings: pd.DataFrame, asof: pd.Timestamp):
    t0 = time.time()
    dates = np.array(sorted(set(np.concatenate([d for d, _ in bars.values()]))), dtype="datetime64[D]")
    di = {d: i for i, d in enumerate(dates)}; nd = len(dates); syms = sorted(bars)
    # ---- L0 per name and the cross-section matrices (dates x names, float32) ----
    S = np.full((nd, len(syms)), np.nan, np.float32); Dm = S.copy(); V20 = S.copy(); CL = S.copy()
    l0 = {}
    for j, sym in enumerate(syms):
        d, A = bars[sym]; sigma, D, rel = l0_arrays(A); l0[sym] = (D, rel)
        ii = np.array([di[x] for x in d])
        S[ii, j] = sigma; Dm[ii, j] = D; CL[ii, j] = A[:, 3]
        V20[ii, j] = pd.Series(A[:, 4]).rolling(W, min_periods=W).median().values
    elig = ~np.isnan(CL) & ~np.isnan(V20) & (CL >= 5.0)
    def band(M):
        Mm = np.where(elig, M, np.nan); q1 = np.nanpercentile(Mm, 25, axis=1); q3 = np.nanpercentile(Mm, 75, axis=1)
        return (Mm > q1[:, None]).astype(np.int8) + (Mm > q3[:, None]).astype(np.int8)
    cell = band(S) * 9 + band(V20) * 3 + band(CL); cell = np.where(elig, cell, -1)
    tau = np.full((nd, len(syms)), np.nan, np.float32)
    for i in range(nd):
        row = cell[i]; Di = Dm[i]
        for c in np.unique(row[row >= 0]):
            m = row == c; tau[i, m] = np.nanmedian(Di[m]) * C
    print(f"[field-db] herd cells and resolution: {len(syms)} names x {nd} days ({time.time() - t0:.0f}s)", flush=True)
    # ---- particle readings at the herd resolution; per-day accumulators for the field ----
    n_trad = np.zeros(nd); n_rel = np.zeros(nd); n_stor = np.zeros(nd); relup_num = np.zeros(nd); relup_den = np.zeros(nd)
    EN = np.full((nd, len(syms)), np.nan, np.float32)
    today = {}; today_bars = {}
    ia = di[np.datetime64(asof.date())]
    for j, sym in enumerate(syms):
        if sym == "SPY": continue
        d, A = bars[sym]; ii = np.array([di[x] for x in d]); n = len(d)
        D, rel = l0[sym]
        r = readings(A[:, :4], tau[ii, j].astype(np.float64), r=rel)
        bnd = np.zeros(n, dtype=bool); bnd[r.t.values] = True
        last = -1; age = np.zeros(n, dtype=int)
        for t in range(n):
            if t >= 1 and bnd[t - 1]: last = t - 1
            age[t] = t - last if last >= 0 else 0
        known = np.zeros(n, dtype=bool); known[1:] = bnd[:-1]
        up_prev = np.zeros(n, dtype=bool); up_prev[2:] = A[1:-1, 3] > A[:-2, 3]
        trad = tradeable_arrays(A)
        Dn = pd.Series(D); EN[ii, j] = np.where((A[:, 3] >= 5) & (A[:, 3] * A[:, 4] >= 2e6), (Dn / Dn.shift(1).rolling(252, min_periods=60).median()).values, np.nan)
        tt = ii[trad]; np.add.at(n_trad, tt, 1); np.add.at(n_rel, tt, known[trad]); np.add.at(n_stor, tt, age[trad] >= 21)
        rr = ii[trad & known]; np.add.at(relup_den, rr, 1); np.add.at(relup_num, rr, up_prev[trad & known])
        if ii[-1] == ia:
            today[sym] = (int(age[-1]), bool(trad[-1]))
            if trad[-1]: today_bars[sym] = A
    fs = pd.DataFrame(index=pd.to_datetime(dates))
    fs["n"] = n_trad; fs["releasing"] = np.where(n_trad > 0, n_rel / np.maximum(n_trad, 1), np.nan); fs["storing"] = np.where(n_trad > 0, n_stor / np.maximum(n_trad, 1), np.nan)
    fs["rel_up"] = np.where(relup_den > 0, relup_num / np.maximum(relup_den, 1), np.nan); fs["temperature"] = np.nanmedian(EN, axis=1)
    fs["releasing_band"] = band_trailing(fs.releasing); fs["rel_up_band"] = band_trailing(fs.rel_up)
    fs["phase"] = np.where(fs.storing > fs.storing.shift(20), "CHARGING", "DISCHARGING")
    fs["polarity20"] = np.where(fs.rel_up.rolling(20, min_periods=10).median() > 0.5, "UP", "DOWN")
    fs["slow120"] = fs.rel_up.rolling(120, min_periods=80).mean()
    p97 = fs.temperature.shift(1).rolling(252, min_periods=120).quantile(0.97)
    fs["epic_day"] = fs.temperature >= p97
    fs["epic_window"] = fs.epic_day.astype(int).rolling(8, min_periods=1).max().astype(bool)
    bear_arr = np.zeros(len(fs), dtype=bool); b = False
    for i, v in enumerate(fs.slow120.values):
        if not np.isnan(v):
            if not b and v < 0.48: b = True
            elif b and v > 0.52: b = False
        bear_arr[i] = b
    fs["bear"] = bear_arr
    c_epic = fs.epic_window & (fs.polarity20 != "UP"); c_d2 = (fs.releasing_band == "HI") & (fs.rel_up_band == "LO") & (fs.polarity20 != "UP")
    c_p8 = (fs.phase == "CHARGING") & (fs.releasing_band == "LO") & (fs.polarity20 != "UP")
    fs["c_epic"], fs["c_d2"], fs["c_p8"] = c_epic, c_d2, c_p8
    fs["field_long"] = np.where(fs.bear, c_epic, c_epic | c_d2 | c_p8)
    fs["priority"] = np.where(c_epic, 0, np.where(c_d2 & ~fs.bear, 1, np.where(c_p8 & ~fs.bear, 2, 9)))
    tdy = fs.loc[pd.Timestamp(asof)]
    # ---- eligible names today ----
    last_f = filings[filings.filing_date <= asof].groupby("ticker").filing_date.max() if len(filings) else pd.Series(dtype="datetime64[ns]")
    rows = []
    for sym, (age, trad) in today.items():
        if not trad: continue
        lf = last_f.get(sym); dsl = int((asof - lf).days) if lf is not None and not pd.isna(lf) else None
        # FIELD-R2 (Claude 2026-10-08, on Joe's "as long as it's a positive move go for it"):
        # the 61-95-day filing window is retired — on the decade book it added nothing over
        # any tradeable name (+59.8 vs +60.2 %, tools/ch2_book_sim_gated.py); the pick is
        # the stock's own energy instead. dsl stays on the row for the record.
        try:
            en = energy_of(today_bars[sym]) if sym in today_bars else None
        except Exception:
            en = None
        rows.append((sym, dsl, age, int(tdy.priority), en))
    elig = pd.DataFrame(rows, columns=["symbol", "dsl", "age", "priority", "energy"])
    state = {"asof": str(asof.date()), "field_long": bool(tdy.field_long), "priority": int(tdy.priority), "bear": bool(tdy.bear),
             "slow120": None if pd.isna(tdy.slow120) else round(float(tdy.slow120), 4), "phase": str(tdy.phase), "polarity20": str(tdy.polarity20),
             "releasing": round(float(tdy.releasing), 4), "releasing_band": str(tdy.releasing_band), "rel_up": None if pd.isna(tdy.rel_up) else round(float(tdy.rel_up), 3),
             "rel_up_band": str(tdy.rel_up_band), "storing": round(float(tdy.storing), 4), "temperature": None if pd.isna(tdy.temperature) else round(float(tdy.temperature), 3),
             "epic_day": bool(tdy.epic_day), "epic_window": bool(tdy.epic_window),
             "rules": {"epic": bool(tdy.c_epic), "down_release": bool(tdy.c_d2), "charging_quiet": bool(tdy.c_p8)},
             "eligible_names": int(len(elig)), "tradeable_names": int(sum(1 for _, (_, t) in today.items() if t)), "pool_names": len(syms) - 1,
             "bars_first": str(dates[0]), "filings_names": int(last_f.shape[0]), "law": "FIELD-R2",
             "energy_up_names": int((elig.energy == 1).sum()) if len(elig) else 0, "energy_read_names": int(elig.energy.notna().sum()) if len(elig) else 0, "seconds": round(time.time() - t0, 1)}
    return state, elig


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--asof", default=None); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    conn = connect(); ensure_tables(conn)
    pool = load_pool(conn)
    if a.asof:
        asof = pd.Timestamp(a.asof)
    else:
        with conn.cursor() as cur:
            cur.execute("SELECT max(bar_date) FROM daily_bars"); asof = pd.Timestamp(cur.fetchone()[0])
    bars = load_bars(conn, pool, asof.date())
    with conn.cursor() as cur:
        cur.execute("SELECT ticker, filing_date FROM ch2_filings"); frows = cur.fetchall()
    filings = pd.DataFrame(frows, columns=["ticker", "filing_date"]); filings["filing_date"] = pd.to_datetime(filings.filing_date)
    print(f"[field-db] as of {asof.date()}: pool {len(pool)} names, {len(bars)} with >= 300 bars, {sum(len(d) for d, _ in bars.values())} bars, {filings.ticker.nunique()} names with filings", flush=True)
    state, elig = compute(bars, filings, asof)
    print(json.dumps(state, indent=1), flush=True)
    if a.dry_run:
        print("[field-db] dry run — nothing written; eligible:", len(elig)); return
    with conn.cursor() as cur:
        cur.execute("INSERT INTO ch2_field_state (as_of, state) VALUES (%s, %s) ON CONFLICT (as_of) DO UPDATE SET state = EXCLUDED.state, computed_at = NOW()", (asof.date(), json.dumps(state)))
        cur.execute("DELETE FROM ch2_field_eligible WHERE as_of = %s", (asof.date(),))
        if len(elig):
            import psycopg2.extras
            psycopg2.extras.execute_values(cur, "INSERT INTO ch2_field_eligible (as_of, ticker, dsl, age, priority, energy) VALUES %s",
                                           [(asof.date(), r.symbol, None if pd.isna(r.dsl) else int(r.dsl), int(r.age), int(r.priority),
                                             None if pd.isna(r.energy) else int(r.energy)) for r in elig.itertuples()])
    conn.commit(); conn.close()
    print(f"[field-db] wrote ch2_field_state[{asof.date()}] and {len(elig)} eligible rows", flush=True)


if __name__ == "__main__":
    main()
