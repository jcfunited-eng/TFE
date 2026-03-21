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
    field_trace: number;
    field_determinant: number;
    field_eigenvalues: [number, number, number, number, number];
    field_negative_modes: number;
    field_positive_modes: number;
    field_zero_modes: number;
    field_positive_mass: number;
    field_negative_mass: number;
    field_coherence: number;
    field_diagonal_norm: number;
    field_offdiagonal_norm: number;
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

const EIGEN_EPSILON = 1e-9;

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

function cloneMatrix(matrix: number[][]): number[][] {
  return matrix.map((row) => [...row]);
}

function matrixTrace(matrix: number[][]): number {
  let trace = 0;
  for (let i = 0; i < matrix.length; i += 1) {
    trace += matrix[i][i];
  }
  return trace;
}

function matrixDeterminant(matrix: number[][]): number {
  const size = matrix.length;
  const working = cloneMatrix(matrix);
  let sign = 1;
  let determinant = 1;

  for (let pivotIndex = 0; pivotIndex < size; pivotIndex += 1) {
    let pivotRow = pivotIndex;
    let pivotAbs = Math.abs(working[pivotIndex][pivotIndex]);

    for (let row = pivotIndex + 1; row < size; row += 1) {
      const candidateAbs = Math.abs(working[row][pivotIndex]);
      if (candidateAbs > pivotAbs) {
        pivotAbs = candidateAbs;
        pivotRow = row;
      }
    }

    if (pivotAbs <= EIGEN_EPSILON) {
      return 0;
    }

    if (pivotRow !== pivotIndex) {
      const temp = working[pivotIndex];
      working[pivotIndex] = working[pivotRow];
      working[pivotRow] = temp;
      sign *= -1;
    }

    const pivot = working[pivotIndex][pivotIndex];
    determinant *= pivot;

    for (let row = pivotIndex + 1; row < size; row += 1) {
      const factor = working[row][pivotIndex] / pivot;
      working[row][pivotIndex] = 0;
      for (let col = pivotIndex + 1; col < size; col += 1) {
        working[row][col] -= factor * working[pivotIndex][col];
      }
    }
  }

  return sign * determinant;
}

function symmetricEigenvalues(matrix: number[][]): [number, number, number, number, number] {
  const size = matrix.length;
  const working = cloneMatrix(matrix);
  const maxIterations = size * size * size * size * size;

  for (let iteration = 0; iteration < maxIterations; iteration += 1) {
    let pivotRow = 0;
    let pivotCol = 1;
    let maxOffDiagonal = 0;

    for (let row = 0; row < size; row += 1) {
      for (let col = row + 1; col < size; col += 1) {
        const candidate = Math.abs(working[row][col]);
        if (candidate > maxOffDiagonal) {
          maxOffDiagonal = candidate;
          pivotRow = row;
          pivotCol = col;
        }
      }
    }

    if (maxOffDiagonal <= EIGEN_EPSILON) {
      break;
    }

    const app = working[pivotRow][pivotRow];
    const aqq = working[pivotCol][pivotCol];
    const apq = working[pivotRow][pivotCol];

    if (Math.abs(apq) <= EIGEN_EPSILON) {
      continue;
    }

    const tau = (aqq - app) / (apq + apq);
    const t =
      tau >= 0
        ? 1 / (tau + Math.sqrt(1 + tau * tau))
        : -1 / (-tau + Math.sqrt(1 + tau * tau));
    const c = 1 / Math.sqrt(1 + t * t);
    const s = t * c;

    working[pivotRow][pivotRow] = app - t * apq;
    working[pivotCol][pivotCol] = aqq + t * apq;
    working[pivotRow][pivotCol] = 0;
    working[pivotCol][pivotRow] = 0;

    for (let k = 0; k < size; k += 1) {
      if (k === pivotRow || k === pivotCol) {
        continue;
      }
      const aik = working[pivotRow][k];
      const akq = working[pivotCol][k];
      const rotatedRow = c * aik - s * akq;
      const rotatedCol = s * aik + c * akq;
      working[pivotRow][k] = rotatedRow;
      working[k][pivotRow] = rotatedRow;
      working[pivotCol][k] = rotatedCol;
      working[k][pivotCol] = rotatedCol;
    }
  }

  const eigenvalues = working
    .map((row, index) => row[index])
    .sort((left, right) => right - left);

  return [
    eigenvalues[0],
    eigenvalues[1],
    eigenvalues[2],
    eigenvalues[3],
    eigenvalues[4],
  ];
}

function frobeniusNorm(matrix: number[][]): number {
  let sumSquares = 0;
  for (const row of matrix) {
    for (const value of row) {
      sumSquares += value * value;
    }
  }
  return Math.sqrt(sumSquares);
}

function calculateRelationalFieldState(
  canonicalInput: NonNullable<DynamicDecisionProvenance["canonicalInput"]>,
): DynamicDecisionTermBreakdown["relationalFieldState"] {
  const supportReserve = canonicalInput.S_UF - canonicalInput.U_star_k;
  const resonanceReserve = canonicalInput.R_UF - canonicalInput.U_star_k;
  const supportResonanceGap = canonicalInput.S_UF - canonicalInput.R_UF;

  const weakCoverage = Math.min(supportReserve, resonanceReserve);
  const secondaryCoverage = Math.max(supportReserve, resonanceReserve);
  const coverageSurplus = positivePart(weakCoverage);
  const coverageDeficit = negativePart(weakCoverage);
  const reserveAsymmetry = Math.abs(supportReserve - resonanceReserve);
  const edgeSupport = positivePart(secondaryCoverage) - positivePart(weakCoverage);
  const doubleSidedDeficit = negativePart(secondaryCoverage);
  const edgeWindow = 1 / (1 + positivePart(weakCoverage) + edgeSupport);

  const reversalCalm = 1 - canonicalInput.R_rev_k;
  const conflictCalm = 1 / (1 + canonicalInput.C_k);
  const persistenceCalm = 1 / (1 + canonicalInput.P_k);
  const conflictDrag = 1 - conflictCalm;
  const persistenceDrag = 1 - persistenceCalm;
  const load = 1 - conflictCalm * persistenceCalm;

  const directionalPositive = positivePart(canonicalInput.D_k);
  const directionalNegative = negativePart(canonicalInput.D_k);
  const directionalStillness = 1 - Math.abs(canonicalInput.D_k);
  const momentumPositive = positivePart(canonicalInput.M_k);
  const momentumNegative = negativePart(canonicalInput.M_k);
  const momentumStillness = 1 - Math.abs(canonicalInput.M_k);
  const carryPositive = positivePart(canonicalInput.B_k);
  const carryNegative = negativePart(canonicalInput.B_k);

  const trajectoryRupture = Math.max(
    directionalNegative,
    momentumNegative,
    carryNegative,
    1 - reversalCalm,
  );
  const trajectoryForward =
    directionalPositive * momentumPositive * carryPositive * reversalCalm;
  const trajectoryContest =
    directionalPositive * reversalCalm * positivePart(1 - trajectoryRupture);

  const tensor = [
    [supportReserve, 0, canonicalInput.D_k, canonicalInput.M_k, canonicalInput.B_k],
    [0, resonanceReserve, canonicalInput.D_k, canonicalInput.M_k, canonicalInput.B_k],
    [canonicalInput.D_k, canonicalInput.D_k, reversalCalm, 0, 0],
    [canonicalInput.M_k, canonicalInput.M_k, 0, conflictCalm, 0],
    [canonicalInput.B_k, canonicalInput.B_k, 0, 0, persistenceCalm],
  ];

  const diagonal = [
    [supportReserve, 0, 0, 0, 0],
    [0, resonanceReserve, 0, 0, 0],
    [0, 0, reversalCalm, 0, 0],
    [0, 0, 0, conflictCalm, 0],
    [0, 0, 0, 0, persistenceCalm],
  ];

  const offDiagonal = [
    [0, 0, canonicalInput.D_k, canonicalInput.M_k, canonicalInput.B_k],
    [0, 0, canonicalInput.D_k, canonicalInput.M_k, canonicalInput.B_k],
    [canonicalInput.D_k, canonicalInput.D_k, 0, 0, 0],
    [canonicalInput.M_k, canonicalInput.M_k, 0, 0, 0],
    [canonicalInput.B_k, canonicalInput.B_k, 0, 0, 0],
  ];

  const fieldTrace = matrixTrace(tensor);
  const fieldDeterminant = matrixDeterminant(tensor);
  const fieldEigenvalues = symmetricEigenvalues(tensor);
  const fieldDiagonalNorm = frobeniusNorm(diagonal);
  const fieldOffdiagonalNorm = frobeniusNorm(offDiagonal);
  const coherenceDenominator = fieldDiagonalNorm + fieldOffdiagonalNorm;
  const fieldCoherence =
    coherenceDenominator === 0 ? 0 : fieldOffdiagonalNorm / coherenceDenominator;

  let fieldPositiveModes = 0;
  let fieldNegativeModes = 0;
  let fieldZeroModes = 0;
  let fieldPositiveMass = 0;
  let fieldNegativeMass = 0;

  for (const eigenvalue of fieldEigenvalues) {
    if (eigenvalue > EIGEN_EPSILON) {
      fieldPositiveModes += 1;
    } else if (eigenvalue < -EIGEN_EPSILON) {
      fieldNegativeModes += 1;
    } else {
      fieldZeroModes += 1;
    }

    fieldPositiveMass += positivePart(eigenvalue);
    fieldNegativeMass += positivePart(-eigenvalue);
  }

  const positiveExcess = positivePart(fieldPositiveMass - fieldNegativeMass);
  const accumulateClaim = positiveExcess * fieldCoherence;
  const holdClaim = positiveExcess * (1 - fieldCoherence);
  const avoidClaim = fieldNegativeMass;

  let dominantRelation: DecisionLabel = "Hold";
  if (
    accumulateClaim > holdClaim &&
    accumulateClaim > avoidClaim
  ) {
    dominantRelation = "Accumulate";
  } else if (
    avoidClaim > accumulateClaim &&
    avoidClaim > holdClaim
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
    accumulate_tendency: accumulateClaim,
    hold_tendency: holdClaim,
    avoid_tendency: avoidClaim,
    continuation_relation: accumulateClaim,
    stillness_relation: holdClaim,
    collapse_relation: avoidClaim,
    field_trace: fieldTrace,
    field_determinant: fieldDeterminant,
    field_eigenvalues: fieldEigenvalues,
    field_negative_modes: fieldNegativeModes,
    field_positive_modes: fieldPositiveModes,
    field_zero_modes: fieldZeroModes,
    field_positive_mass: fieldPositiveMass,
    field_negative_mass: fieldNegativeMass,
    field_coherence: fieldCoherence,
    field_diagonal_norm: fieldDiagonalNorm,
    field_offdiagonal_norm: fieldOffdiagonalNorm,
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
