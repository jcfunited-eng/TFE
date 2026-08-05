#!/usr/bin/env python3
"""
L4 Phase-1 DB sync: persist directional decision + DSF rows into Postgres.

Sources:
- l1_sev_series (SEV rows)
Transforms:
- uf_core.layer1.segment_gates + build_gate_l1_state
- uf_core.layer2.interpret_gates
- uf_core.layer3.compute_resonance
- uf_core.layer4.compute_directional_signal + compute_dsf
Targets:
- l4_decision_states
- l4_dsf_series
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
from uf_core.layer1 import segment_gates
from uf_core.layer2 import interpret_gates
from uf_core.layer3 import compute_resonance
from uf_core.layer4 import compute_directional_signal, compute_dsf
from uf_core.uf_structural_engine import _compute_stability_from_l4

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKUPS_RUNTIME_DIR = REPO_ROOT / "backups" / "runtime"
REQUIRED_PG_ENV = ("PGHOST", "PGDATABASE", "PGUSER", "PGPASSWORD")


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
        "CREATE TABLE IF NOT EXISTS l4_decision_states("
        "symbol TEXT NOT NULL,bar_ts TIMESTAMPTZ NOT NULL,d_k DOUBLE PRECISION NOT NULL,m_k DOUBLE PRECISION NOT NULL,"
        "r_rev_k DOUBLE PRECISION NOT NULL,u_star_k DOUBLE PRECISION NOT NULL,c_k DOUBLE PRECISION NOT NULL,"
        "p_k DOUBLE PRECISION NOT NULL,b_k DOUBLE PRECISION NOT NULL,decision_vector_json JSONB NOT NULL,"
        "computed_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),PRIMARY KEY(symbol,bar_ts));"
        "CREATE INDEX IF NOT EXISTS idx_l4_decision_states_symbol_ts ON l4_decision_states(symbol,bar_ts DESC);"
        "CREATE TABLE IF NOT EXISTS l4_dsf_series("
        "symbol TEXT NOT NULL,bar_ts TIMESTAMPTZ NOT NULL,s_uf DOUBLE PRECISION NOT NULL,r_uf DOUBLE PRECISION NOT NULL,"
        "dsf_json JSONB NOT NULL,computed_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),PRIMARY KEY(symbol,bar_ts));"
        "CREATE INDEX IF NOT EXISTS idx_l4_dsf_series_symbol_ts ON l4_dsf_series(symbol,bar_ts DESC);"
    )
    res = _run_psql(sql=ddl, timeout=120)
    if res.returncode != 0:
        raise RuntimeError((res.stderr or res.stdout or "l4_table_ensure_failed").strip())


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


def _clamp01(value: float) -> float:
    return float(max(0.0, min(1.0, float(value))))


def _build_l4_rows(symbols: List[str]) -> Dict[str, Any]:
    decision_rows: List[List[Any]] = []
    dsf_rows: List[List[Any]] = []
    decision_counts: Dict[str, int] = {}
    dsf_counts: Dict[str, int] = {}
    sev_input_rows = 0

    for symbol in symbols:
        ts_sev = _load_sev_rows(symbol)
        sev_input_rows += len(ts_sev)
        if len(ts_sev) < 3:
            decision_counts[symbol] = 0
            dsf_counts[symbol] = 0
            continue

        ts_values = [row[0] for row in ts_sev]
        sev_values = [row[1] for row in ts_sev]
        gates = segment_gates(sev_values)
        interpretations = interpret_gates(sev_values, gates)
        resonance = compute_resonance(interpretations)
        decisions = compute_directional_signal(resonance)
        dsf_list = compute_dsf(decisions)

        if not (gates and resonance and decisions and dsf_list):
            decision_counts[symbol] = 0
            dsf_counts[symbol] = 0
            continue
        if not (len(gates) == len(resonance) == len(decisions) == len(dsf_list)):
            raise RuntimeError(f"l4_alignment_failed:{symbol}")

        idx = len(dsf_list) - 1
        gate = gates[idx]
        if gate.end_idx < 0 or gate.end_idx >= len(ts_values):
            decision_counts[symbol] = 0
            dsf_counts[symbol] = 0
            continue

        bar_ts = ts_values[gate.end_idx]
        ds = decisions[idx]
        dsf = dsf_list[idx]
        stab = _compute_stability_from_l4(resonance, decisions)
        s_uf = _clamp01(0.5 * float(stab["dsf"]) + 0.5 * float(stab["directional"]))
        r_uf = _clamp01(float(stab["R_mean"]))

        decision_vector = [
            float(ds.D_k),
            float(ds.M_k),
            float(ds.R_rev_k),
            float(ds.U_star_k),
            float(ds.P_k),
            float(ds.B_k),
        ]
        decision_json = json.dumps(
            {
                "gate_id": f"{symbol}:{gate.start_idx}:{gate.end_idx}",
                "decision_vector": decision_vector,
                "gate_count": len(gates),
                "active_gate_count": sum(1 for r in resonance if int(r.g_k) == 1),
            },
            separators=(",", ":"),
            ensure_ascii=True,
        )

        dsf_json = json.dumps(
            {
                "D_k": float(dsf.D_k),
                "M_k": float(dsf.M_k),
                "R_rev_k": float(dsf.R_rev_k),
                "U_star_k": float(dsf.U_star_k),
                "C_k": float(dsf.C_k),
                "P_k": float(dsf.P_k),
                "B_k": float(dsf.B_k),
                "S_UF": float(s_uf),
                "R_UF": float(r_uf),
            },
            separators=(",", ":"),
            ensure_ascii=True,
        )

        decision_rows.append(
            [
                symbol,
                bar_ts,
                float(ds.D_k),
                float(ds.M_k),
                float(ds.R_rev_k),
                float(ds.U_star_k),
                float(ds.C_k),
                float(ds.P_k),
                float(ds.B_k),
                decision_json,
            ]
        )
        dsf_rows.append([symbol, bar_ts, float(s_uf), float(r_uf), dsf_json])
        decision_counts[symbol] = 1
        dsf_counts[symbol] = 1

    if not decision_rows:
        raise RuntimeError("l4_decision_rows_empty")
    if not dsf_rows:
        raise RuntimeError("l4_dsf_rows_empty")

    return {
        "decision_rows": decision_rows,
        "dsf_rows": dsf_rows,
        "decision_counts": decision_counts,
        "dsf_counts": dsf_counts,
        "sev_input_rows": sev_input_rows,
    }


def _upsert_rows(decision_rows: List[List[Any]], dsf_rows: List[List[Any]]) -> None:
    with tempfile.TemporaryDirectory(prefix="l4-sync-") as td:
        tdp = Path(td)
        decision_tsv = tdp / "decision.tsv"
        dsf_tsv = tdp / "dsf.tsv"

        with decision_tsv.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter="\t", quotechar='"', lineterminator="\n")
            for row in decision_rows:
                writer.writerow(row)

        with dsf_tsv.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter="\t", quotechar='"', lineterminator="\n")
            for row in dsf_rows:
                writer.writerow(row)

        decision_sql = f"""
BEGIN;
CREATE TEMP TABLE _d(symbol TEXT,bar_ts TIMESTAMPTZ,d_k DOUBLE PRECISION,m_k DOUBLE PRECISION,r_rev_k DOUBLE PRECISION,u_star_k DOUBLE PRECISION,c_k DOUBLE PRECISION,p_k DOUBLE PRECISION,b_k DOUBLE PRECISION,decision_vector_json TEXT) ON COMMIT DROP;
\\copy _d FROM '{str(decision_tsv).replace("'", "''")}' WITH (FORMAT csv, DELIMITER E'\\t', QUOTE '"');
INSERT INTO l4_decision_states(symbol,bar_ts,d_k,m_k,r_rev_k,u_star_k,c_k,p_k,b_k,decision_vector_json,computed_at_utc)
SELECT UPPER(TRIM(symbol)),bar_ts,d_k,m_k,r_rev_k,u_star_k,c_k,p_k,b_k,decision_vector_json::jsonb,NOW() FROM _d
ON CONFLICT(symbol,bar_ts) DO UPDATE SET
d_k=EXCLUDED.d_k,m_k=EXCLUDED.m_k,r_rev_k=EXCLUDED.r_rev_k,u_star_k=EXCLUDED.u_star_k,c_k=EXCLUDED.c_k,p_k=EXCLUDED.p_k,b_k=EXCLUDED.b_k,decision_vector_json=EXCLUDED.decision_vector_json,computed_at_utc=NOW();
COMMIT;
"""
        d_res = _run_psql(stdin_text=decision_sql, timeout=600)
        if d_res.returncode != 0:
            raise RuntimeError((d_res.stderr or d_res.stdout or "l4_decision_upsert_failed").strip())

        dsf_sql = f"""
BEGIN;
CREATE TEMP TABLE _s(symbol TEXT,bar_ts TIMESTAMPTZ,s_uf DOUBLE PRECISION,r_uf DOUBLE PRECISION,dsf_json TEXT) ON COMMIT DROP;
\\copy _s FROM '{str(dsf_tsv).replace("'", "''")}' WITH (FORMAT csv, DELIMITER E'\\t', QUOTE '"');
INSERT INTO l4_dsf_series(symbol,bar_ts,s_uf,r_uf,dsf_json,computed_at_utc)
SELECT UPPER(TRIM(symbol)),bar_ts,s_uf,r_uf,dsf_json::jsonb,NOW() FROM _s
ON CONFLICT(symbol,bar_ts) DO UPDATE SET
s_uf=EXCLUDED.s_uf,r_uf=EXCLUDED.r_uf,dsf_json=EXCLUDED.dsf_json,computed_at_utc=NOW();
COMMIT;
"""
        s_res = _run_psql(stdin_text=dsf_sql, timeout=600)
        if s_res.returncode != 0:
            raise RuntimeError((s_res.stderr or s_res.stdout or "l4_dsf_upsert_failed").strip())


def _query_counts(symbols: List[str]) -> Dict[str, Any]:
    dt = _run_psql(sql="SELECT COUNT(*)::text FROM l4_decision_states;", timeout=30)
    st = _run_psql(sql="SELECT COUNT(*)::text FROM l4_dsf_series;", timeout=30)
    if dt.returncode != 0 or st.returncode != 0:
        raise RuntimeError("l4_count_query_failed")

    decision_by_symbol: Dict[str, int] = {}
    dsf_by_symbol: Dict[str, int] = {}
    for symbol in symbols:
        dq = _run_psql(sql=f"SELECT COUNT(*)::text FROM l4_decision_states WHERE symbol='{symbol}';", timeout=30)
        sq = _run_psql(sql=f"SELECT COUNT(*)::text FROM l4_dsf_series WHERE symbol='{symbol}';", timeout=30)
        decision_by_symbol[symbol] = int((dq.stdout or "0").strip() or "0") if dq.returncode == 0 else 0
        dsf_by_symbol[symbol] = int((sq.stdout or "0").strip() or "0") if sq.returncode == 0 else 0

    missing_required_q = _run_psql(
        sql=(
            "SELECT COUNT(*)::text FROM l4_decision_states "
            "WHERE d_k IS NULL OR m_k IS NULL OR r_rev_k IS NULL OR u_star_k IS NULL OR c_k IS NULL OR p_k IS NULL OR b_k IS NULL;"
        ),
        timeout=30,
    )
    if missing_required_q.returncode != 0:
        raise RuntimeError("l4_required_fields_query_failed")

    return {
        "decision_table_total": int((dt.stdout or "0").strip() or "0"),
        "dsf_table_total": int((st.stdout or "0").strip() or "0"),
        "decision_rows_by_symbol": decision_by_symbol,
        "dsf_rows_by_symbol": dsf_by_symbol,
        "missing_required_fields_count": int((missing_required_q.stdout or "0").strip() or "0"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync L4 decision + DSF rows into Postgres.")
    parser.add_argument("--sample-size", type=int, default=3)
    parser.add_argument("--output-dir", default="")
    args = parser.parse_args()

    out_dir = Path(str(args.output_dir)).resolve() if str(args.output_dir).strip() else BACKUPS_RUNTIME_DIR / f"l4-db-native-sync-{_stamp()}"
    out_dir.mkdir(parents=True, exist_ok=True)

    summary: Dict[str, Any] = {
        "generated_at_utc": _utc_now_iso(),
        "status": "fail",
        "pass": False,
        "preflight": None,
        "symbols": [],
        "sev_input_rows": 0,
        "decision_input_rows": 0,
        "dsf_input_rows": 0,
        "computed_decision_rows_by_symbol": {},
        "computed_dsf_rows_by_symbol": {},
        "decision_table_total": 0,
        "dsf_table_total": 0,
        "decision_rows_by_symbol": {},
        "dsf_rows_by_symbol": {},
        "missing_required_fields_count": 0,
        "errors": [],
        "output_dir": str(out_dir),
    }

    try:
        summary["preflight"] = _require_preflight()
        _ensure_tables()
        symbols = _resolve_symbols(max(1, int(args.sample_size)))
        payload = _build_l4_rows(symbols)
        _upsert_rows(payload["decision_rows"], payload["dsf_rows"])
        counts = _query_counts(symbols)

        summary["symbols"] = symbols
        summary["sev_input_rows"] = payload["sev_input_rows"]
        summary["decision_input_rows"] = len(payload["decision_rows"])
        summary["dsf_input_rows"] = len(payload["dsf_rows"])
        summary["computed_decision_rows_by_symbol"] = payload["decision_counts"]
        summary["computed_dsf_rows_by_symbol"] = payload["dsf_counts"]
        summary["decision_table_total"] = counts["decision_table_total"]
        summary["dsf_table_total"] = counts["dsf_table_total"]
        summary["decision_rows_by_symbol"] = counts["decision_rows_by_symbol"]
        summary["dsf_rows_by_symbol"] = counts["dsf_rows_by_symbol"]
        summary["missing_required_fields_count"] = counts["missing_required_fields_count"]

        per_symbol_decision_ok = all(int(counts["decision_rows_by_symbol"].get(symbol, 0)) > 0 for symbol in symbols)
        per_symbol_dsf_ok = all(int(counts["dsf_rows_by_symbol"].get(symbol, 0)) > 0 for symbol in symbols)
        pass_ok = bool(
            summary["decision_table_total"] > 0
            and summary["dsf_table_total"] > 0
            and per_symbol_decision_ok
            and per_symbol_dsf_ok
            and summary["missing_required_fields_count"] == 0
        )

        summary["pass"] = pass_ok
        summary["status"] = "pass" if pass_ok else "fail"
        if not pass_ok:
            summary["errors"].append("l4_ingestion_not_confirmed")
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
