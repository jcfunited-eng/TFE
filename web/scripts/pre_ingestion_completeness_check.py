#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_BACKUPS = REPO_ROOT / "backups" / "runtime"

REFRESH_MODE_FULL = "full_universe"
REFRESH_MODE_TARGETED = "targeted_pfsc"

ENV_CANDIDATES = (
    REPO_ROOT / ".env",
    REPO_ROOT / "web" / ".env",
    Path.cwd() / ".env",
)

STOCKS_UNIVERSE_PATH = REPO_ROOT / "massive_universe_stocks.json"
ETF_UNIVERSE_PATH = REPO_ROOT / "massive_universe_etf.json"
INDEX_UNIVERSE_PATH = REPO_ROOT / "massive_universe_index.json"
CRYPTO_UNIVERSE_PATH = REPO_ROOT / "massive_universe_crypto.json"

ACTIVE_SNAPSHOT_PATH = REPO_ROOT / "uf_snapshot.json"
ACTIVE_SNAPSHOT_BACKUP_PATH = REPO_ROOT / "uf_snapshot_old_backup.json"
TRACE_BOOTSTRAP_PATH = (
    REPO_ROOT
    / "backups"
    / "lab"
    / "recommendation_lab"
    / "current_inputs"
    / "real_world_cleaned_universe_l5_row_trace_merged_historical.csv"
)

TARGETED_SELECTOR_SCRIPT_PATH = REPO_ROOT / "web" / "scripts" / "read_runtime_selector_rows.mjs"
TARGETED_SELECTOR_REQUIRED_ENV = ("PGHOST", "PGDATABASE", "PGUSER", "PGPASSWORD")

INDEX_DEFAULT_ROWS = 1
CRYPTO_DEFAULT_ROWS = 8


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def timestamp_token() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _load_env_candidates() -> None:
    for path in ENV_CANDIDATES:
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export ") :].strip()
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if not key or key in os.environ:
                continue
            value = value.strip()
            if value and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            os.environ[key] = value


def _to_text(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    return text or None


def _sanitize_run_id_for_path(run_id: str) -> str:
    out: List[str] = []
    for ch in run_id:
        if ch.isalnum():
            out.append(ch)
        elif ch in {"-", "_"}:
            out.append(ch)
        else:
            out.append("_")
    return "".join(out).strip("_") or "run"


def _resolve_run_id(explicit_run_id: Optional[str]) -> tuple[str, str]:
    candidate = _to_text(explicit_run_id) or _to_text(os.environ.get("TFE_REFRESH_RUN_ID"))
    if candidate:
        return candidate, "explicit_or_env"
    generated = f"pre-ingestion-proof-{timestamp_token()}"
    return generated, "generated_local_proof"


def _json_payload(path: Path) -> tuple[Any, Optional[str]]:
    if not path.exists():
        return None, "path_missing"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, f"json_read_error:{type(exc).__name__}"
    return payload, None


def _json_list_metrics(path: Path) -> Dict[str, Any]:
    metrics: Dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "file_size_bytes": path.stat().st_size if path.exists() else 0,
        "row_count": 0,
        "payload_kind": None,
        "read_error": None,
    }
    payload, err = _json_payload(path)
    if err:
        metrics["read_error"] = err
        return metrics
    if isinstance(payload, list):
        metrics["payload_kind"] = "list"
        metrics["row_count"] = len(payload)
        return metrics
    if isinstance(payload, dict) and isinstance(payload.get("rows"), list):
        metrics["payload_kind"] = "dict.rows"
        metrics["row_count"] = len(payload.get("rows") or [])
        return metrics
    metrics["payload_kind"] = type(payload).__name__
    metrics["read_error"] = "unexpected_json_shape"
    return metrics


def _csv_metrics(path: Path, required_columns: Iterable[str] = ()) -> Dict[str, Any]:
    required = [str(column) for column in required_columns]
    metrics: Dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "file_size_bytes": path.stat().st_size if path.exists() else 0,
        "row_count": 0,
        "header": [],
        "missing_required_columns": [],
        "read_error": None,
    }
    if not path.exists():
        metrics["read_error"] = "path_missing"
        return metrics
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            metrics["header"] = list(reader.fieldnames or [])
            metrics["missing_required_columns"] = [
                column for column in required if column not in metrics["header"]
            ]
            for _row in reader:
                metrics["row_count"] += 1
    except Exception as exc:
        metrics["read_error"] = f"csv_read_error:{type(exc).__name__}"
    return metrics


def _resolve_web_user_data_root() -> Path:
    candidates = (
        REPO_ROOT / "web_user_data",
        REPO_ROOT.parent / "web_user_data",
        Path("/app") / "web_user_data",
        Path("/workspaces") / "Tao_Financial_Engine" / "web_user_data",
    )
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate
    return candidates[0]


def _optional_web_user_data_metrics() -> Dict[str, Any]:
    root = _resolve_web_user_data_root()
    metrics: Dict[str, Any] = {
        "path": str(root),
        "exists": root.exists(),
        "scanned_user_dirs": 0,
        "watchlist_envelopes": 0,
        "portfolio_envelopes": 0,
    }
    if not root.exists() or not root.is_dir():
        return metrics
    try:
        entries = sorted(root.iterdir())
    except Exception:
        return metrics
    for entry in entries:
        if entry.name.startswith(".") or not entry.is_dir():
            continue
        metrics["scanned_user_dirs"] += 1
        if (entry / "watchlist.ses.json").exists():
            metrics["watchlist_envelopes"] += 1
        if (entry / "portfolio_manual.ses.json").exists():
            metrics["portfolio_envelopes"] += 1
    return metrics


def _critical_input_entry(
    *,
    input_name: str,
    classification: str,
    ready: bool,
    metrics: Dict[str, Any],
    code_sources: List[str],
    issues: List[str],
    required_for_refresh: bool,
    publication_blocking_check: bool,
) -> Dict[str, Any]:
    if required_for_refresh:
        status = "ready" if ready else "not_ready"
    else:
        status = "observed_optional" if metrics.get("exists") else "missing_optional"
    return {
        "input_name": input_name,
        "classification": classification,
        "required_for_refresh": required_for_refresh,
        "publication_blocking_check": publication_blocking_check,
        "ready": bool(ready),
        "status": status,
        "code_sources": code_sources,
        "metrics": metrics,
        "issues": issues,
    }


def _probe_market_data_credentials() -> tuple[Dict[str, Any], bool]:
    keys = {
        "MASSIVE_API_KEY": bool(_to_text(os.environ.get("MASSIVE_API_KEY"))),
        "POLYGON_API_KEY": bool(_to_text(os.environ.get("POLYGON_API_KEY"))),
    }
    ready = bool(keys["MASSIVE_API_KEY"] or keys["POLYGON_API_KEY"])
    issues: List[str] = []
    if not ready:
        issues.append("missing_massive_or_polygon_api_key")
    return (
        _critical_input_entry(
            input_name="market_data_primary_credentials",
            classification="required_for_snapshot_rebuild",
            ready=ready,
            metrics={
                "env_keys_present": keys,
                "provider": "massive_primary",
            },
                code_sources=[
                "uf_mdg_snapshot.py:_fetch_history",
                "massive_market_data_service.py:MassiveMarketDataService.__init__",
            ],
            issues=issues,
            required_for_refresh=True,
            publication_blocking_check=False,
        ),
        ready,
    )


def _probe_full_universe_inputs(*, force_refresh_universe: bool, has_massive_key: bool) -> List[Dict[str, Any]]:
    inputs: List[Dict[str, Any]] = []

    for input_name, path, source_file in (
        ("stocks_universe_reference", STOCKS_UNIVERSE_PATH, "massive_universe_cache.py:fetch_massive_stock_universe"),
        ("etf_universe_reference", ETF_UNIVERSE_PATH, "massive_universe_cache_etf.py:fetch_massive_etf_universe"),
    ):
        metrics = _json_list_metrics(path)
        row_count = int(metrics.get("row_count") or 0)
        if force_refresh_universe:
            ready = bool(has_massive_key)
            readiness_basis = "force_refresh_requires_live_massive_reference_fetch"
        else:
            ready = bool(row_count > 0 or has_massive_key)
            readiness_basis = "cache_rows_present_or_live_massive_fetch_available"
        metrics["force_refresh_universe"] = bool(force_refresh_universe)
        metrics["readiness_basis"] = readiness_basis
        issues: List[str] = []
        if row_count <= 0:
            issues.append("cache_rows_missing_or_empty")
        if force_refresh_universe and not has_massive_key:
            issues.append("force_refresh_requested_but_massive_key_missing")
        if not force_refresh_universe and row_count <= 0 and not has_massive_key:
            issues.append("cache_empty_and_live_massive_fetch_unavailable")
        inputs.append(
            _critical_input_entry(
                input_name=input_name,
                classification="required_for_snapshot_rebuild",
                ready=ready,
                metrics=metrics,
                code_sources=[
                    "rebuild_uf_snapshot.py:_build_universe",
                    source_file,
                ],
                issues=issues,
                required_for_refresh=True,
                publication_blocking_check=False,
            )
        )

    for input_name, path, default_rows, source_file in (
        ("index_universe_reference", INDEX_UNIVERSE_PATH, INDEX_DEFAULT_ROWS, "massive_universe_index.py:get_index_tickers_from_universe"),
        ("crypto_universe_reference", CRYPTO_UNIVERSE_PATH, CRYPTO_DEFAULT_ROWS, "massive_universe_crypto.py:get_crypto_tickers_from_universe"),
    ):
        metrics = _json_list_metrics(path)
        row_count = int(metrics.get("row_count") or 0)
        ready = bool(row_count > 0 or default_rows > 0)
        metrics["deterministic_default_rows"] = default_rows
        metrics["readiness_basis"] = "cache_rows_present_or_module_constant_self_seed_available"
        issues: List[str] = []
        if row_count <= 0:
            issues.append("cache_rows_missing_or_empty_but_module_self_seed_available")
        inputs.append(
            _critical_input_entry(
                input_name=input_name,
                classification="required_for_snapshot_rebuild",
                ready=ready,
                metrics=metrics,
                code_sources=[
                    "rebuild_uf_snapshot.py:_build_universe",
                    source_file,
                ],
                issues=issues,
                required_for_refresh=True,
                publication_blocking_check=False,
            )
        )

    return inputs


def _probe_targeted_inputs() -> List[Dict[str, Any]]:
    inputs: List[Dict[str, Any]] = []

    present_map = {
        env_name: bool(_to_text(os.environ.get(env_name)))
        for env_name in TARGETED_SELECTOR_REQUIRED_ENV
    }
    pg_ready = all(present_map.values())
    pg_issues = [f"missing_env:{name}" for name, present in present_map.items() if not present]
    inputs.append(
        _critical_input_entry(
            input_name="targeted_selector_runtime_postgres_env",
            classification="required_for_targeted_selector",
            ready=pg_ready,
            metrics={"env_keys_present": present_map},
            code_sources=[
                "rebuild_uf_snapshot.py:_load_existing_snapshot_rows",
            ],
            issues=pg_issues,
            required_for_refresh=True,
            publication_blocking_check=False,
        )
    )

    node_path = shutil.which("node")
    node_ready = bool(node_path)
    node_issues = [] if node_ready else ["node_binary_missing"]
    inputs.append(
        _critical_input_entry(
            input_name="targeted_selector_node_runtime",
            classification="required_for_targeted_selector",
            ready=node_ready,
            metrics={"node_path": node_path},
            code_sources=[
                "rebuild_uf_snapshot.py:_load_existing_snapshot_rows",
            ],
            issues=node_issues,
            required_for_refresh=True,
            publication_blocking_check=False,
        )
    )

    selector_script_ready = TARGETED_SELECTOR_SCRIPT_PATH.exists()
    selector_script_issues = [] if selector_script_ready else ["targeted_selector_script_missing"]
    inputs.append(
        _critical_input_entry(
            input_name="targeted_selector_script",
            classification="required_for_targeted_selector",
            ready=selector_script_ready,
            metrics={"path": str(TARGETED_SELECTOR_SCRIPT_PATH), "exists": selector_script_ready},
            code_sources=[
                "rebuild_uf_snapshot.py:_load_existing_snapshot_rows",
            ],
            issues=selector_script_issues,
            required_for_refresh=True,
            publication_blocking_check=False,
        )
    )

    tenant_metrics = _optional_web_user_data_metrics()
    tenant_issues: List[str] = []
    if not tenant_metrics.get("exists"):
        tenant_issues.append("web_user_data_root_missing")
    inputs.append(
        _critical_input_entry(
            input_name="tenant_linked_envelope_root",
            classification="optional_targeted_bootstrap",
            ready=bool(tenant_metrics.get("exists")),
            metrics=tenant_metrics,
            code_sources=[
                "rebuild_uf_snapshot.py:_load_tenant_linked_symbols",
            ],
            issues=tenant_issues,
            required_for_refresh=False,
            publication_blocking_check=False,
        )
    )

    return inputs


def _probe_structural_recency_bootstrap_inputs() -> List[Dict[str, Any]]:
    inputs: List[Dict[str, Any]] = []
    for input_name, path, kind, extra in (
        ("structural_recency_trace_bootstrap", TRACE_BOOTSTRAP_PATH, "csv", {"required_columns": ["symbol", "decision_timestamp"]}),
        ("structural_recency_active_snapshot_bootstrap", ACTIVE_SNAPSHOT_PATH, "snapshot_json", {}),
        ("structural_recency_backup_snapshot_bootstrap", ACTIVE_SNAPSHOT_BACKUP_PATH, "snapshot_json", {}),
    ):
        if kind == "csv":
            metrics = _csv_metrics(path, required_columns=extra.get("required_columns") or [])
            ready = bool(metrics.get("exists"))
            issues: List[str] = []
            if metrics.get("missing_required_columns"):
                issues.append(
                    "missing_required_columns:" + ",".join(str(value) for value in metrics["missing_required_columns"])
                )
            if metrics.get("read_error"):
                issues.append(str(metrics["read_error"]))
        else:
            metrics = _json_list_metrics(path)
            ready = bool(metrics.get("exists"))
            issues = []
            if metrics.get("read_error"):
                issues.append(str(metrics["read_error"]))
        inputs.append(
            _critical_input_entry(
                input_name=input_name,
                classification="optional_structural_recency_bootstrap",
                ready=ready,
                metrics=metrics,
                code_sources=[
                    "structural_recency_snapshot.py:_resolve_prior_seed",
                ],
                issues=issues,
                required_for_refresh=False,
                publication_blocking_check=False,
            )
        )
    return inputs


def _summarize_inputs(inputs: List[Dict[str, Any]]) -> Dict[str, Any]:
    critical_inputs = [entry for entry in inputs if bool(entry.get("required_for_refresh"))]
    optional_inputs = [entry for entry in inputs if not bool(entry.get("required_for_refresh"))]
    critical_ready = sum(1 for entry in critical_inputs if bool(entry.get("ready")))
    optional_present = sum(1 for entry in optional_inputs if bool((entry.get("metrics") or {}).get("exists")))
    return {
        "critical_inputs_total": len(critical_inputs),
        "critical_inputs_ready": critical_ready,
        "critical_inputs_not_ready": len(critical_inputs) - critical_ready,
        "critical_inputs_ready_rate": (
            round(float(critical_ready) / float(len(critical_inputs)), 6) if critical_inputs else 1.0
        ),
        "optional_inputs_total": len(optional_inputs),
        "optional_inputs_present": optional_present,
        "optional_inputs_missing": len(optional_inputs) - optional_present,
    }


def build_summary(
    *,
    run_id: str,
    run_id_source: str,
    refresh_mode: str,
    force_refresh_universe: bool,
) -> Dict[str, Any]:
    _load_env_candidates()

    inputs: List[Dict[str, Any]] = []
    market_data_entry, has_massive_key = _probe_market_data_credentials()
    inputs.append(market_data_entry)

    if refresh_mode == REFRESH_MODE_FULL:
        inputs.extend(
            _probe_full_universe_inputs(
                force_refresh_universe=force_refresh_universe,
                has_massive_key=has_massive_key,
            )
        )
    else:
        inputs.extend(_probe_targeted_inputs())

    inputs.extend(_probe_structural_recency_bootstrap_inputs())

    summary_metrics = _summarize_inputs(inputs)
    readiness_status = "ready" if summary_metrics["critical_inputs_not_ready"] == 0 else "missing_required_inputs"

    return {
        "generated_at_utc": utc_now(),
        "run_id": run_id,
        "run_id_source": run_id_source,
        "refresh_mode": refresh_mode,
        "force_refresh_universe": bool(force_refresh_universe),
        "probe_status": "ok",
        "input_readiness_status": readiness_status,
        "publication_blocking": False,
        "blocking_policy": {
            "default_classification": "non_critical",
            "rule": "pre_ingestion_completeness_check_must_not_block_publication_without_explicit_spec_change",
        },
        "summary_metrics": summary_metrics,
        "inputs": inputs,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Record pre-ingestion completeness metrics for one refresh run.")
    parser.add_argument("--run-id", default="")
    parser.add_argument(
        "--refresh-mode",
        choices=[REFRESH_MODE_FULL, REFRESH_MODE_TARGETED],
        default=REFRESH_MODE_FULL,
    )
    parser.add_argument("--force-refresh-universe", action="store_true")
    parser.add_argument("--out-dir", default=str(RUNTIME_BACKUPS))
    args = parser.parse_args()

    run_id, run_id_source = _resolve_run_id(_to_text(args.run_id))
    summary = build_summary(
        run_id=run_id,
        run_id_source=run_id_source,
        refresh_mode=str(args.refresh_mode),
        force_refresh_universe=bool(args.force_refresh_universe),
    )

    output_dir = Path(args.out_dir) / (
        f"pre-ingestion-completeness-{timestamp_token()}-{_sanitize_run_id_for_path(run_id)}"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(str(summary_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
