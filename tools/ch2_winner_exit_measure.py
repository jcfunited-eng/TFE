"""CH2 winner-side exit — the measurement declared in
docs/CH2_WINNER_EXIT_MEASUREMENT_DECLARATION_20260919.md.

Reconstructs CH2 entries from the production kernel lanes, runs the current
exit law (control) and each declared candidate against the SAME entries, adds
a duration-matched random null per candidate, splits the window in half, and
writes one JSON result. Nothing here chooses a rule: it reports what each
declared rule did, wins and failures alike.

Usage:
  PYTHONHASHSEED=0 python tools/ch2_winner_exit_measure.py \
      artifacts/ch4_uf/ch2_lanes_20260919.csv.gz ch4_live_store.parquet
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ch2_v3_basin_py import compute_v3_basin  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "ch4_uf" / "ch2_winner_exit_measurement_20260919.json"

# ── Declared constants (declaration §Candidates; no sweeps) ──────────────
GATE_ACC_MIN = 0.15
GATE_BREAK_MAX = 0.20
GATE_BARS_MIN = 20          # bar_count > 20
DEAD_DAMAGE_PCT = 0.05      # live dead clock
DEAD_SESSIONS = 16          # live dead clock
WALL_DAYS = 90              # live 90-day wall
BRAKE_PCT = 0.20            # live emergency brake
RATCHET_ENGAGE = 0.20       # live profit-protect engage
RATCHET_GIVEBACK = 1 / 3    # live profit-protect giveback
CAND_CONSEC = 5             # A, B, C: consecutive sessions
CAND_SUF_WINDOW = 20        # A: trailing median window
CAND_BK_LOOKBACK = 10       # B: comparison lag
SPLIT_DAY = date(2024, 3, 15)
NULL_SEEDS = 20
SLICE_DOLLARS = 2459.0      # the live per-position slice, for readable dollars


# ── Basin, vectorised, verified against the scalar port ──────────────────
def basin_frame(df: pd.DataFrame) -> pd.DataFrame:
    BETA, CW, MW, MP = 37 / 64, 27 / 64, 3 / 5, 5 / 4
    RBP, CBP, BS = 16, 4, 1 / 128
    s = df.s_uf - df.u_star_k
    r = df.r_uf - df.u_star_k
    s_pos = s.clip(lower=0); r_pos = r.clip(lower=0)
    core = np.minimum(s_pos, r_pos)
    edge = np.maximum(s_pos, r_pos) - core
    live = core + BETA * edge
    contested = CW * edge
    balance = core / (core + edge + 1e-12)
    rupture = (-np.maximum(s, r)).clip(lower=0)
    M_hat = df.m_k.clip(-1, 1)
    D_nonadv = (1 + df.d_k) / 2
    D_adv = (-df.d_k).clip(lower=0)
    M_cont = (1 + M_hat) / 2
    M_bend = (1 - M_hat) / 2
    motion = (MW * np.power(D_nonadv, MP) + (1 - MW) * np.power(M_cont, MP)) ** (1 / MP)
    adverse_break = D_adv * M_bend
    reversal_break = df.r_rev_k * np.power(1 - balance, RBP)
    carry_break = (-df.b_k) * df.r_rev_k * np.power(1 - balance, CBP) * (1 - adverse_break)
    burden = BS * (df.c_k / (1 + df.c_k)) * (df.p_k / (1 + df.p_k))
    break_agreement = np.maximum(np.maximum(adverse_break, reversal_break), carry_break)
    acc = live * motion * (1 - df.r_rev_k) * (1 - adverse_break) * (1 - burden)
    hold = (contested * (1 - break_agreement) + live * df.r_rev_k * balance
            + live * (1 - df.r_rev_k) * ((1 - motion) * (1 - adverse_break) + motion * burden))
    avoid = rupture + (live + contested) * break_agreement
    out = pd.DataFrame({"acc": acc, "hold": hold, "avoid": avoid, "brk": break_agreement})
    mx = out[["acc", "hold", "avoid"]].max(axis=1)
    near = pd.DataFrame({k: (mx - out[k]).abs() <= 1e-12 for k in ("acc", "hold", "avoid")})
    out["is_acc"] = near.acc & (near.sum(axis=1) == 1)
    return out


def verify_vectorised(df: pd.DataFrame, n: int = 2000) -> dict:
    rng = np.random.default_rng(7)
    idx = rng.choice(len(df), size=min(n, len(df)), replace=False)
    sample = df.iloc[idx]
    vec = basin_frame(sample)
    worst_acc = worst_brk = 0.0
    dec_mismatch = 0
    for (_, row), (_, v) in zip(sample.iterrows(), vec.iterrows()):
        p = compute_v3_basin({"S_UF": row.s_uf, "R_UF": row.r_uf, "D_k": row.d_k,
                              "M_k": row.m_k, "R_rev_k": row.r_rev_k, "U_star_k": row.u_star_k,
                              "C_k": row.c_k, "P_k": row.p_k, "B_k": row.b_k})
        if p is None:
            continue
        worst_acc = max(worst_acc, abs(p["accumulate_basin"] - v.acc))
        worst_brk = max(worst_brk, abs(p["break_agreement"] - v.brk))
        if (p["decision_argmax"] == "Accumulate") != bool(v.is_acc):
            dec_mismatch += 1
    return {"checked": int(len(sample)), "decision_mismatches": dec_mismatch,
            "worst_accumulate_diff": worst_acc, "worst_break_diff": worst_brk}


# ── One ticker's positions under a given rule set ────────────────────────
def walk(dates, closes, entry_ok, cand_fire, bar_dates, bar_closes, forced_len=None):
    """Return list of positions. Decisions on session i fill at the next bar close."""
    out = []
    n = len(dates)
    i = 0
    pos_no = 0
    while i < n:
        if not entry_ok[i]:
            i += 1
            continue
        # entry fills at the first bar strictly after this session's date
        j = np.searchsorted(bar_dates, dates[i], side="right")
        if j >= len(bar_dates):
            break
        entry_price = bar_closes[j]
        entry_date = bar_dates[j]
        if not np.isfinite(entry_price) or entry_price <= 0:
            i += 1
            continue
        damage_line = entry_price * (1 - DEAD_DAMAGE_PCT)
        brake_line = entry_price * (1 - BRAKE_PCT)
        peak = entry_price
        below_run = 0
        exit_price = exit_date = reason = None
        held = 0
        # lane index aligned to bar index for candidate evaluation
        k = j
        while k < len(bar_dates):
            px = bar_closes[k]
            held = k - j
            if forced_len is not None and held >= forced_len:
                exit_price, exit_date, reason = px, bar_dates[k], "null_forced"
                break
            if px <= brake_line:
                exit_price, exit_date, reason = px, bar_dates[k], "brake"
                break
            peak = max(peak, px)
            if peak >= entry_price * (1 + RATCHET_ENGAGE):
                floor = entry_price + (peak - entry_price) * (1 - RATCHET_GIVEBACK)
                if px <= floor:
                    exit_price, exit_date, reason = px, bar_dates[k], "ratchet"
                    break
            below_run = below_run + 1 if px <= damage_line else 0
            if below_run > DEAD_SESSIONS:
                nk = min(k + 1, len(bar_dates) - 1)
                exit_price, exit_date, reason = bar_closes[nk], bar_dates[nk], "dead_clock"
                break
            if (bar_dates[k] - entry_date).astype("timedelta64[D]").astype(int) >= WALL_DAYS:
                nk = min(k + 1, len(bar_dates) - 1)
                exit_price, exit_date, reason = bar_closes[nk], bar_dates[nk], "wall"
                break
            if cand_fire is not None and px > entry_price:
                li = np.searchsorted(dates, bar_dates[k], side="right") - 1
                if 0 <= li < n and cand_fire[li]:
                    nk = min(k + 1, len(bar_dates) - 1)
                    exit_price, exit_date, reason = bar_closes[nk], bar_dates[nk], "candidate"
                    break
            k += 1
        if exit_price is None:
            k = len(bar_dates) - 1
            exit_price, exit_date, reason, held = bar_closes[k], bar_dates[k], "window_end", k - j
        out.append({"entry_date": str(np.datetime_as_string(entry_date, unit="D")),
                    "exit_date": str(np.datetime_as_string(exit_date, unit="D")),
                    "ret": float(exit_price / entry_price - 1.0), "held": int(held),
                    "reason": reason})
        pos_no += 1
        # next entry only after this position closed
        i = int(np.searchsorted(dates, exit_date, side="right"))
    return out


def summarise(positions, label):
    if not positions:
        return {"label": label, "positions": 0}
    rets = np.array([p["ret"] for p in positions])
    held = np.array([p["held"] for p in positions])
    first = np.array([p["entry_date"] < str(SPLIT_DAY) for p in positions])
    def blk(mask):
        r = rets[mask]
        if not len(r):
            return {"positions": 0}
        return {"positions": int(len(r)), "total_return_pct": float(r.sum() * 100),
                "dollars": float(r.sum() * SLICE_DOLLARS), "mean_pct": float(r.mean() * 100),
                "median_pct": float(np.median(r) * 100), "win_rate_pct": float((r > 0).mean() * 100),
                "mean_hold_sessions": float(held[mask].mean())}
    reasons = {}
    for p in positions:
        reasons[p["reason"]] = reasons.get(p["reason"], 0) + 1
    return {"label": label, "all": blk(np.ones(len(rets), bool)),
            "first_half": blk(first), "second_half": blk(~first), "exit_reasons": reasons}


def main() -> int:
    lanes_path = Path(sys.argv[1]); bars_path = Path(sys.argv[2])
    print(f"[measure] lanes={lanes_path} bars={bars_path}", flush=True)
    lanes = pd.read_csv(lanes_path, parse_dates=["d"])
    lanes = lanes.dropna(subset=["s_uf", "r_uf", "d_k", "m_k", "r_rev_k", "u_star_k", "c_k", "p_k", "b_k"])
    lanes = lanes.sort_values(["ticker", "d"]).reset_index(drop=True)
    print(f"[measure] lanes rows={len(lanes)} tickers={lanes.ticker.nunique()} "
          f"{lanes.d.min().date()}..{lanes.d.max().date()}", flush=True)

    port = verify_vectorised(lanes)
    print(f"[measure] vectorised-vs-port check: {port}", flush=True)
    if port["decision_mismatches"]:
        print("[measure] ABORT: vectorised basin disagrees with the ported module")
        return 1

    b = basin_frame(lanes)
    lanes["entry_ok"] = (b.is_acc.values & (b.acc.values >= GATE_ACC_MIN)
                         & (b.brk.values < GATE_BREAK_MAX)
                         & (lanes.bar_count.fillna(0).values > GATE_BARS_MIN))
    lanes["brk"] = b.brk.values
    print(f"[measure] entry signals: {int(lanes.entry_ok.sum())}", flush=True)

    bars = pd.read_parquet(bars_path, columns=["Date", "Symbol", "Close"])
    bars = bars.dropna().sort_values(["Symbol", "Date"])
    bar_groups = {sym: (g.Date.values.astype("datetime64[D]"), g.Close.values.astype(float))
                  for sym, g in bars.groupby("Symbol", sort=False)}
    print(f"[measure] bar symbols={len(bar_groups)}", flush=True)

    # candidate firing masks, per ticker, from the lanes
    g = lanes.groupby("ticker", sort=False)
    suf_med = g.s_uf.transform(lambda s: s.rolling(CAND_SUF_WINDOW, min_periods=CAND_SUF_WINDOW).median())
    a_hit = (lanes.s_uf < suf_med).fillna(False)
    b_prev = g.b_k.shift(CAND_BK_LOOKBACK)
    b_hit = (lanes.b_k < b_prev).fillna(False)
    c_hit = (lanes.d_k != 1)
    def consec(mask):
        m = mask.astype(int)
        grp = (m == 0).groupby(lanes.ticker, sort=False).cumsum()
        run = m.groupby([lanes.ticker, grp], sort=False).cumsum()
        return (run >= CAND_CONSEC).values
    cands = {"A_support_sag": consec(a_hit), "B_fuel_drain": consec(b_hit),
             "C_direction_loss": consec(c_hit), "D_basin_break": (lanes.brk >= 0.20).values}

    # Per-ticker arrays built once; every run reuses them.
    print("[measure] building per-ticker arrays", flush=True)
    units = []
    for ticker, gl in lanes.groupby("ticker", sort=False):
        bg = bar_groups.get(ticker)
        if bg is None:
            continue
        idx = gl.index.values
        units.append((ticker, gl.d.values.astype("datetime64[D]"), gl.entry_ok.values,
                      {k: v[idx] for k, v in cands.items()}, bg[0], bg[1]))
    print(f"[measure] tickers with both lanes and bars: {len(units)}", flush=True)

    def run_all(cand_key=None, forced_pool=None, seed=0):
        rng = np.random.default_rng(seed)
        positions = []
        for ticker, d, ok, masks, bd, bc in units:
            forced = int(rng.choice(forced_pool)) if forced_pool is not None else None
            positions += walk(d, None, ok, None if cand_key is None else masks[cand_key],
                              bd, bc, forced_len=forced)
        return positions

    runs = {}
    all_positions = {}
    for label in ["control"] + list(cands):
        positions = run_all(None if label == "control" else label)
        all_positions[label] = positions
        runs[label] = summarise(positions, label)
        a = runs[label].get("all", {})
        print(f"[measure] {label}: n={a.get('positions')} total={a.get('total_return_pct'):.1f}% "
              f"${a.get('dollars'):.0f} win={a.get('win_rate_pct'):.1f}% "
              f"h1={runs[label]['first_half'].get('total_return_pct', 0):.1f}% "
              f"h2={runs[label]['second_half'].get('total_return_pct', 0):.1f}%", flush=True)

    # Null test — only for a candidate that actually beat the control, since a
    # candidate that loses to the control needs no null to be rejected.
    ctrl_total = runs["control"]["all"]["total_return_pct"]
    ctrl_n = len(all_positions["control"])
    nulls = {}
    for label in cands:
        cand_total = runs[label]["all"]["total_return_pct"]
        if cand_total <= ctrl_total:
            nulls[label] = {"skipped": "candidate did not beat the control; null not needed",
                            "candidate_total_pct": cand_total, "control_total_pct": ctrl_total}
            continue
        durations = np.array([p["held"] for p in all_positions[label] if p["reason"] == "candidate"])
        if len(durations) == 0:
            nulls[label] = {"note": "candidate never fired"}
            continue
        totals = []
        for seed in range(NULL_SEEDS):
            pos = run_all(None, forced_pool=durations, seed=1000 + seed)
            totals.append(float(np.array([p["ret"] for p in pos]).sum() * 100))
        nulls[label] = {"seeds": NULL_SEEDS, "mean_total_return_pct": float(np.mean(totals)),
                        "p05": float(np.percentile(totals, 5)), "p95": float(np.percentile(totals, 95)),
                        "duration_pool": int(len(durations)),
                        "candidate_total_pct": cand_total, "control_total_pct": ctrl_total,
                        "beats_null": bool(cand_total > np.percentile(totals, 95))}
        print(f"[measure] null {label}: mean={nulls[label]['mean_total_return_pct']:.1f}% "
              f"p95={nulls[label]['p95']:.1f}% candidate={cand_total:.1f}%", flush=True)

    result = {"declaration": "docs/CH2_WINNER_EXIT_MEASUREMENT_DECLARATION_20260919.md",
              "generated_at_utc": pd.Timestamp.utcnow().isoformat(),
              "lanes": {"rows": int(len(lanes)), "tickers": int(lanes.ticker.nunique()),
                        "first_day": str(lanes.d.min().date()), "last_day": str(lanes.d.max().date())},
              "port_check": port, "control_positions": ctrl_n, "runs": runs, "nulls": nulls,
              "costs_modeled": False, "prices": "closes only (no intraday range in the store)"}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, default=str))
    print(f"[measure] written {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
