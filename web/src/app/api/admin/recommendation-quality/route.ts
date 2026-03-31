import { readFile, stat } from "node:fs/promises";
import path from "node:path";
import { NextResponse } from "next/server";

import { readSessionUserFromRequest } from "@/lib/auth-session";
import { resolveWorkspaceRoot } from "@/lib/workspace-root";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type JsonRecord = Record<string, unknown>;

type QualityTargets = {
  target_5: number | null;
  target_20: number | null;
  target_60: number | null;
  target_avg: number | null;
  target_coverage: number | null;
  target_fallback_max: number | null;
};

type QualityWinner = {
  variant_name: string | null;
  source_mode: string | null;
  eval_mode: string | null;
  min_bars: number | null;
  policy_path: string | null;
  gates: {
    gate_5day: boolean;
    gate_20day: boolean;
    gate_60day: boolean;
    gate_sp_plus_4_proxy_avg: boolean;
    gate_coverage: boolean;
    gate_fallback: boolean;
    quality_gate_count: number;
    reliability_gate_count: number;
    total_gate_count: number;
  };
  horizon_outcome_over_index_pct: {
    "5": number | null;
    "20": number | null;
    "60": number | null;
  };
  avg_outcome_over_index_pct: number | null;
  coverage_rate: number | null;
  fallback_rate: number | null;
  reason: string | null;
};

/**
 * CP-2 audit context — emitted by tools/cp2_quality_audit.py via the
 * cp2_audit block in recommendation-quality-latest.json.
 */
type Cp2AuditContext = {
  profile: string | null;
  decisionPhysics: string | null;
  totalRows: number | null;
  evaluatedRows: number | null;
  fallbackRows: number | null;
  accumulateDecisionsInWindow: number | null;
  historyWindowDays: number | null;
  reasonCodeDistribution: Record<string, number> | null;
};

type RecommendationQualityPayload = {
  exists: boolean;
  status: string | null;
  generatedAtUtc: string | null;
  cpProfile: string | null;
  laneDir: string | null;
  summaryPath: string | null;
  rankedTablePath: string | null;
  methodology: string | null;
  targets: QualityTargets;
  winner: QualityWinner | null;
  cp2: Cp2AuditContext;
  error?: string;
};

// ---------------------------------------------------------------------------
// Paths
// ---------------------------------------------------------------------------

const ROOT_DIR = resolveWorkspaceRoot();
const PACKAGED_QUALITY_SUMMARY_PATH = path.join(
  ROOT_DIR,
  "web",
  "data",
  "recommendation-quality-latest.json",
);

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------

function numberOrNull(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function stringOrNull(value: unknown): string | null {
  const text = typeof value === "string" ? value.trim() : "";
  return text ? text : null;
}

function booleanOrFalse(value: unknown): boolean {
  return value === true;
}

function recordOrEmpty(value: unknown): JsonRecord {
  if (!value || typeof value !== "object" || Array.isArray(value)) return {};
  return value as JsonRecord;
}

async function requireAdmin(request: Request): Promise<NextResponse | null> {
  const user = await readSessionUserFromRequest(request);
  if (!user) {
    return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  }
  if (user.role !== "admin") {
    return NextResponse.json({ error: "Admin role required." }, { status: 403 });
  }
  return null;
}

async function readJsonRecord(filePath: string): Promise<JsonRecord> {
  const raw = await readFile(filePath, "utf-8");
  const parsed = JSON.parse(raw) as unknown;
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error(`JSON payload is not an object: ${filePath}`);
  }
  return parsed as JsonRecord;
}

async function pathExists(filePath: string): Promise<boolean> {
  try {
    await stat(filePath);
    return true;
  } catch {
    return false;
  }
}

// ---------------------------------------------------------------------------
// Builder helpers
// ---------------------------------------------------------------------------

function buildWinner(payload: JsonRecord): QualityWinner | null {
  const winner = (payload.winner as JsonRecord | undefined) ?? null;
  if (!winner) return null;
  const gates    = (winner.gates    as JsonRecord | undefined) ?? {};
  const horizons = (winner.horizon_outcome_over_index_pct as JsonRecord | undefined) ?? {};

  return {
    variant_name:   stringOrNull(winner.variant_name),
    source_mode:    stringOrNull(winner.source_mode),
    eval_mode:      stringOrNull(winner.eval_mode),
    min_bars:       numberOrNull(winner.min_bars),
    policy_path:    stringOrNull(winner.policy_path),
    gates: {
      gate_5day:                booleanOrFalse(gates.gate_5day),
      gate_20day:               booleanOrFalse(gates.gate_20day),
      gate_60day:               booleanOrFalse(gates.gate_60day),
      gate_sp_plus_4_proxy_avg: booleanOrFalse(gates.gate_sp_plus_4_proxy_avg),
      gate_coverage:            booleanOrFalse(gates.gate_coverage),
      gate_fallback:            booleanOrFalse(gates.gate_fallback),
      quality_gate_count:       numberOrNull(gates.quality_gate_count)     ?? 0,
      reliability_gate_count:   numberOrNull(gates.reliability_gate_count) ?? 0,
      total_gate_count:         numberOrNull(gates.total_gate_count)        ?? 0,
    },
    horizon_outcome_over_index_pct: {
      "5":  numberOrNull(horizons["5"]),
      "20": numberOrNull(horizons["20"]),
      "60": numberOrNull(horizons["60"]),
    },
    avg_outcome_over_index_pct: numberOrNull(winner.avg_outcome_over_index_pct),
    coverage_rate:              numberOrNull(winner.coverage_rate),
    fallback_rate:              numberOrNull(winner.fallback_rate),
    reason:                     stringOrNull(winner.reason),
  };
}

function buildCp2Context(payload: JsonRecord): Cp2AuditContext {
  const audit = recordOrEmpty(payload.cp2_audit);
  const dist  = audit.reason_code_distribution;
  let reasonCodeDistribution: Record<string, number> | null = null;
  if (dist && typeof dist === "object" && !Array.isArray(dist)) {
    reasonCodeDistribution = {};
    for (const [k, v] of Object.entries(dist as Record<string, unknown>)) {
      const n = numberOrNull(v);
      if (n !== null) reasonCodeDistribution[k] = n;
    }
  }

  return {
    profile:                      stringOrNull(audit.profile),
    decisionPhysics:              stringOrNull(audit.decision_physics),
    totalRows:                    numberOrNull(audit.total_rows),
    evaluatedRows:                numberOrNull(audit.evaluated_rows),
    fallbackRows:                 numberOrNull(audit.fallback_rows),
    accumulateDecisionsInWindow:  numberOrNull(audit.accumulate_decisions_in_window),
    historyWindowDays:            numberOrNull(audit.history_window_days),
    reasonCodeDistribution,
  };
}

// ---------------------------------------------------------------------------
// Empty fallback shapes
// ---------------------------------------------------------------------------

const EMPTY_TARGETS: QualityTargets = {
  target_5: null, target_20: null, target_60: null,
  target_avg: null, target_coverage: null, target_fallback_max: null,
};

const EMPTY_CP2: Cp2AuditContext = {
  profile: null, decisionPhysics: null, totalRows: null,
  evaluatedRows: null, fallbackRows: null,
  accumulateDecisionsInWindow: null, historyWindowDays: null,
  reasonCodeDistribution: null,
};

// ---------------------------------------------------------------------------
// GET handler
// ---------------------------------------------------------------------------

export async function GET(request: Request) {
  const denied = await requireAdmin(request);
  if (denied) return denied;

  const summaryExists = await pathExists(PACKAGED_QUALITY_SUMMARY_PATH);
  if (!summaryExists) {
    return NextResponse.json({
      exists: false,
      status: null,
      generatedAtUtc: null,
      cpProfile: null,
      laneDir: null,
      summaryPath: null,
      rankedTablePath: null,
      methodology: null,
      targets: EMPTY_TARGETS,
      winner: null,
      cp2: EMPTY_CP2,
      error: "recommendation-quality-latest.json not found. Run tools/cp2_quality_audit.py to generate.",
    } satisfies RecommendationQualityPayload);
  }

  try {
    const summary  = await readJsonRecord(PACKAGED_QUALITY_SUMMARY_PATH);
    const inputs   = recordOrEmpty(summary.inputs);
    const targets  = recordOrEmpty(inputs.targets);
    const notes    = recordOrEmpty(inputs.notes);

    return NextResponse.json({
      exists:         true,
      status:         stringOrNull(summary.status),
      generatedAtUtc: stringOrNull(summary.generated_at_utc),
      cpProfile:      stringOrNull(summary.cp_profile),
      laneDir:        null,
      summaryPath:    PACKAGED_QUALITY_SUMMARY_PATH,
      rankedTablePath: null,
      methodology:    stringOrNull(notes.accuracy_assessment_contract),
      targets: {
        target_5:            numberOrNull(targets.target_5),
        target_20:           numberOrNull(targets.target_20),
        target_60:           numberOrNull(targets.target_60),
        target_avg:          numberOrNull(targets.target_avg),
        target_coverage:     numberOrNull(targets.target_coverage),
        target_fallback_max: numberOrNull(targets.target_fallback_max),
      },
      winner: buildWinner(summary),
      cp2:    buildCp2Context(summary),
    } satisfies RecommendationQualityPayload);
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Failed to load recommendation quality.";
    return NextResponse.json({
      exists: false,
      status: null,
      generatedAtUtc: null,
      cpProfile: null,
      laneDir: null,
      summaryPath: null,
      rankedTablePath: null,
      methodology: null,
      targets: EMPTY_TARGETS,
      winner: null,
      cp2: EMPTY_CP2,
      error: message,
    } satisfies RecommendationQualityPayload);
  }
}
