# TFE Validation Environment — Architecture Specification

**Version:** 1.1 (revised per independent review)  
**Date:** May 27, 2026  
**Status:** REVISED DRAFT — Independent review complete, 8 points addressed  
**Author:** c1 (Claude Opus 4.6)  
**Reviewer:** web Claude (Opus 4.7)  
**Approver:** Joseph  

**Scope clarification:** This is a DEVELOPMENT validation environment, not a production-grade dual-deployment setup. It enables development and testing against production-equivalent data. Commercial-grade multi-tenant infrastructure with atomic dual-deployment is a future requirement, not in scope here.

---

## 1. Purpose

Build a local validation environment in the Codespace that mirrors production. Eliminates the recurring blocker: "can't query the production database from this Codespace." All new development, testing, and validation work runs against this environment before deploying to production.

## 2. Problem Statement

Current state:
- Production runs on AWS ECS with PostgreSQL (RDS). The Codespace cannot connect to production RDS.
- Development backtests use quarantine data from March 2026 — stale, different kernel (raw vs log L0), different L2 formulas.
- Every time we need current structural data, we either query CloudWatch logs (limited) or Alpaca API (positions only, no kernel output).
- The structural exit assessment (horse/herd/topology) requires access to per-bar kernel output history. Without a local database, it cannot be developed or tested.

Target state:
- Local PostgreSQL in the Codespace with the same schema as production
- Populated with current kernel output from the same universe production uses
- Refreshed on the same cadence as production (or on-demand)
- All kernel parameters identical to production (same L0, same constants, same everything)

## 3. Architecture

### 3.1 Two Operating Modes

**Mode A: Regenerate (development/testing)**
- Fetch bars from Polygon, run the local kernel, write output to local PG
- Tests NEW logic against current market data
- Used for: per-stock thresholds, exit assessment development, signal quality experiments

**Mode B: Import (historical validation)**
- Import production's runtime_decisions_history from an RDS export
- Tests against what production ACTUALLY recorded
- Used for: horse/herd self-history lookups, exit assessment backtesting against real trades, verifying that validation env matches production

**Export procedure for Mode B:**
1. AWS Console → RDS → tfe-prod-postgres → export snapshot to S3
2. Or: `pg_dump` via SSH tunnel to bastion host (documented in `tools/run_local_sync_via_tunnel.sh`)
3. Or: boto3 script using the read-only credentials in `tfe/codex/prod/postgres-readonly`
4. Import into local PG: `psql -f production_export.sql validation_db`
5. Frequency: weekly or on-demand before major development work

Both modes write to the same local PostgreSQL tables. Mode B data has a `source='production_import'` tag; Mode A data has `source='validation_runner'`.

**Coexistence rule:** Mode B takes precedence for historical timestamps. Mode A only writes rows with `generated_at_utc` AFTER the most recent Mode B import timestamp. If Mode A encounters a (ticker, date) that already exists from Mode B, it skips that row. This prevents mixed-version data for the same structural moment. Queries that span both modes should filter by `source` or `kernel_sha` when version consistency matters.

### 3.2 Components

```
┌─────────────────────────────────────────────┐
│  CODESPACE (Development/Validation)          │
│                                              │
│  ┌──────────────┐   ┌────────────────────┐  │
│  │ PostgreSQL   │   │ Validation Runner  │  │
│  │ (local)      │←──│ (Python)           │  │
│  │              │   │                    │  │
│  │ Tables:      │   │ - Fetches bars     │  │
│  │ - runtime_   │   │   from Polygon     │  │
│  │   decisions_ │   │ - Runs L0-L4       │  │
│  │   latest     │   │   kernel           │  │
│  │ - runtime_   │   │ - Writes output    │  │
│  │   decisions_ │   │   to local PG      │  │
│  │   history    │   │ - Same universe    │  │
│  │ - species_   │   │   as production    │  │
│  │   profiles   │   │                    │  │
│  └──────────────┘   └────────────────────┘  │
│         │                    │               │
│         │            ┌──────┴──────┐        │
│         │            │ Polygon API │        │
│         │            │ (OHLCV bars)│        │
│         │            └─────────────┘        │
│         │                                    │
│  ┌──────┴──────────────────────────────┐    │
│  │ Development Tools                    │    │
│  │ - Structural exit assessment         │    │
│  │ - Per-stock threshold calibration    │    │
│  │ - Horse/herd/topology lookups        │    │
│  │ - Backtest harness                   │    │
│  │ - Signal quality validation          │    │
│  └──────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

### 3.2 Database Schema

Mirrors production exactly. Three core tables:

**runtime_decisions_latest** (one row per ticker, latest kernel output):
```sql
CREATE TABLE runtime_decisions_latest (
    ticker TEXT PRIMARY KEY,
    decision_label TEXT,          -- Accumulate/Hold/Avoid
    reason_text TEXT,
    reason_code TEXT,
    snapshot_row_json JSONB,      -- full kernel tuple + metadata
    generated_at_utc TIMESTAMPTZ,
    run_id TEXT,
    kernel_sha TEXT,              -- git SHA of kernel code that produced this row
    source TEXT DEFAULT 'validation_runner'  -- 'validation_runner' or 'production_import'
);
```

**runtime_decisions_history** (append-only, per-refresh kernel output):
```sql
CREATE TABLE runtime_decisions_history (
    id SERIAL PRIMARY KEY,
    ticker TEXT NOT NULL,
    decision_label TEXT,
    snapshot_row_json JSONB,
    generated_at_utc TIMESTAMPTZ NOT NULL,
    run_id TEXT,
    kernel_sha TEXT,
    source TEXT DEFAULT 'validation_runner'
);
CREATE INDEX idx_rdh_ticker_date ON runtime_decisions_history(ticker, generated_at_utc);
```

The `kernel_sha` column records the git commit SHA of the kernel code at the time of computation. The validation runner captures this automatically via `git rev-parse HEAD`. This prevents intermixing outputs from different kernel versions without knowing.

**species_profiles** (weekly batch, per-stock structural personality):
```sql
CREATE TABLE species_profiles (
    ticker TEXT PRIMARY KEY,
    delta_bar DOUBLE PRECISION,
    sigma_bar DOUBLE PRECISION,
    classification TEXT,         -- calm/normal/volatile
    field_used TEXT,             -- D_k or s_n
    computed_at TIMESTAMPTZ,
    n_bars INT
);
```

**personal_trade_ledger** (mirror of production trade records — REQUIRED for exit assessment validation):
```sql
-- Same schema as production. Populated from:
-- 1. Alpaca order history API (closed orders with fill data)
-- 2. Production DB export (Mode B import)
-- Required by: structural exit assessment backtesting (would CUT/HOLD
-- have changed outcomes on past trades?)
```

### 3.3 Validation Runner

A Python script: `tools/validation_env_refresh.py`

Responsibilities:
1. Load universe from `massive_universe_stocks.json` (same 10K+ symbols as production)
2. For each symbol, fetch daily bars from Polygon (incremental — only new bars since last refresh)
3. Run production L0-L4 kernel (`uf_core/uf_structural_engine.py`) on the bars
4. Run snapshot state row builder (`uf_mdg_snapshot.py build_snapshot_state_row`) on the bars
5. Compute V3 basin decision (or Mar 26 filter, or whatever L5 is active)
6. Write snapshot_row_json to runtime_decisions_latest (upsert) and runtime_decisions_history (append)
7. Compute species profiles weekly

8. Sync epoch state: copy production's `g32_state.json` from S3 (`s3://tfe-codebuild-src-418384447921-us-east-1/runtime-refresh-checkpoints/`) to local filesystem. The exit assessment depends on epoch weighting — without current epoch state, the assessment runs but epoch weighting is N/A.

Runtime estimate: 6-8 hours for full refresh (revised from initial 3-hour estimate — accounts for Polygon latency, kernel computation overhead, and I/O). Incremental (new bars only) = 1-2 hours.

### 3.4 Bar Storage

Two options:

**Option A: Polygon on-demand (no local bar storage)**
- Fetch bars from Polygon each refresh
- Simpler, no storage cost
- Slower refresh (~3 hours)
- Uses API calls (we have unlimited)

**Option B: Local bar cache (same as production's daily_bars table)**
- First run fetches full history, subsequent runs fetch delta only
- Faster refresh after initial load (~30 min)
- Requires ~2-5 GB local storage
- Same architecture as production's bar_cache.py

Recommendation: **Option B** — matches production architecture, faster iteration.

## 4. Cost Analysis

### 4.1 Polygon API

- Plan: unlimited calls (confirmed)
- Full universe initial load: ~10K symbols × 5 years × 1 call each = ~10K calls
- Daily incremental: ~10K symbols × 1 call each = ~10K calls
- Cost: $0 (unlimited plan)

### 4.2 Codespace Storage

- PostgreSQL data: ~500MB for runtime_decisions tables (10K symbols × 100 refreshes)
- Bar cache: ~2-5 GB (10K symbols × 5 years daily bars)
- Total: ~3-6 GB
- Codespace has 32 GB storage — well within limits

### 4.3 Compute

- Kernel computation: ~1 second per symbol (L0-L4 + CV-1.0 sequential filter)
- Full refresh: 6-8 hours (runs overnight in background, no active time)
- Incremental refresh: 1-2 hours (runs in background after market close)
- No external compute cost — runs in Codespace

### 4.4 PostgreSQL

- Local installation in Codespace (free)
- No RDS cost
- Persists across Codespace sessions (in /var/lib/postgresql)

### 4.5 Total Incremental Cost

**$0/month.** All components use existing resources (Polygon unlimited plan, Codespace storage/compute).

## 5. Equivalence Guarantees

### 5.1 Kernel Equivalence

The validation environment MUST use:
- Same `uf_core/` Python files as production
- Same kernel constants (frozen since Feb 2026)
- Same L0 (log or raw — whichever production currently uses)
- Same snapshot state row computation
- Same L5 decision formula (V3 basin or replacement)

Verification: full-universe equivalence gate. On initial setup and after any kernel code change:
1. Export production's full runtime_decisions_latest table (Mode B import)
2. Run Mode A on the full universe at the same timestamp
3. Diff every field for every ticker with tolerance bands:
   - D_k, R_rev_k, P_k: must match exactly (discrete fields)
   - M_k, B_k, S_UF, R_UF, U_star_k, C_k: allowed ±1e-9 (floating point)
   - F_n, raw_x_m: allowed ±1e-6 (CV-1.0 integrator accumulation)
4. Any field exceeding tolerance triggers investigation
5. Results logged to `backups/validation_env_equivalence_report.json`

On daily incremental refreshes: spot-check 100 random tickers (fast) plus SPY, QQQ, and any tickers with open positions.

### 5.2 Universe Equivalence

Same `massive_universe_stocks.json` as production. Same filtering rules (stocks only, ETFs excluded from CH2, etc.).

### 5.3 Temporal Equivalence

Validation environment refresh runs AFTER production refresh completes. This ensures the same bars are available. A small temporal lag (hours) is acceptable — the structural fields change slowly (daily bars).

## 6. Security and Credentials

### 6.1 API Keys and Secrets

| Credential | Source | Storage | Usage |
|---|---|---|---|
| Polygon API key (MASSIVE_API_KEY) | `.env` file (repo root) | Local file, gitignored | Bar data fetching (Mode A) |
| AWS credentials | IAM role attached to Codespace, or `~/.aws/credentials` | Environment / AWS config | S3 backup, g32 sync, secrets manager |
| Production PG read-only | AWS Secrets Manager (`tfe/codex/prod/postgres-readonly`) | Fetched at runtime, never written to disk | Mode B import only |
| Alpaca credentials | AWS Secrets Manager (`tfe/market-data/prod`) | Fetched at runtime, never written to disk | Trade ledger import |
| Local PG credentials | Hardcoded for local dev (`validation/validation/localhost`) | Local only, no network exposure | Local database access |

### 6.2 Key Rules

1. **No credentials in git.** API keys, database passwords, and secrets MUST NOT appear in committed files. The `.env` file is gitignored. AWS Secrets Manager credentials are fetched at runtime via boto3.
2. **No production write access.** The validation environment uses READ-ONLY credentials for production database access (Mode B). The `tfe/codex/prod/postgres-readonly` secret has SELECT-only permissions. No INSERT, UPDATE, DELETE, or DDL on production.
3. **No credential sharing between environments.** The local PostgreSQL uses its own credentials. Production credentials are used ONLY for import (Mode B) and are not stored in the local database.
4. **S3 access scoped.** Backups write to a specific prefix (`validation-env-backups/`) in the existing TFE S3 bucket. The IAM role should be scoped to that prefix. g32 sync reads from `runtime-refresh-checkpoints/` (read-only).
5. **Secrets rotation.** If any credential is exposed (logged, committed, copied to a file), rotate immediately via AWS Secrets Manager. The validation runner does NOT log credential values — only connection status (success/fail).
6. **Local PG is not network-accessible.** PostgreSQL listens on localhost only (`listen_addresses = 'localhost'`). No external connections to the validation database.

### 6.3 Data Classification

| Data | Classification | Handling |
|---|---|---|
| Kernel output (structural tuples) | Trade secret | Local only, not exported except to S3 backup (encrypted at rest) |
| Bar data (OHLCV from Polygon) | Licensed market data | Subject to Polygon terms of service, not redistributable |
| Trade ledger | Confidential | Contains position sizes, entry/exit prices, P&L |
| Species profiles | Internal | Derived from kernel output, same handling |
| Epoch state | Internal | Macro assessment, not sensitive individually |

## 7. Governance

### 7.1 Refresh Cadence and Triggering

- **Full refresh:** Weekly (Sunday night) — rebuilds all kernel output from scratch
- **Incremental refresh:** Daily (after market close) — fetches new bars, re-runs kernel on updated data
- **On-demand refresh:** Manual trigger for specific tickers or the full universe

**Trigger mechanism:** Manual invocation via `python3 tools/validation_env_refresh.py [--full | --incremental | --tickers SPY,AAPL]`. NOT automated via cron or GitHub Actions — the Codespace may be suspended and automated jobs would fail silently. The validation runner checks Codespace uptime and warns if it hasn't been refreshed in >48 hours on startup.

**When Codespace is suspended:** Refresh skips. On next session start, the validation runner detects stale data (last refresh timestamp) and prompts for incremental refresh. No queue — just run it when needed.

**Backup trigger:** `pg_dump` runs as part of the refresh script's cleanup phase. Also available standalone via `tools/validation_env_backup.sh`.

### 7.2 Schema Migrations

Any schema change to production MUST be mirrored to the validation environment before deploying. The validation runner script checks schema compatibility on startup.

### 7.3 Release Process

Before any code deploys to production:
1. Run the change against the validation environment
2. Verify kernel output hasn't regressed (reference ticker check)
3. Run relevant tests (exit assessment, signal quality, etc.)
4. Document results in deploy evidence

### 7.4 Data Retention

- runtime_decisions_history: retain 6 months (rolling window)
- Bar cache: retain 5 years (matches Polygon availability)
- Species profiles: retain latest only (weekly overwrite)

## 8. Implementation Plan

### Phase 1: Database Setup (30 minutes)
- Install PostgreSQL in Codespace
- Create database and tables
- Verify connectivity

### Phase 2: Bar Cache (2 hours)
- Port production's bar_cache.py for local use
- Initial load of 100 test tickers
- Verify bar data matches Polygon

### Phase 3: Kernel Runner (2 hours)
- Build validation_env_refresh.py
- Run L0-L4 + CV-1.0 sequential filter on test tickers
- Write output to local PostgreSQL
- Verify output structure matches production schema

### Phase 4: Full Universe Load (3+ hours, runs in background)
- Load all 10K+ symbols
- Full 5-year bar history
- Full kernel computation
- Species profile computation

### Phase 5: Validation (1 hour)
- Run full-universe equivalence gate per Section 5.1 (tolerance bands)
- Document any divergences exceeding tolerance
- Fix systematic divergences; document edge cases (delisted tickers, late bars)

### Phase 6: Documentation (30 minutes)
- Update PROJECT_STATE.md
- Update deploy protocol
- Update handoff memory
- Create VALIDATION_ENV_GUIDE.md for future sessions

### Phase 7: Production Data Import — Mode B (2 hours)
- Export production runtime_decisions_history via read-only credentials
- Import into local PG
- Export personal_trade_ledger from Alpaca order history
- Sync g32_state.json from S3

### Phase 8: Backup Setup (30 minutes)
- Configure pg_dump to S3 in refresh script cleanup
- Test backup and restore cycle
- Document recovery procedure

**One-time setup: ~14-18 hours (of which ~8-10 hours is background computation requiring no active involvement).**
**Ongoing: daily incremental refresh (1-2 hours background), weekly full refresh (6-8 hours overnight). Both run unattended.**
**Revised from initial 9-hour estimate per reviewer feedback.**

## 9. Files Created/Modified

### New files:
- `tools/validation_env_refresh.py` — main refresh script (Mode A + epoch sync)
- `tools/validation_env_import.py` — production data import (Mode B)
- `tools/validation_env_setup.sh` — one-time database setup
- `tools/validation_env_check.py` — full-universe equivalence verification
- `tools/validation_env_backup.sh` — pg_dump to S3
- `docs/VALIDATION_ENV_GUIDE.md` — usage guide for future sessions

### Modified files:
- `PROJECT_STATE.md` — add validation environment section
- `.gitignore` — exclude local PG data directory
- Memory files — update with validation environment reference

### NOT modified:
- `uf_core/` — kernel code unchanged
- `uf_mdg_snapshot.py` — state row builder unchanged
- `web/scripts/execution/` — production execution unchanged
- Any production infrastructure

## 10. Risks

| Risk | Mitigation |
|---|---|
| Kernel divergence (validation ≠ production) | Reference ticker check on every refresh |
| Codespace storage fills up | 6-month rolling retention on history table |
| Polygon rate limits during full load | Incremental loading with retry logic (already in bar_cache.py) |
| Codespace restarts lose PostgreSQL data | Nightly `pg_dump` to S3 (`s3://tfe-codebuild-src-418384447921-us-east-1/validation-env-backups/`). Recovery: `psql -f latest_dump.sql`. Bar cache also backed up to S3 weekly. Rebuild from scratch is the fallback, not the primary recovery path. |
| Future session doesn't know about validation env | VALIDATION_ENV_GUIDE.md + memory entry |
| Kernel SHA mismatch (Mode B rows from version X, Mode A from version Y) | Queries spanning both modes must filter by `kernel_sha` or `source`. Aggregations across mixed versions are labeled as multi-version. The coexistence rule (Mode B precedence for historical timestamps) minimizes overlap. |

## 11. Success Criteria

The validation environment is complete when:
1. `SELECT * FROM runtime_decisions_latest WHERE ticker = 'SPY'` returns current kernel output with `kernel_sha` populated
2. `SELECT COUNT(*) FROM runtime_decisions_history` returns >50K rows (10K symbols × 5+ refreshes)
3. Full-universe equivalence gate passes (≥99% of fields within tolerance bands vs production export; remaining divergences documented as edge cases — delisted tickers, late Polygon bars, etc.)
4. Mode B import succeeds: production runtime_decisions_history and personal_trade_ledger loaded
5. The structural exit assessment (horse/herd/topology) runs against local data and produces results
6. `pg_dump` backup to S3 completes successfully and restore is verified
7. g32_state.json is current (synced from S3)
8. A new Claude session can run `python3 tools/validation_env_check.py` and get a PASS result

---

*This specification is a DRAFT. Submit to independent reviewer (web Claude) for cost verification, architecture review, and risk assessment before building.*
