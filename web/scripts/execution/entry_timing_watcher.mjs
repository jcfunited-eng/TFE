/**
 * web/scripts/execution/entry_timing_watcher.mjs
 * Real-time entry timing for CH2 positions.
 *
 * Runs alongside the sentinel daemon during market hours.
 * Watches primed tickers (Accumulate + structural criteria met) that
 * either have no order yet or had a previous order expire/cancel.
 *
 * Uses real-time price from Polygon to time entries:
 *   - Checks if current price is within entry range
 *   - Checks if volume is elevated (energy arriving)
 *   - Submits bracket order when conditions align
 *
 * Does NOT change what we buy — only WHEN we submit the order.
 * The kernel's Accumulate decision is the primer. This is the trigger timing.
 */

import pg from "pg";

const pool = new pg.Pool({
  host:     process.env.PGHOST,
  port:     parseInt(process.env.PGPORT ?? "5432", 10),
  database: process.env.PGDATABASE,
  user:     process.env.PGUSER,
  password: process.env.PGPASSWORD,
  max: 3,
  idleTimeoutMillis: 30_000,
  connectionTimeoutMillis: 5_000,
  ssl: { rejectUnauthorized: false },
});

const POLYGON_KEY = process.env.MASSIVE_API_KEY ?? process.env.POLYGON_API_KEY ?? "";
const POLYGON_BASE = "https://api.polygon.io";

// ── Configuration ───────────────────────────────────────────────────────
// CH2_S_UF_MIN removed 2026-08-11 — the S_UF band is abolished
// permanently (Joe; completes f379f0f1). Selection is the V3 basin's.
const CH2_BAR_COUNT_MIN = 21;     // established stocks only
const MAX_ENTRIES_PER_RUN = 3;    // don't flood — max new entries per 5-min check
const VOLUME_RATIO_MIN  = 1.0;    // volume must be at/above average (not dry)

/**
 * Fetch real-time snapshot from Polygon for a ticker.
 * Returns { price, todayVolume, prevDayVolume }
 */
async function fetchRealTimeSnapshot(ticker) {
  const url = `${POLYGON_BASE}/v2/snapshot/locale/us/markets/stocks/tickers/${ticker}?apiKey=${POLYGON_KEY}`;
  const resp = await fetch(url);
  if (!resp.ok) return null;
  const data = await resp.json();
  const snap = data?.ticker;
  if (!snap) return null;

  return {
    price:         snap.lastTrade?.p ?? snap.min?.c ?? null,
    todayVolume:   snap.day?.v ?? 0,
    prevDayVolume: snap.prevDay?.v ?? 0,
  };
}

/**
 * Get primed tickers: Accumulate stocks that meet CH2 criteria
 * and do NOT have an open/submitted position.
 */
async function getPrimedTickers() {
  // Get tickers with open positions OR recently killed by sentinel — exclude them.
  // The sentinel writes kill_cooldown_<TICKER> to pee1_execution_config when it
  // exits a position. Without this, entry logic can re-enter a ticker in the same
  // daemon cycle the sentinel just closed it — creating a churn loop.
  const [openRes, cooldownRes] = await Promise.all([
    pool.query(`
      SELECT DISTINCT UPPER(TRIM(ticker)) AS ticker
      FROM personal_trade_ledger
      WHERE status IN ('submitted', 'filled', 'pending')
    `),
    pool.query(`
      SELECT key, value FROM pee1_execution_config
      WHERE key LIKE 'kill_cooldown_%'
    `),
  ]);
  const openTickers = new Set(openRes.rows.map(r => r.ticker));
  const COOLDOWN_MS = 15 * 60 * 1000;
  for (const row of cooldownRes.rows) {
    const killedAt = new Date(row.value).getTime();
    if (Date.now() - killedAt <= COOLDOWN_MS) {
      openTickers.add(row.key.replace('kill_cooldown_', ''));
    }
  }

  // Get tickers that were already tried today and expired/canceled
  // These are re-entry candidates
  const triedRes = await pool.query(`
    SELECT DISTINCT UPPER(TRIM(ticker)) AS ticker
    FROM personal_trade_ledger
    WHERE status IN ('rejected', 'canceled', 'expired')
      AND signal_class = 'CH2'
      AND created_at >= CURRENT_DATE
  `);
  const retriableTickers = new Set(triedRes.rows.map(r => r.ticker));

  // Get Accumulate tickers meeting CH2 criteria
  const candidateRes = await pool.query(`
    SELECT
      ticker,
      CAST(NULLIF(snapshot_row_json->>'S_UF', '') AS DOUBLE PRECISION) AS s_uf,
      CAST(NULLIF(snapshot_row_json->>'bar_count', '') AS INTEGER) AS bar_count,
      CAST(NULLIF(snapshot_row_json->>'D_k', '') AS DOUBLE PRECISION) AS d_k,
      CAST(NULLIF(snapshot_row_json->>'B_k', '') AS DOUBLE PRECISION) AS b_k,
      snapshot_row_json->>'regime' AS regime,
      run_id
    FROM runtime_decisions_latest
    WHERE decision_label = 'Accumulate'
      AND CAST(NULLIF(snapshot_row_json->>'bar_count', '') AS INTEGER) > $1
      AND ticker != 'SPY'
    ORDER BY CAST(NULLIF(snapshot_row_json->>'S_UF', '') AS DOUBLE PRECISION) DESC
    LIMIT 50
  `, [CH2_BAR_COUNT_MIN]);

  const primed = [];
  for (const row of candidateRes.rows) {
    const ticker = row.ticker.trim().toUpperCase();
    if (openTickers.has(ticker)) continue;  // already have a position

    primed.push({
      ticker,
      s_uf:      parseFloat(row.s_uf),
      bar_count: parseInt(row.bar_count),
      d_k:       parseFloat(row.d_k ?? "0"),
      b_k:       parseFloat(row.b_k ?? "0"),
      regime:    row.regime ?? "unknown",
      run_id:    row.run_id,
      is_retry:  retriableTickers.has(ticker),
    });
  }

  return primed;
}

/**
 * Main entry timing check — called by sentinel daemon.
 */
export async function runEntryTimingCheck() {
  if (!POLYGON_KEY) {
    console.log("[ENTRY-TIMING] No Polygon API key — skipping.");
    return;
  }

  // No new entries on weekends or market holidays
  {
    const now = new Date();
    const dayOfWeek = now.getUTCDay();
    if (dayOfWeek === 5 || dayOfWeek === 6 || dayOfWeek === 0) return;
    try {
      const { isMarketHoliday } = await import("./market_calendar.mjs");
      if (isMarketHoliday(now)) return;
    } catch {}
  }

  const primed = await getPrimedTickers();
  if (primed.length === 0) {
    console.log("[ENTRY-TIMING] No primed tickers without positions.");
    return;
  }

  console.log(`[ENTRY-TIMING] ${primed.length} primed tickers (${primed.filter(p => p.is_retry).length} retries)`);

  // Check real-time conditions on top candidates
  let entriesThisRun = 0;
  const candidates = [];

  for (const signal of primed) {
    if (entriesThisRun >= MAX_ENTRIES_PER_RUN) break;

    try {
      const snapshot = await fetchRealTimeSnapshot(signal.ticker);
      if (!snapshot || !snapshot.price) continue;

      // Volume ratio: today's volume vs previous day
      // Early in the day, today's volume will be low — normalize by time of day
      const now = new Date();
      const marketOpenMinutes = (now.getUTCHours() - 13) * 60 + (now.getUTCMinutes() - 30);
      const tradingMinutesSoFar = Math.max(1, Math.min(390, marketOpenMinutes));
      const expectedVolumeRatio = tradingMinutesSoFar / 390;  // fraction of day elapsed
      const normalizedVolume = snapshot.prevDayVolume > 0
        ? (snapshot.todayVolume / (snapshot.prevDayVolume * expectedVolumeRatio))
        : 1.0;

      // S_UF band routing removed 2026-08-11 — the band is abolished and
      // this watcher primes CH2 only (see file header).
      const signalClass = "CH2";

      candidates.push({
        ...signal,
        price: snapshot.price,
        todayVolume: snapshot.todayVolume,
        prevDayVolume: snapshot.prevDayVolume,
        normalizedVolume,
        signal_class: signalClass,
      });
    } catch (err) {
      // Skip ticker on error, don't abort the whole run
    }
  }

  // CH3 pool check: how much of the $5K pool is already invested?
  const ch3PoolRes = await pool.query(`
    SELECT COALESCE(SUM(CAST(dollar_allocation AS NUMERIC)), 0) AS invested
    FROM personal_trade_ledger
    WHERE signal_class = 'CH3' AND status IN ('submitted', 'filled')
  `);
  const ch3Invested = parseFloat(ch3PoolRes.rows[0]?.invested ?? "0");
  const ch3Available = Math.max(0, 5000 - ch3Invested);

  // Sort by volume strength — highest volume ratio first
  candidates.sort((a, b) => b.normalizedVolume - a.normalizedVolume);

  for (const c of candidates) {
    if (entriesThisRun >= MAX_ENTRIES_PER_RUN) break;

    // CH3 pool limit — skip if pool exhausted
    if (c.signal_class === "CH3" && ch3Available < 500) {
      continue;
    }

    // Entry condition: volume at or above normal pace
    if (c.normalizedVolume < VOLUME_RATIO_MIN) {
      continue;
    }

    console.log(
      `[ENTRY-TIMING] CANDIDATE: ${c.ticker} | price=$${c.price} | ` +
      `vol=${c.normalizedVolume.toFixed(2)}x | S_UF=${c.s_uf} | ` +
      `D_k=${c.d_k} | retry=${c.is_retry}`
    );

    // CH3 entries: structural hunter — full L4 geometry + epoch filter
    // Volume confirms the energy is flowing, structure confirms the opportunity

    // Route CH2 to bridge
    try {
      const { executeCh2BracketOrder, executeCh3MarketOrder } = await import("./alpaca_bridge.mjs");
      let result;
      if (c.signal_class === "CH3") {
        // Should not reach here — CH3 gated above
        continue;
      } else {
        result = await executeCh2BracketOrder(c);
      }
      if (result?.ok) {
        entriesThisRun++;
        console.log(`[ENTRY-TIMING] FIRED: ${c.ticker} (${c.signal_class}) — orderId=${result.orderId}`);
      } else {
        console.log(`[ENTRY-TIMING] ${c.ticker} (${c.signal_class}) — rejected: ${result?.reason ?? "unknown"}`);
      }
    } catch (err) {
      console.error(`[ENTRY-TIMING] ${c.ticker} order failed: ${err.message}`);
    }
  }

  if (entriesThisRun === 0) {
    console.log(`[ENTRY-TIMING] No entries fired this check.`);
  }
}

export async function closeEntryTimingPool() {
  await pool.end();
}
