#!/usr/bin/env python3
"""
tools/validation_env_import.py — Mode B production import (V4B transport).

Imports production tables (read-only) into local `tfe_validation` Postgres.
See docs/VALIDATION_ENVIRONMENT_SPEC.md §3.1 (Mode B).

TRANSPORT (wC decision, TFE-CMD-VENV-IMPORT-V4B):
  S3 for all bulk tables. ECS Exec only triggers an in-container helper that
  COPYs a projection to a tempfile, gzips, and uploads via boto3 (the aws CLI
  is absent in the container; boto3 is what rebuild_uf_snapshot.py uses).
  Only the helper's small JSON summary returns over SSM — no bulk data on the
  SSM channel (the V3 lesson: SSM truncates large payloads, even ~100KB).

  S3 prefix: runtime-refresh-checkpoints/ — the only prefix the container's
  tfe-ecs-task-role can write (validation-env-exports/ is IAM-denied).
  Filenames namespaced venv_export__<table>[__<window>].csv.gz so they never
  collide with prod-owned objects (daily_bars_export.csv.gz, uf_snapshot.json).

  daily_bars: imported in V3 from the prod-owned daily_bars_export.csv.gz
  (9,760,067 rows, 5y). SKIPPED here unless --force-daily-bars.

Read-only against production DB. New S3 writes only to venv_export__*.
Idempotent UPSERTs (V3 column maps). No credential values logged (§6.2 rule 5).
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
BUCKET = "tfe-codebuild-src-418384447921-us-east-1"
PREFIX = "runtime-refresh-checkpoints"          # writable prefix
LOCAL_DSN = "host=/var/run/postgresql dbname=tfe_validation user=postgres"
SUMMARY_DIR = "backups"
HELPER_PATH = "/tmp/venv_export_helper.py"      # ephemeral, in-container
HISTORY_MAX = 5_000_000

csv.field_size_limit(1 << 24)


def log(m):
    print(f"[venv-import] {m}", flush=True)


# ── In-container helper: COPY → gzip → boto3 upload; prints JSON summary ─────
HELPER_PY = r'''
import sys, base64, subprocess, gzip, shutil, os, boto3
bucket = "%s"
mode = sys.argv[1]
s3 = boto3.client("s3")
if mode == "scalar":
    sql = base64.b64decode(sys.argv[2]).decode(); key = sys.argv[3]
    r = subprocess.run(["psql", "-v", "ON_ERROR_STOP=1", "-At", "-c", sql],
                       capture_output=True, text=True)
    body = (r.stdout.strip() if r.returncode == 0 else "ERR:" + r.stderr[:300]).encode()
    s3.put_object(Bucket=bucket, Key=key, Body=body)
    sys.exit(0 if r.returncode == 0 else 1)
# export mode: argv = export <table> <b64proj> <s3key>
table = sys.argv[2]; proj = base64.b64decode(sys.argv[3]).decode(); s3key = sys.argv[4]
csvp, gzp = "/tmp/%%s.csv" %% table, "/tmp/%%s.csv.gz" %% table
try:
    r = subprocess.run(
        ["psql", "-v", "ON_ERROR_STOP=1", "-c",
         "\\copy (" + proj + ") to '" + csvp + "' with csv header"],
        capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write("PSQL_ERR:" + r.stderr[:600]); sys.exit(1)
    with open(csvp, "rb") as fi, gzip.open(gzp, "wb") as fo:
        shutil.copyfileobj(fi, fo)
    s3.upload_file(gzp, bucket, s3key)  # upload only on COPY success — no partials
finally:
    for p in (csvp, gzp):
        try: os.remove(p)
        except OSError: pass
''' % BUCKET


_SESSION_FLAKES = ("Cannot perform start session", "TargetNotConnected",
                   "start session: EOF", "Connection to destination")


def _exec(task_id, inner_bash, timeout=300, expect=None, attempts=4):
    """Run a command in-container via ECS Exec. Retries on transient SSM
    session-establishment flakes (e.g. 'Cannot perform start session: EOF'),
    which are not result failures — the helper never runs, so retry is safe."""
    import time
    b64 = base64.b64encode(inner_bash.encode()).decode()
    cmd = ["aws", "ecs", "execute-command", "--region", REGION, "--cluster", CLUSTER,
           "--task", task_id, "--container", CONTAINER, "--interactive",
           "--command", f"bash -lc 'echo {b64} | base64 -d | bash'"]
    out = ""
    for a in range(attempts):
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = p.stdout + "\n" + p.stderr
        if expect and expect in out:
            return out
        if not any(f in out for f in _SESSION_FLAKES):
            return out  # genuine result (or a non-transient error)
        time.sleep(3 + a * 2)  # transient session flake — back off and retry
    return out


def stage_helper(task_id):
    hb64 = base64.b64encode(HELPER_PY.encode()).decode()
    inner = f"echo {hb64} | base64 -d > {HELPER_PATH}; wc -l {HELPER_PATH} && echo @@STAGED@@"
    out = _exec(task_id, inner, timeout=60, expect="@@STAGED@@")
    if "@@STAGED@@" not in out:
        raise RuntimeError(f"helper staging failed; output tail:\n{out[-500:]}")


def run_helper_fg(task_id, args, timeout=600):
    """Run the staged helper in the FOREGROUND (blocking) of the SSM session.
    Two facts learned the hard way:
      - Detached procs (nohup/setsid) are SIGKILLed by SSM on session end.
      - A silent blocking command DOES complete (tested to 12s+); the
        'Cannot perform start session: EOF' line is spurious plugin-teardown
        noise, not a failure.
      - The completion marker MUST be `echo` (newline-flushed); `printf`
        without a newline is block-buffered and gets lost on teardown.
    So: run the helper blocking, then echo a flushed completion marker. The
    `expect` match in _exec returns success even alongside the EOF noise."""
    a = " ".join(args)
    inner = (f"python3 {HELPER_PATH} {a} >/tmp/venv_helper.log 2>&1; RC=$?; "
             f"echo @@DONE@@RC=${{RC}}@@; [ $RC -ne 0 ] && cat /tmp/venv_helper.log; true")
    out = _exec(task_id, inner, timeout=timeout, expect="@@DONE@@RC=0@@")
    if "@@DONE@@RC=0@@" not in out:
        raise RuntimeError(f"helper failed (no clean completion); tail:\n{out[-600:]}")
    return out


def export_to_s3(task_id, table, projection, s3_key):
    """Foreground+heartbeat helper writes the gzip to S3; then HEAD for metadata."""
    pb64 = base64.b64encode(projection.encode()).decode()
    run_helper_fg(task_id, ["export", table, pb64, s3_key])
    s3 = boto3.client("s3", region_name=REGION)
    h = s3.head_object(Bucket=BUCKET, Key=s3_key)
    return {"s3_etag": h["ETag"].strip('"'), "gz_bytes": h["ContentLength"]}


def container_scalar(task_id, sql):
    """Scalar COUNT via a foreground helper that writes the result to an S3
    sidecar; read it back, then delete the sidecar."""
    s3 = boto3.client("s3", region_name=REGION)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    key = f"{PREFIX}/venv_export__scalar_{ts}.txt"
    sb64 = base64.b64encode(sql.encode()).decode()
    run_helper_fg(task_id, ["scalar", sb64, key], timeout=300)
    val = s3.get_object(Bucket=BUCKET, Key=key)["Body"].read().decode().strip()
    try:
        s3.delete_object(Bucket=BUCKET, Key=key)
    except Exception:
        pass
    return val


def download_and_upsert(conn, s3_key, temp_ddl, temp_cols, upsert_sql):
    s3 = boto3.client("s3", region_name=REGION)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    local = f"/tmp/venv_import_{os.path.basename(s3_key)}_{ts}"
    s3.download_file(BUCKET, s3_key, local)
    try:
        with gzip.open(local, "rt") as f:
            reader = csv.reader(f)
            next(reader, None)                       # drop CSV header
            body = io.StringIO()
            w = csv.writer(body)
            n = 0
            for row in reader:
                w.writerow(row); n += 1
        body.seek(0)
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS _venv_tmp")
            cur.execute(temp_ddl)
            if n:
                cur.copy_expert(
                    f"COPY _venv_tmp ({','.join(temp_cols)}) FROM STDIN WITH (FORMAT csv)", body)
            cur.execute(upsert_sql)
        conn.commit()
        return n
    finally:
        try: os.remove(local)
        except OSError: pass


# ── Per-table specs (V3 column maps, verbatim) ──────────────────────────────
def specs():
    rdl_cols = ["ticker", "run_id", "generated_at_utc", "snapshot_row_json",
                "decision_label", "reason_code", "reason_text"]
    rs_cols = ["ticker", "run_id", "generated_at_utc", "asset_type", "quote_type",
               "exchange", "company_name", "sector", "industry", "country", "market_cap",
               "shares_outstanding", "float_shares", "profile_json", "updated_at"]
    ptl_cols = ["id", "ticker", "run_id", "signal_class", "spy_dk", "s_uf", "bar_count",
                "f_n", "d_k", "b_k", "vault_equity_at_signal", "risk_per_trade_pct",
                "dollar_allocation", "shares", "atr_14", "alpaca_order_id",
                "alpaca_take_profit_order_id", "alpaca_stop_loss_order_id",
                "entry_limit_price", "take_profit_price", "stop_loss_price", "time_in_force",
                "entry_filled_price", "entry_filled_at", "exit_filled_price", "exit_filled_at",
                "p_l", "p_l_pct", "exit_reason", "status", "rationale_json",
                "signal_detected_at", "created_at", "updated_at"]
    return [
        dict(table="runtime_decisions_latest",
             key=f"{PREFIX}/venv_export__runtime_decisions_latest.csv.gz",
             proj=("SELECT " + ",".join(rdl_cols) +
                   " FROM runtime_decisions_latest ORDER BY ticker ASC"),
             count="SELECT COUNT(*) FROM runtime_decisions_latest",
             temp_ddl="""CREATE TEMP TABLE _venv_tmp (ticker text, run_id text,
                 generated_at_utc timestamptz, snapshot_row_json jsonb,
                 decision_label text, reason_code text, reason_text text)""",
             temp_cols=rdl_cols,
             upsert="""INSERT INTO runtime_decisions_latest
                 (ticker,run_id,generated_at_utc,snapshot_row_json,decision_label,
                  reason_code,reason_text,kernel_sha,source)
                 SELECT ticker,run_id,generated_at_utc,snapshot_row_json,decision_label,
                  reason_code,reason_text,NULL,'production_import' FROM _venv_tmp
                 ON CONFLICT (ticker) DO UPDATE SET run_id=EXCLUDED.run_id,
                  generated_at_utc=EXCLUDED.generated_at_utc,
                  snapshot_row_json=EXCLUDED.snapshot_row_json,
                  decision_label=EXCLUDED.decision_label,reason_code=EXCLUDED.reason_code,
                  reason_text=EXCLUDED.reason_text,source=EXCLUDED.source"""),
        dict(table="runtime_symbols",
             key=f"{PREFIX}/venv_export__runtime_symbols.csv.gz",
             proj="SELECT " + ",".join(rs_cols) + " FROM runtime_symbols ORDER BY ticker ASC",
             count="SELECT COUNT(*) FROM runtime_symbols",
             temp_ddl="""CREATE TEMP TABLE _venv_tmp (ticker text, run_id text,
                 generated_at_utc timestamptz, asset_type text, quote_type text,
                 exchange text, company_name text, sector text, industry text,
                 country text, market_cap float8, shares_outstanding float8,
                 float_shares float8, profile_json jsonb, updated_at timestamptz)""",
             temp_cols=rs_cols,
             upsert=f"""INSERT INTO runtime_symbols ({','.join(rs_cols)})
                 SELECT {','.join(rs_cols)} FROM _venv_tmp
                 ON CONFLICT (ticker) DO UPDATE SET
                 {','.join(f'{c}=EXCLUDED.{c}' for c in rs_cols if c != 'ticker')}"""),
        dict(table="personal_trade_ledger",
             key=f"{PREFIX}/venv_export__personal_trade_ledger.csv.gz",
             proj="SELECT " + ",".join(ptl_cols) + " FROM personal_trade_ledger ORDER BY id ASC",
             count="SELECT COUNT(*) FROM personal_trade_ledger",
             temp_ddl="""CREATE TEMP TABLE _venv_tmp (
                 id bigint, ticker text, run_id text, signal_class text, spy_dk int, s_uf float8,
                 bar_count int, f_n float8, d_k int, b_k float8, vault_equity_at_signal float8,
                 risk_per_trade_pct float8, dollar_allocation float8, shares int, atr_14 float8,
                 alpaca_order_id text, alpaca_take_profit_order_id text, alpaca_stop_loss_order_id text,
                 entry_limit_price float8, take_profit_price float8, stop_loss_price float8,
                 time_in_force text, entry_filled_price float8, entry_filled_at timestamptz,
                 exit_filled_price float8, exit_filled_at timestamptz, p_l float8, p_l_pct float8,
                 exit_reason text, status text, rationale_json jsonb, signal_detected_at timestamptz,
                 created_at timestamptz, updated_at timestamptz)""",
             temp_cols=ptl_cols,
             upsert=f"""INSERT INTO personal_trade_ledger ({','.join(ptl_cols)})
                 SELECT {','.join(ptl_cols)} FROM _venv_tmp
                 ON CONFLICT (id) DO UPDATE SET
                 {','.join(f'{c}=EXCLUDED.{c}' for c in ptl_cols if c not in ('id','rationale_json'))},
                 rationale_json = personal_trade_ledger.rationale_json || EXCLUDED.rationale_json"""),
    ]


def history_spec():
    win = "generated_at_utc >= NOW() - INTERVAL '90 days'"
    cols = ["ticker", "run_id", "generated_at_utc", "snapshot_row_json", "prod_source"]
    return dict(
        table="runtime_decisions_history",
        key=f"{PREFIX}/venv_export__runtime_decisions_history__90d.csv.gz",
        count=f"SELECT COUNT(*) FROM runtime_decisions_history WHERE {win}",
        proj=("SELECT ticker, run_id, generated_at_utc, snapshot_row_json, source AS prod_source "
              f"FROM runtime_decisions_history WHERE {win} "
              "ORDER BY generated_at_utc ASC, ticker ASC"),
        temp_ddl="""CREATE TEMP TABLE _venv_tmp (ticker text, run_id text,
            generated_at_utc timestamptz, snapshot_row_json jsonb, prod_source text)""",
        temp_cols=cols,
        upsert="""INSERT INTO runtime_decisions_history
            (ticker,run_id,generated_at_utc,snapshot_row_json,decision_label,kernel_sha,source)
            SELECT ticker,run_id,generated_at_utc,snapshot_row_json,NULL,NULL,
              COALESCE(prod_source,'production_import') FROM _venv_tmp
            ON CONFLICT (ticker, generated_at_utc) DO NOTHING""")


def find_task():
    ecs = boto3.client("ecs", region_name=REGION)
    arns = ecs.list_tasks(cluster=CLUSTER, serviceName=SERVICE,
                          desiredStatus="RUNNING").get("taskArns", [])
    return arns[0].split("/")[-1] if arns else None


def local_count(conn, table):
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        return cur.fetchone()[0]


def run_table(task_id, conn, summary, spec, src_count):
    t0 = datetime.now(timezone.utc)
    before = local_count(conn, spec["table"])
    exp = export_to_s3(task_id, spec["table"], spec["proj"], spec["key"])
    got = download_and_upsert(conn, spec["key"], spec["temp_ddl"], spec["temp_cols"], spec["upsert"])
    after = local_count(conn, spec["table"])
    summary["tables"].append(dict(
        table=spec["table"], transport="s3_via_boto3", s3_object_key=spec["key"],
        s3_object_size_bytes=exp.get("gz_bytes"), s3_etag=exp.get("s3_etag"),
        source_rows_reported=src_count, helper_rows_copied=exp.get("rows_copied"),
        local_rows_before=before, local_rows_after=after, csv_rows_imported=got,
        wall_time_seconds=(datetime.now(timezone.utc) - t0).total_seconds(), errors=[]))
    flag = "" if after >= src_count else f"  ⚠ local({after}) < source({src_count})"
    log(f"{spec['table']}: source={src_count} helper_copied={exp.get('rows_copied')} "
        f"before={before} after={after}{flag}")


def main():
    force_db = "--force-daily-bars" in sys.argv
    started = datetime.now(timezone.utc)
    task_id = find_task()
    if not task_id:
        log("STOP: no running tfe-web task found.")
        sys.exit(1)
    log(f"using ECS task {task_id}")
    stage_helper(task_id)
    log("helper staged in container")

    conn = psycopg2.connect(LOCAL_DSN)
    summary = {"started_at": started.isoformat(), "ecs_task_arn": task_id,
               "c_investigation_result": {
                   "uf_snapshot_usable": False,
                   "reasoning": "uf_snapshot.json rows carry ticker/run_id/generated_at_utc and the "
                                "raw kernel tuple, but decision_label/reason_code/reason_text and "
                                "snapshot_row_json are ABSENT — not a proxy for runtime_decisions_latest",
                   "fields_present": ["ticker", "run_id", "generated_at_utc", "kernel_tuple(43 fields)"]},
               "tables": [], "skipped": {}}
    any_fail = False

    for spec in specs():
        try:
            src = int(container_scalar(task_id, spec["count"]))
            run_table(task_id, conn, summary, spec, src)
        except Exception as e:
            conn.rollback(); any_fail = True
            summary["tables"].append(dict(table=spec["table"], state="failed", errors=[str(e)[:400]]))
            log(f"STOP {spec['table']}: {str(e)[:300]}")

    # history with the 5M ceiling
    hs = history_spec()
    try:
        hcount = int(container_scalar(task_id, hs["count"]))
        summary["history_90d_count"] = hcount
        log(f"runtime_decisions_history 90d count = {hcount}")
        if hcount > HISTORY_MAX:
            summary["skipped"]["runtime_decisions_history"] = f"90d count {hcount} > {HISTORY_MAX}"
            any_fail = True
            log(f"STOP runtime_decisions_history: {hcount} > {HISTORY_MAX}")
        else:
            run_table(task_id, conn, summary, hs, hcount)
    except Exception as e:
        conn.rollback(); any_fail = True
        summary["tables"].append(dict(table="runtime_decisions_history", state="failed", errors=[str(e)[:400]]))
        log(f"STOP runtime_decisions_history: {str(e)[:300]}")

    if not force_db:
        summary["skipped"]["daily_bars"] = "v3_complete (9,760,067 rows, 5y)"
        log("daily_bars: skipped (V3 import canonical; use --force-daily-bars to re-import)")

    summary["ended_at"] = datetime.now(timezone.utc).isoformat()
    summary["total_wall_time_seconds"] = (datetime.now(timezone.utc) - started).total_seconds()
    summary["final_state"] = "partial" if any_fail else "complete"
    conn.close()
    path = f"{SUMMARY_DIR}/validation_env_import_v4b_{started.strftime('%Y%m%dT%H%M%SZ')}.json"
    with open(path, "w") as f:
        json.dump(summary, f, indent=2)
    log(f"summary → {path} | state={summary['final_state']}")
    sys.exit(0 if not any_fail else 1)


if __name__ == "__main__":
    main()
