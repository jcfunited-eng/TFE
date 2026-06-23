#!/usr/bin/env python3
"""
tools/validation_env_import.py — Mode B production import (V3 transport).

Imports production tables (read-only) into local `tfe_validation` Postgres.
See docs/VALIDATION_ENVIRONMENT_SPEC.md §3.1 (Mode B).

TRANSPORT (wC decision, TFE-CMD-VENV-IMPORT-V3):
  - Four metadata/ledger tables: chunked COPY over ECS Exec. SSM truncates
    bulk single-COPY output above ~2000 rows (found empirically in V2), so
    we keyset-paginate at 1500 rows/chunk inside that ceiling.
  - daily_bars: the production refresh already writes daily_bars_export.csv.gz
    to S3 daily. We download and import it — the dormant export finally gets
    its consumer. ECS Exec can't move millions of bar rows.

Read-only against production (COPY (SELECT ...) TO STDOUT only; S3 read of a
prod-managed object). No SELECT *. Idempotent UPSERTs. Resumable via a
checkpoint file. No credential values logged (spec §6.2 rule 5).
"""

import base64
import csv
import gzip
import io
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

import boto3
import psycopg2

# ── Config ──────────────────────────────────────────────────────────────────
REGION = "us-east-1"
CLUSTER = "tfe-web-cluster"
SERVICE = "tfe-web-service-lb"
CONTAINER = "tfe-web"
LOCAL_DSN = "host=/var/run/postgresql dbname=tfe_validation user=postgres"
SUMMARY_DIR = "backups"
CKPT_PATH = "backups/validation_env_import_checkpoint.json"

S3_BUCKET = "tfe-codebuild-src-418384447921-us-east-1"
S3_KEY = "runtime-refresh-checkpoints/daily_bars_export.csv.gz"
S3_MAX_AGE_HOURS = 48

CHUNK = 1500
HISTORY_MAX = 100_000
MARK_B, MARK_E = "@@VENVB64START@@", "@@VENVB64END@@"

csv.field_size_limit(1 << 24)  # snapshot_row_json blobs can be large


def log(msg):
    print(f"[venv-import] {msg}", flush=True)


# ── ECS Exec: read-only psql in the container, base64-wrapped ───────────────
def _exec(task_id, inner_bash, timeout=300):
    b64 = base64.b64encode(inner_bash.encode()).decode()
    cmd = ["aws", "ecs", "execute-command", "--region", REGION, "--cluster", CLUSTER,
           "--task", task_id, "--container", CONTAINER, "--interactive",
           "--command", f"bash -lc 'echo {b64} | base64 -d | bash'"]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return p.stdout + "\n" + p.stderr


def _payload(raw):
    """Decode the base64 blob between markers; None if markers absent (truncated)."""
    if MARK_B not in raw or MARK_E not in raw:
        return None
    blob = "".join(raw.split(MARK_B, 1)[1].split(MARK_E, 1)[0].split())
    try:
        return base64.b64decode(blob).decode()
    except Exception:
        return None


def prod_scalar(task_id, sql):
    inner = (f"set -euo pipefail; printf '{MARK_B}'; "
             f'psql -v ON_ERROR_STOP=1 -At -c "{sql}" | base64 -w0; printf \'{MARK_E}\'')
    out = _payload(_exec(task_id, inner, timeout=120))
    if out is None:
        raise RuntimeError("prod scalar truncated/failed")
    return out.strip()


def prod_copy(task_id, projection_sql):
    """Run COPY (projection) TO STDOUT as CSV in prod. Return text, or None if
    the SSM channel truncated the response (no end marker)."""
    inner = (f"set -euo pipefail; printf '{MARK_B}'; "
             f"psql -v ON_ERROR_STOP=1 -c \"COPY ({projection_sql}) TO STDOUT WITH (FORMAT csv)\" "
             f"| base64 -w0; printf '{MARK_E}'")
    return _payload(_exec(task_id, inner, timeout=300))


# ── Checkpoint ──────────────────────────────────────────────────────────────
def ckpt_load():
    if os.path.exists(CKPT_PATH):
        with open(CKPT_PATH) as f:
            return json.load(f)
    return {}


def ckpt_save(ck, table, last_key):
    ck[table] = {"last_key_value": last_key,
                 "last_chunk_at": datetime.now(timezone.utc).isoformat()}
    with open(CKPT_PATH, "w") as f:
        json.dump(ck, f, indent=2)


# ── Local helpers ───────────────────────────────────────────────────────────
def local_count(conn, table):
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        return cur.fetchone()[0]


def load_temp_and_upsert(conn, temp_ddl, temp_cols, csv_text, upsert_sql):
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS _venv_tmp")
        cur.execute(temp_ddl)
        if csv_text.strip():
            cur.copy_expert(
                f"COPY _venv_tmp ({','.join(temp_cols)}) FROM STDIN WITH (FORMAT csv)",
                io.StringIO(csv_text))
        cur.execute(upsert_sql)
    conn.commit()


# ── Generic chunked-COPY importer (keyset pagination) ───────────────────────
def chunked_import(task_id, conn, table, build_proj, key_of_row, temp_ddl,
                   temp_cols, upsert_sql, ck, start_key):
    chunks, total = 0, 0
    last_key = start_key
    while True:
        size, csv_text = CHUNK, None
        for _ in range(2):
            csv_text = prod_copy(task_id, build_proj(last_key, size))
            if csv_text is not None:
                break
            size //= 2
            if size < 500:
                raise RuntimeError(
                    f"SSM truncation persists at {CHUNK} rows (retried at {size*2})")
        if csv_text is None:
            raise RuntimeError("chunk truncated twice")
        rows = list(csv.reader(io.StringIO(csv_text)))
        if not rows:
            break
        load_temp_and_upsert(conn, temp_ddl, temp_cols, csv_text, upsert_sql)
        total += len(rows)
        chunks += 1
        last_key = key_of_row(rows[-1])
        ckpt_save(ck, table, last_key)
        log(f"{table}: chunk {chunks} (+{len(rows)} rows) last_key={last_key}")
        if len(rows) < size:
            break
    return total, chunks


# ── Table specs ─────────────────────────────────────────────────────────────
def q(s):  # SQL string literal escape
    return "'" + str(s).replace("'", "''") + "'"


def spec_runtime_decisions_latest():
    cols = ["ticker", "run_id", "generated_at_utc", "snapshot_row_json",
            "decision_label", "reason_code", "reason_text"]
    sel = ",".join(cols)
    return dict(
        table="runtime_decisions_latest", start_key="",
        build=lambda k, n: (f"SELECT {sel} FROM runtime_decisions_latest "
                            f"WHERE ticker > {q(k)} ORDER BY ticker ASC LIMIT {n}"),
        key=lambda r: r[0],
        temp_ddl="""CREATE TEMP TABLE _venv_tmp (ticker text, run_id text,
            generated_at_utc timestamptz, snapshot_row_json jsonb,
            decision_label text, reason_code text, reason_text text)""",
        temp_cols=cols,
        upsert="""INSERT INTO runtime_decisions_latest
            (ticker, run_id, generated_at_utc, snapshot_row_json, decision_label,
             reason_code, reason_text, kernel_sha, source)
            SELECT ticker, run_id, generated_at_utc, snapshot_row_json, decision_label,
                   reason_code, reason_text, NULL, 'production_import' FROM _venv_tmp
            ON CONFLICT (ticker) DO UPDATE SET run_id=EXCLUDED.run_id,
              generated_at_utc=EXCLUDED.generated_at_utc,
              snapshot_row_json=EXCLUDED.snapshot_row_json,
              decision_label=EXCLUDED.decision_label, reason_code=EXCLUDED.reason_code,
              reason_text=EXCLUDED.reason_text, source=EXCLUDED.source""",
        count_sql="SELECT COUNT(*) FROM runtime_decisions_latest")


def spec_runtime_symbols():
    cols = ["ticker", "run_id", "generated_at_utc", "asset_type", "quote_type",
            "exchange", "company_name", "sector", "industry", "country", "market_cap",
            "shares_outstanding", "float_shares", "profile_json", "updated_at"]
    sel = ",".join(cols)
    setc = ",".join(f"{c}=EXCLUDED.{c}" for c in cols if c != "ticker")
    return dict(
        table="runtime_symbols", start_key="",
        build=lambda k, n: (f"SELECT {sel} FROM runtime_symbols "
                            f"WHERE ticker > {q(k)} ORDER BY ticker ASC LIMIT {n}"),
        key=lambda r: r[0],
        temp_ddl="""CREATE TEMP TABLE _venv_tmp (ticker text, run_id text,
            generated_at_utc timestamptz, asset_type text, quote_type text,
            exchange text, company_name text, sector text, industry text,
            country text, market_cap float8, shares_outstanding float8,
            float_shares float8, profile_json jsonb, updated_at timestamptz)""",
        temp_cols=cols,
        upsert=f"""INSERT INTO runtime_symbols ({','.join(cols)})
            SELECT {','.join(cols)} FROM _venv_tmp
            ON CONFLICT (ticker) DO UPDATE SET {setc}""",
        count_sql="SELECT COUNT(*) FROM runtime_symbols")


def spec_personal_trade_ledger():
    cols = ["id", "ticker", "run_id", "signal_class", "spy_dk", "s_uf", "bar_count",
            "f_n", "d_k", "b_k", "vault_equity_at_signal", "risk_per_trade_pct",
            "dollar_allocation", "shares", "atr_14", "alpaca_order_id",
            "alpaca_take_profit_order_id", "alpaca_stop_loss_order_id",
            "entry_limit_price", "take_profit_price", "stop_loss_price", "time_in_force",
            "entry_filled_price", "entry_filled_at", "exit_filled_price", "exit_filled_at",
            "p_l", "p_l_pct", "exit_reason", "status", "rationale_json",
            "signal_detected_at", "created_at", "updated_at"]
    sel = ",".join(cols)
    setc = ",".join(f"{c}=EXCLUDED.{c}" for c in cols if c not in ("id", "rationale_json"))
    ddl = """CREATE TEMP TABLE _venv_tmp (
        id bigint, ticker text, run_id text, signal_class text, spy_dk int, s_uf float8,
        bar_count int, f_n float8, d_k int, b_k float8, vault_equity_at_signal float8,
        risk_per_trade_pct float8, dollar_allocation float8, shares int, atr_14 float8,
        alpaca_order_id text, alpaca_take_profit_order_id text, alpaca_stop_loss_order_id text,
        entry_limit_price float8, take_profit_price float8, stop_loss_price float8,
        time_in_force text, entry_filled_price float8, entry_filled_at timestamptz,
        exit_filled_price float8, exit_filled_at timestamptz, p_l float8, p_l_pct float8,
        exit_reason text, status text, rationale_json jsonb, signal_detected_at timestamptz,
        created_at timestamptz, updated_at timestamptz)"""
    return dict(
        table="personal_trade_ledger", start_key=0,
        build=lambda k, n: (f"SELECT {sel} FROM personal_trade_ledger "
                            f"WHERE id > {int(k)} ORDER BY id ASC LIMIT {n}"),
        key=lambda r: int(r[0]),
        temp_ddl=ddl, temp_cols=cols,
        upsert=f"""INSERT INTO personal_trade_ledger ({sel})
            SELECT {sel} FROM _venv_tmp
            ON CONFLICT (id) DO UPDATE SET {setc},
              rationale_json = personal_trade_ledger.rationale_json || EXCLUDED.rationale_json""",
        count_sql="SELECT COUNT(*) FROM personal_trade_ledger")


def import_history(task_id, conn, ck, summary):
    """90-day window; STOP this table only if it exceeds the transport ceiling."""
    t0 = datetime.now(timezone.utc)
    win = "generated_at_utc >= NOW() - INTERVAL '90 days'"
    src = int(prod_scalar(task_id, f"SELECT COUNT(*) FROM runtime_decisions_history WHERE {win}"))
    if src > HISTORY_MAX:
        log(f"runtime_decisions_history: 90d count={src} > {HISTORY_MAX} — STOP this table "
            f"(transport overload threshold). Other tables proceed.")
        summary["tables"].append(dict(table="runtime_decisions_history", transport="ecs_exec_chunked",
            source_count_at_start=src, rows_imported=0, chunks_count=0, state="stopped_too_large",
            wall_time_seconds=(datetime.now(timezone.utc) - t0).total_seconds()))
        return "stopped"
    cols = ["ticker", "run_id", "generated_at_utc", "snapshot_row_json", "source"]
    sel = ",".join(cols)

    def build(k, n):
        if k is None:
            return (f"SELECT {sel} FROM runtime_decisions_history WHERE {win} "
                    f"ORDER BY generated_at_utc ASC, ticker ASC LIMIT {n}")
        ts, tk = k
        return (f"SELECT {sel} FROM runtime_decisions_history WHERE {win} "
                f"AND (generated_at_utc, ticker) > ({q(ts)}::timestamptz, {q(tk)}) "
                f"ORDER BY generated_at_utc ASC, ticker ASC LIMIT {n}")

    ddl = """CREATE TEMP TABLE _venv_tmp (ticker text, run_id text,
        generated_at_utc timestamptz, snapshot_row_json jsonb, prod_source text)"""
    upsert = """INSERT INTO runtime_decisions_history
        (ticker, run_id, generated_at_utc, snapshot_row_json, decision_label, kernel_sha, source)
        SELECT ticker, run_id, generated_at_utc, snapshot_row_json, NULL, NULL,
               COALESCE(prod_source, 'production_import') FROM _venv_tmp
        ON CONFLICT (ticker, generated_at_utc) DO NOTHING"""
    start = ck.get("runtime_decisions_history", {}).get("last_key_value")
    if isinstance(start, list):
        start = tuple(start)
    total, chunks = chunked_import(task_id, conn, "runtime_decisions_history", build,
        lambda r: [r[2], r[0]], ddl, cols, upsert, ck, start)
    summary["tables"].append(dict(table="runtime_decisions_history", transport="ecs_exec_chunked",
        source_count_at_start=src, rows_imported=total, chunks_count=chunks, state="complete",
        wall_time_seconds=(datetime.now(timezone.utc) - t0).total_seconds()))
    return "ok"


def import_daily_bars(conn, summary):
    """S3 transport: download the prod-emitted gzip export, import OHLCV."""
    t0 = datetime.now(timezone.utc)
    s3 = boto3.client("s3", region_name=REGION)
    head = s3.head_object(Bucket=S3_BUCKET, Key=S3_KEY)
    last_mod = head["LastModified"]
    etag = head["ETag"].strip('"')
    age_h = (datetime.now(timezone.utc) - last_mod).total_seconds() / 3600
    summary["daily_bars_s3"] = {"etag": etag, "last_modified": last_mod.isoformat(),
                                "age_hours": round(age_h, 1)}
    if age_h > S3_MAX_AGE_HOURS:
        log(f"daily_bars: S3 export age {age_h:.1f}h > {S3_MAX_AGE_HOURS}h — STOP this table. "
            f"Prod export pipeline staleness is a separate concern.")
        summary["tables"].append(dict(table="daily_bars", transport="s3_gzip",
            rows_imported=0, chunks_count=0, state="stopped_stale_export",
            wall_time_seconds=(datetime.now(timezone.utc) - t0).total_seconds()))
        return "stopped"
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    local_gz = f"/tmp/daily_bars_export_{ts}.csv.gz"
    s3.download_file(S3_BUCKET, S3_KEY, local_gz)
    nbytes = os.path.getsize(local_gz)

    # Validate header, then COPY into a temp table and bulk-upsert (column map
    # ticker->symbol; drop source/updated_at). COPY is the bulk-insert form of
    # the per-table map; idempotent ON CONFLICT, identical end state.
    with gzip.open(local_gz, "rt") as f:
        first = f.readline()
    header_cells = next(csv.reader([first]))
    has_header = "bar_date" in header_cells
    if not has_header:
        raise RuntimeError(f"daily_bars S3 header mismatch — first row: {header_cells[:10]}")
    needed = {"ticker", "bar_date", "open", "high", "low", "close", "volume"}
    if not needed.issubset(set(header_cells)):
        raise RuntimeError(f"daily_bars S3 header missing columns. Got: {header_cells}")
    idx = {name: i for i, name in enumerate(header_cells)}

    rows_parsed = 0
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS _venv_bars")
        cur.execute("""CREATE TEMP TABLE _venv_bars (symbol text, bar_date date,
            open float8, high float8, low float8, close float8, volume bigint)""")
        buf = io.StringIO()
        w = csv.writer(buf)
        with gzip.open(local_gz, "rt") as f:
            rd = csv.reader(f)
            next(rd)  # skip header
            for r in rd:
                if not r:
                    continue
                w.writerow([r[idx["ticker"]], r[idx["bar_date"]], r[idx["open"]],
                            r[idx["high"]], r[idx["low"]], r[idx["close"]], r[idx["volume"]]])
                rows_parsed += 1
                if rows_parsed % 500000 == 0:
                    buf.seek(0)
                    cur.copy_expert("COPY _venv_bars FROM STDIN WITH (FORMAT csv)", buf)
                    buf.seek(0); buf.truncate(0)
                    log(f"daily_bars: staged {rows_parsed} rows")
        buf.seek(0)
        cur.copy_expert("COPY _venv_bars FROM STDIN WITH (FORMAT csv)", buf)
        cur.execute("""INSERT INTO daily_bars (symbol, bar_date, open, high, low, close, volume)
            SELECT symbol, bar_date, open, high, low, close, volume FROM _venv_bars
            ON CONFLICT (symbol, bar_date) DO UPDATE SET open=EXCLUDED.open,
              high=EXCLUDED.high, low=EXCLUDED.low, close=EXCLUDED.close,
              volume=EXCLUDED.volume""")
    conn.commit()
    os.remove(local_gz)
    summary["tables"].append(dict(table="daily_bars", transport="s3_gzip",
        rows_imported=rows_parsed, chunks_count=1, state="complete",
        bytes_downloaded=nbytes,
        wall_time_seconds=(datetime.now(timezone.utc) - t0).total_seconds()))
    log(f"daily_bars: {rows_parsed} rows from {nbytes} gz bytes")
    return "ok"


def run_chunked_spec(task_id, conn, ck, summary, spec):
    t0 = datetime.now(timezone.utc)
    src = int(prod_scalar(task_id, spec["count_sql"]))
    start = ck.get(spec["table"], {}).get("last_key_value", spec["start_key"])
    total, chunks = chunked_import(task_id, conn, spec["table"], spec["build"],
        spec["key"], spec["temp_ddl"], spec["temp_cols"], spec["upsert"], ck, start)
    summary["tables"].append(dict(table=spec["table"], transport="ecs_exec_chunked",
        source_count_at_start=src, rows_imported=total, chunks_count=chunks, state="complete",
        wall_time_seconds=(datetime.now(timezone.utc) - t0).total_seconds()))


def find_task():
    ecs = boto3.client("ecs", region_name=REGION)
    arns = ecs.list_tasks(cluster=CLUSTER, serviceName=SERVICE,
                          desiredStatus="RUNNING").get("taskArns", [])
    return arns[0].split("/")[-1] if arns else None


def main():
    started = datetime.now(timezone.utc)
    task_id = find_task()
    if not task_id:
        log("STOP: no running tfe-web task found.")
        sys.exit(1)
    log(f"using ECS task {task_id}")
    ck = ckpt_load()
    conn = psycopg2.connect(LOCAL_DSN)
    summary = {"started_at": started.isoformat(), "ecs_task_arn": task_id, "tables": []}
    any_fail = False

    # Chunked tables (each isolated; a failure stops that table, not the rest)
    for spec_fn in (spec_runtime_decisions_latest, spec_runtime_symbols,
                    spec_personal_trade_ledger):
        spec = spec_fn()
        try:
            run_chunked_spec(task_id, conn, ck, summary, spec)
        except Exception as e:
            conn.rollback()
            any_fail = True
            summary["tables"].append(dict(table=spec["table"], state="failed", error=str(e)[:400]))
            log(f"STOP {spec['table']}: {str(e)[:300]}")

    for fn in (lambda: import_history(task_id, conn, ck, summary),
               lambda: import_daily_bars(conn, summary)):
        try:
            r = fn()
            if r == "stopped":
                any_fail = True
        except Exception as e:
            conn.rollback()
            any_fail = True
            summary["tables"].append(dict(state="failed", error=str(e)[:400]))
            log(f"STOP (large table): {str(e)[:300]}")

    summary["ended_at"] = datetime.now(timezone.utc).isoformat()
    summary["total_wall_time_seconds"] = (datetime.now(timezone.utc) - started).total_seconds()
    summary["final_state"] = "partial" if any_fail else "complete"
    conn.close()

    if not any_fail and os.path.exists(CKPT_PATH):
        os.remove(CKPT_PATH)
        log("checkpoint deleted (clean completion)")

    path = f"{SUMMARY_DIR}/validation_env_import_{started.strftime('%Y%m%dT%H%M%SZ')}.json"
    with open(path, "w") as f:
        json.dump(summary, f, indent=2)
    log(f"summary → {path} | state={summary['final_state']}")
    sys.exit(0 if not any_fail else 1)


if __name__ == "__main__":
    main()
