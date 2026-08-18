import "server-only";

import {
  fetchAlpacaCustody,
  reconcileCustody,
  type ExecutionMode,
  type LedgerOpenPosition,
} from "@/lib/alpaca-custody";
import { evaluateRuntimeHealth } from "@/lib/runtime-health";
import { resolveRuntimePostgresPool } from "@/lib/runtime-db";
import { reconcileValidationReport } from "@/lib/validation-report-truth";

export type OperationalCheck = {
  key: string;
  ok: boolean;
  detail: string;
};

export type OperationalHealth = {
  healthy: boolean;
  checks: OperationalCheck[];
  generationId: string | null;
  validation: {
    exists: boolean;
    status: string;
    blockingReason: string | null;
    generatedAtUtc: string | null;
  };
  custody: {
    executionMode: string | null;
    brokerStatus: string;
    brokerPositions: number | null;
    ledgerSymbols: number | null;
    discrepancies: number | null;
    byStatus: Record<string, number>;
    reasons: string[];
  };
};

type ValidationLane = OperationalHealth["validation"];
type CustodyLane = OperationalHealth["custody"];

function executionMode(value: unknown): ExecutionMode {
  if (value === "paper" || value === "live") return value;
  throw new Error("execution_mode_missing_or_invalid");
}

async function loadValidationLane(): Promise<ValidationLane> {
  const pool = resolveRuntimePostgresPool();
  const table = await pool.query<{ table_name: string | null }>(
    "SELECT to_regclass('public.runtime_validation_reports')::text AS table_name",
  );
  if (!table.rows[0]?.table_name) {
    return { exists: false, status: "not_run", blockingReason: "validation_history_missing", generatedAtUtc: null };
  }
  const result = await pool.query<{ report_json: unknown }>(
    `SELECT report_json
     FROM runtime_validation_reports
     ORDER BY generated_at_utc DESC, created_at DESC
     LIMIT 1`,
  );
  if (!result.rows.length) {
    return { exists: false, status: "not_run", blockingReason: "validation_report_missing", generatedAtUtc: null };
  }
  const report = reconcileValidationReport(result.rows[0].report_json);
  if (!report) {
    return { exists: true, status: "fail", blockingReason: "validation_report_invalid", generatedAtUtc: null };
  }
  return {
    exists: true,
    status: String(report.status ?? "fail"),
    blockingReason: report.blocking_reason ?? null,
    generatedAtUtc: report.generated_at_utc ?? null,
  };
}

async function loadCustodyLane(): Promise<CustodyLane> {
  const pool = resolveRuntimePostgresPool();
  const [ledger, configuredMode] = await Promise.all([
    pool.query<LedgerOpenPosition>(
      `SELECT id, ticker, signal_class, shares,
              entry_filled_price, dollar_allocation, atr_14,
              spy_dk, s_uf, bar_count, status,
              signal_detected_at, entry_filled_at, alpaca_order_id
       FROM personal_trade_ledger
       WHERE status IN ('submitted', 'filled')
       ORDER BY signal_detected_at DESC`,
    ),
    pool.query<{ value: string }>(
      "SELECT value FROM pee1_execution_config WHERE key = 'execution_mode' LIMIT 1",
    ),
  ]);
  const mode = executionMode(configuredMode.rows[0]?.value);
  const broker = await fetchAlpacaCustody(mode);
  const reconciled = reconcileCustody(ledger.rows, broker.positions, broker.openOrders);
  return {
    executionMode: mode,
    brokerStatus: broker.status,
    brokerPositions: reconciled.summary.brokerPositions,
    ledgerSymbols: reconciled.summary.ledgerSymbols,
    discrepancies: reconciled.summary.discrepancies,
    byStatus: reconciled.summary.byStatus,
    reasons: broker.reasons,
  };
}

export async function evaluateOperationalHealth(publicationAllowed: boolean): Promise<OperationalHealth> {
  const [runtime, validationResult, custodyResult] = await Promise.all([
    evaluateRuntimeHealth(),
    loadValidationLane().then(
      (value) => ({ ok: true as const, value }),
      (error: unknown) => ({ ok: false as const, error }),
    ),
    loadCustodyLane().then(
      (value) => ({ ok: true as const, value }),
      (error: unknown) => ({ ok: false as const, error }),
    ),
  ]);

  const validation: ValidationLane = validationResult.ok
    ? validationResult.value
    : {
        exists: false,
        status: "fail",
        blockingReason: validationResult.error instanceof Error ? validationResult.error.message : "validation_query_failed",
        generatedAtUtc: null,
      };
  const custody: CustodyLane = custodyResult.ok
    ? custodyResult.value
    : {
        executionMode: null,
        brokerStatus: "unavailable",
        brokerPositions: null,
        ledgerSymbols: null,
        discrepancies: null,
        byStatus: {},
        reasons: [custodyResult.error instanceof Error ? custodyResult.error.message : "custody_query_failed"],
      };

  const validationPass = validation.exists && validation.status === "pass";
  const brokerAvailable = custody.brokerStatus === "available";
  const custodyAligned = brokerAvailable && custody.discrepancies === 0;
  const checks: OperationalCheck[] = [
    { key: "publication-serving", ok: publicationAllowed, detail: publicationAllowed ? "Canonical publication is allowed." : "Canonical publication is blocked." },
    { key: "process-heartbeat", ok: runtime.checks.processHeartbeat, detail: runtime.checks.processHeartbeat ? "Next.js, sentinel, and fundamentals loop are alive." : "One or more essential process heartbeats are absent or stale." },
    { key: "database-reachability", ok: runtime.checks.database, detail: runtime.checks.database ? "PostgreSQL accepted a bounded health query." : "PostgreSQL health query failed." },
    { key: "snapshot-generation-receipts", ok: runtime.checks.snapshotReceipts, detail: runtime.checks.snapshotReceipts ? `Active snapshot generation receipts match (${runtime.generationId ?? "unknown"}).` : "Active snapshot generation receipts are missing or invalid." },
    { key: "validation-gate", ok: validationPass, detail: validationPass ? "Latest durable validation gate passed every check." : `Latest validation gate is ${validation.status}: ${validation.blockingReason ?? "no passing report"}.` },
    { key: "alpaca-custody-feed", ok: brokerAvailable, detail: brokerAvailable ? "Alpaca account, positions, and open orders are available." : `Alpaca custody is ${custody.brokerStatus}: ${custody.reasons.join(", ") || "unknown failure"}.` },
    { key: "broker-ledger-reconciliation", ok: custodyAligned, detail: custodyAligned ? "Broker and ledger custody reconcile with zero discrepancies." : `Custody discrepancies=${custody.discrepancies ?? "unknown"}.` },
  ];

  return {
    healthy: checks.every((check) => check.ok),
    checks,
    generationId: runtime.generationId,
    validation,
    custody,
  };
}
