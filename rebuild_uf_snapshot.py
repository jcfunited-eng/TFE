"""
rebuild_uf_snapshot.py

Unified rebuild tool for UF snapshot generation.

Production behavior:
- Full refresh mode:
    - Fetches universe components (stocks, ETFs, indexes, crypto)
    - Runs UF evaluation for all symbols
- Targeted PFSC mode:
    - Uses latest UF structural snapshot rows as selector source
    - Includes symbol when:
        regime != STABLE OR bar_count < 514 OR symbol is tenant-linked
    - Tenant-linked symbols are loaded from SES-protected user watchlists/portfolios
      plus optional admin-tracked symbols from TFE_ADMIN_TRACKED_SYMBOLS.

Writes:
- uf_snapshot.ses.json (SES-Core envelope for web-path reads)
- uf_snapshot_old_backup.ses.json (previous snapshot envelope backup)
- uf_snapshot_rebuild_report.json (diagnostic report)

Important ingestion rules:
- Stock universe is filtered upstream to CS/ADRC/PFD.
- ETF universe is discovered from Massive instrument type metadata (type == ETF).
- Symbol case is preserved to avoid collisions (example: BCPC vs BCpC).
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import signal
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from aws_root_key_provider import AwsSecretsRootKeyProvider
from massive_universe_cache import get_stock_tickers_from_universe
from massive_universe_cache_etf import get_etf_tickers_from_universe
from massive_universe_index import get_index_tickers_from_universe
from massive_universe_crypto import get_crypto_tickers_from_universe
from ses_core import Envelope
from tfe_ses_core_adapter import (
    TenantIdentity,
    decrypt_blob,
    encrypt_blob,
    initialize_ses_core_for_env,
    make_domain,
    record_custody_event,
)
from uf_mdg_snapshot import evaluate_symbol_snapshot, load_recent_daily_bar_metrics


STRUCTURAL_CACHE_PATH = "uf_structural_cache.json"
SNAPSHOT_ENVELOPE_PATH = "uf_snapshot.ses.json"
SNAPSHOT_ENVELOPE_BACKUP_PATH = "uf_snapshot_old_backup.ses.json"
SNAPSHOT_JSON_FALLBACK_PATH = "uf_snapshot.json"
REBUILD_REPORT_PATH = "uf_snapshot_rebuild_report.json"

PRIVATE_FILE_MODE = 0o600
SES_PURPOSE_PREFIX = "tfe-web"
SES_PURPOSE_SUFFIX = "uf-snapshot"
SES_ACTOR_ID = "web-snapshot-pipeline"
SES_ASSET_ID = "uf_snapshot:web"
TENANT_ID = "tenant-tao"
TENANT_DISPLAY_NAME = "Tao Tenant"

REFRESH_MODE_FULL = "full_universe"
REFRESH_MODE_TARGETED = "targeted_pfsc"

ACCUMULATE_MIN_BARS = 514
WEB_USER_DATA_ROOT = "web_user_data"
REQUIRED_DB_ENV_ALIASES = (
    ("PGHOST", "TFE_DB_HOST"),
    ("PGDATABASE", "TFE_DB_NAME"),
    ("PGUSER", "TFE_DB_USER"),
    ("PGPASSWORD", "TFE_DB_PASSWORD"),
)

REQUIRED_KEYS = (
    "ticker",
    "asset_type",
    "price",
    "regime",
    "S_UF",
    "R_UF",
    "stability_score",
    "max_dd",
    "decision_vector",
)


def _write_private_text(path: str, text: str) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, PRIVATE_FILE_MODE)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    try:
        os.chmod(path, PRIVATE_FILE_MODE)
    except Exception:
        # Best-effort on restricted filesystems.
        pass


def _write_private_json(path: str, payload: Any) -> None:
    _write_private_text(path, json.dumps(payload, indent=2))


def _load_existing_structural_cache() -> Dict[str, Any]:
    if not os.path.exists(STRUCTURAL_CACHE_PATH):
        return {}

    try:
        with open(STRUCTURAL_CACHE_PATH, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        return loaded if isinstance(loaded, dict) else {}
    except Exception:
        return {}


def _save_structural_cache(cache: Dict[str, Any]) -> None:
    try:
        _write_private_json(STRUCTURAL_CACHE_PATH, cache)
    except Exception:
        # Non-critical cache path.
        pass


def _backup_old_snapshot_envelope() -> None:
    if not os.path.exists(SNAPSHOT_ENVELOPE_PATH):
        return

    try:
        shutil.copyfile(SNAPSHOT_ENVELOPE_PATH, SNAPSHOT_ENVELOPE_BACKUP_PATH)
        try:
            os.chmod(SNAPSHOT_ENVELOPE_BACKUP_PATH, PRIVATE_FILE_MODE)
        except Exception:
            pass
    except Exception as exc:
        print(
            "[UF-SNAPSHOT] WARNING: Failed to update snapshot backup envelope "
            f"{SNAPSHOT_ENVELOPE_BACKUP_PATH}: {type(exc).__name__}: {exc}"
        )


def _save_snapshot_envelope(rows: List[Dict[str, Any]], generated_at_utc: str) -> None:
    # Keep snapshot-envelope write key-path identical to web decrypt key-path.
    # In AWS mode this must use AwsSecretsRootKeyProvider via _init_web_ses_context().
    ctx, tenant = _init_web_ses_context()

    domain = make_domain(
        ctx=ctx,
        purpose_suffix=SES_PURPOSE_SUFFIX,
        version="v1",
    )

    payload = {
        "rows": rows,
        "generated_at_utc": generated_at_utc,
    }

    envelope = encrypt_blob(
        ctx=ctx,
        tenant=tenant,
        domain=domain,
        payload=payload,
        actor_id=SES_ACTOR_ID,
    )
    tmp_path = f"{SNAPSHOT_ENVELOPE_PATH}.tmp"

    try:
        _write_private_text(tmp_path, envelope.to_json())
        os.replace(tmp_path, SNAPSHOT_ENVELOPE_PATH)
        try:
            os.chmod(SNAPSHOT_ENVELOPE_PATH, PRIVATE_FILE_MODE)
        except Exception:
            pass
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    record_custody_event(
        ctx=ctx,
        tenant_id=tenant.tenant_id,
        actor_id=SES_ACTOR_ID,
        asset_id=SES_ASSET_ID,
        action="tfe.web.snapshot.encrypt",
        payload={
            "purpose": domain.purpose,
            "version": domain.version,
            "rows": len(rows),
            "envelope_path": SNAPSHOT_ENVELOPE_PATH,
        },
    )


def _save_snapshot_json_fallback(rows: List[Dict[str, Any]], generated_at_utc: str) -> None:
    payload = {
        "rows": rows,
        "generated_at_utc": generated_at_utc,
    }
    _write_private_json(SNAPSHOT_JSON_FALLBACK_PATH, payload)


def _save_rebuild_report(report: Dict[str, Any]) -> None:
    _write_private_json(REBUILD_REPORT_PATH, report)


def _run_pre_ingestion_completeness_check(
    *,
    refresh_mode: str,
    force_refresh_universe: bool,
) -> Dict[str, Any]:
    script_path = os.path.join("web", "scripts", "pre_ingestion_completeness_check.py")
    if not os.path.exists(script_path):
        return {
            "status": "script_missing",
            "publication_blocking": False,
            "error": f"missing_script:{script_path}",
        }

    python_bin = str(os.environ.get("TFE_PYTHON_BIN", "")).strip() or shutil.which("python3") or "python3"
    cmd = [
        python_bin,
        script_path,
        "--refresh-mode",
        refresh_mode,
    ]

    run_id = str(os.environ.get("TFE_REFRESH_RUN_ID", "")).strip()
    if run_id:
        cmd.extend(["--run-id", run_id])
    if force_refresh_universe:
        cmd.append("--force-refresh-universe")

    try:
        completed = subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            check=False,
            timeout=120,
            env=os.environ.copy(),
        )
    except Exception as exc:
        return {
            "status": "probe_error",
            "publication_blocking": False,
            "error": f"{type(exc).__name__}: {exc}",
        }

    stdout_lines = [line.strip() for line in str(completed.stdout or "").splitlines() if line.strip()]
    stderr_lines = [line.strip() for line in str(completed.stderr or "").splitlines() if line.strip()]
    summary_path = stdout_lines[-1] if stdout_lines else ""

    probe_summary: Dict[str, Any] = {}
    if summary_path and os.path.exists(summary_path):
        try:
            with open(summary_path, "r", encoding="utf-8") as handle:
                loaded = json.load(handle)
            if isinstance(loaded, dict):
                probe_summary = loaded
        except Exception:
            probe_summary = {}

    if completed.returncode != 0:
        return {
            "status": "probe_failed",
            "publication_blocking": False,
            "exit_code": completed.returncode,
            "summary_path": summary_path or None,
            "stdout_tail": "\n".join(stdout_lines[-20:]) if stdout_lines else "",
            "stderr_tail": "\n".join(stderr_lines[-20:]) if stderr_lines else "",
            "input_readiness_status": probe_summary.get("input_readiness_status"),
        }

    return {
        "status": "ok",
        "publication_blocking": False,
        "summary_path": summary_path or None,
        "input_readiness_status": probe_summary.get("input_readiness_status"),
        "critical_inputs_not_ready": ((probe_summary.get("summary_metrics") or {}).get("critical_inputs_not_ready")),
        "critical_inputs_ready": ((probe_summary.get("summary_metrics") or {}).get("critical_inputs_ready")),
        "probe_run_id": probe_summary.get("run_id"),
    }


def _normalize_symbol(symbol: Any) -> str:
    return str(symbol).strip()


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        n = int(value)
        return n
    except Exception:
        return default


class _SnapshotSymbolTimeout(TimeoutError):
    pass


def _snapshot_symbol_timeout_handler(signum: int, frame: Any) -> None:
    raise _SnapshotSymbolTimeout("snapshot symbol evaluation timed out")


def _sanitize_username_for_path(username: str) -> str:
    value = str(username or "").strip().lower()
    value = re.sub(r"[^a-z0-9._-]", "_", value)
    return value or "unknown_user"


def _resolve_web_user_data_root() -> str:
    cwd = os.getcwd()
    candidates = [
        os.path.join(cwd, WEB_USER_DATA_ROOT),
        os.path.join(cwd, "..", WEB_USER_DATA_ROOT),
        os.path.join("/app", WEB_USER_DATA_ROOT),
        os.path.join("/workspaces", "Tao_Financial_Engine", WEB_USER_DATA_ROOT),
    ]

    for candidate in candidates:
        if os.path.isdir(candidate):
            return candidate

    return candidates[0]


def _build_universe(force_refresh_universe: bool) -> Tuple[List[Dict[str, str]], Dict[str, int]]:
    stocks: List[str]
    etfs: List[str]
    indexes: List[str]
    crypto: List[str]

    try:
        stocks = get_stock_tickers_from_universe(force_refresh=force_refresh_universe)
    except Exception as exc:
        print(f"[UF-SNAPSHOT] WARNING: Failed to fetch stock universe: {exc}")
        stocks = []

    try:
        etfs = get_etf_tickers_from_universe(force_refresh=force_refresh_universe)
    except Exception as exc:
        print(f"[UF-SNAPSHOT] WARNING: Failed to fetch etf universe: {exc}")
        etfs = []

    try:
        indexes = get_index_tickers_from_universe(force_refresh=force_refresh_universe)
    except Exception as exc:
        print(f"[UF-SNAPSHOT] WARNING: Failed to fetch index universe: {exc}")
        indexes = []

    try:
        crypto = get_crypto_tickers_from_universe(force_refresh=force_refresh_universe)
    except Exception as exc:
        print(f"[UF-SNAPSHOT] WARNING: Failed to fetch crypto universe: {exc}")
        crypto = []

    items: List[Dict[str, str]] = []
    seen: Set[str] = set()

    def add_symbols(symbols: List[str], asset_type: str) -> None:
        for raw_symbol in symbols:
            symbol = _normalize_symbol(raw_symbol)
            if not symbol:
                continue
            if symbol in seen:
                continue
            seen.add(symbol)
            items.append({"symbol": symbol, "asset_type": asset_type})

    # Priority is explicit and deterministic.
    add_symbols(stocks, "stock")
    add_symbols(etfs, "etf")
    add_symbols(indexes, "index")
    add_symbols(crypto, "crypto")

    counts = {
        "stocks": len(stocks),
        "etfs": len(etfs),
        "indexes": len(indexes),
        "crypto": len(crypto),
        "universe_unique": len(items),
    }
    return items, counts


def _init_web_ses_context() -> Tuple[Any, TenantIdentity]:
    environment = str(os.environ.get("TFE_ENV", "dev"))
    region = str(os.environ.get("TFE_REGION", os.environ.get("AWS_REGION", "local")))

    root_key_provider = None
    if environment.strip().lower() == "aws":
        root_key_provider = AwsSecretsRootKeyProvider.from_env()

    ctx = initialize_ses_core_for_env(
        environment=environment,
        region=region,
        purpose_prefix=SES_PURPOSE_PREFIX,
        root_key_provider=root_key_provider,
    )

    tenant = TenantIdentity(
        tenant_id=TENANT_ID,
        display_name=TENANT_DISPLAY_NAME,
        environment=environment,
        attributes={},
    )

    return ctx, tenant


def _unwrap_web_payload(payload: Any) -> Any:
    if isinstance(payload, dict) and "value" in payload:
        return payload.get("value")
    return payload


def _decrypt_user_envelope(
    ctx: Any,
    tenant: TenantIdentity,
    envelope_path: str,
    purpose_suffixes: List[str],
    actor_id: str,
) -> Any:
    with open(envelope_path, "r", encoding="utf-8") as f:
        envelope_raw = f.read()

    envelope = Envelope.from_json(envelope_raw)

    last_error: Optional[str] = None
    for suffix in purpose_suffixes:
        try:
            domain = make_domain(ctx=ctx, purpose_suffix=suffix, version="v1")
            payload = decrypt_blob(
                ctx=ctx,
                tenant=tenant,
                domain=domain,
                envelope=envelope,
                actor_id=actor_id,
            )
            return _unwrap_web_payload(payload)
        except Exception as exc:
            last_error = f"purpose={suffix}: {type(exc).__name__}: {exc}"

    raise RuntimeError(last_error or "decrypt_failed")


def _load_existing_snapshot_rows() -> List[Dict[str, Any]]:
    missing_env: List[str] = []
    for primary_name, alias_name in REQUIRED_DB_ENV_ALIASES:
        primary_value = str(os.environ.get(primary_name, "")).strip()
        alias_value = str(os.environ.get(alias_name, "")).strip()
        if primary_value or alias_value:
            continue
        missing_env.append(f"{primary_name}|{alias_name}")
    if missing_env:
        raise RuntimeError(
            "targeted_selector_runtime_postgres_env_missing:"
            + ",".join(missing_env)
        )

    node_bin = shutil.which("node")
    if node_bin is None:
        raise RuntimeError("targeted_selector_node_missing")

    selector_script = os.path.join(
        os.getcwd(),
        "web",
        "scripts",
        "read_runtime_selector_rows.mjs",
    )
    if not os.path.exists(selector_script):
        raise RuntimeError(f"targeted_selector_script_missing:{selector_script}")

    try:
        completed = subprocess.run(
            [node_bin, selector_script],
            text=True,
            capture_output=True,
            check=False,
            timeout=90,
            env=os.environ.copy(),
        )
    except Exception as exc:
        raise RuntimeError(
            "targeted_selector_runtime_query_failed:"
            f"{type(exc).__name__}:{exc}"
        ) from exc

    stdout = str(completed.stdout or "").strip()
    stderr = str(completed.stderr or "").strip()
    payload_raw = stdout or stderr
    try:
        payload = json.loads(payload_raw) if payload_raw else {}
    except Exception:
        payload = {"ok": False, "reason": payload_raw or "selector_payload_parse_failed"}

    if completed.returncode != 0:
        reason = str(payload.get("reason") or stderr or stdout or "targeted_selector_non_zero_exit")
        raise RuntimeError(reason)

    rows_raw = payload.get("rows", [])
    if not isinstance(rows_raw, list):
        raise RuntimeError("targeted_selector_rows_missing")

    rows = [row for row in rows_raw if isinstance(row, dict)]
    if not rows:
        raise RuntimeError("targeted_selector_rows_empty")

    source_table = str(payload.get("source_table") or "runtime_selector_rows").strip()
    print(
        "[UF-SNAPSHOT] Targeted selector runtime read: loaded "
        f"{len(rows)} rows from {source_table}."
    )
    return rows


def _index_existing_rows_by_ticker(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    indexed: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        ticker = _normalize_symbol(row.get("ticker"))
        if not ticker or ticker in indexed:
            continue
        indexed[ticker] = row
    return indexed


def _clone_previous_snapshot_row(
    previous_row: Dict[str, Any],
    *,
    symbol: str,
    asset_type: str,
    run_id: Optional[str],
    generated_at_utc: str,
) -> Dict[str, Any]:
    cloned = dict(previous_row)
    cloned["ticker"] = symbol
    cloned["asset_type"] = asset_type
    cloned["generated_at_utc"] = generated_at_utc
    if run_id:
        cloned["run_id"] = run_id
    return cloned


def _zero_delta_skip_applies(metrics: Dict[str, Any]) -> bool:
    latest_close = metrics.get("latest_close")
    previous_close = metrics.get("previous_close")
    latest_volume = metrics.get("latest_volume")
    if latest_close is None or previous_close is None or latest_volume is None:
        return False
    return float(latest_close) == float(previous_close) and float(latest_volume) == 0.0


def _zombie_fast_path_applies(previous_row: Dict[str, Any], metrics: Dict[str, Any]) -> bool:
    regime = str(previous_row.get("regime", "")).strip().upper()
    if regime != "DEGENERATE":
        return False
    traded_dollar_volume = metrics.get("latest_traded_dollar_volume")
    if traded_dollar_volume is None:
        return False
    return float(traded_dollar_volume) < 50000.0


def _resolve_skip_reuse_row(
    *,
    symbol: str,
    asset_type: str,
    previous_row: Optional[Dict[str, Any]],
    recent_metrics: Dict[str, Any],
    run_id: Optional[str],
    generated_at_utc: str,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    # Temporary clean-slate override: force fresh evaluation for every selected symbol.
    # The code path still receives the prior-row and metrics inputs, but it never reuses them.
    return None, "forced_rebuild"


def _load_admin_tracked_symbols() -> Set[str]:
    raw = str(os.environ.get("TFE_ADMIN_TRACKED_SYMBOLS", "")).strip()
    if not raw:
        return set()

    symbols: Set[str] = set()
    for token in raw.split(","):
        symbol = _normalize_symbol(token)
        if symbol:
            symbols.add(symbol)
    return symbols


def _load_tenant_linked_symbols() -> Tuple[Set[str], Dict[str, Any]]:
    summary: Dict[str, Any] = {
        "watchlist_symbols": 0,
        "portfolio_symbols": 0,
        "admin_tracked_symbols": 0,
        "scanned_user_dirs": 0,
        "decrypt_errors": [],
    }

    all_symbols: Set[str] = set()
    admin_symbols = _load_admin_tracked_symbols()
    all_symbols.update(admin_symbols)
    summary["admin_tracked_symbols"] = len(admin_symbols)

    root = _resolve_web_user_data_root()
    if not os.path.isdir(root):
        summary["root_missing"] = root
        return all_symbols, summary

    try:
        entries = sorted(os.listdir(root))
    except Exception as exc:
        summary["root_read_error"] = f"{type(exc).__name__}: {exc}"
        return all_symbols, summary

    ctx: Optional[Any] = None
    tenant: Optional[TenantIdentity] = None

    def ensure_ctx() -> Tuple[Any, TenantIdentity]:
        nonlocal ctx, tenant
        if ctx is None or tenant is None:
            ctx, tenant = _init_web_ses_context()
        return ctx, tenant

    watchlist_count = 0
    portfolio_count = 0

    for entry_name in entries:
        if entry_name.startswith("."):
            continue

        user_dir = os.path.join(root, entry_name)
        if not os.path.isdir(user_dir):
            continue

        summary["scanned_user_dirs"] += 1

        username = _sanitize_username_for_path(entry_name)
        actor_id = f"web-user:{username}"

        watchlist_path = os.path.join(user_dir, "watchlist.ses.json")
        if os.path.exists(watchlist_path):
            try:
                ses_ctx, ses_tenant = ensure_ctx()
                watchlist_payload = _decrypt_user_envelope(
                    ctx=ses_ctx,
                    tenant=ses_tenant,
                    envelope_path=watchlist_path,
                    purpose_suffixes=[f"watchlist-{username}", "watchlist"],
                    actor_id=actor_id,
                )

                if isinstance(watchlist_payload, dict):
                    symbols_raw = watchlist_payload.get("symbols", [])
                    if isinstance(symbols_raw, list):
                        for raw_symbol in symbols_raw:
                            symbol = _normalize_symbol(raw_symbol)
                            if symbol:
                                all_symbols.add(symbol)
                                watchlist_count += 1
            except Exception as exc:
                summary["decrypt_errors"].append(
                    {
                        "user": username,
                        "kind": "watchlist",
                        "path": watchlist_path,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )

        portfolio_path = os.path.join(user_dir, "portfolio_manual.ses.json")
        if os.path.exists(portfolio_path):
            try:
                ses_ctx, ses_tenant = ensure_ctx()
                portfolio_payload = _decrypt_user_envelope(
                    ctx=ses_ctx,
                    tenant=ses_tenant,
                    envelope_path=portfolio_path,
                    purpose_suffixes=[f"portfolio-manual-{username}", "portfolio-manual"],
                    actor_id=actor_id,
                )

                if isinstance(portfolio_payload, dict):
                    lots_raw = portfolio_payload.get("lots", [])
                    if isinstance(lots_raw, list):
                        for lot in lots_raw:
                            if not isinstance(lot, dict):
                                continue
                            symbol = _normalize_symbol(lot.get("ticker"))
                            if symbol:
                                all_symbols.add(symbol)
                                portfolio_count += 1
            except Exception as exc:
                summary["decrypt_errors"].append(
                    {
                        "user": username,
                        "kind": "portfolio",
                        "path": portfolio_path,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )

    summary["watchlist_symbols"] = watchlist_count
    summary["portfolio_symbols"] = portfolio_count
    summary["tenant_linked_unique"] = len(all_symbols)
    summary["decrypt_error_count"] = len(summary["decrypt_errors"])

    return all_symbols, summary


def _build_targeted_universe(existing_rows: Optional[List[Dict[str, Any]]] = None) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
    if existing_rows is None:
        existing_rows = _load_existing_snapshot_rows()

    existing_by_ticker: Dict[str, Dict[str, Any]] = {}
    for row in existing_rows:
        ticker = _normalize_symbol(row.get("ticker"))
        if not ticker:
            continue
        if ticker in existing_by_ticker:
            continue
        existing_by_ticker[ticker] = row

    structural_symbols: Set[str] = set()
    for ticker, row in existing_by_ticker.items():
        regime = str(row.get("regime", "UNKNOWN"))
        bar_count = _safe_int(row.get("bar_count"), default=0)
        if regime != "STABLE" or bar_count < ACCUMULATE_MIN_BARS:
            structural_symbols.add(ticker)

    tenant_symbols, tenant_summary = _load_tenant_linked_symbols()

    index_symbols_raw: List[str]
    crypto_symbols_raw: List[str]

    try:
        index_symbols_raw = get_index_tickers_from_universe(force_refresh=False)
    except Exception as exc:
        print(f"[UF-SNAPSHOT] WARNING: Failed to fetch index universe: {exc}")
        index_symbols_raw = []

    index_symbols = {
        _normalize_symbol(symbol)
        for symbol in index_symbols_raw
    }
    index_symbols.discard("")

    try:
        crypto_symbols_raw = get_crypto_tickers_from_universe(force_refresh=False)
    except Exception as exc:
        print(f"[UF-SNAPSHOT] WARNING: Failed to fetch crypto universe: {exc}")
        crypto_symbols_raw = []

    crypto_symbols = {
        _normalize_symbol(symbol)
        for symbol in crypto_symbols_raw
    }
    crypto_symbols.discard("")

    explicit_asset_types: Dict[str, str] = {}
    for symbol in index_symbols:
        explicit_asset_types[symbol] = "index"
    for symbol in crypto_symbols:
        explicit_asset_types[symbol] = "crypto"

    selected_symbols = set(structural_symbols)
    selected_symbols.update(tenant_symbols)
    selected_symbols.update(index_symbols)
    selected_symbols.update(crypto_symbols)

    items: List[Dict[str, str]] = []
    for symbol in sorted(selected_symbols):
        existing_row = existing_by_ticker.get(symbol)
        asset_type = "unknown"
        if existing_row is not None:
            raw_asset_type = _normalize_symbol(existing_row.get("asset_type"))
            if raw_asset_type:
                asset_type = raw_asset_type
        if asset_type == "unknown":
            asset_type = explicit_asset_types.get(symbol, "unknown")
        items.append({"symbol": symbol, "asset_type": asset_type})

    tenant_only = [symbol for symbol in selected_symbols if symbol not in existing_by_ticker]

    counts: Dict[str, Any] = {
        "selector_source_rows": len(existing_rows),
        "selector_source_unique": len(existing_by_ticker),
        "selected_structural": len(structural_symbols),
        "selected_tenant_linked": len(tenant_symbols),
        "selected_indexes": len(index_symbols),
        "selected_crypto": len(crypto_symbols),
        "selected_union": len(selected_symbols),
        "selected_tenant_only": len(tenant_only),
        "selected_tenant_only_examples": sorted(tenant_only)[:25],
        "rule": {
            "description": "Include symbol if regime != STABLE OR bar_count < 514 OR symbol is tenant-linked OR symbol is in the curated index/crypto universe.",
            "regime_condition": "regime != STABLE",
            "bar_count_condition": f"bar_count < {ACCUMULATE_MIN_BARS}",
            "tenant_condition": "watchlist OR portfolio OR admin-tracked",
            "curated_index_condition": "always include curated index universe",
            "curated_crypto_condition": "always include curated crypto universe",
        },
        "tenant_linked": tenant_summary,
    }

    return items, counts


def _row_has_required_keys(row: Dict[str, Any]) -> bool:
    return all(k in row for k in REQUIRED_KEYS)


def _build_summary(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_asset: Dict[str, int] = {}
    by_regime: Dict[str, int] = {}

    for row in rows:
        asset = str(row.get("asset_type", "unknown"))
        regime = str(row.get("regime", "UNKNOWN"))

        by_asset[asset] = by_asset.get(asset, 0) + 1
        by_regime[regime] = by_regime.get(regime, 0) + 1

    processed_rows = 0
    for row in rows:
        regime = str(row.get("regime", "UNKNOWN"))
        if regime not in ("NO_DATA", "DEGENERATE", "INSUFFICIENT_DATA"):
            processed_rows += 1

    return {
        "rows_total": len(rows),
        "rows_processed": processed_rows,
        "rows_excluded": len(rows) - processed_rows,
        "asset_type_counts": by_asset,
        "regime_counts": by_regime,
    }


def rebuild_snapshot(
    refresh_mode: str = REFRESH_MODE_FULL,
    force_refresh_universe: bool = False,
    years_history: int = 5,
) -> Dict[str, Any]:
    if refresh_mode not in (REFRESH_MODE_FULL, REFRESH_MODE_TARGETED):
        raise ValueError(f"Unsupported refresh_mode: {refresh_mode!r}")

    if refresh_mode == REFRESH_MODE_TARGETED and force_refresh_universe:
        raise ValueError("--force-refresh-universe cannot be combined with targeted PFSC mode.")

    start_ts = time.time()
    started_at = datetime.datetime.utcnow().isoformat() + "Z"

    print("[UF-SNAPSHOT] Starting unified rebuild via uf_mdg_snapshot.")
    print(f"[UF-SNAPSHOT] Refresh mode: {refresh_mode}")
    if force_refresh_universe:
        print("[UF-SNAPSHOT] Universe refresh mode: FORCE_REFRESH")
    print(f"[UF-SNAPSHOT] Years history per symbol: {years_history}")

    pre_ingestion_completeness = _run_pre_ingestion_completeness_check(
        refresh_mode=refresh_mode,
        force_refresh_universe=force_refresh_universe,
    )
    print(
        "[UF-SNAPSHOT] Pre-ingestion completeness check: "
        f"status={pre_ingestion_completeness.get('status')} "
        f"input_readiness={pre_ingestion_completeness.get('input_readiness_status')} "
        f"summary_path={pre_ingestion_completeness.get('summary_path')}",
    )

    selector_meta: Dict[str, Any] = {}
    current_run_id = str(os.environ.get("TFE_REFRESH_RUN_ID", "")).strip() or None
    generated_at_utc = datetime.datetime.utcnow().isoformat() + "Z"

    existing_runtime_rows: List[Dict[str, Any]] = []
    existing_runtime_rows_error: Optional[str] = None
    try:
        existing_runtime_rows = _load_existing_snapshot_rows()
    except Exception as exc:
        existing_runtime_rows_error = f"{type(exc).__name__}: {exc}"
        print(f"[UF-SNAPSHOT] Previous runtime row load unavailable: {existing_runtime_rows_error}")
    existing_rows_by_ticker = _index_existing_rows_by_ticker(existing_runtime_rows)

    if refresh_mode == REFRESH_MODE_TARGETED:
        universe_items, universe_counts = _build_targeted_universe(
            existing_rows=existing_runtime_rows if existing_runtime_rows else None,
        )
        selector_meta = {"targeted_selector": universe_counts}
        print(
            "[UF-SNAPSHOT] Targeted selector counts: "
            f"source={universe_counts.get('selector_source_unique', 0)} "
            f"structural={universe_counts.get('selected_structural', 0)} "
            f"tenant={universe_counts.get('selected_tenant_linked', 0)} "
            f"union={universe_counts.get('selected_union', 0)}"
        )
    else:
        universe_items, universe_counts = _build_universe(force_refresh_universe=force_refresh_universe)
        print(
            "[UF-SNAPSHOT] Universe counts: "
            f"stocks={universe_counts['stocks']} "
            f"etfs={universe_counts['etfs']} "
            f"indexes={universe_counts['indexes']} "
            f"crypto={universe_counts['crypto']} "
            f"unique={universe_counts['universe_unique']}"
        )

    structural_cache = _load_existing_structural_cache()

    snapshot_rows: List[Dict[str, Any]] = []
    skipped_rows: List[Dict[str, str]] = []
    fast_path_rows: List[Dict[str, str]] = []
    fast_path_counts = {"zero-delta": 0, "zombie": 0}
    symbol_timeout_count = 0
    symbol_timeout_seconds = max(
        0,
        _safe_int(os.environ.get("TFE_SNAPSHOT_SYMBOL_TIMEOUT_SECONDS", 120), 120),
    )
    progress_log_interval_seconds = max(
        5,
        _safe_int(os.environ.get("TFE_SNAPSHOT_PROGRESS_LOG_INTERVAL_SECONDS", 30), 30),
    )

    total = len(universe_items)
    last_progress_log_ts = time.time()
    for idx, item in enumerate(universe_items, start=1):
        symbol = item["symbol"]
        asset_type = item["asset_type"]

        now = time.time()
        if idx == 1 or idx % 200 == 0 or (now - last_progress_log_ts) >= progress_log_interval_seconds:
            print(f"[UF-SNAPSHOT] Processing {idx}/{total} symbol={symbol}...")
            last_progress_log_ts = now

        timeout_armed = False
        previous_alarm_handler = None

        try:
            recent_metrics = load_recent_daily_bar_metrics(symbol)
            reuse_row, reuse_reason = _resolve_skip_reuse_row(
                symbol=symbol,
                asset_type=asset_type,
                previous_row=existing_rows_by_ticker.get(symbol),
                recent_metrics=recent_metrics,
                run_id=current_run_id,
                generated_at_utc=generated_at_utc,
            )
            if reuse_row is not None and reuse_reason is not None:
                snapshot_rows.append(reuse_row)
                fast_path_counts[reuse_reason] += 1
                fast_path_rows.append(
                    {
                        "symbol": symbol,
                        "asset_type": asset_type,
                        "reason": reuse_reason,
                    }
                )
                print(f"[UF-SNAPSHOT] symbol={symbol} skipped ({reuse_reason})")
                continue

            if symbol_timeout_seconds > 0:
                previous_alarm_handler = signal.getsignal(signal.SIGALRM)
                signal.signal(signal.SIGALRM, _snapshot_symbol_timeout_handler)
                signal.alarm(symbol_timeout_seconds)
                timeout_armed = True
            row = evaluate_symbol_snapshot(
                symbol=symbol,
                asset_type=asset_type,
                years_history=years_history,
            )
        except _SnapshotSymbolTimeout:
            symbol_timeout_count += 1
            skipped_rows.append(
                {
                    "symbol": symbol,
                    "asset_type": asset_type,
                    "reason": f"evaluation_timeout_after_{symbol_timeout_seconds}s",
                }
            )
            print(
                f"[UF-SNAPSHOT] TIMEOUT symbol={symbol} asset_type={asset_type} "
                f"after={symbol_timeout_seconds}s; skipping."
            )
            continue
        except Exception as exc:
            skipped_rows.append(
                {
                    "symbol": symbol,
                    "asset_type": asset_type,
                    "reason": f"evaluation_error: {type(exc).__name__}: {exc}",
                }
            )
            continue
        finally:
            if timeout_armed:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, previous_alarm_handler)

        if not isinstance(row, dict):
            skipped_rows.append(
                {
                    "symbol": symbol,
                    "asset_type": asset_type,
                    "reason": "row_not_dict",
                }
            )
            continue

        # Canonical ownership of identity fields stays with rebuild pipeline.
        row["ticker"] = symbol
        row["asset_type"] = asset_type

        if not _row_has_required_keys(row):
            skipped_rows.append(
                {
                    "symbol": symbol,
                    "asset_type": asset_type,
                    "reason": "missing_required_keys",
                }
            )
            continue

        snapshot_rows.append(row)

    _save_structural_cache(structural_cache)

    if not snapshot_rows:
        print("[UF-SNAPSHOT] No rows produced; preserving old snapshot envelope if present.")

        report = {
            "generated_at_utc": datetime.datetime.utcnow().isoformat() + "Z",
            "started_at_utc": started_at,
            "elapsed_seconds": round(time.time() - start_ts, 2),
            "refresh_mode": refresh_mode,
            "force_refresh_universe": force_refresh_universe,
            "years_history": years_history,
            "universe_counts": universe_counts,
            **selector_meta,
            "rows_written": 0,
            "skipped_count": len(skipped_rows),
            "symbol_timeout_count": symbol_timeout_count,
            "symbol_timeout_seconds": symbol_timeout_seconds,
            "progress_log_interval_seconds": progress_log_interval_seconds,
            "skipped_examples": skipped_rows[:25],
            "fast_path_count": len(fast_path_rows),
            "fast_path_counts": fast_path_counts,
            "fast_path_examples": fast_path_rows[:25],
            "existing_runtime_rows_loaded": len(existing_runtime_rows),
            "existing_runtime_rows_error": existing_runtime_rows_error,
            "summary": {},
            "pre_ingestion_completeness": pre_ingestion_completeness,
            "snapshot_envelope_path": SNAPSHOT_ENVELOPE_PATH,
            "snapshot_envelope_backup_path": SNAPSHOT_ENVELOPE_BACKUP_PATH,
            "status": "no_rows_written",
        }
        _save_rebuild_report(report)
        return report

    _backup_old_snapshot_envelope()

    _save_snapshot_json_fallback(snapshot_rows, generated_at_utc=generated_at_utc)
    _save_snapshot_envelope(snapshot_rows, generated_at_utc=generated_at_utc)

    summary = _build_summary(snapshot_rows)
    report = {
        "generated_at_utc": generated_at_utc,
        "started_at_utc": started_at,
        "elapsed_seconds": round(time.time() - start_ts, 2),
        "refresh_mode": refresh_mode,
        "force_refresh_universe": force_refresh_universe,
        "years_history": years_history,
        "universe_counts": universe_counts,
        **selector_meta,
        "rows_written": len(snapshot_rows),
        "skipped_count": len(skipped_rows),
        "symbol_timeout_count": symbol_timeout_count,
        "symbol_timeout_seconds": symbol_timeout_seconds,
        "progress_log_interval_seconds": progress_log_interval_seconds,
        "skipped_examples": skipped_rows[:25],
        "fast_path_count": len(fast_path_rows),
        "fast_path_counts": fast_path_counts,
        "fast_path_examples": fast_path_rows[:25],
        "existing_runtime_rows_loaded": len(existing_runtime_rows),
        "existing_runtime_rows_error": existing_runtime_rows_error,
        "summary": summary,
        "pre_ingestion_completeness": pre_ingestion_completeness,
        "snapshot_json_fallback_path": SNAPSHOT_JSON_FALLBACK_PATH,
        "snapshot_envelope_path": SNAPSHOT_ENVELOPE_PATH,
        "snapshot_envelope_backup_path": SNAPSHOT_ENVELOPE_BACKUP_PATH,
        "status": "ok",
    }
    _save_rebuild_report(report)

    print(
        "[UF-SNAPSHOT] Rebuild complete. "
        f"rows={len(snapshot_rows)} skipped={len(skipped_rows)} "
        f"processed={summary['rows_processed']}"
    )
    print(f"[UF-SNAPSHOT] Plaintext snapshot written: {SNAPSHOT_JSON_FALLBACK_PATH}")
    print(f"[UF-SNAPSHOT] SES envelope written: {SNAPSHOT_ENVELOPE_PATH}")
    print(f"[UF-SNAPSHOT] Report written: {REBUILD_REPORT_PATH}")

    return report


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rebuild UF snapshot with latest universe + market data.")
    parser.add_argument(
        "--refresh-mode",
        choices=[REFRESH_MODE_FULL, REFRESH_MODE_TARGETED],
        default=REFRESH_MODE_FULL,
        help=f"Refresh mode (default: {REFRESH_MODE_FULL}).",
    )
    parser.add_argument(
        "--targeted-refresh",
        action="store_true",
        help="Shortcut for --refresh-mode targeted_pfsc.",
    )
    parser.add_argument(
        "--force-refresh-universe",
        action="store_true",
        help="Refresh universe caches from Massive before rebuild.",
    )
    parser.add_argument(
        "--years-history",
        type=int,
        default=5,
        help="Years of daily history to fetch per symbol (default: 5).",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    mode = str(args.refresh_mode)
    if bool(args.targeted_refresh):
        mode = REFRESH_MODE_TARGETED

    rebuild_snapshot(
        refresh_mode=mode,
        force_refresh_universe=bool(args.force_refresh_universe),
        years_history=int(args.years_history),
    )


if __name__ == "__main__":
    main()
