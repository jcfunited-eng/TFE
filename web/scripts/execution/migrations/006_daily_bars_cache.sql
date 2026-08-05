-- 006_daily_bars_cache.sql
-- Persistent bar cache: stores daily OHLCV bars so the refresh only fetches
-- incremental deltas from the API instead of 5 years of history every run.
--
-- One row per (ticker, bar_date).  On conflict, update the bar values
-- (handles corrections/adjustments from the data provider).

CREATE TABLE IF NOT EXISTS daily_bars (
    ticker          TEXT        NOT NULL,
    bar_date        DATE        NOT NULL,
    open            DOUBLE PRECISION,
    high            DOUBLE PRECISION,
    low             DOUBLE PRECISION,
    close           DOUBLE PRECISION    NOT NULL,
    volume          BIGINT,
    source          TEXT        DEFAULT 'polygon',
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (ticker, bar_date)
);

-- Index for fast "what's the latest bar date for this ticker?" lookups
CREATE INDEX IF NOT EXISTS idx_daily_bars_ticker_date
    ON daily_bars (ticker, bar_date DESC);

-- Index for bulk reads during snapshot rebuild (all bars for a ticker, sorted)
CREATE INDEX IF NOT EXISTS idx_daily_bars_ticker_asc
    ON daily_bars (ticker, bar_date ASC);
