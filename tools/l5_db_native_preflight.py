#!/usr/bin/env python3
"""
Bounded preflight for L5 DB-native execution modes.

Checks:
- Required L5 input artifact presence
- Policy IO mode validity (file/hybrid/postgres)
- Postgres preflight + table contract + runtime policy availability (when enabled)
- Fail-fast verdict for safe long-run gating
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKUPS_RUNTIME_DIR = REPO_ROOT / "backups" / "runtime"
DEFAULT_ROW_TRACE_PATH = REPO_ROOT / "real_world_cleaned_universe_l5_row_trace_full.csv"
DEFAULT_RUNTIME_POLICY_PATH = REPO_ROOT / "pscf_policy_runtime.json"
DEFAULT_COVERAGE_SNAPSHOT_PATH = REPO_ROOT / "uf_snapshot.ses.json"

sys.path.insert(0, str(REPO_ROOT))

from l5_postgres_io import (  # noqa: E402
    DB_MODE_FILE,
    ensure_l5_policy_tables,
    load_latest_anomaly_policy_from_postgres,
    load_latest_horizon_overrides_from_postgres,
    load_latest_rowtrace_source_stats_from_postgres,
    load_latest_runtime_policy_from_postgres,
    load_latest_validation_dataset_from_postgres,
    normalize_l5_policy_io_mode,
    pg_preflight_for_l5,
    postgres_mode_enabled,
    postgres_mode_is_strict,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _latest_path(pattern: str) -> Optional[Path]:
    matches = sorted(REPO_ROOT.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def _resolve_validation_dataset() -> Optional[Path]:
    env = str(os.environ.get("TFE_POLICY_VALIDATION_DATASET", "")).strip()
    if env:
        p = Path(env)
        if not p.is_absolute():
            p = (REPO_ROOT / p).resolve()
        if p.exists():
            return p
        return p

    latest = _latest_path("backups/strict-ab-frozen-dataset-*.json")
    return latest


def _resolve_spy_dataset() -> Optional[Path]:
    env = str(os.environ.get("TFE_POLICY_SPY_DATASET", "")).strip()
    if env:
        p = Path(env)
        if not p.is_absolute():
            p = (REPO_ROOT / p).resolve()
        if p.exists():
            return p
        return p

    latest = _latest_path("backups/strict-ab-frozen-dataset-*.json")
    return latest


def _resolve_anomaly_policy() -> Optional[Path]:
    env = str(os.environ.get("TFE_POLICY_ANOMALY_POLICY", "")).strip()
    if env:
        p = Path(env)
        if not p.is_absolute():
            p = (REPO_ROOT / p).resolve()
        if p.exists():
            return p
        return p

    candidates = sorted(
        REPO_ROOT.glob("backups/pscf-policy-anomaly-watch-*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for candidate in candidates:
        if "-report-" in candidate.name:
            continue
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
        except Exception:
            continue
        cells = payload.get("cells") if isinstance(payload, dict) else None
        if isinstance(cells, dict) and len(cells) > 0:
            return candidate
    if candidates:
        return candidates[0]
    return None


def _resolve_horizon_overrides() -> Optional[Path]:
    env = str(os.environ.get("TFE_POLICY_HORIZON_DECISION_OVERRIDES_PATH", "")).strip()
    if env:
        if env.lower() in ("0", "off", "false", "none", "null"):
            return None
        p = Path(env)
        if not p.is_absolute():
            p = (REPO_ROOT / p).resolve()
        if p.exists():
            return p
        return p

    default_path = REPO_ROOT / "policy_horizon_overrides.json"
    if default_path.exists():
        return default_path
    return None


def _resolve_runtime_policy_path() -> Path:
    env = str(os.environ.get("TFE_RUNTIME_POLICY_PATH", "")).strip()
    if not env:
        return DEFAULT_RUNTIME_POLICY_PATH
    p = Path(env)
    if not p.is_absolute():
        p = (REPO_ROOT / p).resolve()
    return p


def _resolve_row_trace_path() -> Path:
    env = str(os.environ.get("TFE_POLICY_ROW_TRACE", "")).strip()
    if not env:
        return DEFAULT_ROW_TRACE_PATH
    p = Path(env)
    if not p.is_absolute():
        p = (REPO_ROOT / p).resolve()
    return p


def _resolve_coverage_snapshot_path() -> Path:
    env = str(os.environ.get("TFE_L5_COVERAGE_SNAPSHOT_PATH", "")).strip()
    if not env:
        return DEFAULT_COVERAGE_SNAPSHOT_PATH
    p = Path(env)
    if not p.is_absolute():
        p = (REPO_ROOT / p).resolve()
    return p


def _file_check(path: Optional[Path], *, required: bool = True) -> Dict[str, Any]:
    if path is None:
        return {
            "path": None,
            "exists": False,
            "required": required,
            "pass": not required,
            "reason": "path_unresolved",
        }

    exists = path.exists()
    return {
        "path": str(path),
        "exists": bool(exists),
        "is_file": bool(path.is_file()) if exists else False,
        "required": required,
        "pass": bool(exists) if required else True,
        "size_bytes": int(path.stat().st_size) if exists else None,
        "reason": None if exists or not required else "missing",
    }


def _write_summary(output_dir: Path, summary: Dict[str, Any]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary_path


def run_preflight(*, mode_raw: str) -> Dict[str, Any]:
    mode = normalize_l5_policy_io_mode(mode_raw)
    strict = postgres_mode_is_strict(mode)
    pg_enabled = postgres_mode_enabled(mode)

    row_trace_path = _resolve_row_trace_path()
    runtime_policy_path = _resolve_runtime_policy_path()
    validation_dataset_path = _resolve_validation_dataset()
    spy_dataset_path = _resolve_spy_dataset()
    anomaly_policy_path = _resolve_anomaly_policy()
    horizon_overrides_path = _resolve_horizon_overrides()
    coverage_snapshot_path = _resolve_coverage_snapshot_path()

    files = {
        "row_trace": _file_check(row_trace_path, required=(mode == DB_MODE_FILE)),
        "runtime_policy_file": _file_check(runtime_policy_path, required=(mode == DB_MODE_FILE)),
        "validation_dataset": _file_check(validation_dataset_path, required=(mode == DB_MODE_FILE)),
        "spy_dataset": _file_check(spy_dataset_path, required=(mode == DB_MODE_FILE)),
        "anomaly_policy": _file_check(anomaly_policy_path, required=(mode == DB_MODE_FILE)),
        "horizon_overrides": _file_check(horizon_overrides_path, required=False),
        "coverage_snapshot": _file_check(coverage_snapshot_path, required=True),
    }

    file_checks_pass = all(bool(v.get("pass")) for v in files.values())

    postgres: Dict[str, Any] = {
        "enabled": pg_enabled,
        "strict": strict,
        "preflight": None,
        "table_ensure": None,
        "runtime_policy_present": None,
        "runtime_policy_version_id": None,
        "runtime_policy_trigger": None,
        "runtime_policy_promoted_at_utc": None,
        "rowtrace_dataset": None,
        "validation_dataset": None,
        "anomaly_policy": None,
        "horizon_overrides": None,
        "errors": [],
    }

    postgres_ready = True

    if pg_enabled:
        preflight = pg_preflight_for_l5()
        postgres["preflight"] = preflight.as_dict()
        if not preflight.ok:
            postgres_ready = False
            postgres["errors"].append("postgres_preflight_failed")
        else:
            try:
                table_ensure = ensure_l5_policy_tables()
                postgres["table_ensure"] = table_ensure
            except Exception as exc:
                postgres_ready = False
                postgres["errors"].append(f"postgres_table_ensure_failed:{type(exc).__name__}:{exc}")

            if postgres_ready:
                try:
                    rowtrace_stats = load_latest_rowtrace_source_stats_from_postgres()
                    postgres["rowtrace_dataset"] = rowtrace_stats
                    if strict and not rowtrace_stats:
                        postgres_ready = False
                        postgres["errors"].append("postgres_rowtrace_missing_in_strict_mode")
                except Exception as exc:
                    postgres["rowtrace_dataset"] = None
                    if strict:
                        postgres_ready = False
                        postgres["errors"].append(f"postgres_rowtrace_read_failed:{type(exc).__name__}:{exc}")
                    else:
                        postgres["errors"].append(f"postgres_rowtrace_read_warning:{type(exc).__name__}:{exc}")

            if postgres_ready:
                try:
                    latest_validation = load_latest_validation_dataset_from_postgres()
                    if latest_validation and isinstance(latest_validation.get("dataset"), dict):
                        dataset = latest_validation.get("dataset") or {}
                        spy = dataset.get("spy") if isinstance(dataset.get("spy"), dict) else {}
                        ts_ms = spy.get("ts_ms") if isinstance(spy.get("ts_ms"), list) else []
                        close = spy.get("close") if isinstance(spy.get("close"), list) else []
                        spy_arrays_valid = bool(len(ts_ms) > 0 and len(close) > 0 and len(ts_ms) == len(close))
                        symbols = dataset.get("symbols") if isinstance(dataset.get("symbols"), dict) else {}
                        postgres["validation_dataset"] = {
                            "dataset_id": latest_validation.get("dataset_id"),
                            "source_path": latest_validation.get("source_path"),
                            "symbols_count": len(symbols),
                            "spy_points": len(close),
                            "spy_arrays_valid": spy_arrays_valid,
                        }
                        if strict and not spy_arrays_valid:
                            postgres_ready = False
                            postgres["errors"].append("postgres_validation_spy_missing_in_strict_mode")
                    else:
                        postgres["validation_dataset"] = None
                        if strict:
                            postgres_ready = False
                            postgres["errors"].append("postgres_validation_dataset_missing_in_strict_mode")
                except Exception as exc:
                    postgres["validation_dataset"] = None
                    if strict:
                        postgres_ready = False
                        postgres["errors"].append(f"postgres_validation_dataset_read_failed:{type(exc).__name__}:{exc}")
                    else:
                        postgres["errors"].append(f"postgres_validation_dataset_read_warning:{type(exc).__name__}:{exc}")

            if postgres_ready:
                try:
                    latest_anomaly = load_latest_anomaly_policy_from_postgres()
                    if latest_anomaly and isinstance(latest_anomaly.get("policy"), dict):
                        policy = latest_anomaly.get("policy") or {}
                        cells = policy.get("cells") if isinstance(policy.get("cells"), dict) else {}
                        cells_count = len(cells)
                        postgres["anomaly_policy"] = {
                            "policy_id": latest_anomaly.get("policy_id"),
                            "source_path": latest_anomaly.get("source_path"),
                            "generated_at_utc": latest_anomaly.get("generated_at_utc"),
                            "cells_count": cells_count,
                            "cells_valid": bool(cells_count > 0),
                        }
                        if strict and cells_count <= 0:
                            postgres_ready = False
                            postgres["errors"].append("postgres_anomaly_policy_cells_empty_in_strict_mode")
                    else:
                        postgres["anomaly_policy"] = None
                        if strict:
                            postgres_ready = False
                            postgres["errors"].append("postgres_anomaly_policy_missing_in_strict_mode")
                except Exception as exc:
                    postgres["anomaly_policy"] = None
                    if strict:
                        postgres_ready = False
                        postgres["errors"].append(f"postgres_anomaly_policy_read_failed:{type(exc).__name__}:{exc}")
                    else:
                        postgres["errors"].append(f"postgres_anomaly_policy_read_warning:{type(exc).__name__}:{exc}")

            if postgres_ready:
                try:
                    latest_horizon = load_latest_horizon_overrides_from_postgres()
                    if latest_horizon and isinstance(latest_horizon.get("overrides"), dict):
                        overrides_payload = latest_horizon.get("overrides") or {}
                        cells_count = 0
                        for mapping in overrides_payload.values():
                            if isinstance(mapping, dict):
                                cells_count += len(mapping)
                        postgres["horizon_overrides"] = {
                            "override_set_id": latest_horizon.get("override_set_id"),
                            "source_path": latest_horizon.get("source_path"),
                            "generated_at_utc": latest_horizon.get("generated_at_utc"),
                            "total_overrides": int(cells_count),
                            "cells_valid": bool(cells_count > 0),
                        }
                        if strict and cells_count <= 0:
                            postgres_ready = False
                            postgres["errors"].append("postgres_horizon_overrides_cells_empty_in_strict_mode")
                    else:
                        postgres["horizon_overrides"] = None
                        if strict:
                            postgres_ready = False
                            postgres["errors"].append("postgres_horizon_overrides_missing_in_strict_mode")
                except Exception as exc:
                    postgres["horizon_overrides"] = None
                    if strict:
                        postgres_ready = False
                        postgres["errors"].append(f"postgres_horizon_overrides_read_failed:{type(exc).__name__}:{exc}")
                    else:
                        postgres["errors"].append(f"postgres_horizon_overrides_read_warning:{type(exc).__name__}:{exc}")

            if postgres_ready:
                try:
                    latest = load_latest_runtime_policy_from_postgres()
                except Exception as exc:
                    latest = None
                    postgres_ready = False
                    postgres["errors"].append(f"postgres_runtime_policy_read_failed:{type(exc).__name__}:{exc}")

                if latest and isinstance(latest.get("policy"), dict):
                    postgres["runtime_policy_present"] = True
                    postgres["runtime_policy_version_id"] = latest.get("policy_version_id")
                    postgres["runtime_policy_trigger"] = latest.get("trigger")
                    postgres["runtime_policy_promoted_at_utc"] = latest.get("promoted_at_utc")
                else:
                    postgres["runtime_policy_present"] = False
                    if strict:
                        postgres_ready = False
                        postgres["errors"].append("postgres_runtime_policy_missing_in_strict_mode")

    verdict_reasons: list[str] = []
    warnings: list[str] = []

    if not file_checks_pass:
        verdict_reasons.append("required_input_files_missing")

    rowtrace_file_exists = bool(files["row_trace"].get("exists"))
    rowtrace_pg_stats = postgres.get("rowtrace_dataset") if isinstance(postgres, dict) else None
    rowtrace_pg_present = bool(rowtrace_pg_stats and int(rowtrace_pg_stats.get("row_count") or 0) > 0)
    validation_file_exists = bool(files["validation_dataset"].get("exists"))
    spy_file_exists = bool(files["spy_dataset"].get("exists"))
    anomaly_file_exists = bool(files["anomaly_policy"].get("exists"))
    validation_pg = postgres.get("validation_dataset") if isinstance(postgres, dict) else None
    validation_pg_present = bool(validation_pg and str(validation_pg.get("dataset_id") or "").strip())
    validation_pg_spy_valid = bool(validation_pg and bool(validation_pg.get("spy_arrays_valid")))
    anomaly_pg = postgres.get("anomaly_policy") if isinstance(postgres, dict) else None
    anomaly_pg_present = bool(anomaly_pg and str(anomaly_pg.get("policy_id") or "").strip())
    anomaly_pg_cells_valid = bool(anomaly_pg and bool(anomaly_pg.get("cells_valid")))
    horizon_file_exists = bool(files["horizon_overrides"].get("exists"))
    horizon_pg = postgres.get("horizon_overrides") if isinstance(postgres, dict) else None
    horizon_pg_present = bool(horizon_pg and str(horizon_pg.get("override_set_id") or "").strip())
    horizon_pg_cells_valid = bool(horizon_pg and bool(horizon_pg.get("cells_valid")))
    if pg_enabled:
        if strict and not rowtrace_pg_present:
            verdict_reasons.append("postgres_rowtrace_missing_in_strict_mode")
        if not strict and not (rowtrace_pg_present or rowtrace_file_exists):
            verdict_reasons.append("row_trace_missing_in_postgres_and_file_fallback")
        if strict and not validation_pg_present:
            verdict_reasons.append("postgres_validation_dataset_missing_in_strict_mode")
        if strict and validation_pg_present and not validation_pg_spy_valid:
            verdict_reasons.append("postgres_validation_spy_missing_in_strict_mode")
        if not strict and not (validation_pg_present or (validation_file_exists and spy_file_exists)):
            verdict_reasons.append("validation_dataset_missing_in_postgres_and_file_fallback")
        if strict and not anomaly_pg_present:
            verdict_reasons.append("postgres_anomaly_policy_missing_in_strict_mode")
        if strict and anomaly_pg_present and not anomaly_pg_cells_valid:
            verdict_reasons.append("postgres_anomaly_policy_cells_empty_in_strict_mode")
        if not strict and not (anomaly_pg_present or anomaly_file_exists):
            verdict_reasons.append("anomaly_policy_missing_in_postgres_and_file_fallback")
        if strict and not horizon_pg_present:
            verdict_reasons.append("postgres_horizon_overrides_missing_in_strict_mode")
        if strict and horizon_pg_present and not horizon_pg_cells_valid:
            verdict_reasons.append("postgres_horizon_overrides_cells_empty_in_strict_mode")
        if not strict and not (horizon_pg_present or horizon_file_exists):
            warnings.append("horizon_overrides_missing_in_postgres_and_file_fallback")

    if pg_enabled and not postgres_ready:
        if strict:
            verdict_reasons.append("postgres_not_ready")
        elif bool(files["runtime_policy_file"].get("exists")):
            warnings.append("postgres_not_ready_using_file_fallback")
        else:
            verdict_reasons.append("postgres_not_ready_and_file_fallback_missing")

    if mode == DB_MODE_FILE and not files["runtime_policy_file"]["pass"]:
        verdict_reasons.append("runtime_policy_file_missing_in_file_mode")

    if mode != DB_MODE_FILE and not bool(postgres.get("runtime_policy_present")):
        fallback_exists = bool(files["runtime_policy_file"].get("exists"))
        if strict:
            verdict_reasons.append("postgres_runtime_policy_missing_in_strict_mode")
        elif fallback_exists:
            warnings.append("postgres_runtime_policy_missing_using_file_fallback")
        else:
            verdict_reasons.append("postgres_runtime_policy_missing_and_file_fallback_missing")

    passed = len(verdict_reasons) == 0

    return {
        "generated_at_utc": _utc_now_iso(),
        "repo_root": str(REPO_ROOT),
        "policy_io_mode": mode,
        "postgres_enabled": pg_enabled,
        "postgres_strict": strict,
        "files": files,
        "postgres": postgres,
        "pass": passed,
        "reasons": verdict_reasons,
        "warnings": warnings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run bounded L5 DB-native preflight checks.")
    parser.add_argument(
        "--mode",
        type=str,
        default=str(os.environ.get("TFE_L5_POLICY_IO_MODE", DB_MODE_FILE)),
        help="L5 policy io mode (file|hybrid|postgres).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="",
        help="Optional output directory for summary.json.",
    )
    args = parser.parse_args()

    summary = run_preflight(mode_raw=str(args.mode))

    out_dir = Path(str(args.output_dir).strip()) if str(args.output_dir).strip() else BACKUPS_RUNTIME_DIR / f"l5-db-native-preflight-{normalize_l5_policy_io_mode(str(args.mode))}-{_stamp()}-{os.getpid()}"
    if not out_dir.is_absolute():
        out_dir = (REPO_ROOT / out_dir).resolve()

    summary_path = _write_summary(out_dir, summary)
    summary["summary_path"] = str(summary_path)

    # Write back with summary_path included for single-file operator consumption.
    _write_summary(out_dir, summary)

    print(json.dumps(summary, indent=2))

    if summary.get("pass"):
        raise SystemExit(0)
    raise SystemExit(2)


if __name__ == "__main__":
    main()
