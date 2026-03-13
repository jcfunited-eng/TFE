#!/usr/bin/env python3
"""
L3 Phase-1 DB sync: persist resonance + regime states into Postgres.

Sources:
- l1_sev_series (SEV rows)
- l0_market_bars_daily_clean (close series for drawdown)
Transforms:
- uf_core.layer1.segment_gates + build_gate_l1_state
- uf_core.layer2.interpret_gates
- uf_core.layer3.compute_resonance
- uf_core.layer4.compute_directional_signal
- uf_core.uf_structural_engine regime/stability helpers
Targets:
- l3_resonance_results
- l3_regime_states
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd

from uf_core.layer0 import SEV
from uf_core.layer1 import build_gate_l1_state, segment_gates
from uf_core.layer2 import interpret_gates
from uf_core.layer3 import compute_resonance
from uf_core.layer4 import compute_directional_signal
from uf_core.uf_structural_engine import (
    _aggregate_gate_regime,
    _compute_stability_from_l4,
    _max_drawdown,
    _safe_pct_change,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKUPS_RUNTIME_DIR = REPO_ROOT / "backups" / "runtime"
REQUIRED_PG_ENV = ("PGHOST", "PGDATABASE", "PGUSER", "PGPASSWORD")
ALLOWED_REGIMES = ("STABLE", "TRANSITIONAL", "VOLATILE", "DEGENERATE")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _run_psql(*, sql: str | None = None, stdin_text: str | None = None, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    cmd = ["psql", "-X", "-v", "ON_ERROR_STOP=1", "-qAt", "-F", "\t"]
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


def _ensure_tables() -> None:
    ddl = (
        "CREATE TABLE IF NOT EXISTS l3_resonance_results("
        "symbol TEXT NOT NULL,gate_id TEXT NOT NULL,resonance_id TEXT NOT NULL,resonance_score DOUBLE PRECISION NOT NULL,"
        "resonance_json JSONB NOT NULL,computed_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        "PRIMARY KEY(symbol,resonance_id),"
        "FOREIGN KEY(symbol,gate_id) REFERENCES l2_gate_segments(symbol,gate_id) ON DELETE CASCADE);"
        "CREATE INDEX IF NOT EXISTS idx_l3_resonance_results_symbol_gate ON l3_resonance_results(symbol,gate_id);"
        "CREATE TABLE IF NOT EXISTS l3_regime_states("
        "symbol TEXT NOT NULL,bar_ts TIMESTAMPTZ NOT NULL,regime TEXT NOT NULL,stability_score DOUBLE PRECISION NOT NULL,"
        "max_drawdown DOUBLE PRECISION NOT NULL,regime_json JSONB NOT NULL,computed_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        "PRIMARY KEY(symbol,bar_ts));"
        "CREATE INDEX IF NOT EXISTS idx_l3_regime_states_symbol_ts ON l3_regime_states(symbol,bar_ts DESC);"
    )
    res = _run_psql(sql=ddl, timeout=120)
    if res.returncode != 0:
        raise RuntimeError((res.stderr or res.stdout or "l3_table_ensure_failed").strip())


def _resolve_symbols(limit_count: int) -> List[str]:
    q = _run_psql(sql=f"SELECT DISTINCT symbol FROM l1_sev_series ORDER BY symbol LIMIT {int(limit_count)};", timeout=30)
    if q.returncode != 0:
        raise RuntimeError((q.stderr or q.stdout or "l1_sev_symbol_query_failed").strip())
    symbols = [str(line or "").strip().upper() for line in (q.stdout or "").splitlines()]
    symbols = [s for s in symbols if s]
    if not symbols:
        raise RuntimeError("no_l1_sev_symbols")
    return symbols


def _load_sev_rows(symbol: str) -> List[Tuple[str, SEV]]:
    q = _run_psql(
        sql=(
            "SELECT bar_ts::text,sev_u::text,sev_d::text,sev_l::text,COALESCE(sev_meta_json::text,'{}') "
            f"FROM l1_sev_series WHERE symbol='{symbol}' ORDER BY bar_ts ASC;"
        ),
        timeout=90,
    )
    if q.returncode != 0:
        raise RuntimeError((q.stderr or q.stdout or f"l1_sev_query_failed:{symbol}").strip())

    out: List[Tuple[str, SEV]] = []
    for line in (q.stdout or "").splitlines():
        parts = line.split("\t")
        if len(parts) != 5:
            continue
        bar_ts, sev_u, sev_d, sev_l, meta_text = parts
        try:
            meta = json.loads(meta_text or "{}")
            out.append(
                (
                    bar_ts,
                    SEV(
                        F_norm=float(sev_u),
                        dF=float(sev_d),
                        sigma=float(sev_l),
                        kappa=float(meta.get("kappa", 0.0)),
                        relevance=float(meta.get("relevance", 1.0)),
                        N=int(meta.get("N", 0)),
                    ),
                )
            )
        except Exception:
            continue
    return out


def _load_close_series(symbol: str) -> Tuple[List[str], pd.Series]:
    q = _run_psql(
        sql=(
            "SELECT bar_ts::text,close::text "
            f"FROM l0_market_bars_daily_clean WHERE symbol='{symbol}' ORDER BY bar_ts ASC;"
        ),
        timeout=90,
    )
    if q.returncode != 0:
        raise RuntimeError((q.stderr or q.stdout or f"l0_clean_query_failed:{symbol}").strip())

    ts_values: List[str] = []
    close_values: List[float] = []
    for line in (q.stdout or "").splitlines():
        parts = line.split("\t")
        if len(parts) != 2:
            continue
        bar_ts, close_text = parts
        try:
            ts_values.append(bar_ts)
            close_values.append(float(close_text))
        except Exception:
            continue

    if not close_values:
        return [], pd.Series(dtype=float)
    return ts_values, pd.Series(close_values, dtype=float)


def _clamp01(value: float) -> float:
    return float(max(0.0, min(1.0, float(value))))


def _build_l3_rows(symbols: List[str]) -> Dict[str, Any]:
    resonance_rows: List[List[Any]] = []
    regime_rows: List[List[Any]] = []
    resonance_counts: Dict[str, int] = {}
    regime_counts: Dict[str, int] = {}
    sev_input_rows = 0

    for symbol in symbols:
        ts_sev = _load_sev_rows(symbol)
        sev_input_rows += len(ts_sev)
        if len(ts_sev) < 3:
            resonance_counts[symbol] = 0
            regime_counts[symbol] = 0
            continue

        l1_ts = [row[0] for row in ts_sev]
        sev_values = [row[1] for row in ts_sev]
        gates = segment_gates(sev_values)
        l1_state = build_gate_l1_state(sev_values, gates)
        interpretations = interpret_gates(sev_values, gates)
        resonance = compute_resonance(interpretations)

        if not gates or not resonance:
            resonance_counts[symbol] = 0
            regime_counts[symbol] = 0
            continue
        if not (len(gates) == len(l1_state) == len(interpretations) == len(resonance)):
            raise RuntimeError(f"l3_alignment_failed:{symbol}")

        r_count = 0
        for idx, gate in enumerate(gates):
            if gate.start_idx < 0 or gate.end_idx >= len(l1_ts) or gate.start_idx > gate.end_idx:
                continue
            res = resonance[idx]
            gate_id = f"{symbol}:{gate.start_idx}:{gate.end_idx}"
            resonance_id = gate_id
            resonance_json = json.dumps(
                {
                    "raw_k": float(res.raw_k),
                    "R_k": float(res.R_k),
                    "URF_k": float(res.URF_k),
                    "g_k": int(res.g_k),
                    "U_k": float(res.U_k),
                    "IAS_k": int(res.IAS_k),
                    "Hyst_k": int(res.Hyst_k),
                    "interpretation": {
                        "regime": str(res.interpretation.regime or "").upper(),
                        "S_k": float(res.interpretation.S_k),
                        "C_k": int(res.interpretation.C_k),
                    },
                },
                separators=(",", ":"),
                ensure_ascii=True,
            )
            resonance_rows.append(
                [
                    symbol,
                    gate_id,
                    resonance_id,
                    float(res.R_k),
                    resonance_json,
                ]
            )
            r_count += 1

        resonance_counts[symbol] = r_count

        close_ts, close_series = _load_close_series(symbol)
        if close_series.empty:
            regime_counts[symbol] = 0
            continue
        bar_ts = close_ts[-1]
        regime = str(_aggregate_gate_regime(interpretations) or "").strip().upper()
        decisions = compute_directional_signal(resonance)
        stab = _compute_stability_from_l4(resonance, decisions)
        max_dd = float(_max_drawdown(_safe_pct_change(close_series)))
        s_uf = _clamp01(0.5 * float(stab["dsf"]) + 0.5 * float(stab["directional"]))
        r_uf = _clamp01(float(stab["R_mean"]))
        stability_score = _clamp01(0.5 * float(stab["dsf"]) + 0.3 * float(stab["directional"]) - 2.0 * abs(max_dd))

        regime_json = json.dumps(
            {
                "S_UF": s_uf,
                "R_UF": r_uf,
                "stability_components": {
                    "dsf": float(stab["dsf"]),
                    "directional": float(stab["directional"]),
                    "hysteresis_rate": float(stab["hysteresis_rate"]),
                    "breathing_rate": float(stab["breathing_rate"]),
                    "uncertainty_rate": float(stab["uncertainty_rate"]),
                    "R_mean": float(stab["R_mean"]),
                },
            },
            separators=(",", ":"),
            ensure_ascii=True,
        )

        regime_rows.append(
            [
                symbol,
                bar_ts,
                regime,
                float(stability_score),
                float(max_dd),
                regime_json,
            ]
        )
        regime_counts[symbol] = 1

    if not resonance_rows:
        raise RuntimeError("l3_resonance_rows_empty")
    if not regime_rows:
        raise RuntimeError("l3_regime_rows_empty")

    return {
        "resonance_rows": resonance_rows,
        "regime_rows": regime_rows,
        "resonance_counts": resonance_counts,
        "regime_counts": regime_counts,
        "sev_input_rows": sev_input_rows,
    }


def _upsert_rows(resonance_rows: List[List[Any]], regime_rows: List[List[Any]]) -> None:
    with tempfile.TemporaryDirectory(prefix="l3-sync-") as td:
        tdp = Path(td)
        resonance_tsv = tdp / "resonance.tsv"
        regime_tsv = tdp / "regime.tsv"

        with resonance_tsv.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter="\t", quotechar='"', lineterminator="\n")
            for row in resonance_rows:
                writer.writerow(row)

        with regime_tsv.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter="\t", quotechar='"', lineterminator="\n")
            for row in regime_rows:
                writer.writerow(row)

        resonance_sql = f"""
BEGIN;
CREATE TEMP TABLE _r(symbol TEXT,gate_id TEXT,resonance_id TEXT,resonance_score DOUBLE PRECISION,resonance_json TEXT) ON COMMIT DROP;
\\copy _r FROM '{str(resonance_tsv).replace("'", "''")}' WITH (FORMAT csv, DELIMITER E'\\t', QUOTE '"');
INSERT INTO l3_resonance_results(symbol,gate_id,resonance_id,resonance_score,resonance_json,computed_at_utc)
SELECT UPPER(TRIM(symbol)),gate_id,resonance_id,resonance_score,resonance_json::jsonb,NOW() FROM _r
ON CONFLICT(symbol,resonance_id) DO UPDATE SET
gate_id=EXCLUDED.gate_id,resonance_score=EXCLUDED.resonance_score,resonance_json=EXCLUDED.resonance_json,computed_at_utc=NOW();
COMMIT;
"""
        r_res = _run_psql(stdin_text=resonance_sql, timeout=600)
        if r_res.returncode != 0:
            raise RuntimeError((r_res.stderr or r_res.stdout or "l3_resonance_upsert_failed").strip())

        regime_sql = f"""
BEGIN;
CREATE TEMP TABLE _g(symbol TEXT,bar_ts TIMESTAMPTZ,regime TEXT,stability_score DOUBLE PRECISION,max_drawdown DOUBLE PRECISION,regime_json TEXT) ON COMMIT DROP;
\\copy _g FROM '{str(regime_tsv).replace("'", "''")}' WITH (FORMAT csv, DELIMITER E'\\t', QUOTE '"');
INSERT INTO l3_regime_states(symbol,bar_ts,regime,stability_score,max_drawdown,regime_json,computed_at_utc)
SELECT UPPER(TRIM(symbol)),bar_ts,regime,stability_score,max_drawdown,regime_json::jsonb,NOW() FROM _g
ON CONFLICT(symbol,bar_ts) DO UPDATE SET
regime=EXCLUDED.regime,stability_score=EXCLUDED.stability_score,max_drawdown=EXCLUDED.max_drawdown,regime_json=EXCLUDED.regime_json,computed_at_utc=NOW();
COMMIT;
"""
        g_res = _run_psql(stdin_text=regime_sql, timeout=600)
        if g_res.returncode != 0:
            raise RuntimeError((g_res.stderr or g_res.stdout or "l3_regime_upsert_failed").strip())


def _query_counts(symbols: List[str]) -> Dict[str, Any]:
    rt = _run_psql(sql="SELECT COUNT(*)::text FROM l3_resonance_results;", timeout=30)
    gt = _run_psql(sql="SELECT COUNT(*)::text FROM l3_regime_states;", timeout=30)
    if rt.returncode != 0 or gt.returncode != 0:
        raise RuntimeError("l3_count_query_failed")

    resonance_by_symbol: Dict[str, int] = {}
    regime_by_symbol: Dict[str, int] = {}
    for symbol in symbols:
        rq = _run_psql(sql=f"SELECT COUNT(*)::text FROM l3_resonance_results WHERE symbol='{symbol}';", timeout=30)
        gq = _run_psql(sql=f"SELECT COUNT(*)::text FROM l3_regime_states WHERE symbol='{symbol}';", timeout=30)
        resonance_by_symbol[symbol] = int((rq.stdout or "0").strip() or "0") if rq.returncode == 0 else 0
        regime_by_symbol[symbol] = int((gq.stdout or "0").strip() or "0") if gq.returncode == 0 else 0

    fk_q = _run_psql(
        sql=(
            "SELECT COUNT(*)::text "
            "FROM l3_resonance_results r "
            "LEFT JOIN l2_gate_segments g ON g.symbol=r.symbol AND g.gate_id=r.gate_id "
            "WHERE g.gate_id IS NULL;"
        ),
        timeout=30,
    )
    if fk_q.returncode != 0:
        raise RuntimeError("l3_resonance_fk_query_failed")

    regimes = ",".join([f"'{label}'" for label in ALLOWED_REGIMES])
    regime_enum_q = _run_psql(
        sql=(
            "SELECT COUNT(*)::text "
            "FROM l3_regime_states "
            f"WHERE regime NOT IN ({regimes});"
        ),
        timeout=30,
    )
    if regime_enum_q.returncode != 0:
        raise RuntimeError("l3_regime_enum_query_failed")

    return {
        "resonance_table_total": int((rt.stdout or "0").strip() or "0"),
        "regime_table_total": int((gt.stdout or "0").strip() or "0"),
        "resonance_rows_by_symbol": resonance_by_symbol,
        "regime_rows_by_symbol": regime_by_symbol,
        "resonance_fk_missing_count": int((fk_q.stdout or "0").strip() or "0"),
        "regime_enum_invalid_count": int((regime_enum_q.stdout or "0").strip() or "0"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync L3 resonance + regime rows into Postgres.")
    parser.add_argument("--sample-size", type=int, default=3)
    parser.add_argument("--output-dir", default="")
    args = parser.parse_args()

    out_dir = Path(str(args.output_dir)).resolve() if str(args.output_dir).strip() else BACKUPS_RUNTIME_DIR / f"l3-db-native-sync-{_stamp()}"
    out_dir.mkdir(parents=True, exist_ok=True)

    summary: Dict[str, Any] = {
        "generated_at_utc": _utc_now_iso(),
        "status": "fail",
        "pass": False,
        "preflight": None,
        "symbols": [],
        "allowed_regimes": list(ALLOWED_REGIMES),
        "sev_input_rows": 0,
        "resonance_input_rows": 0,
        "regime_input_rows": 0,
        "computed_resonance_rows_by_symbol": {},
        "computed_regime_rows_by_symbol": {},
        "resonance_table_total": 0,
        "regime_table_total": 0,
        "resonance_rows_by_symbol": {},
        "regime_rows_by_symbol": {},
        "resonance_fk_missing_count": 0,
        "regime_enum_invalid_count": 0,
        "errors": [],
        "output_dir": str(out_dir),
    }

    try:
        summary["preflight"] = _require_preflight()
        _ensure_tables()
        symbols = _resolve_symbols(max(1, int(args.sample_size)))
        payload = _build_l3_rows(symbols)
        _upsert_rows(payload["resonance_rows"], payload["regime_rows"])
        counts = _query_counts(symbols)

        summary["symbols"] = symbols
        summary["sev_input_rows"] = payload["sev_input_rows"]
        summary["resonance_input_rows"] = len(payload["resonance_rows"])
        summary["regime_input_rows"] = len(payload["regime_rows"])
        summary["computed_resonance_rows_by_symbol"] = payload["resonance_counts"]
        summary["computed_regime_rows_by_symbol"] = payload["regime_counts"]
        summary["resonance_table_total"] = counts["resonance_table_total"]
        summary["regime_table_total"] = counts["regime_table_total"]
        summary["resonance_rows_by_symbol"] = counts["resonance_rows_by_symbol"]
        summary["regime_rows_by_symbol"] = counts["regime_rows_by_symbol"]
        summary["resonance_fk_missing_count"] = counts["resonance_fk_missing_count"]
        summary["regime_enum_invalid_count"] = counts["regime_enum_invalid_count"]

        per_symbol_resonance_ok = all(int(counts["resonance_rows_by_symbol"].get(symbol, 0)) > 0 for symbol in symbols)
        per_symbol_regime_ok = all(int(counts["regime_rows_by_symbol"].get(symbol, 0)) > 0 for symbol in symbols)
        pass_ok = bool(
            summary["resonance_table_total"] > 0
            and summary["regime_table_total"] > 0
            and per_symbol_resonance_ok
            and per_symbol_regime_ok
            and summary["resonance_fk_missing_count"] == 0
            and summary["regime_enum_invalid_count"] == 0
        )

        summary["pass"] = pass_ok
        summary["status"] = "pass" if pass_ok else "fail"
        if not pass_ok:
            summary["errors"].append("l3_ingestion_not_confirmed")
    except Exception as exc:
        summary["status"] = "fail"
        summary["pass"] = False
        summary["errors"].append(f"{type(exc).__name__}: {exc}")

    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if summary.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
