-- 004_pee1_stealth_queue.sql
-- Stealth Execution Engine V2 — agent queue and config keys

-- Queued stealth agent orders (fired sequentially with randomized delays)
CREATE TABLE IF NOT EXISTS pee1_stealth_queue (
  id                  SERIAL PRIMARY KEY,
  parent_ledger_id    INTEGER,                          -- first agent's ledger row (agent_index=0)
  ticker              TEXT         NOT NULL,
  signal_json         JSONB        NOT NULL,            -- full signal snapshot for replay
  agent_index         INTEGER      NOT NULL,            -- 0-based position in the slice chain
  total_agents        INTEGER      NOT NULL,
  shares              INTEGER      NOT NULL,
  order_type          TEXT         NOT NULL,            -- 'limit' | 'midpoint'
  entry_limit_price   NUMERIC(12,4),                   -- computed at enqueue time
  take_profit_price   NUMERIC(12,4),
  stop_loss_price     NUMERIC(12,4),
  atr_14              NUMERIC(12,6),
  vault_equity        NUMERIC(14,2),
  scheduled_at        TIMESTAMPTZ  NOT NULL,
  executed_at         TIMESTAMPTZ,
  ledger_id           INTEGER,                          -- personal_trade_ledger id after execution
  alpaca_order_id     TEXT,
  status              TEXT         NOT NULL DEFAULT 'pending',  -- pending | executed | failed | cancelled
  error               TEXT,
  created_at          TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS pee1_stealth_queue_status_scheduled
  ON pee1_stealth_queue (status, scheduled_at)
  WHERE status = 'pending';

-- Config keys for stealth engine
INSERT INTO pee1_execution_config (key, value, updated_by) VALUES
  ('stealth_threshold_dollars', '5000', 'migration'),
  ('stealth_agent_count',       '3',    'migration')
ON CONFLICT (key) DO NOTHING;
