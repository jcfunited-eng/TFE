#!/usr/bin/env python3
"""
L2 Phase-1 DB sync: persist gate segments + interpretations into Postgres.

Sources:
- l1_sev_series (SEV rows per symbol/bar)
Transforms:
- uf_core.layer1.segment_gates + build_gate_l1_state
- uf_core.layer2.interpret_gates
Targets:
- l2_gate_segments
- l2_gate_interpretations
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

from uf_core.layer0 import SEV
from uf_core.layer1 import build_gate_l1_state, segment_gates
from uf_core.layer2 import interpret_gates

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKUPS_RUNTIME_DIR = REPO_ROOT / "backups" / "runtime"
REQUIRED_PG_ENV = ("PGHOST", "PGDATABASE", "PGUSER", "PGPASSWORD")
ALLOWED_LABELS = ("STABLE", "TRANSITIONAL", "VOLATILE", "DEGENERATE")


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
        "CREATE TABLE IF NOT EXISTS l2_gate_segments("
        "symbol TEXT NOT NULL,gate_id TEXT NOT NULL,start_ts TIMESTAMPTZ NOT NULL,end_ts TIMESTAMPTZ NOT NULL,"
        "start_idx INTEGER NOT NULL,end_idx INTEGER NOT NULL,gate_type TEXT NOT NULL,gate_strength DOUBLE PRECISION NOT NULL,"
        "gate_json JSONB NOT NULL,computed_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        "PRIMARY KEY(symbol,gate_id));"
        "CREATE INDEX IF NOT EXISTS idx_l2_gate_segments_symbol_start ON l2_gate_segments(symbol,start_ts DESC);"
        "CREATE TABLE IF NOT EXISTS l2_gate_interpretations("
        "symbol TEXT NOT NULL,gate_id TEXT NOT NULL,interpretation_id TEXT NOT NULL,"
        "interpretation_label TEXT NOT NULL,score DOUBLE PRECISION NOT NULL,interpretation_json JSONB NOT NULL,"
        "computed_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        "PRIMARY KEY(symbol,interpretation_id),"
        "FOREIGN KEY(symbol,gate_id) REFERENCES l2_gate_segments(symbol,gate_id) ON DELETE CASCADE);"
        "CREATE INDEX IF NOT EXISTS idx_l2_gate_interpretations_symbol_gate ON l2_gate_interpretations(symbol,gate_id);"
    )
    res = _run_psql(sql=ddl, timeout=120)
    if res.returncode != 0:
        raise RuntimeError((res.stderr or res.stdout or "l2_table_ensure_failed").strip())


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
        ts_text, sev_u_text, sev_d_text, sev_l_text, meta_text = parts
        try:
            meta = json.loads(meta_text or "{}")
            sev = SEV(
                F_norm=float(sev_u_text),
                dF=float(sev_d_text),
                sigma=float(sev_l_text),
                kappa=float(meta.get("kappa", 0.0)),
                relevance=float(meta.get("relevance", 1.0)),
                N=int(meta.get("N", 0)),
            )
            out.append((ts_text, sev))
        except Exception:
            continue
    return out


def _build_l2_rows(symbols: List[str]) -> Dict[str, Any]:
    gate_rows: List[List[Any]] = []
    interpretation_rows: List[List[Any]] = []
    gate_counts: Dict[str, int] = {}
    interpretation_counts: Dict[str, int] = {}
    sev_input_rows = 0

    for symbol in symbols:
        ts_sev = _load_sev_rows(symbol)
        sev_input_rows += len(ts_sev)
        if len(ts_sev) < 3:
            gate_counts[symbol] = 0
            interpretation_counts[symbol] = 0
            continue

        ts_values = [row[0] for row in ts_sev]
        sev_values = [row[1] for row in ts_sev]
        gates = segment_gates(sev_values)
        l1_state = build_gate_l1_state(sev_values, gates)
        interpretations = interpret_gates(sev_values, gates)

        if not gates:
            gate_counts[symbol] = 0
            interpretation_counts[symbol] = 0
            continue

        if len(gates) != len(l1_state) or len(gates) != len(interpretations):
            raise RuntimeError(f"l2_alignment_failed:{symbol}")

        gate_count = 0
        interpretation_count = 0
        for idx, gate in enumerate(gates):
            if gate.start_idx < 0 or gate.end_idx >= len(ts_values) or gate.start_idx > gate.end_idx:
                continue

            state = l1_state[idx]
            interp = interpretations[idx]
            start_ts = ts_values[gate.start_idx]
            end_ts = ts_values[gate.end_idx]
            gate_id = f"{symbol}:{gate.start_idx}:{gate.end_idx}"
            gate_type = "NEGATIVE_SPACE" if int(state.N_gate) == 1 else "STANDARD"
            gate_strength = float(state.tvr[1])

            gate_json = json.dumps(
                {
                    "tvr": {
                        "T_k": float(state.tvr[0]),
                        "V_k": float(state.tvr[1]),
                        "R_k": float(state.tvr[2]),
                    },
                    "projections": [list(p) for p in state.projections],
                    "C_k": int(state.C_k),
                    "delta_g": float(state.delta_g),
                    "N_gate": int(state.N_gate),
                },
                separators=(",", ":"),
                ensure_ascii=True,
            )
            gate_rows.append(
                [
                    symbol,
                    gate_id,
                    start_ts,
                    end_ts,
                    int(gate.start_idx),
                    int(gate.end_idx),
                    gate_type,
                    gate_strength,
                    gate_json,
                ]
            )
            gate_count += 1

            interpretation_id = gate_id
            label = str(interp.regime or "").strip().upper()
            score = float(interp.S_k)
            interpretation_json = json.dumps(
                {
                    "w_k": float(interp.w_k),
                    "CV_k": [float(interp.CV_k[0]), float(interp.CV_k[1]), float(interp.CV_k[2])],
                    "U_k": float(interp.U_k),
                    "IAS_k": int(interp.IAS_k),
                    "C_k": int(interp.C_k),
                    "delta_g": float(interp.delta_g),
                    "N_gate": int(interp.N_gate),
                    "chi_k": float(interp.chi_k),
                    "psi_k": float(interp.psi_k),
                },
                separators=(",", ":"),
                ensure_ascii=True,
            )
            interpretation_rows.append(
                [
                    symbol,
                    gate_id,
                    interpretation_id,
                    label,
                    score,
                    interpretation_json,
                ]
            )
            interpretation_count += 1

        gate_counts[symbol] = gate_count
        interpretation_counts[symbol] = interpretation_count

    if not gate_rows:
        raise RuntimeError("l2_gate_rows_empty")
    if not interpretation_rows:
        raise RuntimeError("l2_interpretation_rows_empty")

    return {
        "gate_rows": gate_rows,
        "interpretation_rows": interpretation_rows,
        "gate_counts": gate_counts,
        "interpretation_counts": interpretation_counts,
        "sev_input_rows": sev_input_rows,
    }


def _upsert_rows(gate_rows: List[List[Any]], interpretation_rows: List[List[Any]]) -> None:
    with tempfile.TemporaryDirectory(prefix="l2-gates-sync-") as td:
        tdp = Path(td)
        gate_tsv = tdp / "gates.tsv"
        interp_tsv = tdp / "interpretations.tsv"

        with gate_tsv.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter="\t", quotechar='"', lineterminator="\n")
            for row in gate_rows:
                writer.writerow(row)

        with interp_tsv.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter="\t", quotechar='"', lineterminator="\n")
            for row in interpretation_rows:
                writer.writerow(row)

        gate_sql = f"""
BEGIN;
CREATE TEMP TABLE _g(symbol TEXT,gate_id TEXT,start_ts TIMESTAMPTZ,end_ts TIMESTAMPTZ,start_idx INTEGER,end_idx INTEGER,gate_type TEXT,gate_strength DOUBLE PRECISION,gate_json TEXT) ON COMMIT DROP;
\\copy _g FROM '{str(gate_tsv).replace("'", "''")}' WITH (FORMAT csv, DELIMITER E'\\t', QUOTE '"');
INSERT INTO l2_gate_segments(symbol,gate_id,start_ts,end_ts,start_idx,end_idx,gate_type,gate_strength,gate_json,computed_at_utc)
SELECT UPPER(TRIM(symbol)),gate_id,start_ts,end_ts,start_idx,end_idx,gate_type,gate_strength,gate_json::jsonb,NOW() FROM _g
ON CONFLICT(symbol,gate_id) DO UPDATE SET
start_ts=EXCLUDED.start_ts,end_ts=EXCLUDED.end_ts,start_idx=EXCLUDED.start_idx,end_idx=EXCLUDED.end_idx,
gate_type=EXCLUDED.gate_type,gate_strength=EXCLUDED.gate_strength,gate_json=EXCLUDED.gate_json,computed_at_utc=NOW();
COMMIT;
"""
        gate_res = _run_psql(stdin_text=gate_sql, timeout=600)
        if gate_res.returncode != 0:
            raise RuntimeError((gate_res.stderr or gate_res.stdout or "l2_gate_upsert_failed").strip())

        interp_sql = f"""
BEGIN;
CREATE TEMP TABLE _i(symbol TEXT,gate_id TEXT,interpretation_id TEXT,interpretation_label TEXT,score DOUBLE PRECISION,interpretation_json TEXT) ON COMMIT DROP;
\\copy _i FROM '{str(interp_tsv).replace("'", "''")}' WITH (FORMAT csv, DELIMITER E'\\t', QUOTE '"');
INSERT INTO l2_gate_interpretations(symbol,gate_id,interpretation_id,interpretation_label,score,interpretation_json,computed_at_utc)
SELECT UPPER(TRIM(symbol)),gate_id,interpretation_id,interpretation_label,score,interpretation_json::jsonb,NOW() FROM _i
ON CONFLICT(symbol,interpretation_id) DO UPDATE SET
gate_id=EXCLUDED.gate_id,interpretation_label=EXCLUDED.interpretation_label,score=EXCLUDED.score,
interpretation_json=EXCLUDED.interpretation_json,computed_at_utc=NOW();
COMMIT;
"""
        interp_res = _run_psql(stdin_text=interp_sql, timeout=600)
        if interp_res.returncode != 0:
            raise RuntimeError((interp_res.stderr or interp_res.stdout or "l2_interpretation_upsert_failed").strip())


def _query_counts(symbols: List[str]) -> Dict[str, Any]:
    gate_total_q = _run_psql(sql="SELECT COUNT(*)::text FROM l2_gate_segments;", timeout=30)
    interp_total_q = _run_psql(sql="SELECT COUNT(*)::text FROM l2_gate_interpretations;", timeout=30)
    if gate_total_q.returncode != 0 or interp_total_q.returncode != 0:
        raise RuntimeError("l2_count_query_failed")

    gate_by_symbol: Dict[str, int] = {}
    interp_by_symbol: Dict[str, int] = {}
    for symbol in symbols:
        gq = _run_psql(sql=f"SELECT COUNT(*)::text FROM l2_gate_segments WHERE symbol='{symbol}';", timeout=30)
        iq = _run_psql(sql=f"SELECT COUNT(*)::text FROM l2_gate_interpretations WHERE symbol='{symbol}';", timeout=30)
        gate_by_symbol[symbol] = int((gq.stdout or "0").strip() or "0") if gq.returncode == 0 else 0
        interp_by_symbol[symbol] = int((iq.stdout or "0").strip() or "0") if iq.returncode == 0 else 0

    fk_q = _run_psql(
        sql=(
            "SELECT COUNT(*)::text "
            "FROM l2_gate_interpretations i "
            "LEFT JOIN l2_gate_segments g ON g.symbol=i.symbol AND g.gate_id=i.gate_id "
            "WHERE g.gate_id IS NULL;"
        ),
        timeout=30,
    )
    if fk_q.returncode != 0:
        raise RuntimeError("l2_fk_integrity_query_failed")

    labels = ",".join([f"'{label}'" for label in ALLOWED_LABELS])
    label_q = _run_psql(
        sql=(
            "SELECT COUNT(*)::text "
            "FROM l2_gate_interpretations "
            f"WHERE interpretation_label NOT IN ({labels});"
        ),
        timeout=30,
    )
    if label_q.returncode != 0:
        raise RuntimeError("l2_label_contract_query_failed")

    return {
        "gate_table_total": int((gate_total_q.stdout or "0").strip() or "0"),
        "interpretation_table_total": int((interp_total_q.stdout or "0").strip() or "0"),
        "gate_rows_by_symbol": gate_by_symbol,
        "interpretation_rows_by_symbol": interp_by_symbol,
        "fk_missing_count": int((fk_q.stdout or "0").strip() or "0"),
        "label_invalid_count": int((label_q.stdout or "0").strip() or "0"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync L2 gate segments + interpretations into Postgres.")
    parser.add_argument("--sample-size", type=int, default=3)
    parser.add_argument("--output-dir", default="")
    args = parser.parse_args()

    out_dir = Path(str(args.output_dir)).resolve() if str(args.output_dir).strip() else BACKUPS_RUNTIME_DIR / f"l2-db-native-gates-sync-{_stamp()}"
    out_dir.mkdir(parents=True, exist_ok=True)

    summary: Dict[str, Any] = {
        "generated_at_utc": _utc_now_iso(),
        "status": "fail",
        "pass": False,
        "preflight": None,
        "symbols": [],
        "allowed_labels": list(ALLOWED_LABELS),
        "sev_input_rows": 0,
        "gate_input_rows": 0,
        "interpretation_input_rows": 0,
        "computed_gate_rows_by_symbol": {},
        "computed_interpretation_rows_by_symbol": {},
        "gate_table_total": 0,
        "interpretation_table_total": 0,
        "gate_rows_by_symbol": {},
        "interpretation_rows_by_symbol": {},
        "fk_missing_count": 0,
        "label_invalid_count": 0,
        "errors": [],
        "output_dir": str(out_dir),
    }

    try:
        summary["preflight"] = _require_preflight()
        _ensure_tables()
        symbols = _resolve_symbols(max(1, int(args.sample_size)))
        payload = _build_l2_rows(symbols)
        _upsert_rows(payload["gate_rows"], payload["interpretation_rows"])
        counts = _query_counts(symbols)

        summary["symbols"] = symbols
        summary["sev_input_rows"] = payload["sev_input_rows"]
        summary["gate_input_rows"] = len(payload["gate_rows"])
        summary["interpretation_input_rows"] = len(payload["interpretation_rows"])
        summary["computed_gate_rows_by_symbol"] = payload["gate_counts"]
        summary["computed_interpretation_rows_by_symbol"] = payload["interpretation_counts"]
        summary["gate_table_total"] = counts["gate_table_total"]
        summary["interpretation_table_total"] = counts["interpretation_table_total"]
        summary["gate_rows_by_symbol"] = counts["gate_rows_by_symbol"]
        summary["interpretation_rows_by_symbol"] = counts["interpretation_rows_by_symbol"]
        summary["fk_missing_count"] = counts["fk_missing_count"]
        summary["label_invalid_count"] = counts["label_invalid_count"]

        per_symbol_gate_ok = all(int(counts["gate_rows_by_symbol"].get(symbol, 0)) > 0 for symbol in symbols)
        per_symbol_interp_ok = all(int(counts["interpretation_rows_by_symbol"].get(symbol, 0)) > 0 for symbol in symbols)
        pass_ok = bool(
            summary["gate_table_total"] > 0
            and summary["interpretation_table_total"] > 0
            and per_symbol_gate_ok
            and per_symbol_interp_ok
            and summary["fk_missing_count"] == 0
            and summary["label_invalid_count"] == 0
        )
        summary["pass"] = pass_ok
        summary["status"] = "pass" if pass_ok else "fail"
        if not pass_ok:
            summary["errors"].append("l2_gate_ingestion_not_confirmed")
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
