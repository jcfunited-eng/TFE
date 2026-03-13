import { readdir, readFile, stat } from "node:fs/promises";
import path from "node:path";
import { NextResponse } from "next/server";

import { readSessionUserFromRequest } from "@/lib/auth-session";
import { resolveWorkspaceRoot } from "@/lib/workspace-root";

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

type RecommendationQualityFallbackLevel = {
  id: string;
  order: number;
  structuralCoverage: boolean;
  exactStructural: boolean;
  qualityAssessedUnderCurrentContract: boolean;
  description: string | null;
  runtimeRowCount: number | null;
  runtimeRate: number | null;
  runtimePct: number | null;
  snapshotRowCount: number | null;
  snapshotRate: number | null;
  snapshotPct: number | null;
  scoredUnderCurrentContract: boolean | null;
  assessedRowCount: number | null;
  excludedRowCount: number | null;
  avgOutcomeOverIndexPct: number | null;
  avgMeanExcessVsSpy: number | null;
  horizonOutcomeOverIndexPct: {
    "5": number | null;
    "20": number | null;
    "60": number | null;
  };
  horizonMeanExcessVsSpy: {
    "5": number | null;
    "20": number | null;
    "60": number | null;
  };
  notes: string[];
};

type RecommendationQualityTypedFallback = {
  available: boolean;
  schemaName: string | null;
  orthogonalFlags: string[];
  preservedLegacyFields: string[];
  phase3AAdminInternalReady: boolean | null;
  phase3AAdminInternalRecommendation: string | null;
  runtimeClassificationIntegrity: {
    totalRows: number | null;
    classifiedRows: number | null;
    unclassifiedRows: number | null;
    everyRowMapsToExactlyOneLevel: boolean | null;
  };
  runtimeDecisionContext: {
    snapshotPath: string | null;
    policyArtifactPath: string | null;
    persistedProvenanceRunId: string | null;
    decisionProvenanceMinBars: number | null;
    anomalyFallbackEnabled: boolean | null;
    note: string | null;
  };
  coverageSummary: {
    totalSnapshotRows: number | null;
    exactStructuralCoverageRate: number | null;
    exactStructuralCoveragePct: number | null;
    relaxedStructuralCoverageRate: number | null;
    relaxedStructuralCoveragePct: number | null;
    safePolicyFallbackRate: number | null;
    safePolicyFallbackPct: number | null;
    degradedUnmappedRate: number | null;
    degradedUnmappedPct: number | null;
    unavailableOrBlockedRate: number | null;
    unavailableOrBlockedPct: number | null;
    structuralCoverageRate: number | null;
    structuralCoveragePct: number | null;
    nonStructuralRate: number | null;
    nonStructuralPct: number | null;
    qualityWinnerCoverageRate: number | null;
    qualityWinnerFallbackRate: number | null;
  };
  compatibilityChecks: {
    allSnapshotRowsClassifiedExactlyOnce: boolean | null;
    structuralCoverageMatchesQualityWinner: boolean | null;
    nonStructuralShareMatchesQualityWinner: boolean | null;
  };
  levels: RecommendationQualityFallbackLevel[];
  paths: {
    schemaPath: string | null;
    runtimeSemanticsPath: string | null;
    adminBreakdownPath: string | null;
    promotionGatePlanPath: string | null;
  };
};

type RecommendationQualityPayload = {
  exists: boolean;
  status: string | null;
  generatedAtUtc: string | null;
  laneDir: string | null;
  summaryPath: string | null;
  rankedTablePath: string | null;
  methodology: string | null;
  targets: QualityTargets;
  winner: QualityWinner | null;
  provenance: {
    persistencePath: string | null;
    parityPath: string | null;
    latestRunId: string | null;
    completenessRate: number | null;
    mismatchRate: number | null;
    rolloutGatePass: boolean | null;
    status: string | null;
  };
  typedFallback: RecommendationQualityTypedFallback;
  error?: string;
};

const ROOT_DIR = resolveWorkspaceRoot();
const QUALITY_ROOT = path.join(ROOT_DIR, "backups", "runtime");
const QUALITY_PREFIX = "recommendation-quality-audit-lane-";
const PACKAGED_QUALITY_SUMMARY_PATH = path.join(ROOT_DIR, "web", "data", "recommendation-quality-latest.json");
const PROVENANCE_PERSISTENCE_PATH = path.join(ROOT_DIR, "current_l5_provenance_persistence_latest.json");
const PROVENANCE_PARITY_PATH = path.join(ROOT_DIR, "provenance_persistence_parity_latest.json");
const TYPED_FALLBACK_SCHEMA_PATH = path.join(ROOT_DIR, "typed_fallback_ladder_schema_latest.json");
const TYPED_FALLBACK_RUNTIME_PATH = path.join(ROOT_DIR, "runtime_fallback_semantics_latest.json");
const TYPED_FALLBACK_ADMIN_PATH = path.join(ROOT_DIR, "admin_quality_fallback_breakdown_latest.json");
const TYPED_FALLBACK_PROMOTION_PATH = path.join(ROOT_DIR, "promotion_gate_fallback_integration_latest.md");

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
    return await readJsonRecord(filePath);
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

async function readJsonRecord(filePath: string): Promise<JsonRecord> {
  const raw = await readFile(filePath, "utf-8");
  const parsed = JSON.parse(raw) as unknown;
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error(`JSON payload is not an object: ${filePath}`);
  }
  return parsed as JsonRecord;
}

async function resolveLatestQualitySource(): Promise<{
  laneDir: string | null;
  summaryPath: string;
  rankedTablePath: string | null;
}> {
  try {
    await stat(PACKAGED_QUALITY_SUMMARY_PATH);
    return {
      laneDir: null,
      summaryPath: PACKAGED_QUALITY_SUMMARY_PATH,
      rankedTablePath: null,
    };
  } catch {
    // fallback below
  }

  const entries = await readdir(QUALITY_ROOT, { withFileTypes: true });
  const candidates = entries
    .filter((entry) => entry.isDirectory() && entry.name.startsWith(QUALITY_PREFIX))
    .map((entry) => path.join(QUALITY_ROOT, entry.name));

  if (candidates.length === 0) {
    throw new Error("No recommendation quality summary source found.");
  }

  const ranked = await Promise.all(
    candidates.map(async (laneDir) => {
      const summaryPath = path.join(laneDir, "summary.json");
      const laneSummaryPath = path.join(laneDir, "lane-summary.json");
      try {
        const summaryStat = await stat(summaryPath);
        const laneSummaryStat = await stat(laneSummaryPath);
        return {
          laneDir,
          summaryPath,
          rankedTablePath: path.join(laneDir, "ranked-table.csv"),
          sortKey: Math.max(summaryStat.mtimeMs, laneSummaryStat.mtimeMs),
        };
      } catch {
        return null;
      }
    }),
  );

  const available = ranked.filter(
    (item): item is { laneDir: string; summaryPath: string; rankedTablePath: string; sortKey: number } => item !== null,
  );
  if (available.length === 0) {
    throw new Error("No readable recommendation quality summary source found.");
  }
  available.sort((a, b) => b.sortKey - a.sortKey);
  return {
    laneDir: available[0].laneDir,
    summaryPath: available[0].summaryPath,
    rankedTablePath: available[0].rankedTablePath,
  };
}

function buildWinner(payload: JsonRecord): QualityWinner | null {
  const winner = (payload.winner as JsonRecord | undefined) ?? null;
  if (!winner) return null;
  const gates = (winner.gates as JsonRecord | undefined) ?? {};
  const horizons = (winner.horizon_outcome_over_index_pct as JsonRecord | undefined) ?? {};

  return {
    variant_name: stringOrNull(winner.variant_name),
    source_mode: stringOrNull(winner.source_mode),
    eval_mode: stringOrNull(winner.eval_mode),
    min_bars: numberOrNull(winner.min_bars),
    policy_path: stringOrNull(winner.policy_path),
    gates: {
      gate_5day: booleanOrFalse(gates.gate_5day),
      gate_20day: booleanOrFalse(gates.gate_20day),
      gate_60day: booleanOrFalse(gates.gate_60day),
      gate_sp_plus_4_proxy_avg: booleanOrFalse(gates.gate_sp_plus_4_proxy_avg),
      gate_coverage: booleanOrFalse(gates.gate_coverage),
      gate_fallback: booleanOrFalse(gates.gate_fallback),
      quality_gate_count: numberOrNull(gates.quality_gate_count) ?? 0,
      reliability_gate_count: numberOrNull(gates.reliability_gate_count) ?? 0,
      total_gate_count: numberOrNull(gates.total_gate_count) ?? 0,
    },
    horizon_outcome_over_index_pct: {
      "5": numberOrNull(horizons["5"]),
      "20": numberOrNull(horizons["20"]),
      "60": numberOrNull(horizons["60"]),
    },
    avg_outcome_over_index_pct: numberOrNull(winner.avg_outcome_over_index_pct),
    coverage_rate: numberOrNull(winner.coverage_rate),
    fallback_rate: numberOrNull(winner.fallback_rate),
    reason: stringOrNull(winner.reason),
  };
}

function buildTypedFallbackPayload(
  schema: JsonRecord | null,
  runtimeSemantics: JsonRecord | null,
  adminBreakdown: JsonRecord | null,
  promotionGatePlanExists: boolean,
): RecommendationQualityTypedFallback {
  const schemaLevels = new Map<string, JsonRecord>();
  const runtimeLevels = recordOrEmpty(runtimeSemantics?.level_breakdown);
  const adminLevels = recordOrEmpty(adminBreakdown?.level_breakdown);
  const allIds = new Set<string>();

  const rawSchemaLevels = Array.isArray(schema?.levels) ? schema.levels : [];
  for (const item of rawSchemaLevels) {
    const record = recordOrEmpty(item);
    const id = stringOrNull(record.id);
    if (!id) continue;
    schemaLevels.set(id, record);
    allIds.add(id);
  }

  for (const id of Object.keys(runtimeLevels)) {
    allIds.add(id);
  }
  for (const id of Object.keys(adminLevels)) {
    allIds.add(id);
  }

  const levels = Array.from(allIds)
    .map((id) => {
      const schemaLevel = schemaLevels.get(id) ?? {};
      const runtimeLevel = recordOrEmpty(runtimeLevels[id]);
      const adminLevel = recordOrEmpty(adminLevels[id]);
      const order =
        numberOrNull(schemaLevel.order) ?? numberOrNull(adminLevel.level_order) ?? numberOrNull(runtimeLevel.level_order) ?? 999;

      return {
        id,
        order,
        structuralCoverage: booleanOrFalse(schemaLevel.structural_coverage),
        exactStructural: booleanOrFalse(schemaLevel.exact_structural),
        qualityAssessedUnderCurrentContract: booleanOrFalse(schemaLevel.quality_assessed_under_current_contract),
        description: stringOrNull(schemaLevel.description),
        runtimeRowCount: numberOrNull(runtimeLevel.row_count),
        runtimeRate: numberOrNull(runtimeLevel.rate),
        runtimePct: numberOrNull(runtimeLevel.pct),
        snapshotRowCount: numberOrNull(adminLevel.snapshot_row_count),
        snapshotRate: numberOrNull(adminLevel.snapshot_rate),
        snapshotPct: numberOrNull(adminLevel.snapshot_pct),
        scoredUnderCurrentContract: booleanOrNull(adminLevel.scored_under_current_contract),
        assessedRowCount: numberOrNull(adminLevel.assessed_row_count),
        excludedRowCount: numberOrNull(adminLevel.excluded_row_count),
        avgOutcomeOverIndexPct: numberOrNull(adminLevel.avg_outcome_over_index_pct),
        avgMeanExcessVsSpy: numberOrNull(adminLevel.avg_mean_excess_vs_spy),
        horizonOutcomeOverIndexPct: {
          "5": numberOrNull(recordOrEmpty(adminLevel.horizon_outcome_over_index_pct)["5"]),
          "20": numberOrNull(recordOrEmpty(adminLevel.horizon_outcome_over_index_pct)["20"]),
          "60": numberOrNull(recordOrEmpty(adminLevel.horizon_outcome_over_index_pct)["60"]),
        },
        horizonMeanExcessVsSpy: {
          "5": numberOrNull(recordOrEmpty(adminLevel.horizon_mean_excess_vs_spy)["5"]),
          "20": numberOrNull(recordOrEmpty(adminLevel.horizon_mean_excess_vs_spy)["20"]),
          "60": numberOrNull(recordOrEmpty(adminLevel.horizon_mean_excess_vs_spy)["60"]),
        },
        notes: stringArray(adminLevel.notes),
      } satisfies RecommendationQualityFallbackLevel;
    })
    .sort((a, b) => a.order - b.order || a.id.localeCompare(b.id));

  const classificationIntegrity = recordOrEmpty(runtimeSemantics?.classification_integrity);
  const runtimeContext = recordOrEmpty(runtimeSemantics?.source_context);
  const coverageSummary = recordOrEmpty(adminBreakdown?.coverage_summary);
  const compatibilityChecks = recordOrEmpty(adminBreakdown?.compatibility_checks);

  return {
    available: Boolean(schema || runtimeSemantics || adminBreakdown),
    schemaName: stringOrNull(schema?.schema_name),
    orthogonalFlags: stringArray(schema?.orthogonal_flags),
    preservedLegacyFields: stringArray(schema?.preserved_legacy_fields),
    phase3AAdminInternalReady: booleanOrNull(adminBreakdown?.phase_3a_admin_internal_ready),
    phase3AAdminInternalRecommendation: stringOrNull(adminBreakdown?.phase_3a_admin_internal_recommendation),
    runtimeClassificationIntegrity: {
      totalRows: numberOrNull(classificationIntegrity.total_rows),
      classifiedRows: numberOrNull(classificationIntegrity.classified_rows),
      unclassifiedRows: numberOrNull(classificationIntegrity.unclassified_rows),
      everyRowMapsToExactlyOneLevel: booleanOrNull(classificationIntegrity.every_row_maps_to_exactly_one_level),
    },
    runtimeDecisionContext: {
      snapshotPath: stringOrNull(runtimeContext.snapshot_path),
      policyArtifactPath: stringOrNull(runtimeContext.policy_artifact_path),
      persistedProvenanceRunId: stringOrNull(runtimeContext.persisted_provenance_run_id),
      decisionProvenanceMinBars: numberOrNull(runtimeContext.decision_provenance_min_bars),
      anomalyFallbackEnabled: booleanOrNull(runtimeContext.anomaly_fallback_enabled),
      note: stringOrNull(runtimeContext.note),
    },
    coverageSummary: {
      totalSnapshotRows: numberOrNull(coverageSummary.total_snapshot_rows),
      exactStructuralCoverageRate: numberOrNull(coverageSummary.exact_structural_coverage_rate),
      exactStructuralCoveragePct: numberOrNull(coverageSummary.exact_structural_coverage_pct),
      relaxedStructuralCoverageRate: numberOrNull(coverageSummary.relaxed_structural_coverage_rate),
      relaxedStructuralCoveragePct: numberOrNull(coverageSummary.relaxed_structural_coverage_pct),
      safePolicyFallbackRate: numberOrNull(coverageSummary.safe_policy_fallback_rate),
      safePolicyFallbackPct: numberOrNull(coverageSummary.safe_policy_fallback_pct),
      degradedUnmappedRate: numberOrNull(coverageSummary.degraded_unmapped_rate),
      degradedUnmappedPct: numberOrNull(coverageSummary.degraded_unmapped_pct),
      unavailableOrBlockedRate: numberOrNull(coverageSummary.unavailable_or_blocked_rate),
      unavailableOrBlockedPct: numberOrNull(coverageSummary.unavailable_or_blocked_pct),
      structuralCoverageRate: numberOrNull(coverageSummary.structural_coverage_rate),
      structuralCoveragePct: numberOrNull(coverageSummary.structural_coverage_pct),
      nonStructuralRate: numberOrNull(coverageSummary.non_structural_rate),
      nonStructuralPct: numberOrNull(coverageSummary.non_structural_pct),
      qualityWinnerCoverageRate: numberOrNull(coverageSummary.quality_winner_coverage_rate),
      qualityWinnerFallbackRate: numberOrNull(coverageSummary.quality_winner_fallback_rate),
    },
    compatibilityChecks: {
      allSnapshotRowsClassifiedExactlyOnce: booleanOrNull(compatibilityChecks.all_snapshot_rows_classified_exactly_once),
      structuralCoverageMatchesQualityWinner: booleanOrNull(
        compatibilityChecks.structural_coverage_matches_quality_winner,
      ),
      nonStructuralShareMatchesQualityWinner: booleanOrNull(
        compatibilityChecks.non_structural_share_matches_quality_winner,
      ),
    },
    levels,
    paths: {
      schemaPath: schema ? TYPED_FALLBACK_SCHEMA_PATH : null,
      runtimeSemanticsPath: runtimeSemantics ? TYPED_FALLBACK_RUNTIME_PATH : null,
      adminBreakdownPath: adminBreakdown ? TYPED_FALLBACK_ADMIN_PATH : null,
      promotionGatePlanPath: promotionGatePlanExists ? TYPED_FALLBACK_PROMOTION_PATH : null,
    },
  };
}

export async function GET(request: Request) {
  const denied = await requireAdmin(request);
  if (denied) return denied;

  try {
    const latest = await resolveLatestQualitySource();
    const summary = await readJsonRecord(latest.summaryPath);
    const inputs = recordOrEmpty(summary.inputs);
    const targets = recordOrEmpty(inputs.targets);
    const notes = recordOrEmpty(inputs.notes);
    const provenancePersistence = await readOptionalJsonRecord(PROVENANCE_PERSISTENCE_PATH);
    const provenanceParity = await readOptionalJsonRecord(PROVENANCE_PARITY_PATH);
    const typedFallbackSchema = await readOptionalJsonRecord(TYPED_FALLBACK_SCHEMA_PATH);
    const typedFallbackRuntime = await readOptionalJsonRecord(TYPED_FALLBACK_RUNTIME_PATH);
    const typedFallbackAdmin = await readOptionalJsonRecord(TYPED_FALLBACK_ADMIN_PATH);
    const promotionGatePlanExists = await pathExists(TYPED_FALLBACK_PROMOTION_PATH);

    const decisionParity = recordOrEmpty(provenanceParity?.decision_provenance_parity);
    const rolloutGate = recordOrEmpty(provenanceParity?.rollout_gate);

    return NextResponse.json({
      exists: true,
      status: stringOrNull(summary.status),
      generatedAtUtc: stringOrNull(summary.generated_at_utc),
      laneDir: latest.laneDir,
      summaryPath: latest.summaryPath,
      rankedTablePath: latest.rankedTablePath,
      methodology: stringOrNull(notes.accuracy_assessment_contract),
      targets: {
        target_5: numberOrNull(targets.target_5),
        target_20: numberOrNull(targets.target_20),
        target_60: numberOrNull(targets.target_60),
        target_avg: numberOrNull(targets.target_avg),
        target_coverage: numberOrNull(targets.target_coverage),
        target_fallback_max: numberOrNull(targets.target_fallback_max),
      },
      winner: buildWinner(summary),
      provenance: {
        persistencePath: provenancePersistence ? PROVENANCE_PERSISTENCE_PATH : null,
        parityPath: provenanceParity ? PROVENANCE_PARITY_PATH : null,
        latestRunId:
          stringOrNull((provenancePersistence ?? {}).run_id) ??
          stringOrNull((provenanceParity ?? {}).run_id),
        completenessRate: numberOrNull((provenancePersistence ?? {}).completeness_rate),
        mismatchRate: numberOrNull(decisionParity.mismatch_rate),
        rolloutGatePass: rolloutGate.pass === true ? true : rolloutGate.pass === false ? false : null,
        status: stringOrNull((provenanceParity ?? {}).status),
      },
      typedFallback: buildTypedFallbackPayload(
        typedFallbackSchema,
        typedFallbackRuntime,
        typedFallbackAdmin,
        promotionGatePlanExists,
      ),
    } satisfies RecommendationQualityPayload);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Failed to load recommendation quality.";
    return NextResponse.json({
      exists: false,
      status: null,
      generatedAtUtc: null,
      laneDir: null,
      summaryPath: null,
      rankedTablePath: null,
      methodology: null,
      targets: {
        target_5: null,
        target_20: null,
        target_60: null,
        target_avg: null,
        target_coverage: null,
        target_fallback_max: null,
      },
      winner: null,
      provenance: {
        persistencePath: null,
        parityPath: null,
        latestRunId: null,
        completenessRate: null,
        mismatchRate: null,
        rolloutGatePass: null,
        status: null,
      },
      typedFallback: {
        available: false,
        schemaName: null,
        orthogonalFlags: [],
        preservedLegacyFields: [],
        phase3AAdminInternalReady: null,
        phase3AAdminInternalRecommendation: null,
        runtimeClassificationIntegrity: {
          totalRows: null,
          classifiedRows: null,
          unclassifiedRows: null,
          everyRowMapsToExactlyOneLevel: null,
        },
        runtimeDecisionContext: {
          snapshotPath: null,
          policyArtifactPath: null,
          persistedProvenanceRunId: null,
          decisionProvenanceMinBars: null,
          anomalyFallbackEnabled: null,
          note: null,
        },
        coverageSummary: {
          totalSnapshotRows: null,
          exactStructuralCoverageRate: null,
          exactStructuralCoveragePct: null,
          relaxedStructuralCoverageRate: null,
          relaxedStructuralCoveragePct: null,
          safePolicyFallbackRate: null,
          safePolicyFallbackPct: null,
          degradedUnmappedRate: null,
          degradedUnmappedPct: null,
          unavailableOrBlockedRate: null,
          unavailableOrBlockedPct: null,
          structuralCoverageRate: null,
          structuralCoveragePct: null,
          nonStructuralRate: null,
          nonStructuralPct: null,
          qualityWinnerCoverageRate: null,
          qualityWinnerFallbackRate: null,
        },
        compatibilityChecks: {
          allSnapshotRowsClassifiedExactlyOnce: null,
          structuralCoverageMatchesQualityWinner: null,
          nonStructuralShareMatchesQualityWinner: null,
        },
        levels: [],
        paths: {
          schemaPath: null,
          runtimeSemanticsPath: null,
          adminBreakdownPath: null,
          promotionGatePlanPath: null,
        },
      },
      error: message,
    } satisfies RecommendationQualityPayload);
  }
}
