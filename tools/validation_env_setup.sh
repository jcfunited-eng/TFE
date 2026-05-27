#!/bin/bash
# tools/validation_env_setup.sh — One-time validation environment setup
#
# Run this when setting up a new Codespace or after a rebuild.
# Installs PostgreSQL, creates the database and tables, verifies connectivity.
#
# Usage: bash tools/validation_env_setup.sh

set -e

echo "=== TFE Validation Environment Setup ==="

# Check if PostgreSQL server is installed
if ! command -v pg_ctlcluster &>/dev/null; then
    echo "Installing PostgreSQL 17..."
    apt-get update -qq && apt-get install -y -qq postgresql-17
fi

# Fix authentication for root user
PG_HBA=$(find /etc/postgresql -name pg_hba.conf 2>/dev/null | head -1)
if [ -n "$PG_HBA" ]; then
    sed -i 's/local   all             all                                     peer/local   all             all                                     trust/' "$PG_HBA"
    sed -i 's/local   all             postgres                                peer/local   all             postgres                                trust/' "$PG_HBA"
fi

# Start PostgreSQL
pg_ctlcluster 17 main start 2>/dev/null || true
sleep 2

if ! pg_isready &>/dev/null; then
    echo "ERROR: PostgreSQL failed to start"
    exit 1
fi
echo "PostgreSQL running ✓"

# Create database if not exists
psql -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = 'tfe_validation'" | grep -q 1 || \
    psql -U postgres -c "CREATE DATABASE tfe_validation;"

# Create tables
psql -U postgres -d tfe_validation << 'SQL'
CREATE TABLE IF NOT EXISTS runtime_decisions_latest (
    ticker TEXT PRIMARY KEY, decision_label TEXT, reason_text TEXT, reason_code TEXT,
    snapshot_row_json JSONB, generated_at_utc TIMESTAMPTZ, run_id TEXT,
    kernel_sha TEXT, source TEXT DEFAULT 'validation_runner'
);
CREATE TABLE IF NOT EXISTS runtime_decisions_history (
    id SERIAL PRIMARY KEY, ticker TEXT NOT NULL, decision_label TEXT,
    snapshot_row_json JSONB, generated_at_utc TIMESTAMPTZ NOT NULL, run_id TEXT,
    kernel_sha TEXT, source TEXT DEFAULT 'validation_runner'
);
CREATE INDEX IF NOT EXISTS idx_rdh_ticker_date ON runtime_decisions_history(ticker, generated_at_utc);
CREATE TABLE IF NOT EXISTS species_profiles (
    ticker TEXT PRIMARY KEY, delta_bar DOUBLE PRECISION, sigma_bar DOUBLE PRECISION,
    classification TEXT, field_used TEXT, computed_at TIMESTAMPTZ, n_bars INT
);
CREATE TABLE IF NOT EXISTS personal_trade_ledger (
    id SERIAL PRIMARY KEY, ticker TEXT, run_id TEXT, signal_class TEXT, shares INT,
    status TEXT, entry_filled_price DOUBLE PRECISION, entry_filled_at TIMESTAMPTZ,
    exit_filled_price DOUBLE PRECISION, exit_filled_at TIMESTAMPTZ, exit_reason TEXT,
    signal_detected_at TIMESTAMPTZ, created_at TIMESTAMPTZ DEFAULT NOW(),
    p_l DOUBLE PRECISION, p_l_pct DOUBLE PRECISION, rationale_json JSONB DEFAULT '{}'::jsonb,
    alpaca_order_id TEXT, take_profit_price DOUBLE PRECISION, stop_loss_price DOUBLE PRECISION
);
CREATE TABLE IF NOT EXISTS daily_bars (
    symbol TEXT NOT NULL, bar_date DATE NOT NULL,
    open DOUBLE PRECISION, high DOUBLE PRECISION, low DOUBLE PRECISION,
    close DOUBLE PRECISION, volume BIGINT, PRIMARY KEY (symbol, bar_date)
);
SQL

echo "Database tfe_validation ready ✓"
echo "Tables: $(psql -U postgres -d tfe_validation -tc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'" | tr -d ' ') tables"
echo ""
echo "Next: python3 tools/validation_env_refresh.py --full"
