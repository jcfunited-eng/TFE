#!/usr/bin/env python3
"""
tools/validation_env_import.py — Mode B production import via ECS Exec.

Imports production tables (read-only) into the local `tfe_validation`
Postgres so development/validation can run against production-equivalent
data. See docs/VALIDATION_ENVIRONMENT_SPEC.md §3.1 (Mode B).

ACCESS PATH (wC decision, TFE-CMD-VENV-IMPORT-BUILD-V2): ECS Exec into a
running tfe-web task. The Codespace cannot reach prod RDS directly (spec
§2) and the read-only secret resolves to the same VPC-locked endpoint, so
we run `psql` *inside* the container (which is in the VPC) and stream the
result back over the ECS Exec channel. NOT direct connect, NOT tunnel,
NOT snapshot.

Read-only against production: every prod query is `COPY (SELECT ...) TO
STDOUT` — no INSERT/UPDATE/DELETE/DDL on production. Output is base64-wrapped
between markers to survive the SSM TTY intact.

No SELECT *. Explicit column projections per table (per-table maps below).
Idempotent (UPSERT). No credential values or secret ARNs logged (spec §6.2
rule 5) — psql in the container authenticates from its own PG* env vars,
which never cross this channel.

Table order is small/high-value first, the two large streaming tables last,
so a large-table failure does not block the cheap imports (per the command's
"on any per-table failure, STOP further tables" rule).
"""

import csv
import io
import json
import subprocess
import sys
from datetime import datetime, timezone

import boto3
import psycopg2

# ── Config ──────────────────────────────────────────────────────────────────
REGION = "us-east-1"
CLUSTER = "tfe-web-cluster"          # verified live cluster (command said tfe-prod)
SERVICE = "tfe-web-service-lb"
CONTAINER = "tfe-web"
LOCAL_DSN = "host=/var/run/postgresql dbname=tfe_validation user=postgres"
SUMMARY_DIR = "backups"

MARK_B, MARK_E = "@@VENVB64START@@", "@@VENVB64END@@"


def log(msg):
    print(f"[venv-import] {msg}", flush=True)


# ── ECS Exec: run a read-only psql command in the container ─────────────────
def _exec_in_container(task_id, inner_bash, timeout=900):
    """Run inner_bash inside the container via ECS Exec; return its stdout.
    inner_bash is base64-wrapped so its quoting survives the --command arg."""
    import base64
    b64 = base64.b64encode(inner_bash.encode()).decode()
    cmd = [
        "aws", "ecs", "execute-command", "--region", REGION,
        "--cluster", CLUSTER, "--task", task_id, "--container", CONTAINER,
        "--interactive", "--command",
        f"bash -lc 'echo {b64} | base64 -d | bash'",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return proc.stdout + "\n" + proc.stderr


def _extract_b64_payload(raw):
    """Pull the base64 blob between markers and decode to bytes. Returns None
    if markers are absent (command failed inside the container)."""
    import base64
    if MARK_B not in raw or MARK_E not in raw:
        return None
    blob = raw.split(MARK_B, 1)[1].split(MARK_E, 1)[0]
    blob = "".join(blob.split())  # strip whitespace/newlines the TTY may inject
    try:
        return base64.b64decode(blob)
    except Exception:
        return None


def prod_scalar(task_id, sql):
    """Run a scalar SELECT in prod, return the single value as text."""
    inner = (
        "set -euo pipefail; "
        f"printf '{MARK_B}'; "
        f'psql -v ON_ERROR_STOP=1 -At -c "{sql}" | base64 -w0; '
        f"printf '{MARK_E}'"
    )
    raw = _exec_in_container(task_id, inner, timeout=120)
    payload = _extract_b64_payload(raw)
    if payload is None:
        raise RuntimeError(f"prod scalar failed; container output tail:\n{raw[-800:]}")
    return payload.decode().strip()


def prod_copy_csv(task_id, projection_sql, timeout=900):
    """COPY (projection_sql) TO STDOUT as CSV in prod; return decoded CSV text."""
    inner = (
        "set -euo pipefail; "
        f"printf '{MARK_B}'; "
        f"psql -v ON_ERROR_STOP=1 -c \"COPY ({projection_sql}) TO STDOUT WITH (FORMAT csv)\" | base64 -w0; "
        f"printf '{MARK_E}'"
    )
    raw = _exec_in_container(task_id, inner, timeout=timeout)
    payload = _extract_b64_payload(raw)
    if payload is None:
        raise RuntimeError(
            f"prod COPY failed (no marker / decode error); container output tail:\n{raw[-1200:]}"
        )
    return payload.decode()


# ── Local helpers ───────────────────────────────────────────────────────────
def local_count(cur, table):
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    return cur.fetchone()[0]


def load_csv_to_temp(cur, temp_ddl, csv_text, temp_cols):
    cur.execute("DROP TABLE IF EXISTS _venv_tmp")
    cur.execute(temp_ddl)
    if csv_text.strip():
        cur.copy_expert(
            f"COPY _venv_tmp ({','.join(temp_cols)}) FROM STDIN WITH (FORMAT csv)",
            io.StringIO(csv_text),
        )


# ── Per-table specs (explicit projections; NO SELECT *) ─────────────────────
PTL_COLS = [
    "id", "ticker", "run_id", "signal_class", "spy_dk", "s_uf", "bar_count",
    "f_n", "d_k", "b_k", "vault_equity_at_signal", "risk_per_trade_pct",
    "dollar_allocation", "shares", "atr_14", "alpaca_order_id",
    "alpaca_take_profit_order_id", "alpaca_stop_loss_order_id",
    "entry_limit_price", "take_profit_price", "stop_loss_price", "time_in_force",
    "entry_filled_price", "entry_filled_at", "exit_filled_price", "exit_filled_at",
    "p_l", "p_l_pct", "exit_reason", "status", "rationale_json",
    "signal_detected_at", "created_at", "updated_at",
]
PTL_TEMP_DDL = """CREATE TEMP TABLE _venv_tmp (
  id bigint, ticker text, run_id text, signal_class text, spy_dk int, s_uf float8,
  bar_count int, f_n float8, d_k int, b_k float8, vault_equity_at_signal float8,
  risk_per_trade_pct float8, dollar_allocation float8, shares int, atr_14 float8,
  alpaca_order_id text, alpaca_take_profit_order_id text, alpaca_stop_loss_order_id text,
  entry_limit_price float8, take_profit_price float8, stop_loss_price float8,
  time_in_force text, entry_filled_price float8, entry_filled_at timestamptz,
  exit_filled_price float8, exit_filled_at timestamptz, p_l float8, p_l_pct float8,
  exit_reason text, status text, rationale_json jsonb, signal_detected_at timestamptz,
  created_at timestamptz, updated_at timestamptz )"""
PTL_SET = ", ".join(
    f"{c}=EXCLUDED.{c}" for c in PTL_COLS if c not in ("id", "rationale_json")
)
RS_COLS = [
    "ticker", "run_id", "generated_at_utc", "asset_type", "quote_type", "exchange",
    "company_name", "sector", "industry", "country", "market_cap",
    "shares_outstanding", "float_shares", "profile_json", "updated_at",
]
RS_TEMP_DDL = """CREATE TEMP TABLE _venv_tmp (
  ticker text, run_id text, generated_at_utc timestamptz, asset_type text,
  quote_type text, exchange text, company_name text, sector text, industry text,
  country text, market_cap float8, shares_outstanding float8, float_shares float8,
  profile_json jsonb, updated_at timestamptz )"""
RS_SET = ", ".join(f"{c}=EXCLUDED.{c}" for c in RS_COLS if c != "ticker")


def import_runtime_decisions_latest(task_id, cur):
    proj = ("SELECT ticker, run_id, generated_at_utc, snapshot_row_json, "
            "decision_label, reason_code, reason_text FROM runtime_decisions_latest")
    src = int(prod_scalar(task_id, f"SELECT COUNT(*) FROM ({proj}) q"))
    csv_text = prod_copy_csv(task_id, proj)
    cols = ["ticker", "run_id", "generated_at_utc", "snapshot_row_json",
            "decision_label", "reason_code", "reason_text"]
    load_csv_to_temp(cur, """CREATE TEMP TABLE _venv_tmp (
        ticker text, run_id text, generated_at_utc timestamptz, snapshot_row_json jsonb,
        decision_label text, reason_code text, reason_text text )""", csv_text, cols)
    cur.execute("""
        INSERT INTO runtime_decisions_latest
          (ticker, run_id, generated_at_utc, snapshot_row_json, decision_label,
           reason_code, reason_text, kernel_sha, source)
        SELECT ticker, run_id, generated_at_utc, snapshot_row_json, decision_label,
               reason_code, reason_text, NULL, 'production_import' FROM _venv_tmp
        ON CONFLICT (ticker) DO UPDATE SET
           run_id=EXCLUDED.run_id, generated_at_utc=EXCLUDED.generated_at_utc,
           snapshot_row_json=EXCLUDED.snapshot_row_json,
           decision_label=EXCLUDED.decision_label, reason_code=EXCLUDED.reason_code,
           reason_text=EXCLUDED.reason_text, source=EXCLUDED.source
        -- kernel_sha intentionally left alone (preserve Mode A value if present)
    """)
    return src


def import_runtime_symbols(task_id, cur):
    proj = "SELECT " + ", ".join(RS_COLS) + " FROM runtime_symbols"
    src = int(prod_scalar(task_id, f"SELECT COUNT(*) FROM ({proj}) q"))
    csv_text = prod_copy_csv(task_id, proj)
    load_csv_to_temp(cur, RS_TEMP_DDL, csv_text, RS_COLS)
    cur.execute(f"""
        INSERT INTO runtime_symbols ({','.join(RS_COLS)})
        SELECT {','.join(RS_COLS)} FROM _venv_tmp
        ON CONFLICT (ticker) DO UPDATE SET {RS_SET}
    """)
    return src


def import_personal_trade_ledger(task_id, cur):
    proj = "SELECT " + ", ".join(PTL_COLS) + " FROM personal_trade_ledger"
    src = int(prod_scalar(task_id, f"SELECT COUNT(*) FROM ({proj}) q"))
    csv_text = prod_copy_csv(task_id, proj)
    load_csv_to_temp(cur, PTL_TEMP_DDL, csv_text, PTL_COLS)
    cur.execute(f"""
        INSERT INTO personal_trade_ledger ({','.join(PTL_COLS)})
        SELECT {','.join(PTL_COLS)} FROM _venv_tmp
        ON CONFLICT (id) DO UPDATE SET {PTL_SET},
           rationale_json = personal_trade_ledger.rationale_json || EXCLUDED.rationale_json
    """)
    return src


def import_runtime_decisions_history(task_id, cur):
    proj = ("SELECT ticker, run_id, generated_at_utc, snapshot_row_json, source "
            "FROM runtime_decisions_history "
            "WHERE generated_at_utc >= NOW() - INTERVAL '90 days'")
    src = int(prod_scalar(task_id, f"SELECT COUNT(*) FROM ({proj}) q"))
    csv_text = prod_copy_csv(task_id, proj)
    cols = ["ticker", "run_id", "generated_at_utc", "snapshot_row_json", "prod_source"]
    load_csv_to_temp(cur, """CREATE TEMP TABLE _venv_tmp (
        ticker text, run_id text, generated_at_utc timestamptz,
        snapshot_row_json jsonb, prod_source text )""", csv_text, cols)
    cur.execute("""
        INSERT INTO runtime_decisions_history
          (ticker, run_id, generated_at_utc, snapshot_row_json, decision_label,
           kernel_sha, source)
        SELECT ticker, run_id, generated_at_utc, snapshot_row_json, NULL, NULL,
               COALESCE(prod_source, 'production_import') FROM _venv_tmp
        ON CONFLICT (ticker, generated_at_utc) DO NOTHING
    """)
    return src


def import_daily_bars(task_id, cur):
    # Chunk by year to keep each ECS-Exec payload bounded (5y of bars can be
    # very large). Still one logical table import; the COPY stays read-only.
    base = ("SELECT ticker, bar_date, open, high, low, close, volume FROM daily_bars "
            "WHERE bar_date >= CURRENT_DATE - INTERVAL '5 years'")
    src = int(prod_scalar(task_id, f"SELECT COUNT(*) FROM ({base}) q"))
    cols = ["ticker", "bar_date", "open", "high", "low", "close", "volume"]
    cur.execute("DROP TABLE IF EXISTS _venv_tmp")
    cur.execute("""CREATE TEMP TABLE _venv_tmp (
        ticker text, bar_date date, open float8, high float8, low float8,
        close float8, volume bigint )""")
    for yrs_back in range(5, 0, -1):
        lo = f"CURRENT_DATE - INTERVAL '{yrs_back} years'"
        hi = f"CURRENT_DATE - INTERVAL '{yrs_back - 1} years'"
        chunk = (f"SELECT ticker, bar_date, open, high, low, close, volume "
                 f"FROM daily_bars WHERE bar_date >= {lo} AND bar_date < {hi}")
        csv_text = prod_copy_csv(task_id, chunk)
        if csv_text.strip():
            cur.copy_expert(
                f"COPY _venv_tmp ({','.join(cols)}) FROM STDIN WITH (FORMAT csv)",
                io.StringIO(csv_text),
            )
        log(f"daily_bars: streamed chunk year-{yrs_back}")
    cur.execute("""
        INSERT INTO daily_bars (symbol, bar_date, open, high, low, close, volume)
        SELECT ticker, bar_date, open, high, low, close, volume FROM _venv_tmp
        ON CONFLICT (symbol, bar_date) DO UPDATE SET
           open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low,
           close=EXCLUDED.close, volume=EXCLUDED.volume
    """)
    return src


# Order: cheap/high-value first, large streaming tables last.
TABLES = [
    ("runtime_decisions_latest", import_runtime_decisions_latest),
    ("runtime_symbols", import_runtime_symbols),
    ("personal_trade_ledger", import_personal_trade_ledger),
    ("runtime_decisions_history", import_runtime_decisions_history),
    ("daily_bars", import_daily_bars),
]


def find_task():
    ecs = boto3.client("ecs", region_name=REGION)
    arns = ecs.list_tasks(cluster=CLUSTER, serviceName=SERVICE,
                          desiredStatus="RUNNING").get("taskArns", [])
    if not arns:
        return None
    return arns[0].split("/")[-1]


def main():
    started = datetime.now(timezone.utc)
    task_id = find_task()
    if not task_id:
        log("STOP: no running tfe-web task found.")
        sys.exit(1)
    log(f"using ECS task {task_id}")

    conn = psycopg2.connect(LOCAL_DSN)
    conn.autocommit = False
    summary = {"started_at": started.isoformat(), "ecs_task_arn": task_id, "tables": []}
    exit_code = 0

    for name, fn in TABLES:
        with conn.cursor() as cur:
            before = local_count(cur, name)
        t0 = datetime.now(timezone.utc)
        try:
            with conn.cursor() as cur:
                src = fn(task_id, cur)
            conn.commit()
            with conn.cursor() as cur:
                after = local_count(cur, name)
            rec = {"table": name, "source_count": src, "local_count_before": before,
                   "local_count_after": after,
                   "seconds": (datetime.now(timezone.utc) - t0).total_seconds()}
            summary["tables"].append(rec)
            flag = "" if after >= src else f"  ⚠ local({after}) < source({src})"
            log(f"{name}: source={src} before={before} after={after}{flag}")
        except Exception as e:
            conn.rollback()
            summary["tables"].append({"table": name, "error": str(e)[:500],
                                      "local_count_before": before})
            log(f"STOP at {name}: {str(e)[:300]}")
            exit_code = 1
            break

    summary["ended_at"] = datetime.now(timezone.utc).isoformat()
    summary["exit_code"] = exit_code
    conn.close()

    ts = started.strftime("%Y%m%dT%H%M%SZ")
    path = f"{SUMMARY_DIR}/validation_env_import_{ts}.json"
    with open(path, "w") as f:
        json.dump(summary, f, indent=2)
    log(f"summary → {path}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
