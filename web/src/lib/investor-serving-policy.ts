import type {
  RuntimePublicationBundleMeta,
  RuntimeServingPublicationBundleMeta,
} from "@/lib/runtime-publication-bundle";

export type InvestorServingPolicyBlockedReason = "run_mismatch";

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
    freshness_required: boolean;
    validation_status_required: string;
    publication_ids_required: boolean;
    quote_binding_status_required: string;
    run_mismatch_blocking: boolean;
    mode: "bypass_active";
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

export function evaluateInvestorServingPolicy(input: EvaluateInvestorServingPolicyInput): InvestorServingPolicyEvaluation {
  const maxAgeMinutes = normalizePositiveInt(input.maxAgeMinutes, investorServingMaxAgeMinutes(), 5, 20160);
  const nowMs = Number.isFinite(Number(input.nowMs)) ? Number(input.nowMs) : Date.now();
  const generatedAtParsed = parseIsoUtc(
    toTextOrNull(input.bundleMeta.generatedAtUtc) ?? toTextOrNull(input.snapshotGeneratedAtUtc),
  );
  const snapshotAgeMinutes = generatedAtParsed.ms === null
    ? null
    : Math.max(0, Number((((nowMs - generatedAtParsed.ms) / 60000)).toFixed(3)));

  return {
    allowed: true,
    blocked: false,
    reasons: [],
    reasonMessages: [],
    freshness: {
      basis: "runtime_snapshot",
      generated_at_utc: generatedAtParsed.iso,
      generated_at_valid: generatedAtParsed.ms !== null,
      snapshot_age_minutes: snapshotAgeMinutes,
      snapshot_max_age_minutes: maxAgeMinutes,
      stale: false,
    },
    policy: {
      freshness_required: false,
      validation_status_required: "bypass_active",
      publication_ids_required: false,
      quote_binding_status_required: "bypass_active",
      run_mismatch_blocking: false,
      mode: "bypass_active",
    },
    validation_status: "pass",
    snapshot_publication_id: "BYPASS_ACTIVE",
    quote_publication_id: "BYPASS_ACTIVE",
    quote_binding_status: "bypass_active",
    runIds: {
      snapshot_run_id: toTextOrNull(input.snapshotRunId) ?? input.bundleMeta.runId,
      quote_run_id: toTextOrNull(input.quoteRunId) ?? input.bundleMeta.runId,
      serving_bundle_run_id: input.servingBundleMeta.runId,
      active_runtime_run_id: input.servingBundleMeta.activeRuntimeRunId,
    },
    runMismatch: {
      snapshot_vs_quote: false,
      snapshot_vs_serving_bundle: false,
      quote_vs_serving_bundle: false,
      any: false,
    },
  };
}
