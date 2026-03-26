#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path("/workspaces/Tao_Financial_Engine").resolve()
BACKUPS = REPO_ROOT / "backups" / "runtime"
SNAPSHOT_CSV = BACKUPS / "canonical_real_snapshot_production_fixed_snapshot_latest_20260321T013943Z.csv"
NOTE_PATH = REPO_ROOT / "DSF_PRIMITIVE_FULL_FIELD_SORTABLE_V3_RATIONALIZED.md"
SLACK_SCRIPT = REPO_ROOT / "tools" / "codex_notify_slack.sh"
TIE_EPS = 1e-12
BASELINE_COUNTS = {"Accumulate": 133, "Hold": 1132, "Avoid": 4148}
PREVIEW_SIMPLIFIED_PARAMS = {
    "beta": 0.5822062466501764,
    "motion_weight": 0.5854903101631882,
    "motion_power": 1.1841456593345179,
    "reversal_balance_power": 16.0,
    "carry_balance_power": 3.855189811929401,
    "burden_scale": 0.0078125,
}
RATIONALIZED_PARAMS = {
    "beta": 37.0 / 64.0,
    "motion_weight": 3.0 / 5.0,
    "motion_power": 5.0 / 4.0,
    "reversal_balance_power": 16.0,
    "carry_balance_power": 4.0,
    "burden_scale": 1.0 / 128.0,
}
ANCHORS = [
    ("AGO", "Accumulate"),
    ("TXRH", "Accumulate"),
    ("DHI", "Accumulate"),
    ("AAT", "Hold"),
    ("ACGL", "Hold"),
    ("ADC", "Hold"),
    ("AA", "Avoid"),
    ("AAPL", "Avoid"),
    ("ACLS", "Avoid"),
]
REQUIRED_FIELDS = [
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


def utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def load_rows() -> list[dict[str, Any]]:
    if not SNAPSHOT_CSV.exists():
        raise SystemExit(f"missing snapshot csv: {SNAPSHOT_CSV}")
    with SNAPSHOT_CSV.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = [field for field in REQUIRED_FIELDS if field not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit(f"missing required fields: {missing}")
        return list(reader)


def raw_ranges(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for field in ["D_k", "M_k", "R_rev_k", "B_k"]:
        values = [float(row[field]) for row in rows]
        out[field] = {"min": float(min(values)), "max": float(max(values))}
    return out


def decide(accumulate: float, hold: float, avoid: float) -> str:
    basins = [("Accumulate", accumulate), ("Hold", hold), ("Avoid", avoid)]
    best = max(value for _, value in basins)
    near_winners = [name for name, value in basins if best - value <= TIE_EPS]
    if len(near_winners) >= 2:
        return "Hold"
    return near_winners[0]


def evaluate_rows(rows: list[dict[str, Any]], params: dict[str, float]) -> dict[str, Any]:
    row_audit: list[dict[str, Any]] = []
    counts = {"Accumulate": 0, "Hold": 0, "Avoid": 0}
    anchor_rows: dict[str, dict[str, Any]] = {}
    decision_map: dict[tuple[str, str], str] = {}

    for raw in rows:
        symbol = str(raw["symbol"])
        decision_timestamp = str(raw["decision_timestamp"])
        bar_count = int(raw["bar_count"])
        s_uf = float(raw["S_UF"])
        r_uf = float(raw["R_UF"])
        d_k = float(raw["D_k"])
        m_k = float(raw["M_k"])
        r_rev_k = float(raw["R_rev_k"])
        u_star_k = float(raw["U_star_k"])
        c_k = float(raw["C_k"])
        p_k = float(raw["P_k"])
        b_k = float(raw["B_k"])

        m_hat = clip(m_k, -1.0, 1.0)
        s = s_uf - u_star_k
        r = r_uf - u_star_k
        core = min(max(s, 0.0), max(r, 0.0))
        edge = max(max(s, 0.0), max(r, 0.0)) - core
        live = core + params["beta"] * edge
        contested = (1.0 - params["beta"]) * edge
        balance = core / (core + edge + 1e-12)
        rupture = max(-max(s, r), 0.0)

        d_nonadverse = (1.0 + d_k) / 2.0
        d_adverse = max(-d_k, 0.0)
        m_continue = (1.0 + m_hat) / 2.0
        m_bend = (1.0 - m_hat) / 2.0

        motion = (
            params["motion_weight"] * (d_nonadverse ** params["motion_power"])
            + (1.0 - params["motion_weight"]) * (m_continue ** params["motion_power"])
        ) ** (1.0 / params["motion_power"])

        adverse_break = d_adverse * m_bend
        reversal_break = r_rev_k * ((1.0 - balance) ** params["reversal_balance_power"])
        carry_break = (-b_k) * r_rev_k * ((1.0 - balance) ** params["carry_balance_power"]) * (1.0 - adverse_break)
        burden = params["burden_scale"] * (c_k / (1.0 + c_k)) * (p_k / (1.0 + p_k))
        break_agreement = max(adverse_break, reversal_break, carry_break)

        accumulate_basin = live * motion * (1.0 - r_rev_k) * (1.0 - adverse_break) * (1.0 - burden)
        hold_basin = contested * (1.0 - break_agreement) + live * r_rev_k * balance + live * (1.0 - r_rev_k) * (
            (1.0 - motion) * (1.0 - adverse_break) + motion * burden
        )
        avoid_basin = rupture + (live + contested) * break_agreement

        final_decision = decide(accumulate_basin, hold_basin, avoid_basin)
        counts[final_decision] += 1
        decision_map[(symbol, decision_timestamp)] = final_decision

        record = {
            "symbol": symbol,
            "decision_timestamp": decision_timestamp,
            "bar_count": bar_count,
            "final_decision": final_decision,
            "S_UF": s_uf,
            "R_UF": r_uf,
            "D_k": d_k,
            "M_k": m_k,
            "M_hat": m_hat,
            "R_rev_k": r_rev_k,
            "U_star_k": u_star_k,
            "C_k": c_k,
            "P_k": p_k,
            "B_k": b_k,
            "s": s,
            "r": r,
            "core": core,
            "edge": edge,
            "live": live,
            "contested": contested,
            "balance": balance,
            "rupture": rupture,
            "D_nonadverse": d_nonadverse,
            "D_adverse": d_adverse,
            "M_continue": m_continue,
            "M_bend": m_bend,
            "motion": motion,
            "adverse_break": adverse_break,
            "reversal_break": reversal_break,
            "carry_break": carry_break,
            "burden": burden,
            "break_agreement": break_agreement,
            "Accumulate_basin": accumulate_basin,
            "Hold_basin": hold_basin,
            "Avoid_basin": avoid_basin,
        }
        row_audit.append(record)

        if symbol in {item[0] for item in ANCHORS}:
            anchor_rows[symbol] = record

    anchor_results = []
    anchor_matches = 0
    for symbol, expected in ANCHORS:
        row = anchor_rows.get(symbol)
        if row is None:
            anchor_results.append({"symbol": symbol, "expected": expected, "status": "missing"})
            continue
        actual = row["final_decision"]
        match = actual == expected
        if match:
            anchor_matches += 1
        anchor_results.append(
            {
                "symbol": symbol,
                "expected": expected,
                "actual": actual,
                "match": match,
            }
        )

    drift = {key: counts[key] - BASELINE_COUNTS[key] for key in BASELINE_COUNTS}
    exact = counts == BASELINE_COUNTS and anchor_matches == len(ANCHORS)

    return {
        "params": dict(params),
        "row_audit": row_audit,
        "decision_map": decision_map,
        "counts": counts,
        "anchor_results": anchor_results,
        "anchor_matches": anchor_matches,
        "count_delta_vs_baseline": drift,
        "exact_preserved": exact,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Any) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def markdown_summary(summary: dict[str, Any]) -> str:
    lines = [
        "# DSF Full-Field Sortable V3 Rationalized",
        "",
        f"- generated_at_utc: `{summary['generated_at_utc']}`",
        f"- snapshot_csv: `{summary['snapshot_csv']}`",
        f"- verdict: `{summary['verdict']}`",
        f"- counts: `{summary['counts']}`",
        f"- count_delta_vs_baseline: `{summary['count_delta_vs_baseline']}`",
        f"- anchors: `{summary['anchor_matches']}/9`",
        "",
        "## Anchor Table",
        "",
    ]
    for row in summary["anchor_results"]:
        lines.append(
            f"- `{row['symbol']}` expected `{row['expected']}` actual `{row.get('actual', 'missing')}` match `{row.get('match', False)}`"
        )
    lines.extend(
        [
            "",
            "## Delta vs Preview Simplified Candidate",
            "",
            f"- count_delta_vs_preview_simplified: `{summary['delta_vs_preview_simplified']['count_delta']}`",
            f"- changed_row_count: `{summary['delta_vs_preview_simplified']['changed_row_count']}`",
        ]
    )
    for row in summary["delta_vs_preview_simplified"]["changed_rows"]:
        lines.append(
            f"- `{row['symbol']}` at `{row['decision_timestamp']}` preview `{row['preview_simplified_decision']}` -> rationalized `{row['rationalized_decision']}`"
        )
    return "\n".join(lines)


def main() -> int:
    rows = load_rows()
    ranges = raw_ranges(rows)

    preview_simplified = evaluate_rows(rows, PREVIEW_SIMPLIFIED_PARAMS)
    rationalized = evaluate_rows(rows, RATIONALIZED_PARAMS)

    stamp = utc_stamp()
    row_csv = BACKUPS / f"dsf_full_field_sortable_v3_rationalized_rows_{stamp}.csv"
    row_json = BACKUPS / f"dsf_full_field_sortable_v3_rationalized_rows_{stamp}.json"
    anchor_csv = BACKUPS / f"dsf_full_field_sortable_v3_rationalized_anchor_table_{stamp}.csv"
    anchor_json = BACKUPS / f"dsf_full_field_sortable_v3_rationalized_anchor_table_{stamp}.json"
    summary_json = BACKUPS / f"dsf_full_field_sortable_v3_rationalized_summary_{stamp}.json"
    summary_md = BACKUPS / f"dsf_full_field_sortable_v3_rationalized_summary_{stamp}.md"

    write_csv(row_csv, rationalized["row_audit"])
    write_json(row_json, rationalized["row_audit"])
    write_csv(anchor_csv, rationalized["anchor_results"])
    write_json(anchor_json, rationalized["anchor_results"])

    changed_rows = []
    for key, preview_decision in preview_simplified["decision_map"].items():
        rationalized_decision = rationalized["decision_map"][key]
        if preview_decision != rationalized_decision:
            changed_rows.append(
                {
                    "symbol": key[0],
                    "decision_timestamp": key[1],
                    "preview_simplified_decision": preview_decision,
                    "rationalized_decision": rationalized_decision,
                }
            )

    summary = {
        "generated_at_utc": utc_iso(),
        "snapshot_csv": str(SNAPSHOT_CSV),
        "note_path": str(NOTE_PATH),
        "raw_ranges": ranges,
        "rationalized_params": RATIONALIZED_PARAMS,
        "counts": rationalized["counts"],
        "count_delta_vs_baseline": rationalized["count_delta_vs_baseline"],
        "anchor_results": rationalized["anchor_results"],
        "anchor_matches": rationalized["anchor_matches"],
        "row_audit_csv": str(row_csv),
        "row_audit_json": str(row_json),
        "anchor_table_csv": str(anchor_csv),
        "anchor_table_json": str(anchor_json),
        "delta_vs_preview_simplified": {
            "preview_simplified_params": PREVIEW_SIMPLIFIED_PARAMS,
            "preview_simplified_counts": preview_simplified["counts"],
            "count_delta": {
                key: rationalized["counts"][key] - preview_simplified["counts"][key]
                for key in BASELINE_COUNTS
            },
            "changed_row_count": len(changed_rows),
            "changed_rows": changed_rows,
        },
        "verdict": (
            "rationalized candidate preserved exact behavior"
            if rationalized["exact_preserved"]
            else "rationalized candidate failed exact preservation"
        ),
    }

    write_json(summary_json, summary)
    summary_markdown = markdown_summary(summary)
    with summary_md.open("w", encoding="utf-8") as handle:
        handle.write(summary_markdown)

    payload = {
        "text": (
            "Codex completed DSF full-field sortable v3 rationalized audit. "
            f"counts={rationalized['counts']} "
            f"verdict={summary['verdict']} "
            f"summary={summary_json.name}"
        )
    }
    if SLACK_SCRIPT.exists():
        subprocess.run(
            [str(SLACK_SCRIPT)],
            cwd=str(REPO_ROOT),
            input=json.dumps(payload) + "\n",
            text=True,
            check=True,
        )

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
