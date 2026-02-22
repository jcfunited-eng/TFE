import { NextResponse } from "next/server";

import {
  classificationFromDecision,
  decisionInfoFromRow,
  findTickerRow,
  loadSnapshotRows,
} from "@/lib/uf-snapshot";
import { readSessionUserFromRequest } from "@/lib/auth-session";

export const runtime = "nodejs";

function toNumber(value: unknown): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

function toNumberOrNull(value: unknown): number | null {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

export async function GET(request: Request) {
  const sessionUser = await readSessionUserFromRequest(request);
  if (!sessionUser) {
    return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  }

  const { searchParams } = new URL(request.url);
  const ticker = (searchParams.get("ticker") ?? "").trim().toUpperCase();

  if (!ticker) {
    return NextResponse.json({ error: "Ticker is required." }, { status: 400 });
  }

  const { rows, sourcePath, attemptedPaths, failures } = await loadSnapshotRows();

  if (!sourcePath || rows.length === 0) {
    const decisionInfo = decisionInfoFromRow(null);
    const classification = classificationFromDecision(decisionInfo.decision);

    return NextResponse.json(
      {
        ticker,
        found: false,
        decision: decisionInfo.decision,
        decisionReason: decisionInfo.reasonText,
        decisionReasonCode: decisionInfo.reasonCode,
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
          price: null,
          classification,
        },
      },
    );
  }

  const row = findTickerRow(rows, ticker);
  const decisionInfo = decisionInfoFromRow(row);
  const classification = classificationFromDecision(decisionInfo.decision);

  if (!row) {
    return NextResponse.json({
      ticker,
      decision: decisionInfo.decision,
      decisionReason: decisionInfo.reasonText,
      decisionReasonCode: decisionInfo.reasonCode,
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
      price: toNumberOrNull(row.price),
      classification,
    },
    degraded: false,
  });
}
