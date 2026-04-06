import { NextResponse } from "next/server";

import {
  classificationFromDecision,
  decisionInfoFromRow,
  findTickerRow,
  loadSnapshotRows,
} from "@/lib/uf-snapshot";
import { getCurrentServerUser } from "@/lib/server-auth";
import { loadScreenerQuoteCache, quoteCachePriceFromRow } from "@/lib/screener-quote-cache";

export const runtime = "nodejs";

type SnapshotLoadResult = Awaited<ReturnType<typeof loadSnapshotRows>>;

const SNAPSHOT_LOAD_TIMEOUT_MS = normalizeTimeoutMs(process.env.TFE_RECOMMENDATIONS_QUICK_CHECK_SNAPSHOT_TIMEOUT_MS, 20000);

function toNumber(value: unknown): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

function toNumberOrNull(value: unknown): number | null {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function normalizeTimeoutMs(value: unknown, fallbackMs: number): number {
  const n = Number(value);
  if (!Number.isFinite(n)) return fallbackMs;

  const whole = Math.floor(n);
  if (whole < 1000) return 1000;
  if (whole > 45000) return 45000;
  return whole;
}

function assessmentFromReasonCode(reasonCode: string): { status: "ASSESSED" | "NOT_ASSESSED"; label: string } {
  if (reasonCode === "PSCF_POLICY_DECISION") {
    return { status: "ASSESSED", label: "Assessed" };
  }
  if (reasonCode === "PSCF_FALLBACK_INSUFFICIENT_BARS") {
    return { status: "NOT_ASSESSED", label: "Not Assessed (Insufficient Data)" };
  }
  return { status: "NOT_ASSESSED", label: "Not Assessed (Fallback Hold)" };
}

async function loadSnapshotRowsWithTimeout(): Promise<SnapshotLoadResult> {
  let timeoutHandle: ReturnType<typeof setTimeout> | null = null;

  try {
    return await Promise.race([
      loadSnapshotRows(),
      new Promise<SnapshotLoadResult>((_, reject) => {
        timeoutHandle = setTimeout(() => {
          reject(new Error(`Recommendations quick-check snapshot load timed out after ${SNAPSHOT_LOAD_TIMEOUT_MS}ms.`));
        }, SNAPSHOT_LOAD_TIMEOUT_MS);
      }),
    ]);
  } finally {
    if (timeoutHandle) clearTimeout(timeoutHandle);
  }
}

export async function GET(request: Request) {
  const sessionUser = await getCurrentServerUser();
  if (!sessionUser) {
    return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  }

  const { searchParams } = new URL(request.url);
  const ticker = (searchParams.get("ticker") ?? "").trim().toUpperCase();

  if (!ticker) {
    return NextResponse.json({ error: "Ticker is required." }, { status: 400 });
  }

  let rows: SnapshotLoadResult["rows"] = [];
  let sourcePath: string | null = null;
  let attemptedPaths: SnapshotLoadResult["attemptedPaths"] = [];
  let failures: SnapshotLoadResult["failures"] = [];

  try {
    const snapshot = await loadSnapshotRowsWithTimeout();
    rows = snapshot.rows;
    sourcePath = snapshot.sourcePath;
    attemptedPaths = snapshot.attemptedPaths;
    failures = snapshot.failures;
  } catch (error) {
    const reason = error instanceof Error ? error.message : "Unknown snapshot load failure.";
    failures = [{ path: "uf_snapshot.ses.json", reason }];
  }

  if (!sourcePath || rows.length === 0) {
    const decisionInfo = decisionInfoFromRow(null);
    const classification = classificationFromDecision(decisionInfo.decision);
    const assessment = assessmentFromReasonCode(decisionInfo.reasonCode);
    const quoteCache = loadScreenerQuoteCache();
    const quoteCachePrice = quoteCachePriceFromRow(quoteCache.quotes[ticker]);

    return NextResponse.json(
      {
        ticker,
        found: false,
        decision: decisionInfo.decision,
        decisionReason: decisionInfo.reasonText,
        decisionReasonCode: decisionInfo.reasonCode,
        assessmentStatus: assessment.status,
        assessmentLabel: assessment.label,
        reason: decisionInfo.reasonText,
        degraded: true,
        degradedReason: "snapshot_unavailable_or_empty",
        details: "Could not load uf_snapshot.ses.json envelope.",
        attemptedPaths,
        failures,
        snapshotSource: null,
        evidence: {
          barCount: decisionInfo.barCount,
          minBarsForAccumulate: decisionInfo.minBarsForAccumulate,
        },
        metrics: {
          S_UF: 0,
          R_UF: 0,
          asset_type: "unknown",
          price: quoteCachePrice,
          classification,
        },
      },
    );
  }

  const row = findTickerRow(rows, ticker);
  const decisionInfo = decisionInfoFromRow(row);
  const classification = classificationFromDecision(decisionInfo.decision);
  const assessment = assessmentFromReasonCode(decisionInfo.reasonCode);
  const quoteCache = loadScreenerQuoteCache();
  const quoteCachePrice = quoteCachePriceFromRow(quoteCache.quotes[ticker]);

  if (!row) {
    return NextResponse.json({
      ticker,
      decision: decisionInfo.decision,
      decisionReason: decisionInfo.reasonText,
      decisionReasonCode: decisionInfo.reasonCode,
      assessmentStatus: assessment.status,
      assessmentLabel: assessment.label,
      found: false,
      reason: decisionInfo.reasonText,
      snapshotSource: sourcePath,
      evidence: {
        barCount: decisionInfo.barCount,
        minBarsForAccumulate: decisionInfo.minBarsForAccumulate,
      },
    });
  }

  return NextResponse.json({
    ticker,
    decision: decisionInfo.decision,
    decisionReason: decisionInfo.reasonText,
    decisionReasonCode: decisionInfo.reasonCode,
    assessmentStatus: assessment.status,
    assessmentLabel: assessment.label,
    found: true,
    reason: decisionInfo.reasonText,
    snapshotSource: sourcePath,
    evidence: {
      barCount: decisionInfo.barCount,
      minBarsForAccumulate: decisionInfo.minBarsForAccumulate,
    },
    metrics: {
      S_UF: toNumber(row.S_UF),
      R_UF: toNumber(row.R_UF),
      asset_type: String(row.asset_type ?? "unknown"),
      price: quoteCachePrice ?? toNumberOrNull(row.price),
      classification,
    },
    degraded: false,
  });
}
