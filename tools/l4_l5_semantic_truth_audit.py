#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import bisect
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import l5_policy_learning_pipeline as l5


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _policy_decision(raw: Any) -> str:
    decision = str(raw)
    if decision not in l5.DECISIONS:
        return "Hold"
    return decision


def _find_policy_cell_and_decision(row: Dict[str, str], cells: Dict[str, Any]) -> Tuple[str | None, str]:
    selected_key: str | None = None
    selected_cell: Dict[str, Any] | None = None
    for candidate in l5._row_trace_cell_key_candidates(row):
        cell = cells.get(candidate)
        if isinstance(cell, dict):
            selected_key = candidate
            selected_cell = cell
            break

    if selected_key is None or selected_cell is None:
        return None, "Hold"

    return selected_key, _policy_decision(selected_cell.get("decision"))


def _parse_iso_ms(value: str) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def _spy_forward_return(spy_ts: List[int], spy_close: List[float], entry_ts: int, horizon: int) -> float | None:
    idx = bisect.bisect_right(spy_ts, entry_ts) - 1
    if idx < 0:
        return None
    j = idx + int(horizon)
    if j >= len(spy_close):
        return None
    c0 = float(spy_close[idx])
    c1 = float(spy_close[j])
    if c0 <= 0.0:
        return None
    return float(c1 / c0 - 1.0)


def _ast_function_identity(
    old_path: Path,
    new_path: Path,
    function_names: List[str],
) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "old_path": str(old_path),
        "new_path": str(new_path),
        "old_exists": old_path.exists(),
        "new_exists": new_path.exists(),
        "checked_functions": [],
    }

    if not old_path.exists() or not new_path.exists():
        return out

    old_module = ast.parse(old_path.read_text(encoding="utf-8"))
    new_module = ast.parse(new_path.read_text(encoding="utf-8"))

    old_funcs: Dict[str, str] = {}
    new_funcs: Dict[str, str] = {}

    for node in old_module.body:
        if isinstance(node, ast.FunctionDef) and node.name in function_names:
            old_funcs[node.name] = ast.unparse(node)

    for node in new_module.body:
        if isinstance(node, ast.FunctionDef) and node.name in function_names:
            new_funcs[node.name] = ast.unparse(node)

    for name in function_names:
        old_src = old_funcs.get(name)
        new_src = new_funcs.get(name)
        out["checked_functions"].append(
            {
                "function": name,
                "exists_old": old_src is not None,
                "exists_new": new_src is not None,
                "ast_unparse_identical": (old_src == new_src) if (old_src is not None and new_src is not None) else False,
                "old_length": len(old_src) if old_src is not None else None,
                "new_length": len(new_src) if new_src is not None else None,
            }
        )

    return out


def run_audit(
    *,
    row_trace_path: Path,
    spy_dataset_path: Path,
    policy_path: Path,
    old_l5_path: Path,
    new_l5_path: Path,
    old_uf_path: Path,
    new_uf_path: Path,
    train_frac: float,
    holdout_target_horizon: int,
) -> Dict[str, Any]:
    policy_payload = json.loads(policy_path.read_text(encoding="utf-8"))
    cells_obj = policy_payload.get("cells") if isinstance(policy_payload, dict) else None
    cells = cells_obj if isinstance(cells_obj, dict) else {}

    spy_payload = json.loads(spy_dataset_path.read_text(encoding="utf-8"))
    spy_obj = spy_payload.get("spy", {}) if isinstance(spy_payload, dict) else {}
    ts_raw = spy_obj.get("ts_ms", []) if isinstance(spy_obj, dict) else []
    close_raw = spy_obj.get("close", []) if isinstance(spy_obj, dict) else []

    spy_ts: List[int] = []
    spy_close: List[float] = []
    if isinstance(ts_raw, list) and isinstance(close_raw, list):
        for raw_ts, raw_close in zip(ts_raw, close_raw):
            try:
                ts = int(raw_ts)
                close = float(raw_close)
            except Exception:
                continue
            if close <= 0.0:
                continue
            spy_ts.append(ts)
            spy_close.append(close)

    if len(spy_ts) <= max(l5.HORIZONS):
        raise ValueError("spy_dataset_insufficient_points_for_horizons")

    totals = {int(h): 0 for h in l5.HORIZONS}
    benchmarkable = {int(h): 0 for h in l5.HORIZONS}
    mapped = {int(h): 0 for h in l5.HORIZONS}
    invalid_ts = {int(h): 0 for h in l5.HORIZONS}
    bench_missing = {int(h): 0 for h in l5.HORIZONS}
    unmapped = {int(h): 0 for h in l5.HORIZONS}

    wins_index = {int(h): 0 for h in l5.HORIZONS}
    wins_abs = {int(h): 0 for h in l5.HORIZONS}

    decision_stats: Dict[int, Dict[str, Dict[str, float]]] = {
        int(h): {
            d: {"n": 0.0, "wins_over_index": 0.0, "wins_abs": 0.0, "sum_excess": 0.0}
            for d in l5.DECISIONS
        }
        for h in l5.HORIZONS
    }

    decision_timestamps_by_h: Dict[int, Counter] = {int(h): Counter() for h in l5.HORIZONS}

    key_h_decision_wins: Dict[str, Dict[int, Dict[str, List[float]]]] = defaultdict(
        lambda: {
            int(h): {d: [0.0, 0.0] for d in l5.DECISIONS}
            for h in l5.HORIZONS
        }
    )
    rows_by_key: Dict[str, List[Tuple[int, float, float]]] = defaultdict(list)
    policy_decision_by_key: Dict[str, str] = {}

    split_rows: List[Dict[str, Any]] = []

    with row_trace_path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            try:
                horizon = int(float(row.get("horizon", 0)))
            except Exception:
                continue

            if horizon not in l5.HORIZONS:
                continue

            totals[horizon] += 1
            ts_ms = _parse_iso_ms(str(row.get("decision_timestamp", "")))
            if ts_ms is None:
                invalid_ts[horizon] += 1
                continue

            decision_timestamps_by_h[horizon][ts_ms] += 1

            bench = _spy_forward_return(spy_ts, spy_close, ts_ms, horizon)
            if bench is None:
                bench_missing[horizon] += 1
                continue

            benchmarkable[horizon] += 1

            selected_key, decision = _find_policy_cell_and_decision(row, cells)
            split_rows.append(
                {
                    "horizon": int(horizon),
                    "ts_ms": int(ts_ms),
                    "mapped": isinstance(selected_key, str),
                }
            )

            if not isinstance(selected_key, str):
                unmapped[horizon] += 1
                continue

            mapped[horizon] += 1
            policy_decision_by_key[selected_key] = decision

            fwd = float(l5._to_num(row.get("forward_return")))
            action = float(l5._decision_return(decision, fwd))
            wins_index[horizon] += int(action > bench)
            wins_abs[horizon] += int(action > 0.0)

            dstat = decision_stats[horizon][decision]
            dstat["n"] += 1.0
            dstat["wins_over_index"] += float(int(action > bench))
            dstat["wins_abs"] += float(int(action > 0.0))
            dstat["sum_excess"] += float(action - bench)

            rows_by_key[selected_key].append((horizon, fwd, bench))
            for candidate_decision in l5.DECISIONS:
                candidate_action = float(l5._decision_return(candidate_decision, fwd))
                bucket = key_h_decision_wins[selected_key][horizon][candidate_decision]
                bucket[0] += float(int(candidate_action > bench))
                bucket[1] += 1.0

    # Outcome metrics with current policy decisions.
    outcome_over_index_pct = {}
    action_positive_pct = {}
    coverage_by_h = {}
    for h in l5.HORIZONS:
        hh = int(h)
        coverage_by_h[str(hh)] = float(benchmarkable[hh] / totals[hh]) if totals[hh] > 0 else 0.0
        outcome_over_index_pct[str(hh)] = float(100.0 * wins_index[hh] / mapped[hh]) if mapped[hh] > 0 else 0.0
        action_positive_pct[str(hh)] = float(100.0 * wins_abs[hh] / mapped[hh]) if mapped[hh] > 0 else 0.0

    # Decision mix quality by horizon.
    decision_quality = {str(int(h)): {} for h in l5.HORIZONS}
    for h in l5.HORIZONS:
        hh = int(h)
        for d in l5.DECISIONS:
            rec = decision_stats[hh][d]
            n = int(rec["n"])
            if n <= 0:
                continue
            decision_quality[str(hh)][d] = {
                "n": n,
                "outcome_over_index_pct": float(100.0 * rec["wins_over_index"] / n),
                "action_positive_pct": float(100.0 * rec["wins_abs"] / n),
                "mean_excess_vs_spy": float(rec["sum_excess"] / n),
            }

    # Horizon conflict / ceiling diagnostics.
    keys_with_all_horizons = 0
    conflict_keys = 0
    tuple_counter: Counter = Counter()

    for key, per_h in key_h_decision_wins.items():
        if any(int(h) not in per_h for h in l5.HORIZONS):
            continue

        all_present = True
        best_by_h: Dict[int, str] = {}
        for h in l5.HORIZONS:
            hh = int(h)
            # Require rows for all decisions via n>0 check on one decision bucket.
            any_n = per_h[hh]["Accumulate"][1]
            if any_n <= 0:
                all_present = False
                break
            best_decision = max(
                l5.DECISIONS,
                key=lambda d: (per_h[hh][d][0], per_h[hh][d][1]),
            )
            best_by_h[hh] = best_decision

        if not all_present:
            continue

        keys_with_all_horizons += 1
        decision_tuple = (best_by_h[5], best_by_h[20], best_by_h[60])
        tuple_counter[decision_tuple] += 1
        if len(set(decision_tuple)) > 1:
            conflict_keys += 1

    n_rows_by_h = {int(h): 0 for h in l5.HORIZONS}
    wins_current = {int(h): 0 for h in l5.HORIZONS}
    wins_best_single = {int(h): 0 for h in l5.HORIZONS}
    wins_best_per_h = {int(h): 0 for h in l5.HORIZONS}

    for key, rows in rows_by_key.items():
        current_decision = policy_decision_by_key.get(key, "Hold")
        if current_decision not in l5.DECISIONS:
            current_decision = "Hold"

        best_single_decision = max(
            l5.DECISIONS,
            key=lambda d: sum(int(l5._decision_return(d, fwd) > bench) for _, fwd, bench in rows),
        )

        rows_by_h_local: Dict[int, List[Tuple[float, float]]] = defaultdict(list)
        for h, fwd, bench in rows:
            rows_by_h_local[int(h)].append((float(fwd), float(bench)))

        best_per_h: Dict[int, str] = {}
        for h in l5.HORIZONS:
            hh = int(h)
            local_rows = rows_by_h_local.get(hh, [])
            if len(local_rows) == 0:
                continue
            best_per_h[hh] = max(
                l5.DECISIONS,
                key=lambda d: sum(int(l5._decision_return(d, fwd) > bench) for fwd, bench in local_rows),
            )

        for h, fwd, bench in rows:
            hh = int(h)
            n_rows_by_h[hh] += 1
            wins_current[hh] += int(l5._decision_return(current_decision, fwd) > bench)
            wins_best_single[hh] += int(l5._decision_return(best_single_decision, fwd) > bench)
            best_h_decision = best_per_h.get(hh, current_decision)
            wins_best_per_h[hh] += int(l5._decision_return(best_h_decision, fwd) > bench)

    def _pct(wins: int, n: int) -> float:
        return float(100.0 * wins / n) if n > 0 else 0.0

    current_pct = {str(int(h)): _pct(wins_current[int(h)], n_rows_by_h[int(h)]) for h in l5.HORIZONS}
    best_single_pct = {str(int(h)): _pct(wins_best_single[int(h)], n_rows_by_h[int(h)]) for h in l5.HORIZONS}
    best_per_h_pct = {str(int(h)): _pct(wins_best_per_h[int(h)], n_rows_by_h[int(h)]) for h in l5.HORIZONS}

    avg_current = float(sum(current_pct.values()) / len(current_pct))
    avg_best_single = float(sum(best_single_pct.values()) / len(best_single_pct))
    avg_best_per_h = float(sum(best_per_h_pct.values()) / len(best_per_h_pct))

    # Timestamp profile + holdout split profile (same logic family as holdout validator).
    timestamp_profile = {}
    for h in l5.HORIZONS:
        hh = int(h)
        c = decision_timestamps_by_h[hh]
        total = sum(c.values())
        top = c.most_common(5)
        timestamp_profile[str(hh)] = {
            "unique_timestamps": int(len(c)),
            "total_rows_with_valid_timestamp": int(total),
            "top_5_timestamps": [
                {
                    "ts_ms": int(ts),
                    "count": int(cnt),
                    "share_pct": float(100.0 * cnt / total) if total > 0 else 0.0,
                }
                for ts, cnt in top
            ],
        }

    holdout_profile: Dict[str, Any] = {
        "target_horizon": int(holdout_target_horizon),
        "train_frac": float(train_frac),
        "rows_total": int(len(split_rows)),
    }
    target_ts = sorted(
        {
            int(r["ts_ms"])
            for r in split_rows
            if int(r["horizon"]) == int(holdout_target_horizon) and bool(r["mapped"]) is True
        }
    )
    holdout_profile["target_unique_timestamps"] = int(len(target_ts))

    if len(target_ts) >= 2 and 0.5 <= float(train_frac) < 1.0:
        split_idx = int(round((len(target_ts) - 1) * float(train_frac)))
        split_idx = max(0, min(len(target_ts) - 2, split_idx))
        cutoff = int(target_ts[split_idx])
        train_rows = [r for r in split_rows if int(r["ts_ms"]) <= cutoff]
        test_rows = [r for r in split_rows if int(r["ts_ms"]) > cutoff]
        holdout_profile["cutoff_ts_ms"] = cutoff
        holdout_profile["cutoff_ts_iso_utc"] = datetime.fromtimestamp(
            float(cutoff) / 1000.0, tz=timezone.utc
        ).isoformat()
        holdout_profile["train_rows"] = int(len(train_rows))
        holdout_profile["test_rows"] = int(len(test_rows))
        holdout_profile["train_rows_pct"] = float(100.0 * len(train_rows) / len(split_rows)) if len(split_rows) > 0 else 0.0
        holdout_profile["test_rows_pct"] = float(100.0 * len(test_rows) / len(split_rows)) if len(split_rows) > 0 else 0.0
    else:
        holdout_profile["cutoff_ts_ms"] = None
        holdout_profile["cutoff_ts_iso_utc"] = None
        holdout_profile["train_rows"] = 0
        holdout_profile["test_rows"] = 0
        holdout_profile["train_rows_pct"] = 0.0
        holdout_profile["test_rows_pct"] = 0.0

    l5_ast_identity = _ast_function_identity(
        old_path=old_l5_path,
        new_path=new_l5_path,
        function_names=[
            "_row_trace_cell_key",
            "_row_trace_cell_key_candidates",
            "_level5_l4_components",
            "_state_cell_key",
            "_state_cell_key_candidates",
        ],
    )

    uf_file_identity = {
        "old_path": str(old_uf_path),
        "new_path": str(new_uf_path),
        "old_exists": old_uf_path.exists(),
        "new_exists": new_uf_path.exists(),
        "sha256_identical": False,
    }
    if old_uf_path.exists() and new_uf_path.exists():
        old_hash = _sha256(old_uf_path)
        new_hash = _sha256(new_uf_path)
        uf_file_identity.update(
            {
                "old_sha256": old_hash,
                "new_sha256": new_hash,
                "sha256_identical": bool(old_hash == new_hash),
            }
        )

    return {
        "generated_at_utc": _utc_now_iso(),
        "analysis": "l4_l5_semantic_truth_audit",
        "inputs": {
            "row_trace_path": str(row_trace_path),
            "spy_dataset_path": str(spy_dataset_path),
            "policy_path": str(policy_path),
            "policy_cells": int(len(cells)),
            "horizons": [int(h) for h in l5.HORIZONS],
            "holdout_train_frac_reference": float(train_frac),
            "holdout_target_horizon_reference": int(holdout_target_horizon),
        },
        "coverage": {
            "totals_by_horizon": {str(h): int(totals[h]) for h in l5.HORIZONS},
            "benchmarkable_by_horizon": {str(h): int(benchmarkable[h]) for h in l5.HORIZONS},
            "mapped_by_horizon": {str(h): int(mapped[h]) for h in l5.HORIZONS},
            "unmapped_by_horizon": {str(h): int(unmapped[h]) for h in l5.HORIZONS},
            "invalid_timestamp_by_horizon": {str(h): int(invalid_ts[h]) for h in l5.HORIZONS},
            "benchmark_missing_by_horizon": {str(h): int(bench_missing[h]) for h in l5.HORIZONS},
            "benchmark_coverage_by_horizon": coverage_by_h,
        },
        "current_policy_metrics": {
            "outcome_over_index_pct_by_horizon": outcome_over_index_pct,
            "action_positive_pct_by_horizon": action_positive_pct,
            "avg_outcome_over_index_pct": float(sum(outcome_over_index_pct.values()) / len(outcome_over_index_pct)),
            "avg_action_positive_pct": float(sum(action_positive_pct.values()) / len(action_positive_pct)),
            "decision_quality_by_horizon": decision_quality,
        },
        "horizon_conflict": {
            "keys_with_all_3_horizons": int(keys_with_all_horizons),
            "conflict_keys": int(conflict_keys),
            "conflict_rate_pct": float(100.0 * conflict_keys / keys_with_all_horizons)
            if keys_with_all_horizons > 0
            else 0.0,
            "top_best_decision_tuples_5_20_60": [
                {"tuple_5_20_60": list(t), "count": int(c)}
                for t, c in tuple_counter.most_common(10)
            ],
            "current_outcome_over_index_pct": current_pct,
            "best_single_decision_per_key_outcome_over_index_pct_ceiling": best_single_pct,
            "best_per_horizon_decision_per_key_outcome_over_index_pct_ceiling": best_per_h_pct,
            "avg_current": avg_current,
            "avg_best_single_decision_per_key_ceiling": avg_best_single,
            "avg_best_per_horizon_decision_per_key_ceiling": avg_best_per_h,
        },
        "timestamp_profile": timestamp_profile,
        "holdout_split_reference_profile": holdout_profile,
        "implementation_identity": {
            "l5_keypath_ast_identity": l5_ast_identity,
            "uf_structural_engine_file_identity": uf_file_identity,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="L4->L5 semantic truth audit with implementation identity checks.")
    parser.add_argument("--row-trace", default="real_world_cleaned_universe_l5_row_trace_full.csv")
    parser.add_argument("--spy-dataset", default="backups/strict-ab-frozen-dataset-20260306T180841Z.json")
    parser.add_argument("--policy", default="pscf_policy_runtime.json")
    parser.add_argument("--old-l5", default="backups/predeploy-prod-restore-20260224T195512Z/l5_policy_learning_pipeline.py")
    parser.add_argument("--new-l5", default="l5_policy_learning_pipeline.py")
    parser.add_argument("--old-uf", default="backups/predeploy-prod-restore-20260224T195512Z/uf_core/uf_structural_engine.py")
    parser.add_argument("--new-uf", default="uf_core/uf_structural_engine.py")
    parser.add_argument("--train-frac", type=float, default=0.8)
    parser.add_argument("--target-horizon", type=int, default=60)
    parser.add_argument("--report-out", default="")
    parser.add_argument(
        "--report-latest",
        default="backups/lab/recommendation_lab/runs/lab-diagnosis-20260306T174519Z/l4_l5_semantic_truth_audit_latest.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run_audit(
        row_trace_path=Path(args.row_trace),
        spy_dataset_path=Path(args.spy_dataset),
        policy_path=Path(args.policy),
        old_l5_path=Path(args.old_l5),
        new_l5_path=Path(args.new_l5),
        old_uf_path=Path(args.old_uf),
        new_uf_path=Path(args.new_uf),
        train_frac=float(args.train_frac),
        holdout_target_horizon=int(args.target_horizon),
    )

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_out = (
        Path(args.report_out)
        if str(args.report_out).strip()
        else Path(f"backups/lab/recommendation_lab/runs/lab-diagnosis-20260306T174519Z/l4_l5_semantic_truth_audit_{stamp}.json")
    )
    report_latest = Path(args.report_latest)

    report_out.parent.mkdir(parents=True, exist_ok=True)
    report_latest.parent.mkdir(parents=True, exist_ok=True)

    report_out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report_latest.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(str(report_out))
    print(str(report_latest))
    print(
        json.dumps(
            {
                "avg_outcome_over_index_pct": report["current_policy_metrics"]["avg_outcome_over_index_pct"],
                "conflict_rate_pct": report["horizon_conflict"]["conflict_rate_pct"],
                "holdout_train_rows_pct": report["holdout_split_reference_profile"]["train_rows_pct"],
                "l5_keypath_ast_identical_all": all(
                    bool(item.get("ast_unparse_identical", False))
                    for item in report["implementation_identity"]["l5_keypath_ast_identity"].get("checked_functions", [])
                ),
                "uf_structural_engine_sha_identical": report["implementation_identity"]["uf_structural_engine_file_identity"].get(
                    "sha256_identical", False
                ),
            },
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
