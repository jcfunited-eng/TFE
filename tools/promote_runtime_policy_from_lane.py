#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME_POLICY_PATH = REPO_ROOT / "pscf_policy_runtime.json"
DEFAULT_CONTRACT_PATH = REPO_ROOT / "recommendation_policy_promotion_contract.json"

REQUIRED_GATES = (
    "gate_5day",
    "gate_20day",
    "gate_60day",
    "gate_sp_plus_4_proxy_avg",
    "gate_coverage",
    "gate_fallback",
)

REQUIRED_BENCHMARK_MIN_ROWS_PER_HORIZON = 20


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _to_int(value: Any, default: int) -> int:
    try:
        return int(float(value))
    except Exception:
        return int(default)


def _extract_winner(lane_summary: Dict[str, Any], lane_summary_path: Path) -> Dict[str, Any]:
    winner = lane_summary.get("winner")
    if not isinstance(winner, dict):
        raise RuntimeError(f"lane_summary_missing_winner:{lane_summary_path}")
    return winner


def _winner_policy_path(winner: Dict[str, Any]) -> Path:
    raw = str(winner.get("policy_path", "")).strip()
    if not raw:
        raise RuntimeError("winner_policy_path_missing")
    p = Path(raw)
    if not p.is_absolute():
        p = (REPO_ROOT / p).resolve()
    return p


def _winner_gates(winner: Dict[str, Any]) -> Dict[str, Any]:
    gates = winner.get("gates")
    if not isinstance(gates, dict):
        raise RuntimeError("winner_gates_missing")
    return gates


def _all_required_gates_true(gates: Dict[str, Any]) -> Tuple[bool, Dict[str, bool]]:
    state: Dict[str, bool] = {}
    for gate_name in REQUIRED_GATES:
        state[gate_name] = bool(gates.get(gate_name, False))
    return all(state.values()), state


def _extract_benchmark_gate(benchmark_lane_summary: Dict[str, Any], benchmark_lane_summary_path: Path) -> Dict[str, Any]:
    bench_gate = benchmark_lane_summary.get("competitive_gate")
    if not isinstance(bench_gate, dict):
        raise RuntimeError(f"benchmark_lane_missing_competitive_gate:{benchmark_lane_summary_path}")

    raw_pass = bool(bench_gate.get("pass", False))
    external_coverage_ok = bool(bench_gate.get("external_coverage_ok", False))
    external_min_rows_per_horizon = _to_int(bench_gate.get("external_min_rows_per_horizon"), 0)
    meets_support_threshold = external_min_rows_per_horizon >= int(REQUIRED_BENCHMARK_MIN_ROWS_PER_HORIZON)
    effective_pass = bool(raw_pass and external_coverage_ok and meets_support_threshold)

    return {
        "tfe_beats_external_proxy_on_avg_outcome": bool(
            bench_gate.get("tfe_beats_external_proxy_on_avg_outcome", False)
        ),
        "tfe_beats_external_proxy_on_h60_outcome": bool(
            bench_gate.get("tfe_beats_external_proxy_on_h60_outcome", False)
        ),
        "tfe_beats_external_proxy_on_avg_excess": bool(
            bench_gate.get("tfe_beats_external_proxy_on_avg_excess", False)
        ),
        "external_coverage_ok": external_coverage_ok,
        "external_min_rows_per_horizon": int(external_min_rows_per_horizon),
        "required_external_min_rows_per_horizon": int(REQUIRED_BENCHMARK_MIN_ROWS_PER_HORIZON),
        "meets_external_support_threshold": bool(meets_support_threshold),
        "pass": raw_pass,
        "effective_pass": effective_pass,
    }


def _atomic_replace(src_policy: Path, runtime_policy_path: Path) -> None:
    tmp_path = runtime_policy_path.with_suffix(runtime_policy_path.suffix + ".tmp")
    tmp_path.write_text(src_policy.read_text(encoding="utf-8"), encoding="utf-8")
    os.replace(tmp_path, runtime_policy_path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Promote runtime recommendation policy only when canonical gates and benchmark gates pass."
    )
    parser.add_argument("--lane-summary", required=True)
    parser.add_argument("--benchmark-lane-summary", required=True)
    parser.add_argument("--runtime-policy", default=str(DEFAULT_RUNTIME_POLICY_PATH))
    parser.add_argument("--contract-path", default=str(DEFAULT_CONTRACT_PATH))
    parser.add_argument("--output-dir", default="")
    args = parser.parse_args()

    lane_summary_path = Path(str(args.lane_summary)).resolve()
    if not lane_summary_path.exists():
        raise FileNotFoundError(f"lane_summary_not_found:{lane_summary_path}")

    benchmark_lane_summary_path = Path(str(args.benchmark_lane_summary)).resolve()
    if not benchmark_lane_summary_path.exists():
        raise FileNotFoundError(f"benchmark_lane_summary_not_found:{benchmark_lane_summary_path}")

    runtime_policy_path = Path(str(args.runtime_policy)).resolve()
    contract_path = Path(str(args.contract_path)).resolve()

    out_dir = (
        Path(str(args.output_dir)).resolve()
        if str(args.output_dir).strip()
        else REPO_ROOT / "backups" / "runtime" / f"recommendation-policy-canonicalize-{_utc_stamp()}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    lane_summary = _load_json(lane_summary_path)
    winner = _extract_winner(lane_summary, lane_summary_path)
    gates = _winner_gates(winner)
    gates_pass, gate_state = _all_required_gates_true(gates)

    benchmark_lane_summary = _load_json(benchmark_lane_summary_path)
    benchmark_gate_state = _extract_benchmark_gate(benchmark_lane_summary, benchmark_lane_summary_path)
    benchmark_pass = bool(benchmark_gate_state["effective_pass"])

    winner_policy_path = _winner_policy_path(winner)
    if not winner_policy_path.exists():
        raise FileNotFoundError(f"winner_policy_not_found:{winner_policy_path}")

    if not runtime_policy_path.exists():
        raise FileNotFoundError(f"runtime_policy_not_found:{runtime_policy_path}")

    runtime_sha_before = _sha256(runtime_policy_path)
    winner_sha = _sha256(winner_policy_path)

    promoted = False
    promotion_reason = "winner_already_runtime"
    runtime_backup_path = None

    if not gates_pass:
        promotion_reason = "blocked_required_gates_failed"
    elif not bool(benchmark_gate_state.get("pass", False)):
        promotion_reason = "blocked_benchmark_gate_failed"
    elif not bool(benchmark_gate_state.get("meets_external_support_threshold", False)):
        promotion_reason = "blocked_benchmark_support_threshold"
    elif not benchmark_pass:
        promotion_reason = "blocked_benchmark_effective_gate_failed"
    elif winner_sha != runtime_sha_before:
        runtime_backup_path = out_dir / f"runtime-policy-backup-{_utc_stamp()}.json"
        runtime_backup_path.write_text(runtime_policy_path.read_text(encoding="utf-8"), encoding="utf-8")
        _atomic_replace(winner_policy_path, runtime_policy_path)
        promoted = True
        promotion_reason = "promoted_winner_over_runtime"

    runtime_sha_after = _sha256(runtime_policy_path)

    contract_payload = {
        "version": 3,
        "updated_at_utc": _utc_now_iso(),
        "canonical_rule": "Runtime recommendation policy remains canonical unless a lane winner passes all required quality/reliability gates and benchmark-beat gate, then is explicitly promoted by this governance gate.",
        "required_gates": list(REQUIRED_GATES),
        "required_benchmark_gate": {
            "source": str(benchmark_lane_summary_path),
            "required": "competitive_gate.pass == true AND competitive_gate.external_min_rows_per_horizon >= 20",
            "state": benchmark_gate_state,
        },
        "promotion_requirements": {
            "require_all_gates_pass": True,
            "require_benchmark_pass": True,
            "require_ranked_winner_from_lane": True,
            "require_benchmark_min_rows_per_horizon": int(REQUIRED_BENCHMARK_MIN_ROWS_PER_HORIZON),
            "auto_promotion_disabled_by_default_in_l5": True,
            "manual_promotion_command": "python3 tools/promote_runtime_policy_from_lane.py --lane-summary <path> --benchmark-lane-summary <path>",
        },
        "current_canonical": {
            "policy_path": str(runtime_policy_path),
            "policy_sha256": runtime_sha_after,
            "source_lane_summary": str(lane_summary_path),
            "winner_variant_name": str(winner.get("variant_name", "")),
            "winner_reason": str(winner.get("reason", "")),
            "metrics": {
                "horizon_outcome_over_index_pct": winner.get("horizon_outcome_over_index_pct", {}),
                "avg_outcome_over_index_pct": winner.get("avg_outcome_over_index_pct"),
                "coverage_rate": winner.get("coverage_rate"),
                "fallback_rate": winner.get("fallback_rate"),
            },
            "gates": gates,
        },
    }
    contract_path.write_text(json.dumps(contract_payload, indent=2), encoding="utf-8")

    summary = {
        "status": "pass" if (gates_pass and benchmark_pass) else "fail",
        "generated_at_utc": _utc_now_iso(),
        "lane_summary": str(lane_summary_path),
        "benchmark_lane_summary": str(benchmark_lane_summary_path),
        "runtime_policy_path": str(runtime_policy_path),
        "winner_policy_path": str(winner_policy_path),
        "gates_pass": bool(gates_pass),
        "required_gate_state": gate_state,
        "benchmark_pass": bool(benchmark_pass),
        "benchmark_gate_state": benchmark_gate_state,
        "promoted": bool(promoted),
        "promotion_reason": promotion_reason,
        "runtime_policy_sha256_before": runtime_sha_before,
        "winner_policy_sha256": winner_sha,
        "runtime_policy_sha256_after": runtime_sha_after,
        "runtime_backup_path": str(runtime_backup_path) if runtime_backup_path is not None else None,
        "contract_path": str(contract_path),
    }

    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lane_summary_out = {
        "status": summary["status"],
        "generated_at_utc": summary["generated_at_utc"],
        "summary_json": str(summary_path),
        "promoted": summary["promoted"],
        "promotion_reason": summary["promotion_reason"],
        "contract_path": summary["contract_path"],
    }
    lane_summary_out_path = out_dir / "lane-summary.json"
    lane_summary_out_path.write_text(json.dumps(lane_summary_out, indent=2), encoding="utf-8")

    print(str(lane_summary_out_path))
    print(json.dumps(lane_summary_out, indent=2))

    return 0 if (gates_pass and benchmark_pass) else 2


if __name__ == "__main__":
    raise SystemExit(main())
