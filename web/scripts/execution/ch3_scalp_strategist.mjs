/**
 * web/scripts/execution/ch3_scalp_strategist.mjs
 * PEE-1 Chapter 3 — True Intraday Scalp
 *
 * Smash-and-grab: enter on live morning momentum, exit same day.
 *
 * Candidate pool: V3 Accumulate stocks (structural quality gate).
 * Selection gate: live intraday momentum at entry time, scored via
 *   Alpaca snapshot API:
 *     - up on the day vs prev close
 *     - up from today's open (momentum continuing, not fading)
 *     - RVOL >= 1.5 (relative volume vs yesterday, annualized)
 *     - not gapping down > 1% (no falling knives)
 *   Sort: momentum_pct × rvol (highest live energy first)
 *
 * EOD close: sentinel_monitor EXIT-CH3-EOD forces all CH3 positions
 * closed by 3:30 PM ET. No overnight holds.
 *
 * Exit brackets (Alpaca-managed):
 *   TAKE PROFIT: entry × 1.015 (+1.5%)
 *   STOP LOSS:   entry × 0.990 (-1.0%)
 *
 * Pool: $5K total, $2.5K per trade, $1K daily loss limit
 */

import pg from "pg";
import {
  easternClock,
  isRegularMarketSession,
  regularSessionMinutesElapsed,
} from "./market_clock.mjs";
import { readFileSync } from "fs";

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

const ALPACA_DATA = "https://data.alpaca.markets";

// ── CH3 constants ─────────────────────────────────────────────────────────
const CH3_BAR_COUNT_MIN    = 21;
// Safety backstop well above the ~2,100-ticker Accumulate universe; if it
// ever binds the hunter logs it loudly instead of silently truncating.
const CH3_CANDIDATE_POOL_CAP = 4000;
// Alpaca snapshot endpoint: symbols ride in the URL, so batch to keep each
// request comfortably under URL-length limits.
export const CH3_SNAPSHOT_BATCH_SIZE = 100;

export function chunkSymbols(tickers, size = CH3_SNAPSHOT_BATCH_SIZE) {
  const out = [];
  for (let i = 0; i < tickers.length; i += size) out.push(tickers.slice(i, i + size));
  return out;
}
const CH3_POOL_TOTAL       = 5000;
const CH3_MAX_PER_TRADE    = 2500;
const CH3_DAILY_LOSS_LIMIT = 1000;
const CH3_STOP_LOSS_PCT    = 0.01;   // -1% cut fast
const CH3_TAKE_PROFIT_PCT  = 0.015;  // +1.5% grab

// Momentum gates — evaluated against live Alpaca snapshot at entry time
const RVOL_MIN      = 1.5;    // relative volume vs yesterday, annualized to full day
const GAP_DOWN_MAX  = -0.01;  // reject gap-downs worse than -1%
// must_be_green and must_be_up_from_open are implicit in the filter below

// Tradability + rocket ceiling (2026-07-20: the full-universe scan's first
// pass picked the market's two most extreme gappers — WAI +38% at $2.60
// [bridge $5 floor refused it] and VACH +69%/+56% gap [broker refused the
// order] — and both slots died while 173 sane HOT names went untaken).
const CH3_MIN_PRICE = 5.0;    // keep in sync with alpaca_bridge MIN_SHARE_PRICE
const GAP_UP_MAX    = 0.10;   // a +10% gap already happened without us
const DAY_UP_MAX    = 0.15;   // +15% on the day is a missed move, not an entry
// Thin-book guard (2026-07-21 LINK: stale last trade beat the $5 floor and
// the -1% stop slipped to -2.84% in a thin book). Floor checks use the live
// BID when available; spreads wider than 1% are books a scalp can't exit
// cleanly.
const SPREAD_MAX    = 0.01;

export function ch3MomentumVerdict(m) {
  const tooHot      = m.day_pct > DAY_UP_MAX || m.gap_pct > GAP_UP_MAX;
  const floorPrice  = m.bid_price > 0 ? m.bid_price : m.current_price;
  const subMinPrice = floorPrice < CH3_MIN_PRICE;
  const tooThin     = m.spread_pct !== null && m.spread_pct !== undefined && m.spread_pct > SPREAD_MAX;
  const passes =
    m.day_pct      >  0            &&
    m.momentum_pct >  0            &&
    m.rvol         >= RVOL_MIN     &&
    m.gap_pct      >= GAP_DOWN_MAX &&
    !tooHot && !subMinPrice && !tooThin;
  return { passes, tooHot, subMinPrice, tooThin };
}

function toFloat(v) {
  const n = parseFloat(v);
  return isFinite(n) ? n : null;
}

function alpacaHeaders() {
  return {
    "APCA-API-KEY-ID":     process.env.APCA_API_KEY_ID,
    "APCA-API-SECRET-KEY": process.env.APCA_API_SECRET_KEY,
  };
}

// ── Pool & risk management ────────────────────────────────────────────────

async function getTodayCh3PL() {
  const res = await pool.query(
    `SELECT COALESCE(SUM(p_l), 0) AS total_pl
     FROM personal_trade_ledger
     WHERE signal_class = 'CH3'
       AND status = 'closed'
       AND exit_filled_at >= CURRENT_DATE`
  );
  return parseFloat(res.rows[0]?.total_pl ?? "0");
}

async function getCh3PoolRemaining() {
  const res = await pool.query(
    `SELECT COALESCE(SUM(CASE WHEN p_l < 0 THEN p_l ELSE 0 END), 0) AS total_losses
     FROM personal_trade_ledger
     WHERE signal_class = 'CH3'
       AND status = 'closed'`
  );
  const totalLosses = Math.abs(parseFloat(res.rows[0]?.total_losses ?? "0"));
  return Math.max(0, CH3_POOL_TOTAL - totalLosses);
}

async function fetchOpenPositionTickers() {
  const [openRes, cooldownRes] = await Promise.all([
    pool.query(
      `SELECT DISTINCT UPPER(TRIM(ticker)) AS ticker
       FROM personal_trade_ledger
       WHERE status IN ('pending', 'submitted', 'filled')`
    ),
    pool.query(
      `SELECT key, value FROM pee1_execution_config
       WHERE key LIKE 'kill_cooldown_%'`
    ),
  ]);
  const tickers = new Set(openRes.rows.map(r => r.ticker));
  const COOLDOWN_MS = 15 * 60 * 1000;
  for (const row of cooldownRes.rows) {
    const killedAt = new Date(row.value).getTime();
    if (Date.now() - killedAt <= COOLDOWN_MS) {
      tickers.add(row.key.replace("kill_cooldown_", ""));
    }
  }
  return tickers;
}

async function fetchTodayCh3Tickers() {
  const res = await pool.query(
    `SELECT DISTINCT UPPER(TRIM(ticker)) AS ticker
     FROM personal_trade_ledger
     WHERE signal_class = 'CH3'
       AND signal_detected_at >= CURRENT_DATE`
  );
  return new Set(res.rows.map(r => r.ticker));
}

async function fetchRecentCh3Losers() {
  const res = await pool.query(
    `SELECT DISTINCT UPPER(TRIM(ticker)) AS ticker
     FROM personal_trade_ledger
     WHERE signal_class = 'CH3'
       AND status = 'closed'
       AND COALESCE(p_l, 0) < 0
       AND updated_at >= NOW() - INTERVAL '7 days'`
  );
  return new Set(res.rows.map(r => r.ticker));
}

// ── Structural candidate pool ─────────────────────────────────────────────

async function fetchCandidateRows() {
  const res = await pool.query(
    `SELECT
       r.ticker,
       r.run_id,
       r.decision_label,
       r.snapshot_row_json,
       COALESCE(f.sector, 'Unknown') AS sector
     FROM runtime_decisions_latest r
     LEFT JOIN l5_fundamentals_normalized f ON f.ticker = r.ticker
     WHERE r.ticker != 'SPY'
       AND r.ticker NOT LIKE 'I:%'
       AND r.ticker NOT LIKE 'X:%'
       AND r.decision_label = 'Accumulate'
       AND CAST(NULLIF(r.snapshot_row_json->>'bar_count', '') AS INTEGER) > $1
     ORDER BY r.ticker
     LIMIT $2`,
    [CH3_BAR_COUNT_MIN - 1, CH3_CANDIDATE_POOL_CAP]
  );
  // The old LIMIT 100 (no ORDER BY) fed the hunter an arbitrary ~alphabetical
  // 100 of 2,118 eligible tickers — every entry ever taken was an A-name.
  // The cap is now a loud safety backstop, not a silent selector.
  if (res.rows.length >= CH3_CANDIDATE_POOL_CAP) {
    console.warn(
      `[CH3-HUNTER] POOL CAP BOUND — universe exceeds ${CH3_CANDIDATE_POOL_CAP} rows, tail dropped alphabetically. Raise CH3_CANDIDATE_POOL_CAP.`
    );
  }
  return res.rows;
}

function parseCandidate(row) {
  const snap     = row.snapshot_row_json ?? {};
  const ticker   = String(row.ticker ?? "").trim().toUpperCase();
  const runId    = String(row.run_id ?? "").trim();
  const barCount = parseInt(snap.bar_count, 10);
  const price    = toFloat(snap.price);
  const sector   = String(row.sector ?? "").trim();

  if (!ticker || !runId) return null;
  // Dot-class shares (CWEN.A, BRK.A) — Alpaca rejects them as inactive
  // assets (422, CWEN.A 2026-07-23), which burns a slot at the bridge.
  if (ticker.includes(".")) return null;
  if (!isFinite(barCount) || barCount < CH3_BAR_COUNT_MIN) return null;
  if (price === null || price < 1) return null;

  // Epoch governance
  let epochPressure = 0;
  let epochStatus   = "NEUTRAL";
  try {
    const g32 = JSON.parse(readFileSync("/app/g32_state.json", "utf-8"));
    epochPressure = (g32.sector_pressures ?? {})[sector] ?? 0;
    epochStatus   = epochPressure <= -0.5 ? "ADVERSE" : epochPressure > 0.3 ? "TAILWIND" : "NEUTRAL";
  } catch {}

  if (epochStatus === "ADVERSE") {
    console.log(`[CH3-HUNTER]   ${ticker} — skip (sector ${sector} ADVERSE pressure=${epochPressure.toFixed(2)})`);
    return null;
  }

  return {
    ticker,
    run_id:          runId,
    signal_class:    "CH3",
    s_uf:            toFloat(snap.S_UF),
    d_k:             toFloat(snap.D_k),
    b_k:             toFloat(snap.B_k),
    bar_count:       barCount,
    price,
    sector,
    epoch_status:    epochStatus,
    epoch_pressure:  epochPressure,
    ch3_stop_loss_pct:   CH3_STOP_LOSS_PCT,
    ch3_take_profit_pct: CH3_TAKE_PROFIT_PCT,
  };
}

// ── Intraday momentum scoring via Alpaca snapshot ─────────────────────────

/**
 * Batch-fetch Alpaca snapshots for all candidate tickers.
 * Score each on live morning momentum:
 *   gap_pct      = (today_open - prev_close) / prev_close
 *   momentum_pct = (current_price - today_open) / today_open   [up-from-open]
 *   day_pct      = (current_price - prev_close) / prev_close   [up on day]
 *   rvol         = (today_vol / prev_day_vol) × (390 / mins_elapsed)
 *   score        = momentum_pct × max(rvol, 1)
 *
 * passes = day_pct>0 AND momentum_pct>0 AND rvol>=RVOL_MIN AND gap_pct>=GAP_DOWN_MAX
 */
async function fetchIntradayMomentum(tickers) {
  if (!tickers.length) return new Map();

  // Minutes elapsed since the 09:30 ET open, independent of EST/EDT.
  const elapsed = regularSessionMinutesElapsed();

  // Batched snapshots — a failed batch drops only its own tickers
  const snapshots = {};
  let failedBatches = 0;
  const batches = chunkSymbols(tickers);
  for (let b = 0; b < batches.length; b++) {
    const url = `${ALPACA_DATA}/v2/stocks/snapshots?symbols=${encodeURIComponent(batches[b].join(","))}&feed=iex`;
    try {
      const res = await fetch(url, { headers: alpacaHeaders() });
      if (!res.ok) {
        const body = await res.text().catch(() => "");
        throw new Error(`HTTP ${res.status}: ${body.slice(0, 200)}`);
      }
      Object.assign(snapshots, await res.json());
    } catch (err) {
      failedBatches++;
      console.error(`[CH3-HUNTER] Snapshot batch ${b + 1}/${batches.length} failed (${batches[b].length} tickers): ${err.message}`);
    }
  }
  if (failedBatches === batches.length && batches.length > 0) {
    console.error(`[CH3-HUNTER] All ${batches.length} snapshot batches failed — no momentum data this pass`);
    return new Map();
  }

  const results = new Map();
  for (const ticker of tickers) {
    const snap = snapshots[ticker];
    if (!snap) continue;

    const prevClose = snap.prevDailyBar?.c;
    const todayOpen = snap.dailyBar?.o;
    const todayVol  = snap.dailyBar?.v  ?? 0;
    const prevVol   = snap.prevDailyBar?.v ?? 0;
    const current   = snap.latestTrade?.p ?? snap.minuteBar?.c;
    // Live book, for tradability: on thin names the last trade can be hours
    // stale (2026-07-21 LINK printed >=$5 while the real market sat at $4.58,
    // defeating the price floor and slipping the stop to -2.84%).
    const bid = toFloat(snap.latestQuote?.bp);
    const ask = toFloat(snap.latestQuote?.ap);
    const spread_pct = bid > 0 && ask > bid ? (ask - bid) / ((ask + bid) / 2) : null;

    if (!prevClose || !todayOpen || !current || prevClose <= 0 || prevVol <= 0) continue;

    const gap_pct      = (todayOpen - prevClose) / prevClose;
    const momentum_pct = (current   - todayOpen)  / todayOpen;
    const day_pct      = (current   - prevClose)  / prevClose;

    // Annualize today's volume run-rate vs yesterday's total volume
    const rvol = (todayVol / prevVol) * (390 / elapsed);

    // Score: momentum × volume intensity
    const score = momentum_pct * Math.max(rvol, 1);

    const verdict = ch3MomentumVerdict({ gap_pct, momentum_pct, day_pct, rvol, current_price: current, bid_price: bid, spread_pct });

    results.set(ticker, { gap_pct, momentum_pct, day_pct, rvol, current_price: current, bid_price: bid, spread_pct, score, ...verdict });
  }

  return results;
}

// ── Main entry point ──────────────────────────────────────────────────────

export async function getCh3Signals() {
  console.log("[CH3-HUNTER] Scalp hunter scanning (live momentum mode)...");

  // Gate 0: market hours
  const now = new Date();
  const eastern = easternClock(now);
  if (!isRegularMarketSession(now)) {
    console.log(`[CH3-HUNTER] SKIP — market closed (${eastern.hour}:${String(eastern.minute).padStart(2,"0")} ET)`);
    return [];
  }
  try {
    const { isMarketHoliday, getHolidayName } = await import("./market_calendar.mjs");
    if (isMarketHoliday(now)) {
      console.log(`[CH3-HUNTER] SKIP — ${getHolidayName(now) ?? "market holiday"}`);
      return [];
    }
  } catch {}

  // Gate 1: daily loss limit
  const todayPL = await getTodayCh3PL();
  if (todayPL <= -CH3_DAILY_LOSS_LIMIT) {
    console.log(`[CH3-HUNTER] HALTED — daily loss limit hit ($${todayPL.toFixed(2)} today)`);
    return [];
  }

  // Gate 2: pool remaining
  const poolRemaining = await getCh3PoolRemaining();
  if (poolRemaining <= 0) {
    console.log("[CH3-HUNTER] HALTED — scalp pool depleted");
    return [];
  }

  // Gate 3: available pool vs currently invested CH3
  const ch3InvestedRes = await pool.query(`
    SELECT COALESCE(SUM(CAST(dollar_allocation AS NUMERIC)), 0) AS invested
    FROM personal_trade_ledger
    WHERE signal_class = 'CH3' AND status IN ('submitted', 'filled')
  `);
  const ch3Invested    = parseFloat(ch3InvestedRes.rows[0]?.invested ?? "0");
  const availablePool  = Math.max(0, poolRemaining - ch3Invested);
  if (availablePool < 500) {
    console.log(`[CH3-HUNTER] SKIP — pool fully allocated ($${availablePool.toFixed(0)} available)`);
    return [];
  }

  // Step 1: structural candidate pool (V3 Accumulate universe)
  const rows      = await fetchCandidateRows();
  const candidates = rows.map(parseCandidate).filter(Boolean);
  console.log(`[CH3-HUNTER] ${rows.length} Accumulate rows → ${candidates.length} passed structural/epoch filter`);

  // Step 2: exclusions (open positions, already traded, recent losers)
  const [openTickers, todayCh3Tickers, recentLosers] = await Promise.all([
    fetchOpenPositionTickers(),
    fetchTodayCh3Tickers(),
    fetchRecentCh3Losers(),
  ]);
  const available = [];
  for (const s of candidates) {
    if (openTickers.has(s.ticker))    { console.log(`[CH3-HUNTER]   ${s.ticker} — skip (open position)`);     continue; }
    if (todayCh3Tickers.has(s.ticker)){ console.log(`[CH3-HUNTER]   ${s.ticker} — skip (already traded today)`); continue; }
    if (recentLosers.has(s.ticker))   { console.log(`[CH3-HUNTER]   ${s.ticker} — skip (lost money in last 7d)`); continue; }
    available.push(s);
  }

  if (!available.length) {
    console.log("[CH3-HUNTER] No candidates after exclusions");
    return [];
  }

  // Step 3: live intraday momentum scoring via Alpaca snapshot
  const momentumMap = await fetchIntradayMomentum(available.map(s => s.ticker));

  // Per-ticker lines only for HOT and named skips (rockets, sub-$5) — a
  // full-universe pass (~2k tickers) would otherwise print thousands of
  // COLD lines per day. Rockets are logged by name so "why didn't we take
  // X?" is answerable straight from the pass log.
  const hot = [];
  let coldCount = 0;
  let noSnapCount = 0;
  let rocketCount = 0;
  let pennyCount = 0;
  let thinCount = 0;
  for (const s of available) {
    const m = momentumMap.get(s.ticker);
    if (!m) {
      noSnapCount++;
      continue;
    }
    const tag = `day=${(m.day_pct*100).toFixed(2)}% open_mom=${(m.momentum_pct*100).toFixed(2)}% rvol=${m.rvol.toFixed(2)}x gap=${(m.gap_pct*100).toFixed(2)}%`;
    if (!m.passes) {
      if (m.tooHot) {
        rocketCount++;
        console.log(`[CH3-HUNTER]   ${s.ticker} — ROCKET SKIP: ${tag} price=${m.current_price} (move already happened)`);
      } else if (m.subMinPrice) {
        pennyCount++;
      } else if (m.tooThin) {
        thinCount++;
      } else {
        coldCount++;
      }
      continue;
    }
    console.log(`[CH3-HUNTER]   ${s.ticker} — HOT:  ${tag} score=${m.score.toFixed(4)}`);
    s.momentum = m;
    s.price    = m.current_price;  // use live price, not stale snapshot
    hot.push(s);
  }
  console.log(`[CH3-HUNTER] Scored ${available.length}: ${hot.length} HOT | ${coldCount} COLD | ${rocketCount} rockets | ${pennyCount} sub-$${CH3_MIN_PRICE} | ${thinCount} thin-book | ${noSnapCount} no-snapshot`);

  if (!hot.length) {
    console.log("[CH3-HUNTER] No stocks passing momentum gates today");
    return [];
  }

  // Sort by live momentum score — highest energy first
  hot.sort((a, b) => (b.momentum.score ?? 0) - (a.momentum.score ?? 0));

  // Pool-limited: up to 2 signals
  const results       = [];
  let remainingPool   = availablePool;
  for (const candidate of hot.slice(0, 2)) {
    if (remainingPool < 500) break;
    const perTradeAmount = Math.min(CH3_MAX_PER_TRADE, remainingPool);
    candidate.ch3_trade_amount = perTradeAmount;
    remainingPool -= perTradeAmount;
    console.log(`[CH3-HUNTER] SIGNAL: ${candidate.ticker} | score=${candidate.momentum.score.toFixed(4)} | rvol=${candidate.momentum.rvol.toFixed(2)}x | mom=${(candidate.momentum.momentum_pct*100).toFixed(2)}% | $${perTradeAmount}`);
    results.push(candidate);
  }

  return results;
}

export const CH3_CONFIG = {
  DAILY_LOSS_LIMIT: CH3_DAILY_LOSS_LIMIT,
  STOP_LOSS_PCT:    CH3_STOP_LOSS_PCT,
  TAKE_PROFIT_PCT:  CH3_TAKE_PROFIT_PCT,
  RVOL_MIN,
};

export async function closeCh3StrategistPool() {
  await pool.end();
}
