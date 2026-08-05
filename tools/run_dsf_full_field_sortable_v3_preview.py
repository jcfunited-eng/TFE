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
NOTE_PATH = REPO_ROOT / "DSF_PRIMITIVE_FULL_FIELD_SORTABLE_V3_PREVIEW.md"
SLACK_SCRIPT = REPO_ROOT / "tools" / "codex_notify_slack.sh"
TIE_EPS = 1e-12
BASELINE_COUNTS = {"Accumulate": 133, "Hold": 1132, "Avoid": 4148}
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
PREVIEW_PARAMS = {
    "beta": 0.5822062466501764,
    "motion_weight": 0.5854903101631882,
    "motion_power": 1.1841456593345179,
    "reversal_balance_power": 20.521505855173686,
    "carry_balance_power": 3.855189811929401,
    "burden_scale": 0.008137131392678132,
}
SIMPLIFICATION_AXES = [
    ("motion_power", [1.0, 1.25, 1.5]),
    ("motion_weight", [0.55, 0.5625, 0.575, 0.6]),
    ("beta", [0.55, 0.5625, 0.575, 0.6]),
    ("reversal_balance_power", [8, 10, 12, 16, 20]),
    ("carry_balance_power", [2, 3, 4]),
    ("burden_scale", [0.0, 0.00390625, 0.0078125, 0.015625]),
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

    drift = sum(abs(counts[key] - BASELINE_COUNTS[key]) for key in BASELINE_COUNTS)
    exact = counts == BASELINE_COUNTS and anchor_matches == len(ANCHORS)
    within5 = drift <= 5 and anchor_matches == len(ANCHORS)

    return {
        "params": dict(params),
        "row_audit": row_audit,
        "counts": counts,
        "anchor_results": anchor_results,
        "anchor_matches": anchor_matches,
        "drift_l1": drift,
        "exact_preserved": exact,
        "within5_preserved": within5,
    }


def write_row_artifacts(stem: str, rows: list[dict[str, Any]]) -> tuple[Path, Path]:
    csv_path = BACKUPS / f"{stem}.csv"
    json_path = BACKUPS / f"{stem}.json"

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(rows, handle, indent=2)

    return csv_path, json_path


def simplicity_key(value: float | int) -> tuple[int, float]:
    return (len(str(value)), abs(float(value)))


def choose_axis_candidate(
    rows: list[dict[str, Any]],
    current_params: dict[str, float],
    current_result: dict[str, Any],
    axis: str,
    values: list[float | int],
) -> dict[str, Any]:
    trials = []
    for value in values:
        params = dict(current_params)
        params[axis] = float(value)
        result = evaluate_rows(rows, params)
        result["axis"] = axis
        result["candidate_value"] = value
        trials.append(result)

    selected: dict[str, Any] | None = None

    if current_result["exact_preserved"]:
        exact = [trial for trial in trials if trial["exact_preserved"]]
        if exact:
            selected = sorted(exact, key=lambda trial: simplicity_key(trial["candidate_value"]))[0]
    else:
        exact = [trial for trial in trials if trial["exact_preserved"]]
        if exact:
            selected = sorted(exact, key=lambda trial: simplicity_key(trial["candidate_value"]))[0]
        else:
            admissible = [
                trial
                for trial in trials
                if trial["within5_preserved"] and trial["drift_l1"] <= current_result["drift_l1"]
            ]
            if admissible:
                selected = sorted(admissible, key=lambda trial: (trial["drift_l1"], simplicity_key(trial["candidate_value"])))[0]

    return {
        "axis": axis,
        "current_value": current_params[axis],
        "trials": [
            {
                "value": trial["candidate_value"],
                "counts": trial["counts"],
                "anchor_matches": trial["anchor_matches"],
                "drift_l1": trial["drift_l1"],
                "exact_preserved": trial["exact_preserved"],
                "within5_preserved": trial["within5_preserved"],
                "selected": selected is not None and trial["candidate_value"] == selected["candidate_value"],
            }
            for trial in trials
        ],
        "selected_value": None if selected is None else selected["candidate_value"],
        "selected_result": selected,
    }


def markdown_summary(summary: dict[str, Any]) -> str:
    preview = summary["preview"]
    simplified = summary["selected_simplified_candidate"]
    lines = [
        "# DSF Full-Field Sortable V3 Preview",
        "",
        f"- generated_at_utc: `{summary['generated_at_utc']}`",
        f"- snapshot_csv: `{summary['snapshot_csv']}`",
        f"- tie_eps: `{summary['tie_eps']}`",
        "",
        "## Reproduction",
        "",
        f"- verdict: `{summary['preview_reproduction_verdict']}`",
        f"- counts: `{preview['counts']}`",
        f"- anchor_matches: `{preview['anchor_matches']}/9`",
        "",
        "## Simplification",
        "",
        f"- verdict: `{summary['final_verdict']}`",
    ]
    if simplified is None:
        lines.append("- selected_simplified_candidate: `none`")
    else:
        lines.append(f"- selected_params: `{simplified['params']}`")
        lines.append(f"- selected_counts: `{simplified['counts']}`")
        lines.append(f"- selected_anchor_matches: `{simplified['anchor_matches']}/9`")
        lines.append(f"- selected_drift_l1: `{simplified['drift_l1']}`")
    lines.extend(["", "## Axis Table", ""])
    for axis_entry in summary["simplification_table"]:
        lines.append(f"### {axis_entry['axis']}")
        lines.append(f"- current_value: `{axis_entry['current_value']}`")
        for trial in axis_entry["trials"]:
            lines.append(
                f"- value `{trial['value']}` -> counts `{trial['counts']}`, anchors `{trial['anchor_matches']}/9`, "
                f"drift `{trial['drift_l1']}`, exact `{trial['exact_preserved']}`, within5 `{trial['within5_preserved']}`, "
                f"selected `{trial['selected']}`"
            )
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    rows = load_rows()
    ranges = raw_ranges(rows)

    preview = evaluate_rows(rows, PREVIEW_PARAMS)
    preview_reproduced = preview["exact_preserved"]

    current_params = dict(PREVIEW_PARAMS)
    current_result = preview
    simplification_table = []
    any_simplification_applied = False

    for axis, values in SIMPLIFICATION_AXES:
        axis_result = choose_axis_candidate(rows, current_params, current_result, axis, values)
        simplification_table.append(axis_result)
        selected = axis_result["selected_result"]
        if selected is not None and float(selected["candidate_value"]) != float(current_params[axis]):
            current_params[axis] = float(selected["candidate_value"])
            current_result = evaluate_rows(rows, current_params)
            any_simplification_applied = True

    selected_simplified_candidate = current_result if any_simplification_applied else None

    if not preview_reproduced:
        final_verdict = "preview did not reproduce"
    elif any_simplification_applied and current_result["within5_preserved"]:
        final_verdict = "preview reproduced; simplification succeeded"
    else:
        final_verdict = "preview reproduced; simplification failed, keep exact preview"

    stamp = utc_stamp()
    preview_csv, preview_json = write_row_artifacts(
        f"dsf_full_field_sortable_v3_preview_rows_{stamp}",
        preview["row_audit"],
    )

    simplified_csv = None
    simplified_json = None
    if selected_simplified_candidate is not None:
        simplified_csv, simplified_json = write_row_artifacts(
            f"dsf_full_field_sortable_v3_preview_simplified_rows_{stamp}",
            selected_simplified_candidate["row_audit"],
        )

    summary = {
        "generated_at_utc": utc_iso(),
        "snapshot_csv": str(SNAPSHOT_CSV),
        "note_path": str(NOTE_PATH),
        "tie_eps": TIE_EPS,
        "raw_ranges": ranges,
        "preview_params": PREVIEW_PARAMS,
        "preview": {
            "counts": preview["counts"],
            "anchor_results": preview["anchor_results"],
            "anchor_matches": preview["anchor_matches"],
            "drift_l1": preview["drift_l1"],
        },
        "preview_reproduction_verdict": "preview reproduced" if preview_reproduced else "preview did not reproduce",
        "preview_row_audit_csv": str(preview_csv),
        "preview_row_audit_json": str(preview_json),
        "simplification_table": simplification_table,
        "selected_simplified_candidate": None if selected_simplified_candidate is None else {
            "params": selected_simplified_candidate["params"],
            "counts": selected_simplified_candidate["counts"],
            "anchor_results": selected_simplified_candidate["anchor_results"],
            "anchor_matches": selected_simplified_candidate["anchor_matches"],
            "drift_l1": selected_simplified_candidate["drift_l1"],
            "row_audit_csv": None if simplified_csv is None else str(simplified_csv),
            "row_audit_json": None if simplified_json is None else str(simplified_json),
        },
        "final_verdict": final_verdict,
    }

    summary_json = BACKUPS / f"dsf_full_field_sortable_v3_preview_summary_{stamp}.json"
    summary_md = BACKUPS / f"dsf_full_field_sortable_v3_preview_summary_{stamp}.md"

    with summary_json.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    with summary_md.open("w", encoding="utf-8") as handle:
        handle.write(markdown_summary(summary))

    if SLACK_SCRIPT.exists():
        payload = {
            "text": (
                "Codex completed DSF full-field sortable v3 preview reproduction and simplification. "
                f"preview_counts={preview['counts']} "
                f"final_verdict={final_verdict} "
                f"summary={summary_json.name}"
            )
        }
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
