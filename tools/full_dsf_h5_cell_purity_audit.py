#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import full_dsf_horizon_lab as base
import l5_policy_learning_pipeline as l5


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _policy_decision(raw: Any) -> str:
    d = str(raw)
    if d not in base.DECISIONS:
        return "Hold"
    return d


def _symbol_split(symbols: List[str], train_frac: float) -> Tuple[set[str], set[str], Dict[str, Any]]:
    if not (0.5 <= float(train_frac) < 1.0):
        raise ValueError("train_frac must satisfy 0.5 <= train_frac < 1.0")
    ranked = sorted(
        sorted(set(symbols)),
        key=lambda s: (
            hashlib.sha1(s.encode("utf-8")).hexdigest(),
            s,
        ),
    )
    if len(ranked) < 2:
        raise ValueError("need_at_least_two_symbols_for_split")
    split_idx = int(math.floor(float(train_frac) * len(ranked)))
    split_idx = max(1, min(len(ranked) - 1, split_idx))
    train_symbols = set(ranked[:split_idx])
    test_symbols = set(ranked[split_idx:])
    return train_symbols, test_symbols, {
        "symbols_total": len(ranked),
        "symbols_train": len(train_symbols),
        "symbols_test": len(test_symbols),
        "train_frac_requested": float(train_frac),
        "train_frac_actual_symbols": float(len(train_symbols) / len(ranked)),
    }


def _wilson_lcb(wins: int, n: int, z: float) -> float:
    n_int = int(n)
    if n_int <= 0:
        return 0.0
    p = float(wins) / float(n_int)
    z2 = float(z) * float(z)
    denom = 1.0 + (z2 / n_int)
    center = p + (z2 / (2.0 * n_int))
    margin = float(z) * math.sqrt((p * (1.0 - p) / n_int) + (z2 / (4.0 * n_int * n_int)))
    return float((center - margin) / denom)


def _beta_shrunk_mean(wins: int, n: int, prior_strength: float) -> float:
    alpha = max(0.0, float(prior_strength)) / 2.0
    beta = max(0.0, float(prior_strength)) / 2.0
    return float((float(wins) + alpha) / (float(n) + alpha + beta)) if n > 0 else 0.5


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "5D exact-hit cell-purity audit with train/test symbol split, "
            "beta shrinkage, and Wilson lower-confidence bound scoring."
        )
    )
    p.add_argument("--row-trace", default="real_world_cleaned_universe_l5_row_trace_full.csv")
    p.add_argument("--spy-dataset", default="backups/strict-ab-frozen-dataset-20260306T180841Z.json")
    p.add_argument("--policy", default="pscf_policy_runtime.json")
    p.add_argument("--d-transform", choices=list(base.D_TRANSFORM_MODES), default="raw")
    p.add_argument("--train-frac", type=float, default=0.8)
    p.add_argument("--prior-strength", type=float, default=20.0)
    p.add_argument("--confidence-z", type=float, default=1.96)
    p.add_argument("--min-test-support", type=int, default=20)
    p.add_argument("--top-k", type=int, default=100)
    p.add_argument("--report-out", default="")
    p.add_argument(
        "--report-latest",
        default=(
            "backups/lab/recommendation_lab/runs/lab-diagnosis-20260306T174519Z/"
            "full_dsf_h5_cell_purity_audit_latest.json"
        ),
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()

    policy_payload = json.loads(Path(args.policy).read_text(encoding="utf-8"))
    cells_obj = policy_payload.get("cells") if isinstance(policy_payload, dict) else None
    cells = cells_obj if isinstance(cells_obj, dict) else {}

    loaded = base._load_rows(
        row_trace_path=Path(args.row_trace),
        spy_dataset_path=Path(args.spy_dataset),
        d_transform=str(args.d_transform),
    )
    rows_all = loaded["rows"]
    rows_h5 = [r for r in rows_all if int(r.horizon) == 5]

    exact_rows: List[Dict[str, Any]] = []
    for row in rows_h5:
        key = l5._row_trace_cell_key(row.raw_csv)
        cell = cells.get(key)
        if not isinstance(cell, dict):
            continue
        decision = _policy_decision(cell.get("decision"))
        action_ret = float(l5._decision_return(decision, float(row.fwd)))
        win = int(action_ret > float(row.bench))
        exact_rows.append(
            {
                "symbol": row.symbol,
                "cell_key": key,
                "decision": decision,
                "win": win,
            }
        )

    if len(exact_rows) < 2:
        raise RuntimeError("insufficient_exact_rows_for_h5_cell_purity_audit")

    train_symbols, test_symbols, split_meta = _symbol_split(
        symbols=[str(r["symbol"]) for r in exact_rows],
        train_frac=float(args.train_frac),
    )

    train_stats: Dict[str, Dict[str, int]] = {}
    test_stats: Dict[str, Dict[str, int]] = {}
    cell_decision: Dict[str, str] = {}

    def _upd(container: Dict[str, Dict[str, int]], key: str, win: int) -> None:
        rec = container.setdefault(key, {"n": 0, "wins": 0})
        rec["n"] += 1
        rec["wins"] += int(win)

    rows_train = 0
    rows_test = 0
    for row in exact_rows:
        key = str(row["cell_key"])
        decision = str(row["decision"])
        cell_decision[key] = decision
        if str(row["symbol"]) in train_symbols:
            rows_train += 1
            _upd(train_stats, key, int(row["win"]))
        else:
            rows_test += 1
            _upd(test_stats, key, int(row["win"]))

    all_cells = sorted(set(list(train_stats.keys()) + list(test_stats.keys())))
    rows_by_cell: List[Dict[str, Any]] = []

    min_support = int(max(1, args.min_test_support))
    stable_lcb_cells = 0
    stable_winrate_cells = 0
    stable_lcb_rows = 0
    stable_winrate_rows = 0

    for key in all_cells:
        tr = train_stats.get(key, {"n": 0, "wins": 0})
        te = test_stats.get(key, {"n": 0, "wins": 0})

        tr_n = int(tr["n"])
        tr_w = int(tr["wins"])
        te_n = int(te["n"])
        te_w = int(te["wins"])

        tr_wr = float(tr_w / tr_n) if tr_n > 0 else 0.0
        te_wr = float(te_w / te_n) if te_n > 0 else 0.0

        tr_shr = _beta_shrunk_mean(tr_w, tr_n, float(args.prior_strength))
        te_shr = _beta_shrunk_mean(te_w, te_n, float(args.prior_strength))

        tr_lcb = _wilson_lcb(tr_w, tr_n, float(args.confidence_z))
        te_lcb = _wilson_lcb(te_w, te_n, float(args.confidence_z))

        pass_support = te_n >= min_support
        pass_winrate = bool(pass_support and te_wr > 0.5)
        pass_lcb = bool(pass_support and te_lcb > 0.5)

        if pass_winrate:
            stable_winrate_cells += 1
            stable_winrate_rows += te_n
        if pass_lcb:
            stable_lcb_cells += 1
            stable_lcb_rows += te_n

        rows_by_cell.append(
            {
                "cell_key": key,
                "decision": cell_decision.get(key, "Hold"),
                "train_support_n": tr_n,
                "test_support_n": te_n,
                "train_winrate": tr_wr,
                "test_winrate": te_wr,
                "train_shrunk_winrate": tr_shr,
                "test_shrunk_winrate": te_shr,
                "train_wilson_lcb": tr_lcb,
                "test_wilson_lcb": te_lcb,
                "meets_min_test_support": pass_support,
                "test_winrate_gt_50": pass_winrate,
                "test_wilson_lcb_gt_50": pass_lcb,
            }
        )

    ranked_lcb = sorted(
        [r for r in rows_by_cell if bool(r["meets_min_test_support"])],
        key=lambda r: (float(r["test_wilson_lcb"]), float(r["test_winrate"]), int(r["test_support_n"])),
        reverse=True,
    )

    test_total = int(rows_test)
    train_total = int(rows_train)
    stable_winrate_rows_pct = float(100.0 * stable_winrate_rows / test_total) if test_total > 0 else 0.0
    stable_lcb_rows_pct = float(100.0 * stable_lcb_rows / test_total) if test_total > 0 else 0.0

    report = {
        "generated_at_utc": _utc_now_iso(),
        "analysis": "full_dsf_h5_cell_purity_audit_exact_hit_symbol_split",
        "inputs": {
            "row_trace_path": str(args.row_trace),
            "spy_dataset_path": str(args.spy_dataset),
            "runtime_policy_path": str(args.policy),
            "d_transform": str(args.d_transform),
            "train_frac": float(args.train_frac),
            "prior_strength": float(args.prior_strength),
            "confidence_z": float(args.confidence_z),
            "min_test_support": int(min_support),
            "top_k": int(args.top_k),
        },
        "data_health": {
            "rows_loaded_all_horizons": int(len(rows_all)),
            "rows_loaded_h5": int(len(rows_h5)),
            "rows_exact_hit_h5": int(len(exact_rows)),
            "rows_exact_hit_h5_pct_of_h5": float(100.0 * len(exact_rows) / len(rows_h5)) if len(rows_h5) > 0 else 0.0,
            "policy_cells": int(len(cells)),
            "skip_counts": loaded["skip_counts"],
            "spy_points": int(loaded["spy_points"]),
            "spy_first_ts_ms": int(loaded["spy_first_ts_ms"]),
            "spy_last_ts_ms": int(loaded["spy_last_ts_ms"]),
        },
        "split": {
            **split_meta,
            "rows_train": train_total,
            "rows_test": test_total,
        },
        "aggregate": {
            "cells_total": int(len(all_cells)),
            "cells_with_min_test_support": int(sum(1 for r in rows_by_cell if bool(r["meets_min_test_support"]))),
            "cells_test_winrate_gt_50_with_min_support": int(stable_winrate_cells),
            "cells_test_wilson_lcb_gt_50_with_min_support": int(stable_lcb_cells),
            "test_rows_in_cells_test_winrate_gt_50": int(stable_winrate_rows),
            "test_rows_in_cells_test_wilson_lcb_gt_50": int(stable_lcb_rows),
            "test_rows_in_cells_test_winrate_gt_50_pct": stable_winrate_rows_pct,
            "test_rows_in_cells_test_wilson_lcb_gt_50_pct": stable_lcb_rows_pct,
        },
        "top_cells_by_test_wilson_lcb": ranked_lcb[: int(max(1, args.top_k))],
        "all_cells": rows_by_cell,
    }

    stamp = _utc_stamp()
    report_out = (
        Path(args.report_out)
        if str(args.report_out).strip()
        else Path(
            "backups/lab/recommendation_lab/runs/lab-diagnosis-20260306T174519Z/"
            f"full_dsf_h5_cell_purity_audit_{stamp}.json"
        )
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
                "rows_exact_hit_h5": report["data_health"]["rows_exact_hit_h5"],
                "cells_total": report["aggregate"]["cells_total"],
                "cells_with_min_test_support": report["aggregate"]["cells_with_min_test_support"],
                "cells_test_winrate_gt_50_with_min_support": report["aggregate"][
                    "cells_test_winrate_gt_50_with_min_support"
                ],
                "cells_test_wilson_lcb_gt_50_with_min_support": report["aggregate"][
                    "cells_test_wilson_lcb_gt_50_with_min_support"
                ],
                "test_rows_in_cells_test_wilson_lcb_gt_50_pct": report["aggregate"][
                    "test_rows_in_cells_test_wilson_lcb_gt_50_pct"
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
