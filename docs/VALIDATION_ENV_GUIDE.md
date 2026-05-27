# TFE Validation Environment — Usage Guide

**For any Claude/c1 session working on TFE.**

## Quick Start

### First time in a new Codespace:
```bash
bash tools/validation_env_setup.sh
python3 tools/validation_env_refresh.py --full  # 6-8 hours, run in background
```

### Returning to an existing Codespace:
```bash
# Start PostgreSQL (may have stopped)
pg_ctlcluster 17 main start

# Check if data is stale
psql -U postgres -d tfe_validation -c "SELECT MAX(generated_at_utc) FROM runtime_decisions_latest;"

# If stale (>48 hours), run incremental refresh
python3 tools/validation_env_refresh.py  # 1-2 hours, run in background
```

### Quick check that everything works:
```bash
psql -U postgres -d tfe_validation -c "
  SELECT COUNT(*) as tickers FROM runtime_decisions_latest;
  SELECT COUNT(*) as history_rows FROM runtime_decisions_history;
  SELECT COUNT(*) as bar_rows FROM daily_bars;
  SELECT ticker, decision_label, snapshot_row_json->>'D_k' as d_k, 
         snapshot_row_json->>'S_UF' as s_uf, kernel_sha 
  FROM runtime_decisions_latest WHERE ticker = 'SPY';
"
```

## Connection Details

```
Host: /var/run/postgresql (Unix socket)
Database: tfe_validation
User: postgres
Password: (none — trust auth for local connections)
```

Python:
```python
import psycopg2
conn = psycopg2.connect(host="/var/run/postgresql", dbname="tfe_validation", user="postgres")
```

## Tables

| Table | Rows (typical) | Purpose |
|---|---|---|
| `runtime_decisions_latest` | ~10,000 | Current kernel output per ticker |
| `runtime_decisions_history` | 50,000+ | Append-only history of kernel output |
| `daily_bars` | ~12M | Cached OHLCV bars from Polygon |
| `species_profiles` | ~10,000 | Per-stock structural personality |
| `personal_trade_ledger` | ~500 | Trade history from Alpaca |

## Key Columns

Every row in `runtime_decisions_latest` and `runtime_decisions_history` has:
- `kernel_sha` — git SHA of the kernel that produced this row
- `source` — `'validation_runner'` (Mode A) or `'production_import'` (Mode B)
- `snapshot_row_json` — full coupled tuple as JSONB

## Querying the Full Tuple

```sql
-- Get BSM's full structural state
SELECT 
    ticker,
    decision_label,
    snapshot_row_json->>'D_k' as d_k,
    snapshot_row_json->>'M_k' as m_k,
    snapshot_row_json->>'B_k' as b_k,
    snapshot_row_json->>'S_UF' as s_uf,
    snapshot_row_json->>'R_UF' as r_uf,
    snapshot_row_json->>'U_star_k' as u_star_k,
    snapshot_row_json->>'C_k' as c_k,
    snapshot_row_json->>'P_k' as p_k,
    snapshot_row_json->>'R_rev_k' as r_rev_k,
    snapshot_row_json->>'F_n' as f_n,
    snapshot_row_json->>'raw_x_m' as raw_x_m,
    snapshot_row_json->>'regime' as regime
FROM runtime_decisions_latest 
WHERE ticker = 'BSM';
```

```sql
-- Get a stock's structural history (for horse/herd assessment)
SELECT 
    generated_at_utc,
    snapshot_row_json->>'D_k' as d_k,
    snapshot_row_json->>'M_k' as m_k,
    snapshot_row_json->>'B_k' as b_k,
    snapshot_row_json->>'S_UF' as s_uf
FROM runtime_decisions_history 
WHERE ticker = 'BSM' 
ORDER BY generated_at_utc DESC 
LIMIT 30;
```

## Refresh Commands

```bash
# Incremental refresh (new bars only, ~1-2 hours)
python3 tools/validation_env_refresh.py

# Full refresh (all history, ~6-8 hours)
python3 tools/validation_env_refresh.py --full

# Specific tickers only (fast)
python3 tools/validation_env_refresh.py --tickers SPY,AAPL,BSM,VIRT
```

## Mode A vs Mode B

**Mode A (validation_env_refresh.py):** Fetches bars from Polygon, runs the LOCAL kernel, writes output. Tests NEW logic.

**Mode B (validation_env_import.py):** Imports PRODUCTION data from RDS export. Tests against what production ACTUALLY recorded. Required for horse/herd self-history lookups.

Mode B precedence: for historical timestamps, Mode B data takes priority. Mode A only writes timestamps after the most recent Mode B import.

## Do NOT

- Do not modify kernel code (`uf_core/`) to make validation pass — fix the divergence
- Do not delete `daily_bars` data to save space — it's the bar cache
- Do not connect to production RDS with write credentials
- Do not commit the local PostgreSQL data directory to git
- Do not assume validation env data is identical to production without running the equivalence check

## Files

| File | Purpose |
|---|---|
| `tools/validation_env_setup.sh` | One-time setup |
| `tools/validation_env_refresh.py` | Mode A refresh |
| `tools/validation_env_import.py` | Mode B import (TBD) |
| `tools/validation_env_check.py` | Equivalence verification (TBD) |
| `tools/validation_env_backup.sh` | pg_dump to S3 (TBD) |
| `docs/VALIDATION_ENVIRONMENT_SPEC.md` | Architecture spec |
| `docs/VALIDATION_ENV_GUIDE.md` | This file |
