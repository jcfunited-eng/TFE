"""
uf_mdg_v01_backtest.py

Market Data Governance (MDG) v0.1 backtest helper.

Purpose:
    - Consume an existing UF-Core energy/entropy phase-map log
      (energy_entropy_output.txt) produced by uf_energy_entropy_phase_map.py.
    - Derive simple governance-relevant summaries:
        * overall long vs short behaviour by horizon
        * best energy bucket (E_low/E_mid/E_high) per horizon
        * best entropy bucket (H_low/H_mid/H_high) per horizon
    - No UF-Core execution, no market data download.

Usage:
    Place this file in the same folder as energy_entropy_output.txt
    and run:

        python uf_mdg_v01_backtest.py
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Tuple


LOG_FILE = "energy_entropy_output.txt"


def _parse_block(lines, header_prefix: str) -> list[str]:
    """
    Extract all non-empty lines following a header until the next
    dashed separator or blank line.
    """
    out: list[str] = []
    in_block = False
    for line in lines:
        s = line.strip()
        if not in_block:
            if s.startswith(header_prefix):
                in_block = True
            continue
        # inside block
        if not s or s.startswith("-" * 5):
            break
        out.append(line.rstrip("\n"))
    return out


def _parse_global(lines: list[str]) -> Dict[int, Dict[str, float]]:
    """
    Parse lines of the form:
        H= 5  trades=244766  hit=0.512  avg_tr=0.0008
    """
    out: Dict[int, Dict[str, float]] = {}
    pat = re.compile(
        r"H=\s*(?P<H>\d+)\s+"
        r"trades=\s*(?P<trades>\d+)\s+"
        r"hit=(?P<hit>[0-9.\-]+)\s+"
        r"avg_tr=(?P<avg>[0-9.\-]+)"
    )
    for line in lines:
        m = pat.match(line)
        if not m:
            continue
        h = int(m.group("H"))
        out[h] = {
            "trades": float(m.group("trades")),
            "hit": float(m.group("hit")),
            "avg_tr": float(m.group("avg")),
        }
    return out


def _parse_long_short(lines: list[str]) -> Dict[int, Dict[str, Dict[str, float]]]:
    """
    Parse lines of the form:
        H= 5  LONG   trades=162047  hit=0.532  avg_tr=0.0026
        H= 5  SHORT  trades= 82719  hit=0.473  avg_tr=-0.0025
    """
    out: Dict[int, Dict[str, Dict[str, float]]] = {}
    pat = re.compile(
        r"H=\s*(?P<H>\d+)\s+"
        r"(?P<side>LONG|SHORT)\s+"
        r"trades=\s*(?P<trades>\d+)\s+"
        r"hit=(?P<hit>[0-9.\-]+)\s+"
        r"avg_tr=(?P<avg>[0-9.\-]+)"
    )
    for line in lines:
        m = pat.match(line)
        if not m:
            continue
        h = int(m.group("H"))
        side = m.group("side")
        out.setdefault(h, {})[side] = {
            "trades": float(m.group("trades")),
            "hit": float(m.group("hit")),
            "avg_tr": float(m.group("avg")),
        }
    return out


def _parse_bucket(lines: list[str], prefix: str) -> Dict[int, Dict[str, Dict[str, float]]]:
    """
    Parse bucket lines, e.g. for magnitude / energy / entropy:

        H= 5  M_low   trades=147669  avg_tr=0.0012
        H= 5  E_mid   trades= 80773  avg_tr=0.0017
        H= 5  H_mid   trades= 80617  avg_tr=0.0016
    """
    out: Dict[int, Dict[str, Dict[str, float]]] = {}
    for line in lines:
        s = line.strip()
        if not s or s.startswith("E quantiles") or s.startswith("H_D quantiles"):
            continue
        m = re.match(
            r"H=\s*(?P<H>\d+)\s+"
            r"(?P<b>" + re.escape(prefix) + r"\w+)\s+"
            r"trades=\s*(?P<trades>\d+)\s+avg_tr=(?P<avg>[0-9.\-]+)",
            line,
        )
        if not m:
            continue
        h = int(m.group("H"))
        bucket = m.group("b")
        out.setdefault(h, {})[bucket] = {
            "trades": float(m.group("trades")),
            "avg_tr": float(m.group("avg")),
        }
    return out


def _best_bucket(
    buckets: Dict[int, Dict[str, Dict[str, float]]]
) -> Dict[int, Tuple[str, Dict[str, float]]]:
    """
    For each horizon H, pick the bucket with the highest avg_tr.
    """
    best: Dict[int, Tuple[str, Dict[str, float]]] = {}
    for h, bdict in buckets.items():
        if not bdict:
            continue
        bucket, stats = max(bdict.items(), key=lambda kv: kv[1]["avg_tr"])
        best[h] = (bucket, stats)
    return best


def main() -> None:
    p = Path(LOG_FILE)
    if not p.exists():
        raise SystemExit(f"Log file not found: {p} (expected energy_entropy_output.txt)")

    text = p.read_text()
    lines = text.splitlines()

    # Extract relevant blocks from the log.
    global_block = _parse_block(lines, "GLOBAL STATS BY HORIZON")
    ls_block = _parse_block(lines, "LONG / SHORT STATS BY HORIZON")
    mag_block = _parse_block(lines, "MAGNITUDE |M_k| BUCKETS BY HORIZON")
    eng_block = _parse_block(lines, "ENERGY BUCKETS BY HORIZON")
    ent_block = _parse_block(lines, "ENTROPY BUCKETS BY HORIZON")

    global_stats = _parse_global(global_block)
    long_short = _parse_long_short(ls_block)
    mag_buckets = _parse_bucket(mag_block, "M_")
    energy_buckets = _parse_bucket(eng_block, "E_")
    entropy_buckets = _parse_bucket(ent_block, "H_")

    best_energy = _best_bucket(energy_buckets)
    best_entropy = _best_bucket(entropy_buckets)

    print("UF-Core MDG v0.1 summary from existing energy/entropy phase map")
    print(f"Source log: {p}")
    print("-" * 120)

    horizons = sorted(global_stats.keys())
    header = (
        "H  "
        "trades  hit   avg_tr   "
        "LONG_hit  LONG_avg   SHORT_hit  SHORT_avg   "
        "best_E(avg)   best_H(avg)"
    )
    print(header)
    print("-" * len(header))

    for h in horizons:
        gs = global_stats.get(h, {})
        ls = long_short.get(h, {})
        long = ls.get("LONG", {"hit": float("nan"), "avg_tr": float("nan")})
        short = ls.get("SHORT", {"hit": float("nan"), "avg_tr": float("nan")})

        be_name, be_stats = best_energy.get(h, ("-", {"avg_tr": float("nan")}))
        bh_name, bh_stats = best_entropy.get(h, ("-", {"avg_tr": float("nan")}))

        line = (
            f"{h:<2d} "
            f"{int(gs.get('trades', 0)):>7d} "
            f"{gs.get('hit', float('nan')):>5.3f} "
            f"{gs.get('avg_tr', float('nan')):>7.4f}   "
            f"{long.get('hit', float('nan')):>8.3f} "
            f"{long.get('avg_tr', float('nan')):>8.4f}   "
            f"{short.get('hit', float('nan')):>9.3f} "
            f"{short.get('avg_tr', float('nan')):>9.4f}   "
            f"{be_name:>7s}({be_stats['avg_tr']:>+7.4f})   "
            f"{bh_name:>7s}({bh_stats['avg_tr']:>+7.4f})"
        )
        print(line)

    print("-" * 120)
    print("Interpretation hints (MDG v0.1, structural only):")
    print("  - LONG is favoured when LONG_avg > 0 and SHORT_avg < 0 at a given horizon.")
    print("  - best_E / best_H show which energy / entropy buckets have the highest avg per-trade return.")
    print("  - Governance rules can restrict trading to those (H, bucket) combinations instead of using all trades.")


if __name__ == "__main__":
    main()
