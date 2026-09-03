"""ninegauge_study.py — the rise study on the true nine-gauge field.

Joe's recipe, exactly: catalog the historical price rises (done,
rise_catalog.parquet); evaluate the tuple story that preceded them at
5, 25, and 90 sessions and what proceeded 25 after; read the individual
symbol, the herd, and the whole system; find the recurring structures;
then one sealed cold-half shot with win rate and dollars.

KERNEL-TRUE READING — declared before running, per the joint-field spec:
every discrete class below is an EXACT sign/ordering relation between
field coordinates the kernel itself defines. No medians, no quantiles,
no fitted thresholds. The nine gauges enter in their stated roles:

  motion  = sgn(D_k) x (M_k continuing / bending / flat RELATIVE to D_k)
  rev     = R_rev_k fired (first-class state change)
  trust   = U_star_k read AGAINST support and resonance:
            (sgn(S_UF - U*), sgn(R_UF - U*))
  conflict= sgn(C_k - C_k[t-1])  (conflict burden rising/steady/falling)
  stress  = P_k present (>0) or absent
  carry   = (sgn(B_k), sgn(B_k - B_k[t-5]))  (fueled/indebted x
            accumulating/draining)

Window story over w in {5,25,90} (sessions before the reading day):
  net carry sgn(B_t-B_{t-w}), net support sgn(S_t-S_{t-w}),
  net conflict sgn(C_t-C_{t-w}), reversal count class {0,1,2+},
  modal motion class of the window.

Herd scale (proven pedigree cell eband x gband as the grouping):
  majority sgn(D_k) and majority sgn(B_k) inside the cell that day.
System scale (all operating lives that day):
  majority sgn(D_k), majority sgn(B_k),
  sgn(reversal_rate_t - reversal_rate_{t-1}).

DECLARED CONSTANTS (before any counting):
  SPLIT   = 2024-03-01   derive strictly before; confirm at/after
  SUPPORT = 300          minimum derive occurrences of a structure
  RATIO   = 2.0          P(structure|rise-eve) / P(structure|ordinary)
  Family preference order (first family with >=1 qualifier wins; ALL
  its qualifiers are taken, never a cherry-picked best):
    1. eve x herd x system   2. eve x w25   3. eve alone
    4. w25 alone             5. herd x system alone
  CONFIRM TRADING LAW (frozen now): whenever a selected structure shows
  at a session close (clean frame: close>=$5, no 1000x shell, med20
  dollar >= $200k floor only, no 25%-day in prior 10), buy next session
  close, $2,500 slice; sell at first close with gain >= +15%, else at
  the 25th session close. Control: every 10th clean ordinary session,
  same exit law. Reported: win rate, $ per slice, vs control.

Aftermath (25 sessions after each derive-half rise peak): descriptive
frequencies of the same classes — filed for the exit-law discussion,
never mined for entry.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LANES = os.path.join(ROOT, "artifacts", "ninegauge", "lanes")
CATALOG = os.path.join(ROOT, "artifacts", "ninegauge", "rise_catalog.parquet")
HERD = os.path.join(ROOT, "artifacts", "ch4_uf", "herd_state_live.parquet")
OUTDIR = os.path.join(ROOT, "artifacts", "ninegauge")
SPLIT = "2024-03-01"
SUPPORT = 300
RATIO = 2.0
WINDOWS = (5, 25, 90)
HOLD = 25
HARVEST = 0.15
SLICE = 2_500.0

S = lambda x: 0 if x == 0 else (1 if x > 0 else -1)  # noqa: E731


def sgn_arr(a: np.ndarray) -> np.ndarray:
    return np.sign(a).astype(np.int8)


def motion_class(D: np.ndarray, M: np.ndarray) -> np.ndarray:
    """0..8: sgn(D) in {-,0,+} x M-relation {bending, flat, continuing}.
    M-relation: sgn(M)*sgn(D): +1 continuing, -1 bending, 0 flat."""
    sd = sgn_arr(D)
    rel = sgn_arr(M) * sd
    return ((sd + 1) * 3 + (rel + 1)).astype(np.int8)


def build_symbol(sym: str) -> dict | None:
    try:
        lf = pd.read_parquet(os.path.join(LANES, f"{sym}.parquet"))
    except Exception:  # noqa: BLE001
        return None
    if len(lf) < 30:
        return None
    d = lf["date"].to_numpy()
    c = lf["close"].to_numpy(float)
    v = lf["volume"].to_numpy(float)
    D = lf["D_k"].to_numpy(float)
    M = lf["M_k"].to_numpy(float)
    RV = lf["R_rev_k"].to_numpy(float)
    U = lf["U_star_k"].to_numpy(float)
    C = lf["C_k"].to_numpy(float)
    P = lf["P_k"].to_numpy(float)
    B = lf["B_k"].to_numpy(float)
    SU = lf["S_UF"].to_numpy(float)
    RU = lf["R_UF"].to_numpy(float)
    n = len(c)
    mot = motion_class(D, M)
    rev = (RV > 0).astype(np.int8)
    trust_s = sgn_arr(SU - U)          # support covers instability?
    trust_r = sgn_arr(RU - U)          # resonance covers instability?
    dC = np.zeros(n, np.int8)
    dC[1:] = sgn_arr(np.diff(C))
    stress = (P > 0).astype(np.int8)
    carry_b = sgn_arr(B)
    dB5 = np.zeros(n, np.int8)
    dB5[5:] = sgn_arr(B[5:] - B[:-5])
    # rolling modal motion per window via 9-class cumulative counts
    cum = np.zeros((n + 1, 9), np.int32)
    for k in range(9):
        cum[1:, k] = np.cumsum(mot == k)
    crev = np.concatenate([[0], np.cumsum(rev)])
    return {"sym": sym, "date": d, "close": c, "vol": v, "n": n,
            "mot": mot, "rev": rev, "trust_s": trust_s, "trust_r": trust_r,
            "dC": dC, "stress": stress, "carry_b": carry_b, "dB5": dB5,
            "B": B, "SU": SU, "C": C, "cum": cum, "crev": crev,
            "idx": {dd: i for i, dd in enumerate(d)}}


def eve_tuple(sd: dict, i: int) -> tuple:
    return (int(sd["mot"][i]), int(sd["rev"][i]),
            int(sd["trust_s"][i]), int(sd["trust_r"][i]),
            int(sd["dC"][i]), int(sd["stress"][i]),
            int(sd["carry_b"][i]), int(sd["dB5"][i]))


def window_tuple(sd: dict, i: int, w: int) -> tuple | None:
    if i - w < 0:
        return None
    nb = S(sd["B"][i] - sd["B"][i - w])
    ns = S(sd["SU"][i] - sd["SU"][i - w])
    nc = S(sd["C"][i] - sd["C"][i - w])
    rv = int(sd["crev"][i + 1] - sd["crev"][i + 1 - w])
    rvc = 0 if rv == 0 else (1 if rv == 1 else 2)
    counts = sd["cum"][i + 1] - sd["cum"][i + 1 - w]
    modal = int(np.argmax(counts))
    return (nb, ns, nc, rvc, modal)


def clean_ok(sd: dict, i: int) -> bool:
    c = sd["close"]
    if i < 20 or c[i] < 5:
        return False
    if float(np.max(c[:i + 1])) / c[i] >= 1000:
        return False
    dv = c[max(0, i - 19):i + 1] * sd["vol"][max(0, i - 19):i + 1]
    med = float(np.median(dv))
    if med < 200_000:  # floor only — no large-cap ceiling (see catalog)
        return False
    w = c[i - 10:i + 1]
    return not any(a > 0 and b / a >= 1.25 for a, b in zip(w, w[1:]))


def main() -> None:
    print("[study] loading lanes", flush=True)
    syms = sorted(f[:-8] for f in os.listdir(LANES) if f.endswith(".parquet"))
    data = {}
    for s_ in syms:
        sd = build_symbol(s_)
        if sd is not None:
            data[s_] = sd
    print(f"[study] {len(data)} lives loaded", flush=True)

    # ---- system scale: per-day majority signs over all lives
    day_d, day_b, day_rev, day_n = (defaultdict(int), defaultdict(int),
                                    defaultdict(int), defaultdict(int))
    for sd in data.values():
        for i in range(sd["n"]):
            dd = sd["date"][i]
            day_d[dd] += S(sd["mot"][i] // 3 - 1)  # sgn(D) from class
            day_b[dd] += int(sd["carry_b"][i])
            day_rev[dd] += int(sd["rev"][i])
            day_n[dd] += 1
    days_sorted = sorted(day_n)
    sysmap = {}
    prev_rate = None
    for dd in days_sorted:
        rate = day_rev[dd] / day_n[dd]
        drate = 0 if prev_rate is None else S(round(rate - prev_rate, 9))
        sysmap[dd] = (S(day_d[dd]), S(day_b[dd]), drate)
        prev_rate = rate
    print("[study] system scale ready", flush=True)

    # ---- herd scale: per (day, cell) majority signs
    herd = pd.read_parquet(HERD)
    herd["d"] = pd.to_datetime(herd["date"], format="%Y%m%d").dt.strftime("%Y-%m-%d")
    cell_of = {(r.sym, r.d): (int(r.eband), int(r.gband))
               for r in herd.itertuples()}
    del herd
    agg = defaultdict(lambda: [0, 0])
    for sd in data.values():
        s_ = sd["sym"]
        for i in range(sd["n"]):
            cell = cell_of.get((s_, sd["date"][i]))
            if cell is None:
                continue
            a = agg[(sd["date"][i], cell)]
            a[0] += S(sd["mot"][i] // 3 - 1)
            a[1] += int(sd["carry_b"][i])
    herdmap = {k: (S(a[0]), S(a[1])) for k, a in agg.items()}
    del agg
    print("[study] herd scale ready", flush=True)

    # ---- readings at rise eves and ordinary days
    cat = pd.read_parquet(CATALOG)
    eves = defaultdict(list)      # sym -> [lanes idx of t0]
    for r in cat.itertuples():
        sd = data.get(r.symbol)
        if sd is None:
            continue
        i = sd["idx"].get(r.t0_date)
        if i is not None and i >= 90:
            eves[r.symbol].append(i)
    eve_set = {(s_, i) for s_, lst in eves.items() for i in lst}

    def full_reading(sd: dict, i: int):
        ev = eve_tuple(sd, i)
        w5 = window_tuple(sd, i, 5)
        w25 = window_tuple(sd, i, 25)
        w90 = window_tuple(sd, i, 90)
        if w5 is None or w25 is None or w90 is None:
            return None
        dd = sd["date"][i]
        hd = herdmap.get((dd, cell_of.get((sd["sym"], dd), None)))
        sy = sysmap.get(dd)
        if hd is None or sy is None:
            return None
        return ev, w5, w25, w90, hd, sy

    FAMILIES = ["eve*herd*sys", "eve*w25", "eve", "w25", "herd*sys"]

    def fam_key(fam: str, rd) -> tuple:
        ev, w5, w25, w90, hd, sy = rd
        if fam == "eve*herd*sys":
            return ev + hd + sy
        if fam == "eve*w25":
            return ev + w25
        if fam == "eve":
            return ev
        if fam == "w25":
            return w25
        return hd + sy

    cnt_eve = {f: Counter() for f in FAMILIES}
    cnt_base = {f: Counter() for f in FAMILIES}
    n_eve = n_base = 0
    for s_, sd in data.items():
        for i in range(90, sd["n"]):
            if sd["date"][i] >= SPLIT:
                continue
            rd = full_reading(sd, i)
            if rd is None:
                continue
            is_eve = (s_, i) in eve_set
            tgt = cnt_eve if is_eve else cnt_base
            if is_eve:
                n_eve += 1
            else:
                n_base += 1
            for f in FAMILIES:
                tgt[f][fam_key(f, rd)] += 1
    print(f"[study] derive counted: eves={n_eve} base={n_base}", flush=True)

    # ---- selection under the declared rule
    chosen_family, chosen = None, {}
    report_fam = {}
    for f in FAMILIES:
        quals = {}
        for k, ne in cnt_eve[f].items():
            nb = cnt_base[f][k]
            tot = ne + nb
            if tot < SUPPORT:
                continue
            p_here = ne / tot
            p_base = n_eve / (n_eve + n_base)
            ratio = p_here / p_base if p_base > 0 else 0.0
            if ratio >= RATIO:
                quals[str(k)] = {"n_eve": ne, "n_total": tot,
                                 "ratio": round(ratio, 3)}
        report_fam[f] = {"qualifiers": len(quals),
                         "top": sorted(quals.items(),
                                       key=lambda x: -x[1]["ratio"])[:10]}
        if quals and chosen_family is None:
            chosen_family = f
            chosen = {eval(k) for k in quals}
    print(f"[study] family={chosen_family} structures={len(chosen)}",
          flush=True)

    # ---- aftermath descriptives (derive rises, 25 after peak)
    aft_mot = Counter()
    aft_rev_day = Counter()
    for r in cat.itertuples():
        if r.t0_date >= SPLIT:
            continue
        sd = data.get(r.symbol)
        if sd is None:
            continue
        ip = sd["idx"].get(r.peak_date)
        if ip is None:
            continue
        for j in range(ip + 1, min(sd["n"], ip + 1 + 25)):
            aft_mot[int(sd["mot"][j])] += 1
            if sd["rev"][j]:
                aft_rev_day[j - ip] += 1

    # ---- confirm: frozen trading law on the sealed half
    sim = {"trades": [], "control": []}
    if chosen_family:
        for s_, sd in data.items():
            n = sd["n"]
            for i in range(90, n - 1):
                dd = sd["date"][i]
                if dd < SPLIT:
                    continue
                rd = full_reading(sd, i)
                ordinary = True
                if rd is not None and fam_key(chosen_family, rd) in chosen \
                        and clean_ok(sd, i):
                    ordinary = False
                    e = i + 1
                    if e >= n:
                        continue
                    px = sd["close"][e]
                    exit_px, exit_j = None, None
                    for j in range(e + 1, min(n, e + 1 + HOLD)):
                        if sd["close"][j] / px - 1 >= HARVEST:
                            exit_px, exit_j = sd["close"][j], j
                            break
                    if exit_px is None:
                        j = min(n - 1, e + HOLD)
                        if j <= e:
                            continue
                        exit_px, exit_j = sd["close"][j], j
                    sim["trades"].append(
                        {"sym": s_, "entry": sd["date"][e],
                         "ret": round(100 * (exit_px / px - 1), 2),
                         "held": exit_j - e})
                if ordinary and i % 10 == 0 and clean_ok(sd, i):
                    e = i + 1
                    px = sd["close"][e] if e < n else None
                    if not px:
                        continue
                    exit_px = None
                    for j in range(e + 1, min(n, e + 1 + HOLD)):
                        if sd["close"][j] / px - 1 >= HARVEST:
                            exit_px = sd["close"][j]
                            break
                    if exit_px is None:
                        j = min(n - 1, e + HOLD)
                        if j <= e:
                            continue
                        exit_px = sd["close"][j]
                    sim["control"].append(round(100 * (exit_px / px - 1), 2))

    tr = [t["ret"] for t in sim["trades"]]
    ct = sim["control"]
    verdict = {
        "declared": {"SPLIT": SPLIT, "SUPPORT": SUPPORT, "RATIO": RATIO,
                     "HOLD": HOLD, "HARVEST": HARVEST,
                     "families": FAMILIES},
        "derive": {"eves": n_eve, "base": n_base,
                   "family_report": report_fam,
                   "chosen_family": chosen_family,
                   "n_structures": len(chosen)},
        "aftermath_derive": {
            "motion_freq": {str(k): v for k, v in aft_mot.most_common()},
            "reversal_by_day_after_peak":
                {str(k): aft_rev_day[k] for k in sorted(aft_rev_day)}},
        "confirm": {
            "n_trades": len(tr),
            "win_rate_pct": round(100 * np.mean([r > 0 for r in tr]), 1)
            if tr else None,
            "avg_ret_pct": round(float(np.mean(tr)), 2) if tr else None,
            "profit_per_slice": round(float(np.mean(tr)) / 100 * SLICE, 2)
            if tr else None,
            "control_n": len(ct),
            "control_avg_ret_pct": round(float(np.mean(ct)), 2)
            if ct else None,
            "control_profit_per_slice": round(float(np.mean(ct)) / 100 * SLICE,
                                              2) if ct else None,
        },
    }
    os.makedirs(OUTDIR, exist_ok=True)
    with open(os.path.join(OUTDIR, "study_results.json"), "w") as fh:
        json.dump(verdict, fh, indent=1)
    with open(os.path.join(OUTDIR, "confirm_trades.json"), "w") as fh:
        json.dump(sim["trades"][:5000], fh)
    print(json.dumps(verdict["confirm"], indent=1), flush=True)
    print("[study] filed artifacts/ninegauge/study_results.json", flush=True)


if __name__ == "__main__":
    main()
