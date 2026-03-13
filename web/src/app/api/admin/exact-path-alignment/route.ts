import { readFile, stat } from "node:fs/promises";
import path from "node:path";
import { NextResponse } from "next/server";

import { readSessionUserFromRequest } from "@/lib/auth-session";
import { resolveWorkspaceRoot } from "@/lib/workspace-root";

type JsonRecord = Record<string, unknown>;

type ExactPathAlignmentPayload = {
  exists: boolean;
  generatedAtUtc: string | null;
  status: string | null;
  cpProfile: string | null;
  currentExactAnchorMode: string | null;
  proposedExactAnchorMode: string | null;
  phase1: {
    pass: boolean | null;
    rowsEvaluated: number | null;
    exactRestoredCount: number | null;
    exactRestoredPct: number | null;
    selectedCellChangeCount: number | null;
    decisionChangeCount: number | null;
    fallbackReasonChangeCount: number | null;
    blockedReasons: string[];
  };
  phase2: {
    ready: boolean | null;
    scope: string | null;
    routePath: string | null;
    note: string | null;
  };
  phase3: {
    ready: boolean | null;
    executed: boolean | null;
    blockedReasons: string[];
    note: string | null;
  };
  summaryMetrics: {
    rowsEvaluated: number | null;
    exactRestoredCount: number | null;
    exactRestoredPct: number | null;
    selectedCellChangeCount: number | null;
    decisionChangeCount: number | null;
    fallbackReasonChangeCount: number | null;
  };
  ladderLevelMigrations: Array<{
    from: string | null;
    to: string | null;
    rowCount: number | null;
    rowPct: number | null;
  }>;
  strategyFamilyGating: {
    requireL0Exact: string[];
    allowL1Relaxed: string[];
    safeOnlyL2L3L4: string[];
  };
  currentResolverParity: {
    totalRowsChecked: number | null;
    mismatchCount: number | null;
    mismatchRate: number | null;
    sortedNonzeroMismatches: Array<{
      id: string | null;
      rowCount: number | null;
      rowPct: number | null;
    }>;
  };
  recommendation: string | null;
  paths: {
    shadowJson: string | null;
    shadowMd: string | null;
    contractMd: string | null;
    readinessJson: string | null;
  };
  error?: string;
};

const ROOT_DIR = resolveWorkspaceRoot();
const SHADOW_JSON_PATH = path.join(ROOT_DIR, "exact_path_alignment_shadow_latest.json");
const SHADOW_MD_PATH = path.join(ROOT_DIR, "exact_path_alignment_shadow_latest.md");
const CONTRACT_MD_PATH = path.join(ROOT_DIR, "exact_path_alignment_contract_latest.md");
const READINESS_JSON_PATH = path.join(ROOT_DIR, "exact_path_alignment_readiness_latest.json");

function numberOrNull(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function stringOrNull(value: unknown): string | null {
  const text = typeof value === "string" ? value.trim() : "";
  return text ? text : null;
}

function booleanOrNull(value: unknown): boolean | null {
  if (value === true) return true;
  if (value === false) return false;
  return null;
}

function stringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  const out: string[] = [];
  for (const item of value) {
    const text = stringOrNull(item);
    if (!text) continue;
    out.push(text);
  }
  return out;
}

function recordOrEmpty(value: unknown): JsonRecord {
  if (!value || typeof value !== "object" || Array.isArray(value)) return {};
  return value as JsonRecord;
}

async function readOptionalJsonRecord(filePath: string): Promise<JsonRecord | null> {
  try {
    await stat(filePath);
    const raw = await readFile(filePath, "utf-8");
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new Error(`JSON payload is not an object: ${filePath}`);
    }
    return parsed as JsonRecord;
  } catch {
    return null;
  }
}

async function pathExists(filePath: string): Promise<boolean> {
  try {
    await stat(filePath);
    return true;
  } catch {
    return false;
  }
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

export async function GET(request: Request) {
  const denied = await requireAdmin(request);
  if (denied) return denied;

  try {
    const shadow = await readOptionalJsonRecord(SHADOW_JSON_PATH);
    const readiness = await readOptionalJsonRecord(READINESS_JSON_PATH);
    const contractExists = await pathExists(CONTRACT_MD_PATH);
    const shadowMdExists = await pathExists(SHADOW_MD_PATH);

    if (!shadow || !readiness) {
      return NextResponse.json({
        exists: false,
        generatedAtUtc: null,
        status: null,
        cpProfile: null,
        currentExactAnchorMode: null,
        proposedExactAnchorMode: null,
        phase1: {
          pass: null,
          rowsEvaluated: null,
          exactRestoredCount: null,
          exactRestoredPct: null,
          selectedCellChangeCount: null,
          decisionChangeCount: null,
          fallbackReasonChangeCount: null,
          blockedReasons: [],
        },
        phase2: {
          ready: null,
          scope: null,
          routePath: null,
          note: null,
        },
        phase3: {
          ready: null,
          executed: null,
          blockedReasons: [],
          note: null,
        },
        summaryMetrics: {
          rowsEvaluated: null,
          exactRestoredCount: null,
          exactRestoredPct: null,
          selectedCellChangeCount: null,
          decisionChangeCount: null,
          fallbackReasonChangeCount: null,
        },
        ladderLevelMigrations: [],
        strategyFamilyGating: {
          requireL0Exact: [],
          allowL1Relaxed: [],
          safeOnlyL2L3L4: [],
        },
        currentResolverParity: {
          totalRowsChecked: null,
          mismatchCount: null,
          mismatchRate: null,
          sortedNonzeroMismatches: [],
        },
        recommendation: null,
        paths: {
          shadowJson: null,
          shadowMd: null,
          contractMd: null,
          readinessJson: null,
        },
      } satisfies ExactPathAlignmentPayload);
    }

    const phase1 = recordOrEmpty(readiness.phase_1_shadow);
    const phase2 = recordOrEmpty(readiness.phase_2_admin_internal_exposure);
    const phase3 = recordOrEmpty(readiness.phase_3_controlled_adoption);
    const summary = recordOrEmpty(shadow.summary_metrics);
    const parity = recordOrEmpty(shadow.current_resolver_parity);
    const strategyFamilyGating = recordOrEmpty(readiness.strategy_family_gating_registry);
    const sortedMigrations = Array.isArray(summary.ladder_level_migration_counts_sorted)
      ? summary.ladder_level_migration_counts_sorted
      : [];
    const sortedParity = Array.isArray(parity.sorted_nonzero_mismatches)
      ? parity.sorted_nonzero_mismatches
      : [];

    return NextResponse.json({
      exists: true,
      generatedAtUtc: stringOrNull(shadow.generated_at_utc) ?? stringOrNull(readiness.generated_at_utc),
      status: stringOrNull(shadow.status) ?? stringOrNull(readiness.status),
      cpProfile: stringOrNull(shadow.cp_profile) ?? stringOrNull(readiness.cp_profile),
      currentExactAnchorMode: stringOrNull(readiness.current_exact_anchor_mode),
      proposedExactAnchorMode: stringOrNull(readiness.proposed_exact_anchor_mode),
      phase1: {
        pass: booleanOrNull(phase1.pass),
        rowsEvaluated: numberOrNull(phase1.rows_evaluated),
        exactRestoredCount: numberOrNull(phase1.exact_restored_count),
        exactRestoredPct: numberOrNull(phase1.exact_restored_pct),
        selectedCellChangeCount: numberOrNull(phase1.selected_cell_change_count),
        decisionChangeCount: numberOrNull(phase1.decision_change_count),
        fallbackReasonChangeCount: numberOrNull(phase1.fallback_reason_change_count),
        blockedReasons: stringArray(phase1.blocked_reasons),
      },
      phase2: {
        ready: booleanOrNull(phase2.ready),
        scope: stringOrNull(phase2.scope),
        routePath: stringOrNull(phase2.route_path),
        note: stringOrNull(phase2.note),
      },
      phase3: {
        ready: booleanOrNull(phase3.ready),
        executed: booleanOrNull(phase3.executed),
        blockedReasons: stringArray(phase3.blocked_reasons),
        note: stringOrNull(phase3.note),
      },
      summaryMetrics: {
        rowsEvaluated: numberOrNull(summary.rows_evaluated),
        exactRestoredCount: numberOrNull(summary.exact_restored_count),
        exactRestoredPct: numberOrNull(summary.exact_restored_pct),
        selectedCellChangeCount: numberOrNull(summary.selected_cell_change_count),
        decisionChangeCount: numberOrNull(summary.decision_change_count),
        fallbackReasonChangeCount: numberOrNull(summary.fallback_reason_change_count),
      },
      ladderLevelMigrations: sortedMigrations.map((item) => {
        const record = recordOrEmpty(item);
        return {
          from: stringOrNull(record.from),
          to: stringOrNull(record.to),
          rowCount: numberOrNull(record.row_count),
          rowPct: numberOrNull(record.row_pct),
        };
      }),
      strategyFamilyGating: {
        requireL0Exact: stringArray(strategyFamilyGating.require_L0_exact),
        allowL1Relaxed: stringArray(strategyFamilyGating.allow_L1_relaxed),
        safeOnlyL2L3L4: stringArray(strategyFamilyGating.safe_only_L2_L3_L4),
      },
      currentResolverParity: {
        totalRowsChecked: numberOrNull(parity.total_rows_checked),
        mismatchCount: numberOrNull(parity.mismatch_count),
        mismatchRate: numberOrNull(parity.mismatch_rate),
        sortedNonzeroMismatches: sortedParity.map((item) => {
          const record = recordOrEmpty(item);
          return {
            id: stringOrNull(record.id),
            rowCount: numberOrNull(record.row_count),
            rowPct: numberOrNull(record.row_pct),
          };
        }),
      },
      recommendation: stringOrNull(readiness.recommendation),
      paths: {
        shadowJson: SHADOW_JSON_PATH,
        shadowMd: shadowMdExists ? SHADOW_MD_PATH : null,
        contractMd: contractExists ? CONTRACT_MD_PATH : null,
        readinessJson: READINESS_JSON_PATH,
      },
    } satisfies ExactPathAlignmentPayload);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Failed to load exact path alignment artifacts.";
    return NextResponse.json({
      exists: false,
      generatedAtUtc: null,
      status: null,
      cpProfile: null,
      currentExactAnchorMode: null,
      proposedExactAnchorMode: null,
      phase1: {
        pass: null,
        rowsEvaluated: null,
        exactRestoredCount: null,
        exactRestoredPct: null,
        selectedCellChangeCount: null,
        decisionChangeCount: null,
        fallbackReasonChangeCount: null,
        blockedReasons: [],
      },
      phase2: {
        ready: null,
        scope: null,
        routePath: null,
        note: null,
      },
      phase3: {
        ready: null,
        executed: null,
        blockedReasons: [],
        note: null,
      },
      summaryMetrics: {
        rowsEvaluated: null,
        exactRestoredCount: null,
        exactRestoredPct: null,
        selectedCellChangeCount: null,
        decisionChangeCount: null,
        fallbackReasonChangeCount: null,
      },
      ladderLevelMigrations: [],
      strategyFamilyGating: {
        requireL0Exact: [],
        allowL1Relaxed: [],
        safeOnlyL2L3L4: [],
      },
      currentResolverParity: {
        totalRowsChecked: null,
        mismatchCount: null,
        mismatchRate: null,
        sortedNonzeroMismatches: [],
      },
      recommendation: null,
      paths: {
        shadowJson: null,
        shadowMd: null,
        contractMd: null,
        readinessJson: null,
      },
      error: message,
    } satisfies ExactPathAlignmentPayload);
  }
}
