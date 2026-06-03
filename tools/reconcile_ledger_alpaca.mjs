/**
 * tools/reconcile_ledger_alpaca.mjs
 *
 * Reconcile personal_trade_ledger against Alpaca positions (ground truth).
 *
 * For each Alpaca position:
 *   - Ensure exactly one open ledger row with correct entry date and qty
 *   - Fix orphan rows that have wrong entry_filled_at (NOW instead of real date)
 *   - Create missing open rows for ghost positions (DUK, VIRT, etc.)
 *   - Mark false-closed rows (closed but position still on Alpaca)
 *
 * Usage:
 *   DRY_RUN=1 node tools/reconcile_ledger_alpaca.mjs   # show changes, don't write
 *   node tools/reconcile_ledger_alpaca.mjs              # execute
 *
 * Must run from inside the ECS container or with prod DB + Alpaca credentials.
 * For Codespace: run via ECS exec.
 */

import pg from "pg";
import https from "https";

const pool = new pg.Pool({
  ssl: { rejectUnauthorized: false },
  max: 1,
});

const DRY_RUN = process.env.DRY_RUN === "1";
const BASE = "https://paper-api.alpaca.markets";
const KEY = process.env.ALPACA_API_KEY || process.env.APCA_API_KEY_ID;
const SECRET = process.env.ALPACA_SECRET_KEY || process.env.APCA_API_SECRET_KEY;

function alpacaGet(path) {
  return new Promise((resolve, reject) => {
    const req = https.get(BASE + path, {
      headers: { "APCA-API-KEY-ID": KEY, "APCA-API-SECRET-KEY": SECRET },
    }, (res) => {
      let d = "";
      res.on("data", (c) => d += c);
      res.on("end", () => resolve({ status: res.statusCode, body: d }));
    });
    req.on("error", reject);
  });
}

async function main() {
  console.log(`\n${"=".repeat(70)}`);
  console.log(`LEDGER/ALPACA RECONCILIATION ${DRY_RUN ? "(DRY RUN)" : "(LIVE)"}`);
  console.log(`${"=".repeat(70)}\n`);

  // 1. Get all Alpaca positions
  const posRes = await alpacaGet("/v2/positions");
  const alpacaPositions = JSON.parse(posRes.body);
  console.log(`Alpaca positions: ${alpacaPositions.length}`);

  const changes = [];

  for (const ap of alpacaPositions) {
    const ticker = ap.symbol.trim().toUpperCase();
    const alpacaQty = parseInt(ap.qty, 10);
    const alpacaEntry = parseFloat(ap.avg_entry_price);

    // 2. Get all ledger rows for this ticker
    const ledgerRes = await pool.query(
      `SELECT id, status, exit_reason, shares, entry_filled_price, entry_filled_at,
              exit_filled_price, run_id, signal_class
       FROM personal_trade_ledger
       WHERE UPPER(TRIM(ticker)) = $1
       ORDER BY created_at DESC`, [ticker]
    );

    const openRows = ledgerRes.rows.filter(r => r.status === "filled" || r.status === "submitted");
    const closedRows = ledgerRes.rows.filter(r => r.status === "closed");

    // Find the real entry date for the lot Alpaca currently holds.
    // Match on entry_filled_price ≈ Alpaca avg_entry_price (within $0.02).
    // Among matches, take the EARLIEST — that's when the currently-held lot started.
    // For multi-cycle tickers (BELFB, BSM), this skips intermediate round trips.
    const priceMatches = ledgerRes.rows
      .filter(r => r.entry_filled_at && r.entry_filled_price != null
        && Math.abs(parseFloat(r.entry_filled_price) - alpacaEntry) < 0.02)
      .sort((a, b) => new Date(a.entry_filled_at) - new Date(b.entry_filled_at)); // earliest first
    const realEntryRow = priceMatches[0]
      ?? ledgerRes.rows.filter(r => r.entry_filled_at && r.run_id !== "orphan_sync")
           .sort((a, b) => new Date(a.entry_filled_at) - new Date(b.entry_filled_at))[0]
      ?? null;
    const realEntryAt = realEntryRow?.entry_filled_at ?? null;
    const realSignalClass = realEntryRow?.signal_class ?? "CH2";
    const realEntrySource = realEntryRow ? `row_id=${realEntryRow.id} price=${realEntryRow.entry_filled_price}` : "none";

    // Find false-closed rows: closed but we know the position is still on Alpaca
    const falseClosed = closedRows.filter(r => r.exit_filled_price == null);

    if (openRows.length === 1) {
      const open = openRows[0];
      const isOrphan = open.run_id === "orphan_sync";
      const entryDateWrong = realEntryAt && isOrphan &&
        Math.abs(new Date(open.entry_filled_at) - new Date(realEntryAt)) > 3600000; // >1hr diff

      if (entryDateWrong) {
        changes.push({
          action: "FIX_ENTRY_DATE",
          ticker,
          rowId: open.id,
          oldDate: open.entry_filled_at,
          newDate: realEntryAt,
          source: realEntrySource,
          reason: `orphan row has wrong entry date (${open.entry_filled_at} → ${realEntryAt}, source: ${realEntrySource})`,
        });
      }

      // Fix shares if mismatched
      if (parseInt(open.shares) !== alpacaQty) {
        changes.push({
          action: "FIX_SHARES",
          ticker,
          rowId: open.id,
          oldShares: open.shares,
          newShares: alpacaQty,
          reason: `qty mismatch (ledger=${open.shares} alpaca=${alpacaQty})`,
        });
      }
    } else if (openRows.length === 0) {
      // Ghost: Alpaca has position, ledger has no open row
      changes.push({
        action: "CREATE_OPEN_ROW",
        ticker,
        qty: alpacaQty,
        entryPrice: alpacaEntry,
        entryAt: realEntryAt ?? new Date().toISOString(),
        signalClass: realSignalClass,
        source: realEntrySource,
        reason: `ghost position — Alpaca holds ${alpacaQty} shares, no open ledger row (entry source: ${realEntrySource})`,
      });
    } else if (openRows.length > 1) {
      // Multiple open rows — keep newest, close duplicates
      const keep = openRows[0];
      for (let i = 1; i < openRows.length; i++) {
        changes.push({
          action: "CLOSE_DUPLICATE",
          ticker,
          rowId: openRows[i].id,
          reason: `duplicate open row (keeping id=${keep.id})`,
        });
      }
    }

    // Mark false-closed rows
    for (const fc of falseClosed) {
      changes.push({
        action: "MARK_FALSE_CLOSE",
        ticker,
        rowId: fc.id,
        exitReason: fc.exit_reason,
        reason: `closed with null exit_filled_price but position still on Alpaca`,
      });
    }
  }

  // 3. Report
  console.log(`\nChanges: ${changes.length}\n`);
  const byAction = {};
  for (const c of changes) {
    byAction[c.action] = (byAction[c.action] || 0) + 1;
    console.log(`  ${c.action.padEnd(20)} | ${c.ticker.padEnd(6)} | id=${c.rowId ?? "NEW"} | ${c.reason}`);
  }
  console.log(`\nSummary: ${JSON.stringify(byAction)}`);

  if (DRY_RUN) {
    console.log("\nDRY RUN — no writes. Set DRY_RUN=0 or omit to execute.");
    await pool.end();
    return;
  }

  // 4. Execute
  console.log("\nExecuting...");
  for (const c of changes) {
    try {
      switch (c.action) {
        case "FIX_ENTRY_DATE":
          await pool.query(
            `UPDATE personal_trade_ledger
             SET entry_filled_at = $1, signal_detected_at = $1,
                 rationale_json = rationale_json || '{"reconciled":"entry_date_fixed"}'::jsonb
             WHERE id = $2`, [c.newDate, c.rowId]
          );
          console.log(`  FIXED entry date: ${c.ticker} id=${c.rowId}`);
          break;

        case "FIX_SHARES":
          await pool.query(
            `UPDATE personal_trade_ledger
             SET shares = $1,
                 rationale_json = rationale_json || '{"reconciled":"shares_fixed"}'::jsonb
             WHERE id = $2`, [c.newShares, c.rowId]
          );
          console.log(`  FIXED shares: ${c.ticker} id=${c.rowId} → ${c.newShares}`);
          break;

        case "CREATE_OPEN_ROW":
          await pool.query(
            `INSERT INTO personal_trade_ledger
               (ticker, run_id, signal_class, shares, status,
                entry_filled_price, entry_filled_at, signal_detected_at,
                rationale_json)
             VALUES ($1, 'reconciliation', $2, $3, 'filled', $4, $5, $5,
                     '{"reconciled":"ghost_position_created"}'::jsonb)`,
            [c.ticker, c.signalClass, c.qty, c.entryPrice, c.entryAt]
          );
          console.log(`  CREATED open row: ${c.ticker} qty=${c.qty}`);
          break;

        case "CLOSE_DUPLICATE":
          await pool.query(
            `UPDATE personal_trade_ledger
             SET status = 'cancelled', exit_reason = 'reconciliation_duplicate',
                 rationale_json = rationale_json || '{"reconciled":"duplicate_closed"}'::jsonb
             WHERE id = $1`, [c.rowId]
          );
          console.log(`  CLOSED duplicate: ${c.ticker} id=${c.rowId}`);
          break;

        case "MARK_FALSE_CLOSE":
          await pool.query(
            `UPDATE personal_trade_ledger
             SET rationale_json = rationale_json || '{"reconciled":"false_close_unfilled_sell"}'::jsonb
             WHERE id = $1`, [c.rowId]
          );
          console.log(`  MARKED false close: ${c.ticker} id=${c.rowId}`);
          break;
      }
    } catch (e) {
      console.error(`  ERROR on ${c.action} ${c.ticker}: ${e.message}`);
    }
  }

  // 5. Post-run verification
  console.log("\n--- POST-RUN VERIFICATION ---");
  const openCount = await pool.query(
    `SELECT COUNT(*) AS n FROM personal_trade_ledger WHERE status IN ('submitted','filled')`
  );
  console.log(`Open ledger rows: ${openCount.rows[0].n} (should be ${alpacaPositions.length})`);

  const mismatches = [];
  for (const ap of alpacaPositions) {
    const ticker = ap.symbol.trim().toUpperCase();
    const r = await pool.query(
      `SELECT id, shares, entry_filled_at FROM personal_trade_ledger
       WHERE UPPER(TRIM(ticker)) = $1 AND status IN ('submitted','filled')`, [ticker]
    );
    if (r.rows.length !== 1) {
      mismatches.push(`${ticker}: ${r.rows.length} open rows (expected 1)`);
    }
  }
  if (mismatches.length === 0) {
    console.log("Ledger ↔ Alpaca: 1:1 match ✓");
  } else {
    console.log(`Mismatches: ${mismatches.length}`);
    for (const m of mismatches) console.log(`  ${m}`);
  }

  // BSM entry date check
  const bsmCheck = await pool.query(
    `SELECT entry_filled_at FROM personal_trade_ledger
     WHERE UPPER(TRIM(ticker)) = 'BSM' AND status IN ('submitted','filled')`
  );
  if (bsmCheck.rows.length > 0) {
    console.log(`BSM entry_filled_at: ${bsmCheck.rows[0].entry_filled_at}`);
  }

  await pool.end();
  console.log("\nDone.");
}

main().catch(e => { console.error(e); process.exit(1); });
