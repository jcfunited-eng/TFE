#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path("/workspaces/Tao_Financial_Engine").resolve()
BACKUPS = REPO_ROOT / "backups" / "runtime"
DEFAULT_SNAPSHOT = BACKUPS / "canonical_real_snapshot_production_fixed_snapshot_latest_20260321T013943Z.csv"


def utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit only the mathematical meaning of B_k on the approved fixed-snapshot primitive surface."
    )
    parser.add_argument("--snapshot-csv", default=str(DEFAULT_SNAPSHOT))
    return parser.parse_args()


def clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def quantile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    idx = (len(ordered) - 1) * q
    lo = int(idx)
    hi = min(lo + 1, len(ordered) - 1)
    frac = idx - lo
    return float(ordered[lo] * (1.0 - frac) + ordered[hi] * frac)


def mean(values: list[float]) -> float | None:
    if not values:
        return None
    return float(sum(values) / len(values))


def std(values: list[float]) -> float | None:
    if not values:
        return None
    m = mean(values)
    if m is None:
        return None
    return float((sum((v - m) ** 2 for v in values) / len(values)) ** 0.5)


def correlation(xs: list[float], ys: list[float]) -> float | None:
    if not xs or not ys or len(xs) != len(ys):
        return None
    mx = mean(xs)
    my = mean(ys)
    if mx is None or my is None:
        return None
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx <= 0 or vy <= 0:
        return None
    return float(cov / (vx ** 0.5 * vy ** 0.5))


def bucket_summary(values: list[float]) -> dict[str, float | int | None]:
    return {
        "count": len(values),
        "mean": mean(values),
        "median": quantile(values, 0.5),
        "std": std(values),
        "p10": quantile(values, 0.10),
        "p25": quantile(values, 0.25),
        "p75": quantile(values, 0.75),
        "p90": quantile(values, 0.90),
    }


def histogram(values: list[float]) -> dict[str, int]:
    bins: Counter[str] = Counter()
    for value in values:
        if value < 0:
            label = "<0"
        elif value >= 1:
            label = "1.0"
        else:
            lo = math.floor(value * 10) / 10
            hi = lo + 0.1
            label = f"{lo:.1f}-{hi:.1f}"
        bins[label] += 1
    return dict(bins)


def classify_bucket(
    s: float,
    r: float,
    d_k: float,
    m_hat: float,
    r_rev_k: float,
) -> str:
    w = min(s, r)
    e = max(s, r)

    covered_two_sided = w > 0
    covered_one_sided = w <= 0 and e > 0
    rupture = e <= 0

    if covered_two_sided and d_k > 0 and m_hat > 0 and r_rev_k == 0:
        return "covered_forward"
    if covered_two_sided and d_k > 0 and m_hat < 0 and r_rev_k == 0:
        return "covered_bending"
    if covered_two_sided and d_k < 0:
        return "covered_adverse"
    if covered_two_sided and r_rev_k > 0:
        return "covered_reversal"
    if covered_one_sided and d_k > 0 and r_rev_k == 0:
        return "one_sided_forward"
    if covered_one_sided and (d_k < 0 or m_hat < 0 or r_rev_k > 0):
        return "one_sided_break"
    if rupture:
        return "rupture_rows"
    return "unclassified"


def interpretation_verdict(
    summaries: dict[str, dict[str, float | int | None]],
) -> tuple[str, str]:
    cf = summaries["covered_forward"]["median"]
    ca = summaries["covered_adverse"]["median"]
    cr = summaries["covered_reversal"]["median"]
    rr = summaries["rupture_rows"]["median"]
    osf = summaries["one_sided_forward"]["median"]
    osb = summaries["one_sided_break"]["median"]

    if not all(isinstance(v, (int, float)) for v in [cf, ca, cr, rr, osf, osb]):
        return (
            "ambiguous",
            "B_k semantics remain ambiguous on this snapshot; do not build formula v2 yet.",
        )

    cf = float(cf)
    ca = float(ca)
    cr = float(cr)
    rr = float(rr)
    osf = float(osf)
    osb = float(osb)

    t1 = cf > ca and cf > cr and cf > rr
    t2 = ca > cf and cr > cf and rr > cf
    t3 = cf > 0.20 and ca > 0.20 and cr > 0.20

    if t1:
        return (
            "live_carry_magnitude",
            "B_k is nonnegative live-carry magnitude and enters late as admissibility support.",
        )
    if t2:
        return (
            "exhaustion_magnitude",
            "B_k is nonnegative exhaustion magnitude and enters late as admissibility decay.",
        )
    if t3:
        return (
            "unsigned_persistence_magnitude",
            "B_k is unsigned persistence magnitude and must be aligned with D_k / M_hat / R_rev_k before affecting action.",
        )
    return (
        "ambiguous",
        "B_k semantics remain ambiguous on this snapshot; do not build formula v2 yet.",
    )


def main() -> int:
    args = parse_args()
    snapshot_csv = Path(args.snapshot_csv).resolve()
    if not snapshot_csv.exists():
        raise SystemExit(f"missing snapshot csv: {snapshot_csv}")

    required_fields = [
        "symbol",
        "decision_timestamp",
        "bar_count",
        "S_UF",
        "R_UF",
        "D_k",
        "M_k",
        "R_rev_k",
        "U_star_k",
        "C_k",
        "P_k",
        "B_k",
    ]

    rows: list[dict[str, Any]] = []
    with snapshot_csv.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = [field for field in required_fields if field not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit(f"missing required fields: {missing}")
        for row in reader:
            try:
                d_k = float(row["D_k"])
                m_k = float(row["M_k"])
                r_rev_k = float(row["R_rev_k"])
                u_star_k = float(row["U_star_k"])
                c_k = float(row["C_k"])
                p_k = float(row["P_k"])
                b_k = float(row["B_k"])
                s_uf = float(row["S_UF"])
                r_uf = float(row["R_UF"])
            except Exception as exc:
                raise SystemExit(
                    f"field parse failure on row {row.get('symbol')} {row.get('decision_timestamp')}: {exc}"
                )

            m_hat = clip(m_k, -1.0, 1.0)
            s = s_uf - u_star_k
            r = r_uf - u_star_k
            w = min(s, r)
            e = max(s, r)
            raw_carry = -b_k
            bucket = classify_bucket(s, r, d_k, m_hat, r_rev_k)

            rows.append(
                {
                    "bucket": bucket,
                    "raw_carry": raw_carry,
                    "D_k": d_k,
                    "M_hat": m_hat,
                    "R_rev_k": r_rev_k,
                    "C_k": c_k,
                    "P_k": p_k,
                    "s": s,
                    "r": r,
                    "w": w,
                    "e": e,
                }
            )

    raw_carry_values = [row["raw_carry"] for row in rows]
    range_summary = {
        "min": min(raw_carry_values),
        "max": max(raw_carry_values),
        "p01": quantile(raw_carry_values, 0.01),
        "p10": quantile(raw_carry_values, 0.10),
        "p25": quantile(raw_carry_values, 0.25),
        "p50": quantile(raw_carry_values, 0.50),
        "p75": quantile(raw_carry_values, 0.75),
        "p90": quantile(raw_carry_values, 0.90),
        "p99": quantile(raw_carry_values, 0.99),
        "histogram": histogram(raw_carry_values),
    }

    bucket_names = [
        "covered_forward",
        "covered_bending",
        "covered_adverse",
        "covered_reversal",
        "one_sided_forward",
        "one_sided_break",
        "rupture_rows",
    ]
    bucket_table = {
        bucket: bucket_summary([row["raw_carry"] for row in rows if row["bucket"] == bucket])
        for bucket in bucket_names
    }

    pair_defs = [
        ("covered_forward", "covered_bending"),
        ("covered_forward", "covered_adverse"),
        ("covered_forward", "covered_reversal"),
        ("one_sided_forward", "one_sided_break"),
        ("covered_forward", "rupture_rows"),
    ]
    pairwise = {}
    for left, right in pair_defs:
        lsum = bucket_table[left]
        rsum = bucket_table[right]
        pairwise[f"{left} vs {right}"] = {
            "median_delta": (
                None
                if lsum["median"] is None or rsum["median"] is None
                else float(lsum["median"] - rsum["median"])
            ),
            "mean_delta": (
                None
                if lsum["mean"] is None or rsum["mean"] is None
                else float(lsum["mean"] - rsum["mean"])
            ),
            "count_left": lsum["count"],
            "count_right": rsum["count"],
        }

    correlations = {
        "D_k": correlation(raw_carry_values, [row["D_k"] for row in rows]),
        "M_hat": correlation(raw_carry_values, [row["M_hat"] for row in rows]),
        "R_rev_k": correlation(raw_carry_values, [row["R_rev_k"] for row in rows]),
        "C_k": correlation(raw_carry_values, [row["C_k"] for row in rows]),
        "P_k": correlation(raw_carry_values, [row["P_k"] for row in rows]),
        "s": correlation(raw_carry_values, [row["s"] for row in rows]),
        "r": correlation(raw_carry_values, [row["r"] for row in rows]),
    }

    verdict, contract = interpretation_verdict(bucket_table)
    recommendation = (
        "stop because B_k is still not honestly resolved"
        if verdict == "ambiguous"
        else "proceed to C_k/P_k element"
    )

    report = {
        "generated_at_utc": utc_iso(),
        "snapshot_csv": str(snapshot_csv),
        "scope": "B_k semantics only on the approved primitive surface",
        "approved_fixed_definitions": {
            "M_hat": "max(-1.0, min(1.0, M_k))",
            "s": "S_UF - U_star_k",
            "r": "R_UF - U_star_k",
            "w": "min(s, r)",
            "e": "max(s, r)",
            "covered_two_sided": "w > 0",
            "covered_one_sided": "w <= 0 and e > 0",
            "rupture": "e <= 0",
            "raw_carry": "-B_k",
        },
        "range_summary": range_summary,
        "bucket_table": bucket_table,
        "pairwise_comparisons": pairwise,
        "correlations": correlations,
        "verdict": verdict,
        "formula_contract": None if verdict == "ambiguous" else contract,
        "stop_rule_message": (
            "B_k semantics remain ambiguous on this snapshot; do not build formula v2 yet."
            if verdict == "ambiguous"
            else None
        ),
        "recommendation": recommendation,
        "unclassified_count": sum(1 for row in rows if row["bucket"] == "unclassified"),
    }

    stamp = utc_stamp()
    json_path = BACKUPS / f"dsf_primitive_bk_recovery_audit_{stamp}.json"
    md_path = BACKUPS / f"dsf_primitive_bk_recovery_audit_{stamp}.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# DSF B_k Recovery Audit",
        "",
        f"Generated UTC: {report['generated_at_utc']}",
        f"Snapshot CSV: `{snapshot_csv}`",
        "",
        "## Verdict",
        "",
        f"- `{verdict}`",
        f"- recommendation: `{recommendation}`",
        "",
        "## Raw Carry Range",
        "",
    ]
    for key in ["min", "max", "p01", "p10", "p25", "p50", "p75", "p90", "p99"]:
        lines.append(f"- `{key} = {range_summary[key]}`")
    lines.extend(
        [
            "",
            "## Bucket Table",
            "",
            "| bucket | count | mean | median | std | p10 | p25 | p75 | p90 |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for bucket in bucket_names:
        stats = bucket_table[bucket]
        lines.append(
            f"| {bucket} | {stats['count']} | {stats['mean']} | {stats['median']} | {stats['std']} | {stats['p10']} | {stats['p25']} | {stats['p75']} | {stats['p90']} |"
        )
    lines.extend(
        [
            "",
            "## Pairwise Comparisons",
            "",
        ]
    )
    for label, stats in pairwise.items():
        lines.append(
            f"- `{label}`: median_delta=`{stats['median_delta']}`, mean_delta=`{stats['mean_delta']}`"
        )
    lines.extend(
        [
            "",
            "## Correlations",
            "",
        ]
    )
    for key, value in correlations.items():
        lines.append(f"- `{key}`: `{value}`")
    if verdict == "ambiguous":
        lines.extend(
            [
                "",
                "## Stop Rule",
                "",
                "- `B_k semantics remain ambiguous on this snapshot; do not build formula v2 yet.`",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "## Formula Contract",
                "",
                f"- {contract}",
            ]
        )

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "json_report_path": str(json_path),
                "md_report_path": str(md_path),
                "verdict": verdict,
                "recommendation": recommendation,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
