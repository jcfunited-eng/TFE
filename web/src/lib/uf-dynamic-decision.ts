export type DecisionLabel = "Accumulate" | "Hold" | "Avoid";

export type DynamicDecisionInput = {
  symbol?: string;
  barCount: number;
  S_UF: number | null;
  R_UF: number | null;
  D_k: number | null;
  M_k: number | null;
  R_rev_k: number | null;
  U_star_k: number | null;
  C_k: number | null;
  P_k: number | null;
  B_k: number | null;
};

export type DynamicDecisionProfile = {
  profileId: string;
  generatedAtUtc: string;
  minBars: number;
};

export type DynamicDecisionBlockerCode =
  | "NONE"
  | "ROW_NOT_FOUND"
  | "INSUFFICIENT_BARS"
  | "STRUCTURAL_INCOMPLETE";

export type DynamicDecisionTermBreakdown = {
  canonicalField: {
    S_UF: number;
    R_UF: number;
    D_k: number;
    M_k: number;
    R_rev_k: number;
    U_star_k: number;
    C_k: number;
    P_k: number;
    B_k: number;
  };
  relationalFieldState: {
    support_reserve: number;
    resonance_reserve: number;
    support_resonance_gap: number;
    weak_coverage: number;
    secondary_coverage: number;
    coverage_surplus: number;
    coverage_deficit: number;
    reserve_asymmetry: number;
    edge_support: number;
    double_sided_deficit: number;
    edge_window: number;
    reversal_calm: number;
    conflict_calm: number;
    persistence_calm: number;
    conflict_drag: number;
    persistence_drag: number;
    load: number;
    directional_positive: number;
    directional_negative: number;
    directional_stillness: number;
    momentum_positive: number;
    momentum_negative: number;
    momentum_stillness: number;
    carry_positive: number;
    carry_negative: number;
    trajectory_forward: number;
    trajectory_contest: number;
    trajectory_rupture: number;
    accumulate_tendency: number;
    hold_tendency: number;
    avoid_tendency: number;
    continuation_relation: number;
    stillness_relation: number;
    collapse_relation: number;
    dominant_relation: DecisionLabel;
  };
};

export type DynamicDecisionProvenance = {
  decisionSource: "primitive_dynamic_runtime_direct_field_relation";
  profileId: string;
  generatedAtUtc: string;
  blockerCode: DynamicDecisionBlockerCode;
  blockerActive: boolean;
  structuralComplete: boolean;
  structuralMissingFields: string[];
  rawInput: DynamicDecisionInput | null;
  canonicalInput: DynamicDecisionTermBreakdown["canonicalField"] | null;
};

export type DynamicDecisionResult = {
  decision: DecisionLabel;
  blockerCode: DynamicDecisionBlockerCode;
  blockerActive: boolean;
  termBreakdown: DynamicDecisionTermBreakdown | null;
  provenance: DynamicDecisionProvenance;
};

const REQUIRED_FIELDS: Array<keyof DynamicDecisionInput> = [
  "S_UF",
  "R_UF",
  "D_k",
  "M_k",
  "R_rev_k",
  "U_star_k",
  "C_k",
  "P_k",
  "B_k",
];

const LOCAL_SEAM_RELEASE_W = 0.02;
const LOCAL_SEAM_ZERO_WEIGHT = 0.75;
const LOCAL_SEAM_COVERED_WEIGHT = 0.4533;
const COVERED_RUPTURE_HOLD_LOAD_FLOOR = 0.5;

function clip(value: number, min: number, max: number): number {
  if (value < min) return min;
  if (value > max) return max;
  return value;
}

function finiteOrNull(value: unknown): number | null {
  if (value === null || value === undefined) {
    return null;
  }

  if (typeof value === "number") {
    return Number.isFinite(value) ? value : null;
  }

  if (typeof value === "string" && value.trim() !== "") {
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
  }

  return null;
}

function finiteIntegerOrNull(value: unknown): number | null {
  const n = finiteOrNull(value);
  if (n === null) return null;
  return Math.floor(n);
}

function positivePart(value: number): number {
  return Math.max(value, 0);
}

function negativePart(value: number): number {
  return Math.max(-value, 0);
}

function smoothStep01(value: number): number {
  const t = clip(value, 0, 1);
  return t * t * (3 - 2 * t);
}

function coveredSideSeamWeight(coverageSurplus: number): number {
  const seamProgress = smoothStep01(coverageSurplus / LOCAL_SEAM_RELEASE_W);
  return (
    LOCAL_SEAM_ZERO_WEIGHT -
    (LOCAL_SEAM_ZERO_WEIGHT - LOCAL_SEAM_COVERED_WEIGHT) * seamProgress
  );
}

function missingStructuralFields(input: DynamicDecisionInput): string[] {
  const out: string[] = [];
  for (const key of REQUIRED_FIELDS) {
    if (finiteOrNull(input[key]) === null) {
      out.push(key);
    }
  }
  return out;
}

function blockerCodeForInput(
  input: DynamicDecisionInput | null,
  profile: DynamicDecisionProfile,
): { blockerCode: DynamicDecisionBlockerCode; structuralMissingFields: string[] } {
  if (input === null) {
    return { blockerCode: "ROW_NOT_FOUND", structuralMissingFields: ["row"] };
  }

  const profileMinBars = finiteIntegerOrNull(profile.minBars);
  const barCount = finiteIntegerOrNull(input.barCount);
  const missingFields = missingStructuralFields(input);

  if (barCount === null || profileMinBars === null) {
    return {
      blockerCode: "STRUCTURAL_INCOMPLETE",
      structuralMissingFields: [...missingFields, "barCount"],
    };
  }

  if (barCount < profileMinBars) {
    return { blockerCode: "INSUFFICIENT_BARS", structuralMissingFields: missingFields };
  }

  if (missingFields.length > 0) {
    return { blockerCode: "STRUCTURAL_INCOMPLETE", structuralMissingFields: missingFields };
  }

  return { blockerCode: "NONE", structuralMissingFields: [] };
}

function canonicalizeInput(
  input: DynamicDecisionInput,
): NonNullable<DynamicDecisionProvenance["canonicalInput"]> {
  return {
    S_UF: clip(finiteOrNull(input.S_UF) ?? 0, 0, 1),
    R_UF: clip(finiteOrNull(input.R_UF) ?? 0, 0, 1),
    D_k: clip(finiteOrNull(input.D_k) ?? 0, -1, 1),
    M_k: clip(finiteOrNull(input.M_k) ?? 0, -1, 1),
    R_rev_k: clip(finiteOrNull(input.R_rev_k) ?? 0, 0, 1),
    U_star_k: clip(finiteOrNull(input.U_star_k) ?? 0, 0, 1),
    C_k: Math.max(0, finiteOrNull(input.C_k) ?? 0),
    P_k: Math.max(0, finiteOrNull(input.P_k) ?? 0),
    B_k: clip(finiteOrNull(input.B_k) ?? 0, -1, 1),
  };
}

function calculateRelationalFieldState(
  canonicalInput: NonNullable<DynamicDecisionProvenance["canonicalInput"]>,
): DynamicDecisionTermBreakdown["relationalFieldState"] {
  const supportReserve = canonicalInput.S_UF - canonicalInput.U_star_k;
  const resonanceReserve = canonicalInput.R_UF - canonicalInput.U_star_k;
  const supportResonanceGap = canonicalInput.S_UF - canonicalInput.R_UF;

  const weakCoverage = Math.min(supportReserve, resonanceReserve);
  const secondaryCoverage = weakCoverage + Math.abs(supportResonanceGap);
  const coverageSurplus = positivePart(weakCoverage);
  const coverageDeficit = negativePart(weakCoverage);
  const reserveAsymmetry = Math.abs(supportResonanceGap);
  const edgeSupport = positivePart(secondaryCoverage) - positivePart(weakCoverage);
  const doubleSidedDeficit = negativePart(secondaryCoverage);
  const edgeWindow = 1 / (1 + positivePart(weakCoverage) + edgeSupport);
  const edgeHoldWeight = coveredSideSeamWeight(coverageSurplus);

  const reversalCalm = 1 - canonicalInput.R_rev_k;
  const reversalStress = 1 - reversalCalm;
  const conflictDrag = canonicalInput.C_k / (1 + canonicalInput.C_k);
  const persistenceDrag = canonicalInput.P_k / (1 + canonicalInput.P_k);
  const conflictCalm = 1 - conflictDrag;
  const persistenceCalm = 1 - persistenceDrag;
  const load = 0.5 * conflictDrag + 0.5 * persistenceDrag;

  const directionalPositive = positivePart(canonicalInput.D_k);
  const directionalNegative = positivePart(-canonicalInput.D_k);
  const directionalStillness = 1 - Math.abs(canonicalInput.D_k);

  const momentumPositive = positivePart(canonicalInput.M_k);
  const momentumNegative = positivePart(-canonicalInput.M_k);
  const momentumStillness = 1 - Math.abs(canonicalInput.M_k);

  const carryPositive = positivePart(canonicalInput.B_k);
  const carryNegative = positivePart(-canonicalInput.B_k);

  const trajectoryForward =
    (directionalPositive + 0.5 * momentumPositive + 0.5 * carryPositive) / 2;
  const trajectoryContest =
    0.75 *
    (directionalPositive + 0.5 * (1 - momentumNegative) + 0.5 * (1 - carryNegative)) /
    2 *
    (1 - 0.5 * canonicalInput.R_rev_k);
  const trajectoryRupture =
    directionalNegative +
    0.5 * momentumNegative +
    0.5 * carryNegative +
    canonicalInput.R_rev_k;

  const accumulateTendency =
    (coverageSurplus + 0.5 * edgeSupport) *
    trajectoryForward *
    reversalCalm *
    (1 - 0.5 * load);

  const holdCoverage =
    (0.5 * coverageSurplus + edgeHoldWeight * edgeSupport) * edgeWindow;
  const stillHoldTendency =
    holdCoverage *
    Math.max(trajectoryContest - 0.5 * trajectoryRupture, 0) *
    (0.5 + 0.5 * persistenceCalm);

  const coveredRuptureBase =
    coverageSurplus *
    (1 + edgeSupport) *
    positivePart(trajectoryRupture - trajectoryContest) *
    positivePart(load - COVERED_RUPTURE_HOLD_LOAD_FLOOR);
  const coveredRuptureCalmHoldTendency =
    coveredRuptureBase *
    (1 - trajectoryForward) *
    reversalCalm *
    (0.5 + 0.5 * persistenceCalm);
  const coveredRuptureReversalHoldTendency =
    coveredRuptureBase *
    (0.5 + 0.5 * trajectoryForward) *
    reversalStress *
    (0.5 + 0.5 * persistenceCalm);

  const holdTendency = Math.max(
    stillHoldTendency,
    coveredRuptureCalmHoldTendency,
    coveredRuptureReversalHoldTendency,
  );

  const avoidTendency =
    coverageDeficit *
    (1 + doubleSidedDeficit) *
    (1 + trajectoryRupture) *
    (1 + 0.5 * load);

  let dominantRelation: DecisionLabel = "Hold";
  if (
    accumulateTendency > holdTendency &&
    accumulateTendency > avoidTendency
  ) {
    dominantRelation = "Accumulate";
  } else if (
    avoidTendency > accumulateTendency &&
    avoidTendency > holdTendency
  ) {
    dominantRelation = "Avoid";
  }

  return {
    support_reserve: supportReserve,
    resonance_reserve: resonanceReserve,
    support_resonance_gap: supportResonanceGap,
    weak_coverage: weakCoverage,
    secondary_coverage: secondaryCoverage,
    coverage_surplus: coverageSurplus,
    coverage_deficit: coverageDeficit,
    reserve_asymmetry: reserveAsymmetry,
    edge_support: edgeSupport,
    double_sided_deficit: doubleSidedDeficit,
    edge_window: edgeWindow,
    reversal_calm: reversalCalm,
    conflict_calm: conflictCalm,
    persistence_calm: persistenceCalm,
    conflict_drag: conflictDrag,
    persistence_drag: persistenceDrag,
    load,
    directional_positive: directionalPositive,
    directional_negative: directionalNegative,
    directional_stillness: directionalStillness,
    momentum_positive: momentumPositive,
    momentum_negative: momentumNegative,
    momentum_stillness: momentumStillness,
    carry_positive: carryPositive,
    carry_negative: carryNegative,
    trajectory_forward: trajectoryForward,
    trajectory_contest: trajectoryContest,
    trajectory_rupture: trajectoryRupture,
    accumulate_tendency: accumulateTendency,
    hold_tendency: holdTendency,
    avoid_tendency: avoidTendency,
    continuation_relation: accumulateTendency,
    stillness_relation: holdTendency,
    collapse_relation: avoidTendency,
    dominant_relation: dominantRelation,
  };
}

function buildTermBreakdown(
  canonicalInput: NonNullable<DynamicDecisionProvenance["canonicalInput"]>,
): DynamicDecisionTermBreakdown {
  return {
    canonicalField: canonicalInput,
    relationalFieldState: calculateRelationalFieldState(canonicalInput),
  };
}

export function computePrimitiveDynamicDecision(
  input: DynamicDecisionInput | null,
  profile: DynamicDecisionProfile,
): DynamicDecisionResult {
  const blocker = blockerCodeForInput(input, profile);
  const blockerActive = blocker.blockerCode !== "NONE";

  if (input === null) {
    return {
      decision: "Hold",
      blockerCode: blocker.blockerCode,
      blockerActive,
      termBreakdown: null,
      provenance: {
        decisionSource: "primitive_dynamic_runtime_direct_field_relation",
        profileId: profile.profileId,
        generatedAtUtc: profile.generatedAtUtc,
        blockerCode: blocker.blockerCode,
        blockerActive,
        structuralComplete: false,
        structuralMissingFields: blocker.structuralMissingFields,
        rawInput: null,
        canonicalInput: null,
      },
    };
  }

  if (blockerActive) {
    return {
      decision: "Hold",
      blockerCode: blocker.blockerCode,
      blockerActive,
      termBreakdown: null,
      provenance: {
        decisionSource: "primitive_dynamic_runtime_direct_field_relation",
        profileId: profile.profileId,
        generatedAtUtc: profile.generatedAtUtc,
        blockerCode: blocker.blockerCode,
        blockerActive,
        structuralComplete: blocker.structuralMissingFields.length === 0,
        structuralMissingFields: blocker.structuralMissingFields,
        rawInput: input,
        canonicalInput: null,
      },
    };
  }

  const canonicalInput = canonicalizeInput(input);
  const termBreakdown = buildTermBreakdown(canonicalInput);
  const decision = termBreakdown.relationalFieldState.dominant_relation;

  return {
    decision,
    blockerCode: "NONE",
    blockerActive: false,
    termBreakdown,
    provenance: {
      decisionSource: "primitive_dynamic_runtime_direct_field_relation",
      profileId: profile.profileId,
      generatedAtUtc: profile.generatedAtUtc,
      blockerCode: "NONE",
      blockerActive: false,
      structuralComplete: true,
      structuralMissingFields: [],
      rawInput: input,
      canonicalInput,
    },
  };
}
