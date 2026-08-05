#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import evaluate_recommendation_policy_snapshot as ev
from tfe_market_data_factory import get_market_data_service
from uf_mdg_snapshot import evaluate_symbol_snapshot


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _env_int(name: str, default_value: int, low: int, high: int) -> int:
    raw = str(os.environ.get(name, str(default_value))).strip()
    try:
        value = int(raw)
    except Exception:
        value = int(default_value)
    if value < low:
        return low
    if value > high:
        return high
    return value


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return int(default)


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_symbol(value: Any) -> str:
    return _safe_text(value).upper()


def _normalize_asset_type(value: Any) -> str:
    text = _safe_text(value).lower()
    if text in {"stock", "etf", "index", "crypto"}:
        return text
    return "stock"


def _load_env_file_fallback(env_path: Path) -> None:
    if not env_path.exists() or not env_path.is_file():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"").strip("'")
        if not key:
            continue
        if key in os.environ and _safe_text(os.environ.get(key)):
            continue
        os.environ[key] = value


def _read_csv_rows(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]


def _load_policy_cells(policy_path: Path) -> Dict[str, Any]:
    payload = json.loads(policy_path.read_text(encoding="utf-8"))
    cells = payload.get("cells") if isinstance(payload, dict) else None
    return cells if isinstance(cells, dict) else {}


def _evaluate_snapshot_metrics(
    *,
    rows: List[Dict[str, Any]],
    policy_cells: Dict[str, Any],
    min_bars: int,
    anomaly_fallback_enabled: bool,
) -> Dict[str, Any]:
    total = len(rows)
    mapped = 0
    fallback = 0
    reason_counts: Counter[str] = Counter()

    for row in rows:
        basis = ev.resolve_basis(row)
        bar_count = max(0, ev.to_int(row.get("bar_count"), 0))
        reason = "PSCF_FALLBACK_POLICY_MISSING"

        if bar_count < int(min_bars):
            reason = "PSCF_FALLBACK_INSUFFICIENT_BARS"
        elif basis.missing_fields:
            reason = "PSCF_FALLBACK_STRUCTURAL_INCOMPLETE"
        else:
            candidates = ev.key_candidates(row, basis)
            if not policy_cells:
                reason = "PSCF_FALLBACK_POLICY_MISSING"
            elif not candidates:
                reason = "PSCF_FALLBACK_CELL_KEY_UNAVAILABLE"
            else:
                matched_key = None
                matched_cell = None
                for candidate in candidates:
                    cell = policy_cells.get(candidate)
                    if isinstance(cell, dict):
                        matched_key = candidate
                        matched_cell = cell
                        break
                if matched_key is None or matched_cell is None:
                    reason = "PSCF_FALLBACK_CELL_UNMAPPED"
                elif anomaly_fallback_enabled and ev.anomaly_any(row):
                    reason = "PSCF_FALLBACK_ANOMALOUS"
                else:
                    reason = "PSCF_POLICY_DECISION"
                    mapped += 1

        if reason != "PSCF_POLICY_DECISION":
            fallback += 1
        reason_counts[reason] += 1

    coverage_rate = float(mapped / total) if total > 0 else 0.0
    fallback_rate = float(fallback / total) if total > 0 else 0.0

    return {
        "total_rows": int(total),
        "mapped_rows": int(mapped),
        "fallback_rows": int(fallback),
        "coverage_rate": float(coverage_rate),
        "fallback_rate": float(fallback_rate),
        "reason_counts": dict(reason_counts),
    }


@dataclass
class TargetSymbol:
    symbol: str
    asset_type: str
    from_insufficient: bool
    from_unmapped: bool


def _build_target_symbols(*, plan_dir: Path, min_bars: int, max_symbols: int) -> List[TargetSymbol]:
    insufficient_path = plan_dir / "insufficient-bars.csv"
    unmapped_path = plan_dir / "unmapped-cells.csv"

    if not insufficient_path.exists():
        raise FileNotFoundError(f"insufficient_csv_not_found:{insufficient_path}")
    if not unmapped_path.exists():
        raise FileNotFoundError(f"unmapped_csv_not_found:{unmapped_path}")

    out: Dict[str, TargetSymbol] = {}

    for row in _read_csv_rows(insufficient_path):
        symbol = _normalize_symbol(row.get("ticker"))
        if not symbol:
            continue
        bar_count = max(0, _safe_int(row.get("bar_count"), 0))
        if bar_count >= int(min_bars):
            continue

        entry = out.get(symbol)
        if entry is None:
            out[symbol] = TargetSymbol(
                symbol=symbol,
                asset_type=_normalize_asset_type(row.get("asset_type")),
                from_insufficient=True,
                from_unmapped=False,
            )
        else:
            entry.from_insufficient = True

    for row in _read_csv_rows(unmapped_path):
        symbol = _normalize_symbol(row.get("ticker"))
        if not symbol:
            continue

        entry = out.get(symbol)
        if entry is None:
            out[symbol] = TargetSymbol(
                symbol=symbol,
                asset_type=_normalize_asset_type(row.get("asset_type")),
                from_insufficient=False,
                from_unmapped=True,
            )
        else:
            entry.from_unmapped = True

    ordered = [out[symbol] for symbol in sorted(out.keys())]
    if max_symbols > 0:
        ordered = ordered[: int(max_symbols)]
    return ordered


def _load_snapshot_rows(snapshot_path: Path) -> List[Dict[str, Any]]:
    rows = ev.load_rows(snapshot_path)
    return [row for row in rows if isinstance(row, dict)]


def _write_snapshot_rows(snapshot_path: Path, rows: List[Dict[str, Any]], generated_at_utc: str) -> None:
    payload = {
        "rows": rows,
        "generated_at_utc": generated_at_utc,
    }
    snapshot_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Targeted recommendation data remediation lane (Step 4B).")
    parser.add_argument(
        "--plan-dir",
        default=str(REPO_ROOT / "backups" / "runtime" / "recommendation-remediation-target-plan-20260304T211033Z"),
    )
    parser.add_argument("--snapshot", default=str(REPO_ROOT / "uf_snapshot.json"))
    parser.add_argument("--snapshot-backup", default=str(REPO_ROOT / "uf_snapshot_old_backup.json"))
    parser.add_argument("--policy", default=str(REPO_ROOT / "pscf_policy_runtime.json"))
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--years-history", type=int, default=5)
    parser.add_argument("--max-symbols", type=int, default=0)
    parser.add_argument("--min-bars", type=int, default=_env_int("TFE_RECOMMENDATIONS_MIN_BARS", 180, 20, 2520))
    parser.add_argument("--anomaly-fallback", action="store_true")
    args = parser.parse_args()

    out_dir = (
        Path(args.output_dir).resolve()
        if _safe_text(args.output_dir)
        else REPO_ROOT / "backups" / "runtime" / f"recommendation-data-remediation-lane-{_utc_stamp()}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    plan_dir = Path(args.plan_dir).resolve()
    snapshot_path = Path(args.snapshot).resolve()
    backup_path = Path(args.snapshot_backup).resolve()
    policy_path = Path(args.policy).resolve()

    if not plan_dir.exists() or not plan_dir.is_dir():
        raise FileNotFoundError(f"plan_dir_not_found:{plan_dir}")
    if not snapshot_path.exists():
        raise FileNotFoundError(f"snapshot_not_found:{snapshot_path}")
    if not policy_path.exists():
        raise FileNotFoundError(f"policy_not_found:{policy_path}")

    _load_env_file_fallback(REPO_ROOT / ".env")

    policy_cells = _load_policy_cells(policy_path)
    pre_rows = _load_snapshot_rows(snapshot_path)
    pre_metrics = _evaluate_snapshot_metrics(
        rows=pre_rows,
        policy_cells=policy_cells,
        min_bars=int(args.min_bars),
        anomaly_fallback_enabled=bool(args.anomaly_fallback),
    )

    targets = _build_target_symbols(
        plan_dir=plan_dir,
        min_bars=int(args.min_bars),
        max_symbols=max(0, int(args.max_symbols)),
    )

    existing_by_symbol: Dict[str, Dict[str, Any]] = {}
    for row in pre_rows:
        symbol = _normalize_symbol(row.get("ticker"))
        if symbol and symbol not in existing_by_symbol:
            existing_by_symbol[symbol] = row

    client = get_market_data_service()
    updated_rows: Dict[str, Dict[str, Any]] = {}
    failures: List[Dict[str, Any]] = []
    per_symbol_results: List[Dict[str, Any]] = []

    for idx, target in enumerate(targets, start=1):
        symbol = target.symbol
        prior = existing_by_symbol.get(symbol, {})
        prior_bar_count = max(0, _safe_int(prior.get("bar_count"), 0)) if isinstance(prior, dict) else 0

        try:
            row = evaluate_symbol_snapshot(
                symbol=symbol,
                asset_type=target.asset_type,
                years_history=max(1, int(args.years_history)),
                client=client,
            )
            if not isinstance(row, dict):
                raise RuntimeError("evaluate_symbol_snapshot returned non-dict row")

            row["ticker"] = symbol
            row["asset_type"] = _normalize_asset_type(row.get("asset_type") or target.asset_type)
            new_bar_count = max(0, _safe_int(row.get("bar_count"), 0))

            updated_rows[symbol] = row
            per_symbol_results.append(
                {
                    "symbol": symbol,
                    "asset_type": target.asset_type,
                    "from_insufficient": bool(target.from_insufficient),
                    "from_unmapped": bool(target.from_unmapped),
                    "prior_bar_count": int(prior_bar_count),
                    "new_bar_count": int(new_bar_count),
                    "bar_count_delta": int(new_bar_count - prior_bar_count),
                    "status": "updated",
                    "index": int(idx),
                }
            )
        except Exception as exc:
            signature = f"{type(exc).__name__}:{str(exc)}"
            failures.append(
                {
                    "symbol": symbol,
                    "asset_type": target.asset_type,
                    "from_insufficient": bool(target.from_insufficient),
                    "from_unmapped": bool(target.from_unmapped),
                    "index": int(idx),
                    "error": signature,
                }
            )
            per_symbol_results.append(
                {
                    "symbol": symbol,
                    "asset_type": target.asset_type,
                    "from_insufficient": bool(target.from_insufficient),
                    "from_unmapped": bool(target.from_unmapped),
                    "prior_bar_count": int(prior_bar_count),
                    "new_bar_count": None,
                    "bar_count_delta": None,
                    "status": "failed",
                    "error": signature,
                    "index": int(idx),
                }
            )

    merged_rows: List[Dict[str, Any]] = []
    seen: set[str] = set()

    for row in pre_rows:
        symbol = _normalize_symbol(row.get("ticker"))
        if symbol and symbol in updated_rows:
            merged_rows.append(updated_rows[symbol])
            seen.add(symbol)
        else:
            merged_rows.append(row)
            if symbol:
                seen.add(symbol)

    for symbol in sorted(updated_rows.keys()):
        if symbol in seen:
            continue
        merged_rows.append(updated_rows[symbol])

    generated_at_utc = _utc_now_iso()

    if snapshot_path.exists():
        shutil.copy2(snapshot_path, backup_path)

    _write_snapshot_rows(snapshot_path=snapshot_path, rows=merged_rows, generated_at_utc=generated_at_utc)

    post_rows = _load_snapshot_rows(snapshot_path)
    post_metrics = _evaluate_snapshot_metrics(
        rows=post_rows,
        policy_cells=policy_cells,
        min_bars=int(args.min_bars),
        anomaly_fallback_enabled=bool(args.anomaly_fallback),
    )

    failure_counter = Counter([entry.get("error", "") for entry in failures])

    per_symbol_csv = out_dir / "per-symbol-results.csv"
    with per_symbol_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "index",
                "symbol",
                "asset_type",
                "from_insufficient",
                "from_unmapped",
                "prior_bar_count",
                "new_bar_count",
                "bar_count_delta",
                "status",
                "error",
            ]
        )
        for row in per_symbol_results:
            writer.writerow(
                [
                    row.get("index"),
                    row.get("symbol"),
                    row.get("asset_type"),
                    row.get("from_insufficient"),
                    row.get("from_unmapped"),
                    row.get("prior_bar_count"),
                    row.get("new_bar_count"),
                    row.get("bar_count_delta"),
                    row.get("status"),
                    row.get("error", ""),
                ]
            )

    summary = {
        "generated_at_utc": generated_at_utc,
        "status": "pass",
        "inputs": {
            "plan_dir": str(plan_dir),
            "snapshot": str(snapshot_path),
            "snapshot_backup": str(backup_path),
            "policy": str(policy_path),
            "years_history": int(args.years_history),
            "min_bars": int(args.min_bars),
            "anomaly_fallback_enabled": bool(args.anomaly_fallback),
            "max_symbols": int(args.max_symbols),
        },
        "target_counts": {
            "total_targets": int(len(targets)),
            "insufficient_targets": int(sum(1 for t in targets if t.from_insufficient)),
            "unmapped_targets": int(sum(1 for t in targets if t.from_unmapped)),
        },
        "run_counts": {
            "updated": int(sum(1 for r in per_symbol_results if r.get("status") == "updated")),
            "failed": int(sum(1 for r in per_symbol_results if r.get("status") == "failed")),
        },
        "failure_signatures": [
            {"error": key, "count": int(value)}
            for key, value in sorted(failure_counter.items(), key=lambda kv: (-kv[1], kv[0]))
            if key
        ],
        "pre_metrics": pre_metrics,
        "post_metrics": post_metrics,
        "delta": {
            "coverage_rate": float(post_metrics["coverage_rate"] - pre_metrics["coverage_rate"]),
            "fallback_rate": float(post_metrics["fallback_rate"] - pre_metrics["fallback_rate"]),
            "mapped_rows": int(post_metrics["mapped_rows"] - pre_metrics["mapped_rows"]),
            "fallback_rows": int(post_metrics["fallback_rows"] - pre_metrics["fallback_rows"]),
        },
        "artifacts": {
            "per_symbol_results_csv": str(per_symbol_csv),
        },
    }

    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lane_summary = {
        "status": "pass",
        "generated_at_utc": generated_at_utc,
        "summary_json": str(summary_path),
        "targets": summary["target_counts"],
        "run_counts": summary["run_counts"],
        "delta": summary["delta"],
    }

    lane_summary_path = out_dir / "lane-summary.json"
    lane_summary_path.write_text(json.dumps(lane_summary, indent=2), encoding="utf-8")

    print(str(lane_summary_path))
    print(json.dumps(lane_summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
