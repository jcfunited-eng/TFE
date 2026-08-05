#!/usr/bin/env python3
"""
L0 Phase-1 DB sync: ingest seed/universe artifacts into Postgres.

Artifacts:
- sp500.csv -> l0_universe_seed_symbols
- massive_universe_stocks.json -> l0_universe_symbols (asset_type=stocks)
- massive_universe_etf.json -> l0_universe_symbols (asset_type=etf)
- massive_universe_index.json -> l0_universe_symbols (asset_type=index)
- massive_universe_crypto.json -> l0_universe_symbols (asset_type=crypto)
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKUPS_RUNTIME_DIR = REPO_ROOT / "backups" / "runtime"

DEFAULT_SP500 = REPO_ROOT / "sp500.csv"
DEFAULT_STOCKS = REPO_ROOT / "massive_universe_stocks.json"
DEFAULT_ETF = REPO_ROOT / "massive_universe_etf.json"
DEFAULT_INDEX = REPO_ROOT / "massive_universe_index.json"
DEFAULT_CRYPTO = REPO_ROOT / "massive_universe_crypto.json"

REQUIRED_PG_ENV = (
    "PGHOST",
    "PGDATABASE",
    "PGUSER",
    "PGPASSWORD",
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _json_compact(payload: Any) -> str:
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=True)


def _sql_literal(text: str) -> str:
    return "'" + str(text).replace("'", "''") + "'"


def _run_psql(*, sql: str | None = None, stdin_text: str | None = None, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    cmd = ["psql", "-X", "-v", "ON_ERROR_STOP=1", "-qAt"]
    if sql is not None:
        cmd.extend(["-c", sql])
    return subprocess.run(
        cmd,
        input=stdin_text,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
        env=os.environ.copy(),
    )


def _require_preflight() -> Dict[str, Any]:
    missing = [k for k in REQUIRED_PG_ENV if not str(os.environ.get(k, "")).strip()]
    psql_path = shutil.which("psql")
    if not psql_path:
        raise RuntimeError("psql_not_found")
    if missing:
        raise RuntimeError(f"missing_pg_env:{','.join(missing)}")

    probe = _run_psql(sql="SELECT 1;", timeout=30)
    if probe.returncode != 0:
        raise RuntimeError((probe.stderr or probe.stdout or "psql_connect_failed").strip())

    return {"ok": True, "psql_path": psql_path, "missing_env": []}


def _ensure_l0_tables() -> None:
    ddl = """
    CREATE TABLE IF NOT EXISTS l0_universe_seed_symbols (
      seed_id BIGSERIAL PRIMARY KEY,
      symbol TEXT NOT NULL UNIQUE,
      source_path TEXT NOT NULL,
      ingested_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      active BOOLEAN NOT NULL DEFAULT TRUE
    );

    CREATE INDEX IF NOT EXISTS idx_l0_universe_seed_symbols_active
      ON l0_universe_seed_symbols(active);

    CREATE TABLE IF NOT EXISTS l0_universe_symbols (
      symbol TEXT NOT NULL,
      asset_type TEXT NOT NULL,
      source_path TEXT NOT NULL,
      source_hash TEXT NOT NULL,
      ingested_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      meta_json JSONB NOT NULL,
      PRIMARY KEY (symbol, asset_type)
    );

    CREATE INDEX IF NOT EXISTS idx_l0_universe_symbols_asset_type
      ON l0_universe_symbols(asset_type);
    """
    res = _run_psql(sql=ddl, timeout=120)
    if res.returncode != 0:
        raise RuntimeError((res.stderr or res.stdout or "l0_table_ensure_failed").strip())


def _read_sp500_symbols(path: Path) -> List[str]:
    if not path.exists():
        raise FileNotFoundError(f"sp500_missing:{path}")
    symbols: List[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        symbol = str(line or "").strip().upper()
        if not symbol:
            continue
        symbols.append(symbol)
    # Deduplicate, stable order.
    seen = set()
    out: List[str] = []
    for symbol in symbols:
        if symbol in seen:
            continue
        seen.add(symbol)
        out.append(symbol)
    return out


def _load_json_array(path: Path) -> List[Any]:
    if not path.exists():
        raise FileNotFoundError(f"universe_artifact_missing:{path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise RuntimeError(f"universe_artifact_invalid_payload:{path}")
    return payload


def _extract_symbol_and_meta(entry: Any) -> Optional[Tuple[str, Dict[str, Any]]]:
    if isinstance(entry, str):
        symbol = entry.strip().upper()
        if not symbol:
            return None
        return symbol, {"symbol": symbol}
    if isinstance(entry, dict):
        raw = entry.get("ticker")
        if not raw:
            raw = entry.get("symbol")
        symbol = str(raw or "").strip().upper()
        if not symbol:
            return None
        meta = dict(entry)
        meta["symbol"] = symbol
        return symbol, meta
    return None


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sync_seed_symbols(*, path: Path, tmp_dir: Path) -> Dict[str, Any]:
    symbols = _read_sp500_symbols(path)
    stage_file = tmp_dir / "l0_seed_symbols_stage.tsv"
    with stage_file.open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out, delimiter="\t", quotechar='"', lineterminator="\n")
        for symbol in symbols:
            writer.writerow([symbol, str(path), "true"])

    script = f"""
BEGIN;
CREATE TEMP TABLE _l0_seed_stage (
  symbol TEXT,
  source_path TEXT,
  active BOOLEAN
) ON COMMIT DROP;
\\copy _l0_seed_stage FROM '{str(stage_file).replace("'", "''")}' WITH (FORMAT csv, DELIMITER E'\\t', QUOTE '"');
INSERT INTO l0_universe_seed_symbols (
  symbol,
  source_path,
  ingested_at_utc,
  active
)
SELECT
  UPPER(TRIM(symbol)),
  source_path,
  NOW(),
  COALESCE(active, TRUE)
FROM _l0_seed_stage
WHERE TRIM(symbol) <> ''
ON CONFLICT (symbol) DO UPDATE SET
  source_path = EXCLUDED.source_path,
  ingested_at_utc = NOW(),
  active = EXCLUDED.active;
COMMIT;
"""
    res = _run_psql(stdin_text=script, timeout=300)
    if res.returncode != 0:
        raise RuntimeError((res.stderr or res.stdout or "seed_symbols_upsert_failed").strip())

    count_res = _run_psql(sql="SELECT COUNT(*)::text FROM l0_universe_seed_symbols;", timeout=60)
    if count_res.returncode != 0:
        raise RuntimeError((count_res.stderr or count_res.stdout or "seed_symbols_count_failed").strip())

    return {
        "source_path": str(path),
        "input_symbols": int(len(symbols)),
        "table_count": int((count_res.stdout or "0").strip() or "0"),
    }


def _build_universe_rows(asset_type: str, path: Path) -> List[Tuple[str, str, str, str, str]]:
    raw_items = _load_json_array(path)
    rows: List[Tuple[str, str, str, str, str]] = []
    seen = set()
    for item in raw_items:
        parsed = _extract_symbol_and_meta(item)
        if parsed is None:
            continue
        symbol, meta = parsed
        key = (symbol, asset_type)
        if key in seen:
            continue
        seen.add(key)
        meta_json = _json_compact(meta)
        source_hash = _sha256_text(f"{asset_type}|{symbol}|{meta_json}")
        rows.append((symbol, asset_type, str(path), source_hash, meta_json))
    return rows


def _sync_universe_symbols(*, asset_inputs: Dict[str, Path], tmp_dir: Path) -> Dict[str, Any]:
    stage_file = tmp_dir / "l0_universe_symbols_stage.tsv"
    total_input_rows = 0
    per_asset_input_rows: Dict[str, int] = {}

    with stage_file.open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out, delimiter="\t", quotechar='"', lineterminator="\n")
        for asset_type, path in asset_inputs.items():
            rows = _build_universe_rows(asset_type, path)
            per_asset_input_rows[asset_type] = int(len(rows))
            total_input_rows += int(len(rows))
            for symbol, a_type, source_path, source_hash, meta_json in rows:
                writer.writerow([symbol, a_type, source_path, source_hash, meta_json])

    script = f"""
BEGIN;
CREATE TEMP TABLE _l0_universe_stage (
  symbol TEXT,
  asset_type TEXT,
  source_path TEXT,
  source_hash TEXT,
  meta_json TEXT
) ON COMMIT DROP;
\\copy _l0_universe_stage FROM '{str(stage_file).replace("'", "''")}' WITH (FORMAT csv, DELIMITER E'\\t', QUOTE '"');
INSERT INTO l0_universe_symbols (
  symbol,
  asset_type,
  source_path,
  source_hash,
  ingested_at_utc,
  meta_json
)
SELECT
  UPPER(TRIM(symbol)),
  LOWER(TRIM(asset_type)),
  source_path,
  source_hash,
  NOW(),
  meta_json::jsonb
FROM _l0_universe_stage
WHERE TRIM(symbol) <> '' AND TRIM(asset_type) <> ''
ON CONFLICT (symbol, asset_type) DO UPDATE SET
  source_path = EXCLUDED.source_path,
  source_hash = EXCLUDED.source_hash,
  ingested_at_utc = NOW(),
  meta_json = EXCLUDED.meta_json;
COMMIT;
"""
    res = _run_psql(stdin_text=script, timeout=600)
    if res.returncode != 0:
        raise RuntimeError((res.stderr or res.stdout or "universe_symbols_upsert_failed").strip())

    counts_res = _run_psql(
        sql="SELECT asset_type || E'\\t' || COUNT(*)::text FROM l0_universe_symbols GROUP BY asset_type ORDER BY asset_type;",
        timeout=60,
    )
    if counts_res.returncode != 0:
        raise RuntimeError((counts_res.stderr or counts_res.stdout or "universe_symbols_count_failed").strip())

    table_counts_by_asset: Dict[str, int] = {}
    for line in (counts_res.stdout or "").splitlines():
        parts = line.split("\t")
        if len(parts) != 2:
            continue
        table_counts_by_asset[parts[0]] = int(parts[1])

    total_res = _run_psql(sql="SELECT COUNT(*)::text FROM l0_universe_symbols;", timeout=60)
    if total_res.returncode != 0:
        raise RuntimeError((total_res.stderr or total_res.stdout or "universe_symbols_total_count_failed").strip())

    return {
        "input_rows_total": int(total_input_rows),
        "input_rows_by_asset": per_asset_input_rows,
        "table_rows_total": int((total_res.stdout or "0").strip() or "0"),
        "table_rows_by_asset": table_counts_by_asset,
        "source_paths": {k: str(v) for k, v in asset_inputs.items()},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync L0 seed/universe artifacts into Postgres.")
    parser.add_argument("--sp500", default=str(DEFAULT_SP500))
    parser.add_argument("--stocks-json", default=str(DEFAULT_STOCKS))
    parser.add_argument("--etf-json", default=str(DEFAULT_ETF))
    parser.add_argument("--index-json", default=str(DEFAULT_INDEX))
    parser.add_argument("--crypto-json", default=str(DEFAULT_CRYPTO))
    parser.add_argument("--output-dir", default="")
    args = parser.parse_args()

    sp500_path = Path(str(args.sp500)).resolve()
    stocks_path = Path(str(args.stocks_json)).resolve()
    etf_path = Path(str(args.etf_json)).resolve()
    index_path = Path(str(args.index_json)).resolve()
    crypto_path = Path(str(args.crypto_json)).resolve()

    out_dir = Path(str(args.output_dir)).resolve() if str(args.output_dir).strip() else BACKUPS_RUNTIME_DIR / f"l0-db-native-universe-sync-{_stamp()}"
    out_dir.mkdir(parents=True, exist_ok=True)

    summary: Dict[str, Any] = {
        "generated_at_utc": _utc_now_iso(),
        "status": "fail",
        "preflight": None,
        "tables": [],
        "seed_symbols": None,
        "universe_symbols": None,
        "errors": [],
        "output_dir": str(out_dir),
    }

    try:
        summary["preflight"] = _require_preflight()
        _ensure_l0_tables()
        summary["tables"] = [
            "l0_universe_seed_symbols",
            "l0_universe_symbols",
        ]

        with tempfile.TemporaryDirectory(prefix="l0-phase1-sync-") as tmp:
            tmp_dir = Path(tmp)
            summary["seed_symbols"] = _sync_seed_symbols(path=sp500_path, tmp_dir=tmp_dir)
            summary["universe_symbols"] = _sync_universe_symbols(
                asset_inputs={
                    "stocks": stocks_path,
                    "etf": etf_path,
                    "index": index_path,
                    "crypto": crypto_path,
                },
                tmp_dir=tmp_dir,
            )
        summary["status"] = "pass"
    except Exception as exc:
        summary["status"] = "fail"
        summary["errors"].append(f"{type(exc).__name__}: {exc}")

    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
