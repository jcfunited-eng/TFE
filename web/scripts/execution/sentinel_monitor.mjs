/**
 * web/scripts/execution/sentinel_monitor.mjs
 * PEE-1 Sentinel Monitor — Live Position Audit + Kill Switches
 *
 * Runs after each market day against all open positions in personal_trade_ledger.
 *
 * Four kill conditions:
 *   1. CIRCUIT BREAKER: portfolio dropped > max_drawdown_pct in session
 *      → liquidate ALL positions, halt new trades for circuit_breaker_hours
 *   2. SPY FLIP: SPY D_k flipped to 0/-1 → liquidate ALL positions
 *   3. CALAMITY: R_rev_k > 0 on individual position → market sell that position
 *   4. ZOMBIE:   position age > tau_in_max bars → market sell that position
 *
 * Circuit breaker state is written to pee1_circuit_breaker table.
 * pee1_runner checks this table before executing any new orders.
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

const ZOMBIE_BAR_THRESHOLD = parseInt(process.env.SENTINEL_ZOMBIE_BARS ?? "10", 10);

// ── Alpaca helpers (duplicated intentionally — sentinel is independent) ───
function alpacaHeaders() {
  return {
    "APCA-API-KEY-ID":     process.env.APCA_API_KEY_ID,
    "APCA-API-SECRET-KEY": process.env.APCA_API_SECRET_KEY,
    "Content-Type":        "application/json",
  };
}

async function resolveAlpacaBase() {
  try {
    const res = await pool.query(
      `SELECT value FROM pee1_execution_config WHERE key = 'execution_mode' LIMIT 1`
    );
    return (res.rows[0]?.value ?? "paper") === "live"
      ? "https://api.alpaca.markets"
      : "https://paper-api.alpaca.markets";
  } catch {
    return "https://paper-api.alpaca.markets";
  }
}

const ALPACA_DATA = "https://data.alpaca.markets";

async function alpacaGet(path, base) {
  const res = await fetch(`${base}${path}`, { headers: alpacaHeaders() });
  const body = await res.json();
  if (!res.ok) throw new Error(`Alpaca GET ${path} → ${res.status}: ${JSON.stringify(body)}`);
  return body;
}

async function alpacaPost(path, payload, base) {
  const res = await fetch(`${base}${path}`, {
    method: "POST",
    headers: alpacaHeaders(),
    body: JSON.stringify(payload),
  });
  const body = await res.json();
  if (!res.ok) throw new Error(`Alpaca POST ${path} → ${res.status}: ${JSON.stringify(body)}`);
  return body;
}

// ── Cancel open bracket legs before liquidating ──────────────────────────
async function cancelOrder(orderId, base) {
  try {
    await fetch(`${base}/v2/orders/${orderId}`, {
      method: "DELETE",
      headers: alpacaHeaders(),
    });
  } catch (e) {
    console.warn(`[SENTINEL] Could not cancel order ${orderId}: ${e.message}`);
  }
}

// ── Market sell ───────────────────────────────────────────────────────────
async function marketSell(ticker, qty, base) {
  return alpacaPost("/v2/orders", {
    symbol:        ticker,
    qty,
    side:          "sell",
    type:          "market",
    time_in_force: "day",
  }, base);
}

// ── Current SPY D_k ──────────────────────────────────────────────────────
async function fetchSpyDk() {
  try {
    const res = await pool.query(
      `SELECT snapshot_row_json FROM runtime_decisions_latest
       WHERE ticker = 'SPY' ORDER BY generated_at_utc DESC LIMIT 1`
    );
    if (!res.rows.length) return null;
    const snap = res.rows[0].snapshot_row_json ?? {};
    const dk = parseInt(snap.D_k ?? snap.d_k ?? "", 10);
    return isFinite(dk) ? dk : null;
  } catch {
    return null;
  }
}

// ── Current R_rev_k, bar age, S_UF, D_k for a ticker ────────────────────
async function fetchStructuralFields(ticker) {
  try {
    const res = await pool.query(
      `SELECT snapshot_row_json FROM runtime_decisions_latest
       WHERE ticker = $1 ORDER BY generated_at_utc DESC LIMIT 1`,
      [ticker]
    );
    if (!res.rows.length) return {};
    const snap = res.rows[0].snapshot_row_json ?? {};
    return {
      r_rev_k:   parseFloat(snap.R_rev_k ?? snap.r_rev_k ?? "NaN"),
      bar_count: parseInt(snap.bar_count ?? "", 10),
      s_uf:      parseFloat(snap.S_UF ?? snap.s_uf ?? "NaN"),
      d_k:       parseInt(snap.D_k ?? snap.d_k ?? "NaN", 10),
    };
  } catch {
    return {};
  }
}

// ── Open positions from ledger ────────────────────────────────────────────
async function fetchOpenPositions() {
  const res = await pool.query(
    `SELECT id, ticker, shares, signal_class, alpaca_order_id,
            alpaca_take_profit_order_id, alpaca_stop_loss_order_id,
            entry_filled_at, signal_detected_at,
            take_profit_price, stop_loss_price
     FROM personal_trade_ledger
     WHERE status IN ('submitted', 'filled')
       AND (signal_class IS NULL OR signal_class != 'manual')
     ORDER BY created_at ASC`
  );
  return res.rows;
}

// ── Ledger: mark closed, compute P&L if exit price known ─────────────────
async function ledgerClose(id, exitReason, exitOrderId, exitFilledPrice = null) {
  // Fetch entry data to compute P&L
  let pl = null;
  let plPct = null;
  if (exitFilledPrice != null) {
    try {
      const posRes = await pool.query(
        `SELECT entry_filled_price, shares FROM personal_trade_ledger WHERE id=$1`, [id]
      );
      const pos = posRes.rows[0];
      const entry = parseFloat(pos?.entry_filled_price ?? "0");
      const shares = parseFloat(pos?.shares ?? "0");
      if (entry > 0 && shares > 0) {
        pl = (exitFilledPrice - entry) * shares;
        plPct = ((exitFilledPrice - entry) / entry) * 100;
      }
    } catch { /* non-fatal */ }
  }
  await pool.query(
    `UPDATE personal_trade_ledger
     SET status='closed', exit_reason=$1,
         rationale_json = rationale_json || $2::jsonb,
         exit_filled_at = NOW(),
         exit_filled_price = COALESCE($4, exit_filled_price),
         p_l = COALESCE($5, p_l),
         p_l_pct = COALESCE($6, p_l_pct)
     WHERE id=$3`,
    [exitReason, JSON.stringify({ sentinel_exit_order_id: exitOrderId ?? null }), id,
     exitFilledPrice, pl, plPct]
  );
}

// ── Kill a single position ────────────────────────────────────────────────
async function killPosition(pos, exitReason, base) {
  const { id, ticker, shares, alpaca_order_id, alpaca_take_profit_order_id, alpaca_stop_loss_order_id } = pos;
  console.log(`[SENTINEL] KILL ${ticker} | reason=${exitReason} | shares=${shares}`);

  // Cancel parent bracket order first (releases held shares), then individual legs
  if (alpaca_order_id)             await cancelOrder(alpaca_order_id, base);
  if (alpaca_take_profit_order_id) await cancelOrder(alpaca_take_profit_order_id, base);
  if (alpaca_stop_loss_order_id)   await cancelOrder(alpaca_stop_loss_order_id, base);

  // Small delay to let Alpaca process the cancellations before selling
  await new Promise(r => setTimeout(r, 1500));

  // Verify position still exists in Alpaca — bracket TP/SL may have already closed it
  let sellQty = shares;  // default to DB value, override with Alpaca actual
  try {
    const alpacaPos = await alpacaGet(`/v2/positions/${encodeURIComponent(ticker)}`, base);
    const alpacaQty = parseFloat(alpacaPos?.qty ?? "0");
    if (alpacaQty <= 0) {
      // Short or zero — don't sell, just close DB record
      console.log(`[SENTINEL] ${ticker} — Alpaca qty=${alpacaQty} (already closed or short). Marking DB closed without sell.`);
      await ledgerClose(id, `${exitReason}_bracket_exit`, null).catch(e => {
        console.error(`[SENTINEL] Ledger close failed for ${ticker}:`, e.message);
      });
      return;
    }
    // Use Alpaca's actual qty — DB may be stale (e.g. partial fill on entry)
    if (alpacaQty !== shares) {
      console.log(`[SENTINEL] ${ticker} — qty mismatch: DB=${shares}, Alpaca=${alpacaQty}. Using Alpaca qty.`);
    }
    sellQty = alpacaQty;
  } catch (e) {
    const msg = String(e.message);
    if (msg.includes("40410000") || msg.toLowerCase().includes("position does not exist")) {
      // Bracket already closed the position (TP or SL fired) — try to get exit price from legs
      let bracketExitPrice = null;
      if (alpaca_order_id) {
        try {
          const parentOrder = await alpacaGet(`/v2/orders/${alpaca_order_id}`, base);
          for (const leg of (parentOrder?.legs ?? [])) {
            if (leg.filled_avg_price && leg.side === "sell") {
              bracketExitPrice = parseFloat(leg.filled_avg_price);
              break;
            }
          }
        } catch { /* non-fatal */ }
      }
      console.log(`[SENTINEL] ${ticker} — position already closed in Alpaca (bracket exit @ $${bracketExitPrice ?? "unknown"}). Marking DB closed.`);
      await ledgerClose(id, `${exitReason}_bracket_exit`, null, bracketExitPrice).catch(ex => {
        console.error(`[SENTINEL] Ledger close failed for ${ticker}:`, ex.message);
      });
      return;
    }
    // Other error — log but continue and attempt sell anyway
    console.warn(`[SENTINEL] ${ticker} — position existence check error: ${msg}. Attempting sell anyway.`);
  }

  let exitOrderId = null;
  let exitFilledPrice = null;
  try {
    const sellOrder = await marketSell(ticker, sellQty, base);
    exitOrderId = sellOrder.id;
    console.log(`[SENTINEL] Market sell placed | ${ticker} | orderId=${exitOrderId}`);
  } catch (err) {
    console.error(`[SENTINEL] CRITICAL: market sell FAILED for ${ticker}: ${err.message}`);
    await pool.query(
      `UPDATE personal_trade_ledger
       SET rationale_json = rationale_json || $1::jsonb
       WHERE id=$2`,
      [JSON.stringify({ sentinel_kill_failed: err.message, kill_reason: exitReason }), id]
    ).catch(() => {});
    return;
  }

  // Brief wait for market order to fill, then capture exit price for P&L
  if (exitOrderId) {
    await new Promise(r => setTimeout(r, 2000));
    try {
      const fillCheck = await alpacaGet(`/v2/orders/${exitOrderId}`, base);
      if (fillCheck?.filled_avg_price) {
        exitFilledPrice = parseFloat(fillCheck.filled_avg_price);
        console.log(`[SENTINEL] Exit fill: ${ticker} @ $${exitFilledPrice}`);
      }
    } catch { /* non-fatal — p_l will be null */ }
  }

  await ledgerClose(id, exitReason, exitOrderId, exitFilledPrice).catch(e => {
    console.error(`[SENTINEL] Ledger close failed for ${ticker}:`, e.message);
  });
}

// ── Circuit breaker ───────────────────────────────────────────────────────
async function fetchConfig(key) {
  const res = await pool.query(
    `SELECT value FROM pee1_execution_config WHERE key = $1`, [key]
  );
  return res.rows[0]?.value ?? null;
}

async function isCircuitBreakerActive() {
  const res = await pool.query(
    `SELECT id, trigger_reason, expires_at FROM pee1_circuit_breaker
     WHERE cleared_at IS NULL AND expires_at > NOW()
     ORDER BY triggered_at DESC LIMIT 1`
  );
  if (!res.rows.length) return null;
  return res.rows[0];
}

async function triggerCircuitBreaker({ equityOpen, equityNow, drawdownPct, thresholdPct, hours }) {
  const expiresAt = new Date(Date.now() + hours * 60 * 60 * 1000).toISOString();
  await pool.query(
    `INSERT INTO pee1_circuit_breaker
       (trigger_reason, expires_at, vault_equity_open, vault_equity_low, drawdown_pct, threshold_pct)
     VALUES ('max_drawdown', $1, $2, $3, $4, $5)`,
    [expiresAt, equityOpen, equityNow, drawdownPct, thresholdPct]
  );
  console.log(`[SENTINEL] ⚡ CIRCUIT BREAKER TRIGGERED | drawdown=${drawdownPct.toFixed(2)}% > ${thresholdPct}% | halt until ${expiresAt}`);
}

async function checkMaxDrawdown(equityNow) {
  // Session open equity = equity at the earliest 'submitted' trade today, or current
  const res = await pool.query(
    `SELECT vault_equity_at_signal FROM personal_trade_ledger
     WHERE DATE(signal_detected_at) = CURRENT_DATE
     ORDER BY signal_detected_at ASC LIMIT 1`
  );
  const equityOpen = parseFloat(res.rows[0]?.vault_equity_at_signal ?? equityNow);
  if (equityOpen <= 0) return null;

  const drawdownPct = ((equityOpen - equityNow) / equityOpen) * 100;
  const thresholdPct = parseFloat(await fetchConfig("max_drawdown_pct") ?? "5.0");
  const hours = parseInt(await fetchConfig("circuit_breaker_hours") ?? "24", 10);

  if (drawdownPct >= thresholdPct) {
    await triggerCircuitBreaker({ equityOpen, equityNow, drawdownPct, thresholdPct, hours });
    return { triggered: true, drawdownPct, thresholdPct };
  }
  return { triggered: false, drawdownPct, thresholdPct };
}

// ── Main ──────────────────────────────────────────────────────────────────
export async function runSentinel() {
  console.log("[SENTINEL] Starting position audit...");

  // Circuit breaker: check if already halted
  const existingHalt = await isCircuitBreakerActive().catch(() => null);
  if (existingHalt) {
    console.log(`[SENTINEL] ⚡ Circuit breaker ACTIVE (${existingHalt.trigger_reason}) — expires ${existingHalt.expires_at}. No new actions.`);
    return { halted: true, reason: existingHalt.trigger_reason, expires: existingHalt.expires_at };
  }

  const ALPACA_BASE = await resolveAlpacaBase();
  console.log(`[SENTINEL] Alpaca base: ${ALPACA_BASE}`);

  const [positions, spyDk, accountRaw] = await Promise.all([
    fetchOpenPositions(),
    fetchSpyDk(),
    alpacaGet("/v2/account", ALPACA_BASE).catch(() => null),
  ]);

  const equityNow = parseFloat(accountRaw?.equity ?? "0");
  console.log(`[SENTINEL] Open positions: ${positions.length} | SPY D_k: ${spyDk ?? "unknown"} | Equity: $${equityNow.toFixed(2)}`);

  // Max drawdown circuit breaker check (runs before any per-position logic)
  if (equityNow > 0) {
    const ddCheck = await checkMaxDrawdown(equityNow).catch(e => {
      console.error("[SENTINEL] Drawdown check failed:", e.message);
      return null;
    });
    if (ddCheck?.triggered) {
      console.log(`[SENTINEL] ⚡ MAX DRAWDOWN — liquidating all ${positions.length} positions`);
      for (const pos of positions) {
        await killPosition(pos, "sentinel_max_drawdown", ALPACA_BASE);
      }
      return { halted: true, reason: "max_drawdown", drawdownPct: ddCheck.drawdownPct };
    } else if (ddCheck) {
      console.log(`[SENTINEL] Drawdown check: ${ddCheck.drawdownPct.toFixed(2)}% / ${ddCheck.thresholdPct}% threshold — OK`);
    }
  }

  console.log(`[SENTINEL] Open positions: ${positions.length} | SPY D_k: ${spyDk ?? "unknown"}`);

  // Wave 3 flip — liquidate Ch1 (3WA) positions only if SPY D_k is no longer 1
  // Ch2 positions use their own per-ticker D_k exit (Exit B) — SPY flip does not apply
  const spyFlip = spyDk !== null && spyDk !== 1;
  if (spyFlip) {
    const exemptClasses = new Set(["CH2", "CH3"]);
    const ch1Positions = positions.filter(p => !exemptClasses.has(String(p.signal_class ?? "").trim().toUpperCase()));
    if (ch1Positions.length > 0) {
      console.log(`[SENTINEL] SPY D_k=${spyDk} — Wave 3 GONE — liquidating ${ch1Positions.length} Ch1 position(s)`);
      for (const pos of ch1Positions) {
        await killPosition(pos, "sentinel_spy_flip", ALPACA_BASE);
      }
    } else {
      console.log(`[SENTINEL] SPY D_k=${spyDk} — Wave 3 GONE — no Ch1 positions to liquidate (Ch2 positions use ticker-level D_k exit)`);
    }
  }

  // ── Sync fill/cancel status from Alpaca → ledger ─────────────────────────
  const submittedPositions = positions.filter(p => p.status === "submitted" || !p.entry_filled_at);
  if (submittedPositions.length > 0) {
    console.log(`[SENTINEL] Syncing fill status for ${submittedPositions.length} submitted positions...`);
    for (const pos of submittedPositions) {
      if (!pos.alpaca_order_id) continue;
      try {
        const order = await alpacaGet(`/v2/orders/${pos.alpaca_order_id}`, ALPACA_BASE);
        if (order?.status === "filled" || order?.status === "partially_filled") {
          const filledPrice = parseFloat(order.filled_avg_price ?? "0");
          const filledAt = order.filled_at ?? new Date().toISOString();
          if (filledPrice > 0) {
            await pool.query(
              `UPDATE personal_trade_ledger
               SET status='filled', entry_filled_price=$1, entry_filled_at=$2
               WHERE id=$3 AND status='submitted'`,
              [filledPrice, filledAt, pos.id]
            );
            console.log(`[SENTINEL] Fill synced: ${pos.ticker} @ $${filledPrice}`);
            pos.status = "filled"; // update in-memory so exit checks work
          }
        } else if (order?.status === "canceled" && parseFloat(order.filled_qty ?? "0") === 0) {
          // Order was cancelled before filling — mark ledger record as cancelled
          await pool.query(
            `UPDATE personal_trade_ledger SET status='cancelled' WHERE id=$1 AND status='submitted'`,
            [pos.id]
          );
          console.log(`[SENTINEL] Cancel synced: ${pos.ticker} — order cancelled, never filled`);
          pos.status = "cancelled"; // skip exit checks below
        }
      } catch (e) {
        console.warn(`[SENTINEL] Fill sync failed for ${pos.ticker}: ${e.message}`);
      }
    }
  }

  // ── Sync filled positions that were closed by bracket TP/SL ──────────────
  const filledPositions = positions.filter(p => p.status === "filled" && p.entry_filled_at);
  for (const pos of filledPositions) {
    try {
      await alpacaGet(`/v2/positions/${encodeURIComponent(pos.ticker)}`, ALPACA_BASE);
      // Position still open — no action needed
    } catch (e) {
      const msg = String(e.message);
      if (msg.includes("40410000") || msg.toLowerCase().includes("position does not exist")) {
        // Bracket TP or SL closed this position — get exit price from bracket legs
        let bracketExitPrice = null;
        if (pos.alpaca_order_id) {
          try {
            const parentOrder = await alpacaGet(`/v2/orders/${pos.alpaca_order_id}`, ALPACA_BASE);
            for (const leg of (parentOrder?.legs ?? [])) {
              if (leg.filled_avg_price && leg.side === "sell") {
                bracketExitPrice = parseFloat(leg.filled_avg_price);
                break;
              }
            }
          } catch { /* non-fatal */ }
        }
        console.log(`[SENTINEL] Bracket exit detected: ${pos.ticker} @ $${bracketExitPrice ?? "unknown"} — marking DB closed.`);
        await ledgerClose(pos.id, "bracket_tp_sl_exit", null, bracketExitPrice).catch(ex => {
          console.error(`[SENTINEL] Ledger close failed for ${pos.ticker}:`, ex.message);
        });
        pos.status = "closed"; // skip exit checks below
      }
    }
  }

  // Per-position checks (skip cancelled or already-closed records)
  for (const pos of positions) {
    if (pos.status === "cancelled" || pos.status === "closed") continue;
    const fields = await fetchStructuralFields(pos.ticker);
    const signalClass = String(pos.signal_class ?? "").trim().toUpperCase();

    // ── Chapter 2 exit logic (independent path) ─────────────────────────
    if (signalClass === "CH2") {
      const currentSUf = isFinite(fields.s_uf) ? fields.s_uf : null;
      const currentDk  = isFinite(fields.d_k)  ? fields.d_k  : null;

      // Exit A — Acceleration complete: S_UF crossed into high-conviction band
      if (currentSUf !== null && currentSUf >= 0.75) {
        console.log(`[SENTINEL] CH2 EXIT-A ${pos.ticker} | S_UF=${currentSUf} >= 0.75 — acceleration complete, taking profit`);
        await killPosition(pos, "ch2_exit_acceleration_complete", ALPACA_BASE);
        continue;
      }

      // Exit B — Directional collapse: D_k no longer 1
      if (currentDk !== null && currentDk !== 1) {
        console.log(`[SENTINEL] CH2 EXIT-B ${pos.ticker} | D_k=${currentDk} — directional collapse, exiting`);
        await killPosition(pos, "ch2_exit_dk_collapse", ALPACA_BASE);
        continue;
      }

      // Exit D — Trailing profit ratchet
      // Once gain exceeds 5%, set a rising floor that locks in profit.
      // Floor = max(0, (max_gain - 5%) * 0.5). Ratchets up only, never down.
      // Checked every sentinel cycle (~5 min during market hours).
      // Must use Alpaca live price — DB has no current_price field.
      try {
        const alpacaCh2Pos = await alpacaGet(`/v2/positions/${encodeURIComponent(pos.ticker)}`, ALPACA_BASE).catch(() => null);
        const costBasis = parseFloat(alpacaCh2Pos?.avg_entry_price ?? pos.avg_entry_price ?? "0");
        const currentPrice = parseFloat(alpacaCh2Pos?.current_price ?? "0");
        if (costBasis > 0 && currentPrice > 0) {
          const gainPct = ((currentPrice / costBasis) - 1) * 100;

          // Track max gain per position in global cache
          if (!global._maxGainCache) global._maxGainCache = {};
          const prevMax = global._maxGainCache[pos.ticker] ?? 0;
          const maxGain = Math.max(prevMax, gainPct);
          global._maxGainCache[pos.ticker] = maxGain;

          // Momentum-aware profit exit using τ_out energy ratio
          // High gain + exhausted energy = take profit now
          // High gain + plenty of energy = let it run with wide trail
          const cached = (global._tauCache ?? {})[pos.ticker];
          const tauOut = cached?.tau_out_days ?? 0;
          const entryDate = pos.signal_detected_at ?? pos.created_at;
          let posAge = 0;
          if (entryDate) {
            posAge = Math.floor((Date.now() - new Date(entryDate).getTime()) / (1000*60*60*24));
          }
          // energyRatio: 0 = fully spent, 1 = just entered
          const energyRatio = tauOut > 0 ? Math.max(0, 1 - posAge / tauOut) : 0.5;

          // Tighten trail as energy depletes:
          //   Full energy (1.0): floor = (max - 5%) * 0.4  (wide, let it run)
          //   Half energy (0.5): floor = (max - 4%) * 0.55
          //   Low energy  (0.2): floor = (max - 3%) * 0.65 (tight, protect gains)
          //   Exhausted   (0.0): floor = (max - 2%) * 0.75 (very tight)
          const cushion = 2 + 3 * energyRatio;       // 2-5% cushion
          const trailPct = 0.75 - 0.35 * energyRatio; // 40-75% trail factor
          const floorPct = Math.max(0, (maxGain - cushion) * trailPct);

          if (maxGain >= 5.0 && gainPct <= floorPct) {
            console.log(
              `[SENTINEL] CH2 EXIT-D ${pos.ticker} | trailing profit hit floor ` +
              `(current=${gainPct.toFixed(1)}% max=${maxGain.toFixed(1)}% floor=${floorPct.toFixed(1)}% energy=${energyRatio.toFixed(2)})`
            );
            await killPosition(pos, "ch2_exit_trailing_profit", ALPACA_BASE);
            continue;
          }
        }
      } catch (trailErr) {
        // Non-fatal — continue to other exit checks
      }

      // Exit C — Exhaustion Timer (τ_out) — bar-level resolution
      // τ_in = consecutive TRADING DAYS D_k was compressed before expansion
      // τ_out = floor(τ_in / 3) = trading days of expansion energy
      //
      // Uses backfill cache (tau_backfill_days.json) for bar-level accuracy.
      // The DB (runtime_decisions_history) only has gate-level data which
      // collapses months of compression into 1 gate — wrong unit of measure.
      // The backfill ran the L0-L4 kernel on Polygon bars to get true day counts.
      try {
        // Load backfill cache (computed by tfe_cold_start_backfill)
        if (!global._tauCache) {
          try {
            const { readFileSync, existsSync } = await import("fs");
            const tauPath = "/app/tau_backfill_days.json";
            if (existsSync(tauPath)) {
              const raw = readFileSync(tauPath, "utf-8");
              global._tauCache = JSON.parse(raw);
              console.log(`[SENTINEL] τ cache loaded: ${Object.keys(global._tauCache).length} entries`);
            } else {
              global._tauCache = {};
            }
          } catch {
            global._tauCache = {};
          }
        }

        const cached = global._tauCache[pos.ticker];
        if (cached && cached.tau_out_days > 0) {
          const tauIn = cached.tau_in_days;
          const tauOut = cached.tau_out_days;
          const expansionDays = cached.expansion_days ?? 0;

          // Position age: days since entry
          const entryDate = pos.signal_detected_at ?? pos.created_at;
          let positionAge = expansionDays; // fallback to backfill expansion count
          if (entryDate) {
            const entryMs = new Date(entryDate).getTime();
            const nowMs = Date.now();
            positionAge = Math.floor((nowMs - entryMs) / (1000 * 60 * 60 * 24));
          }

          if (positionAge > tauOut) {
            console.log(
              `[SENTINEL] CH2 EXIT-C ${pos.ticker} | τ_in=${tauIn}d τ_out=${tauOut}d age=${positionAge}d — ` +
              `structural energy spent, exiting`
            );
            await killPosition(pos, "ch2_exit_tau_exhaustion", ALPACA_BASE);
            continue;
          }

          const remaining = tauOut - positionAge;
          console.log(
            `[SENTINEL] CH2 ${pos.ticker} CLEAR | S_UF=${currentSUf ?? "n/a"} | D_k=${currentDk ?? "n/a"} | ` +
            `τ_in=${tauIn}d τ_out=${tauOut}d age=${positionAge}d (${remaining}d remaining)`
          );
        } else if (cached && cached.status === "EXPIRED") {
          // Backfill already flagged this as expired
          console.log(
            `[SENTINEL] CH2 EXIT-C ${pos.ticker} | EXPIRED per backfill ` +
            `(compressed ${cached.tau_in_days}d, budget ${cached.tau_out_days}d, expanded ${cached.expansion_days}d)`
          );
          await killPosition(pos, "ch2_exit_tau_exhaustion", ALPACA_BASE);
          continue;
        } else {
          console.log(`[SENTINEL] CH2 ${pos.ticker} CLEAR | S_UF=${currentSUf ?? "n/a"} | D_k=${currentDk ?? "n/a"} | no τ data`);
        }
      } catch (tauErr) {
        console.log(`[SENTINEL] CH2 ${pos.ticker} CLEAR | S_UF=${currentSUf ?? "n/a"} | D_k=${currentDk ?? "n/a"} | τ error: ${tauErr.message}`);
      }
      continue;
    }

    // ── Chapter 3 — fuel gauge exit logic ────────────────────────────────
    if (signalClass === "CH3") {
      // CH3 exits: bracket (TP/SL) as safety net, fuel gauge as primary.
      // Fuel gauge: monitor real-time volume flow. When fuel runs out, exit.
      try {
        // Check if bracket already closed this position
        const alpacaPos = await alpacaGet(`/v2/positions/${encodeURIComponent(pos.ticker)}`, ALPACA_BASE).catch(() => null);
        if (!alpacaPos) {
          console.log(`[SENTINEL] CH3 ${pos.ticker} — position closed by bracket (TP/SL). Marking DB closed.`);
          await ledgerClose(pos.id, "ch3_bracket_exit", null).catch(e => {
            console.error(`[SENTINEL] CH3 ledger close failed for ${pos.ticker}:`, e.message);
          });
          continue;
        }

        const currentPrice = parseFloat(alpacaPos?.current_price ?? "0");
        const entryPrice   = parseFloat(alpacaPos?.avg_entry_price ?? "0");
        const plPct        = entryPrice > 0 ? (currentPrice - entryPrice) / entryPrice : 0;
        const tpPrice = parseFloat(pos.take_profit_price ?? "0");
        const slPrice = parseFloat(pos.stop_loss_price ?? "0");

        // ── Fuel Gauge: check real-time volume vs previous day ──────────
        // Volume is the fuel. When it dries up, the move is over.
        let fuelStatus = "UNKNOWN";
        let volumeRatio = null;
        try {
          const POLYGON_KEY = process.env.MASSIVE_API_KEY ?? process.env.POLYGON_API_KEY ?? "";
          if (POLYGON_KEY) {
            const snapResp = await fetch(
              `https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers/${pos.ticker}?apiKey=${POLYGON_KEY}`
            );
            if (snapResp.ok) {
              const snapData = await snapResp.json();
              const snap = snapData?.ticker;
              if (snap) {
                const todayVol  = snap.day?.v ?? 0;
                const prevDayVol = snap.prevDay?.v ?? 0;

                // Normalize by time of day (early = low volume is normal)
                const now = new Date();
                const marketMins = (now.getUTCHours() - 13) * 60 + (now.getUTCMinutes() - 30);
                const tradingMinutes = Math.max(1, Math.min(390, marketMins));
                const expectedRatio = tradingMinutes / 390;

                volumeRatio = prevDayVol > 0
                  ? todayVol / (prevDayVol * expectedRatio)
                  : 1.0;

                // Fuel classification
                if (volumeRatio >= 1.5)      fuelStatus = "SURGING";
                else if (volumeRatio >= 1.0)  fuelStatus = "FLOWING";
                else if (volumeRatio >= 0.7)  fuelStatus = "THINNING";
                else                          fuelStatus = "EXHAUSTED";
              }
            }
          }
        } catch (volErr) {
          // Volume check is best-effort
        }

        // ── Smash and Grab exit logic ──────────────────────────────────
        // CH3 is fast in, fast out. Ride the surge, grab the moment
        // momentum decelerates. Never let a winner become a loser.
        //
        // Exit physics: the spring's kinetic energy is the fuel ratio.
        // When the fuel DECELERATES across two consecutive checks while
        // in profit, the expansion is over. Grab immediately.
        // Don't wait for fuel to drop below 1.0x — that's too late.
        //
        // Track fuel history per ticker in memory for derivative check.

        // Store fuel reading for deceleration check
        if (!global._ch3FuelHistory) global._ch3FuelHistory = {};
        const fuelHist = global._ch3FuelHistory[pos.ticker] || [];
        fuelHist.push(volumeRatio ?? 0);
        if (fuelHist.length > 5) fuelHist.shift(); // keep last 5 readings
        global._ch3FuelHistory[pos.ticker] = fuelHist;

        // Check deceleration: fuel dropping across last 2 consecutive checks
        const fuelDecelerating = fuelHist.length >= 2 &&
          fuelHist[fuelHist.length - 1] < fuelHist[fuelHist.length - 2];
        const fuelDecel2 = fuelHist.length >= 3 &&
          fuelHist[fuelHist.length - 1] < fuelHist[fuelHist.length - 2] &&
          fuelHist[fuelHist.length - 2] < fuelHist[fuelHist.length - 3];

        // Exit trigger: in profit + fuel decelerating across 2 consecutive checks
        if (plPct > 0.005 && fuelDecel2) {
          console.log(
            `[SENTINEL] CH3 ${pos.ticker} GRAB | P&L=${(plPct*100).toFixed(2)}% | ` +
            `fuel=${volumeRatio?.toFixed(2) ?? "?"}x (decel: ${fuelHist.slice(-3).map(f=>f.toFixed(2)).join('→')}) | ` +
            `Spring expansion over — taking profit`
          );
          await killPosition(pos, "ch3_smash_grab_decel", ALPACA_BASE);
          delete global._ch3FuelHistory[pos.ticker];
          continue;
        }

        // Backstop: fuel fully exhausted at any profit
        if (fuelStatus === "EXHAUSTED" && plPct > 0) {
          console.log(
            `[SENTINEL] CH3 ${pos.ticker} FUEL OUT | P&L=${(plPct*100).toFixed(2)}% | ` +
            `Grabbing remaining profit`
          );
          await killPosition(pos, "ch3_fuel_exhausted", ALPACA_BASE);
          delete global._ch3FuelHistory[pos.ticker];
          continue;
        }

        console.log(
          `[SENTINEL] CH3 ${pos.ticker} HOLD | P&L=${(plPct*100).toFixed(2)}% | ` +
          `entry=${entryPrice} | current=${currentPrice} | TP=${tpPrice} | SL=${slPrice} | ` +
          `fuel=${fuelStatus}${volumeRatio ? `(${volumeRatio.toFixed(2)}x)` : ""}`
        );
      } catch (e) {
        console.warn(`[SENTINEL] CH3 ${pos.ticker} — position check error: ${e.message}`);
      }
      continue;
    }

    // ── Chapter 1 (3WA) and legacy exit logic ───────────────────────────

    // Calamity check: R_rev_k > 0
    if (isFinite(fields.r_rev_k) && fields.r_rev_k > 0) {
      await killPosition(pos, "sentinel_calamity", ALPACA_BASE);
      continue;
    }

    // Zombie check: position older than tau_in_max bars
    const barCount = isFinite(fields.bar_count) ? fields.bar_count : null;
    if (barCount !== null && barCount > ZOMBIE_BAR_THRESHOLD) {
      await killPosition(pos, "sentinel_zombie", ALPACA_BASE);
      continue;
    }

    console.log(`[SENTINEL] ${pos.ticker} CLEAR | R_rev_k=${fields.r_rev_k ?? "n/a"} | bar_count=${barCount ?? "n/a"}`);
  }

  console.log("[SENTINEL] Audit complete.");
}

export async function closeSentinelPool() {
  await pool.end();
}
