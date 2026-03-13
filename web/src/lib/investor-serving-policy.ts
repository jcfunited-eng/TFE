import type {
  RuntimePublicationBundleMeta,
  RuntimeServingPublicationBundleMeta,
} from "@/lib/runtime-publication-bundle";

export type InvestorServingPolicyBlockedReason =
  | "stale"
  | "validation_failed"
  | "missing_publication_ids"
  | "quote_binding_not_aligned"
  | "run_mismatch";

export type InvestorServingPolicyEvaluation = {
  allowed: boolean;
  blocked: boolean;
  reasons: InvestorServingPolicyBlockedReason[];
  reasonMessages: string[];
  freshness: {
    basis: "publication_bundle" | "runtime_snapshot";
    generated_at_utc: string | null;
    generated_at_valid: boolean;
    snapshot_age_minutes: number | null;
    snapshot_max_age_minutes: number;
    stale: boolean;
  };
  policy: {
    freshness_required: true;
    validation_status_required: "pass";
    publication_ids_required: true;
    quote_binding_status_required: "aligned";
    run_mismatch_blocking: true;
  };
  validation_status: string | null;
  snapshot_publication_id: string | null;
  quote_publication_id: string | null;
  quote_binding_status: string | null;
  runIds: {
    snapshot_run_id: string | null;
    quote_run_id: string | null;
    serving_bundle_run_id: string | null;
    active_runtime_run_id: string | null;
  };
  runMismatch: {
    snapshot_vs_quote: boolean;
    snapshot_vs_serving_bundle: boolean;
    quote_vs_serving_bundle: boolean;
    any: boolean;
  };
};

type EvaluateInvestorServingPolicyInput = {
  bundleMeta: RuntimePublicationBundleMeta;
  servingBundleMeta: RuntimeServingPublicationBundleMeta;
  snapshotRunId: string | null;
  snapshotGeneratedAtUtc: string | null;
  quoteRunId: string | null;
  maxAgeMinutes?: number;
  nowMs?: number;
};

function toTextOrNull(value: unknown): string | null {
  const text = String(value ?? "").trim();
  return text ? text : null;
}

function parseIsoUtc(value: string | null | undefined): { iso: string | null; ms: number | null } {
  const text = toTextOrNull(value);
  if (!text) return { iso: null, ms: null };
  const parsed = Date.parse(text);
  if (!Number.isFinite(parsed)) return { iso: text, ms: null };
  return { iso: new Date(parsed).toISOString(), ms: parsed };
}

function normalizePositiveInt(value: unknown, fallback: number, minimum: number, maximum: number): number {
  const n = Number(value);
  if (!Number.isFinite(n)) return fallback;
  const whole = Math.floor(n);
  if (whole < minimum) return minimum;
  if (whole > maximum) return maximum;
  return whole;
}

export function investorServingMaxAgeMinutes(): number {
  const explicit = String(process.env.TFE_INVESTOR_SERVING_MAX_AGE_MINUTES ?? "").trim();
  if (explicit) {
    return normalizePositiveInt(explicit, 1800, 5, 20160);
  }
  return normalizePositiveInt(process.env.TFE_RECOMMENDATIONS_MAX_AGE_MINUTES, 1800, 5, 20160);
}

function reasonMessage(reason: InvestorServingPolicyBlockedReason): string {
  if (reason === "stale") return "Serving snapshot freshness is stale or timestamp is invalid.";
  if (reason === "validation_failed") return "Publication bundle validation_status is not pass.";
  if (reason === "missing_publication_ids") return "Required publication IDs are missing.";
  if (reason === "quote_binding_not_aligned") return "quote_binding_status is not aligned.";
  return "Runtime serving run IDs are mismatched.";
}

export function evaluateInvestorServingPolicy(input: EvaluateInvestorServingPolicyInput): InvestorServingPolicyEvaluation {
  const maxAgeMinutes = normalizePositiveInt(input.maxAgeMinutes, investorServingMaxAgeMinutes(), 5, 20160);
  const nowMs = Number.isFinite(Number(input.nowMs)) ? Number(input.nowMs) : Date.now();

  const generatedAtFromBundle = toTextOrNull(input.bundleMeta.generatedAtUtc);
  const generatedAtFromSnapshot = toTextOrNull(input.snapshotGeneratedAtUtc);
  const freshnessBasis: "publication_bundle" | "runtime_snapshot" = generatedAtFromBundle
    ? "publication_bundle"
    : "runtime_snapshot";
  const generatedAt = generatedAtFromBundle ?? generatedAtFromSnapshot;
  const generatedAtParsed = parseIsoUtc(generatedAt);

  let snapshotAgeMinutes: number | null = null;
  let stale = false;
  if (generatedAtParsed.ms === null) {
    stale = true;
  } else {
    const rawAge = (nowMs - generatedAtParsed.ms) / 60000;
    snapshotAgeMinutes = rawAge > 0 ? Number(rawAge.toFixed(3)) : 0;
    stale = rawAge > maxAgeMinutes;
  }

  const validationStatus = toTextOrNull(input.bundleMeta.validationStatus)?.toLowerCase() ?? null;
  const snapshotPublicationId = toTextOrNull(input.bundleMeta.snapshotPublicationId);
  const quotePublicationId = toTextOrNull(input.bundleMeta.quotePublicationId);
  const quoteBindingStatus = toTextOrNull(input.bundleMeta.quoteBindingStatus)?.toLowerCase() ?? null;

  const snapshotRunId = toTextOrNull(input.snapshotRunId);
  const quoteRunId = toTextOrNull(input.quoteRunId);
  const servingBundleRunId = toTextOrNull(input.servingBundleMeta.runId);
  const activeRuntimeRunId = toTextOrNull(input.servingBundleMeta.activeRuntimeRunId);

  const runMismatch = {
    snapshot_vs_quote: Boolean(snapshotRunId && quoteRunId && snapshotRunId !== quoteRunId),
    snapshot_vs_serving_bundle: Boolean(snapshotRunId && servingBundleRunId && snapshotRunId !== servingBundleRunId),
    quote_vs_serving_bundle: Boolean(quoteRunId && servingBundleRunId && quoteRunId !== servingBundleRunId),
    any: false,
  };
  runMismatch.any = runMismatch.snapshot_vs_quote || runMismatch.snapshot_vs_serving_bundle || runMismatch.quote_vs_serving_bundle;

  const reasons: InvestorServingPolicyBlockedReason[] = [];
  if (stale) reasons.push("stale");
  if (validationStatus !== "pass") reasons.push("validation_failed");
  if (!snapshotPublicationId || !quotePublicationId) reasons.push("missing_publication_ids");
  if (quoteBindingStatus !== "aligned") reasons.push("quote_binding_not_aligned");
  if (runMismatch.any) reasons.push("run_mismatch");

  return {
    allowed: reasons.length === 0,
    blocked: reasons.length > 0,
    reasons,
    reasonMessages: reasons.map(reasonMessage),
    freshness: {
      basis: freshnessBasis,
      generated_at_utc: generatedAtParsed.iso,
      generated_at_valid: generatedAtParsed.ms !== null,
      snapshot_age_minutes: snapshotAgeMinutes,
      snapshot_max_age_minutes: maxAgeMinutes,
      stale,
    },
    policy: {
      freshness_required: true,
      validation_status_required: "pass",
      publication_ids_required: true,
      quote_binding_status_required: "aligned",
      run_mismatch_blocking: true,
    },
    validation_status: validationStatus,
    snapshot_publication_id: snapshotPublicationId,
    quote_publication_id: quotePublicationId,
    quote_binding_status: quoteBindingStatus,
    runIds: {
      snapshot_run_id: snapshotRunId,
      quote_run_id: quoteRunId,
      serving_bundle_run_id: servingBundleRunId,
      active_runtime_run_id: activeRuntimeRunId,
    },
    runMismatch,
  };
}
