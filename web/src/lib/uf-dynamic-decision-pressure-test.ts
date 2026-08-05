import {
  type DecisionLabel,
  type DynamicDecisionInput,
  type DynamicDecisionProfile,
  type DynamicDecisionResult,
  computePrimitiveDynamicDecision,
} from "@/lib/uf-dynamic-decision";

export type SnapshotLikeRow = {
  ticker?: string;
  bar_count?: number | string;
  S_UF?: number | string;
  R_UF?: number | string;
  D_k?: number | string;
  M_k?: number | string;
  R_rev_k?: number | string;
  U_star_k?: number | string;
  C_k?: number | string;
  P_k?: number | string;
  B_k?: number | string;
  [key: string]: unknown;
};

export type PressureTestCase = {
  id: string;
  symbol: string;
  input: DynamicDecisionInput | null;
  expectedDecision?: DecisionLabel;
  note?: string;
};

export type PressureTestCaseResult = {
  id: string;
  symbol: string;
  expectedDecision: DecisionLabel | null;
  expectedDecisionMatched: boolean | null;
  note: string | null;
  result: DynamicDecisionResult;
};

export type PressureTestSummary = {
  totalCases: number;
  matchedExpectedCount: number;
  mismatchedExpectedCount: number;
  noExpectationCount: number;
  decisionCounts: Record<DecisionLabel, number>;
  blockerCounts: Record<string, number>;
};

export type PressureTestRun = {
  profileId: string;
  results: PressureTestCaseResult[];
  summary: PressureTestSummary;
};

export const PRESSURE_TEST_PROFILE_EXAMPLE_V1: DynamicDecisionProfile = {
  profileId: "pressure_test_profile_example_v1_non_production",
  generatedAtUtc: "2026-03-18T03:20:00Z",
  minBars: 180,
};

function toFiniteOrNull(value: unknown): number | null {
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

function rowNumberField(row: SnapshotLikeRow, key: string): number | null {
  return toFiniteOrNull(row[key]);
}

function findTickerRow(rows: SnapshotLikeRow[], ticker: string): SnapshotLikeRow | null {
  const target = ticker.trim().toUpperCase();
  if (!target) return null;

  for (const row of rows) {
    if (String(row.ticker ?? "").trim().toUpperCase() === target) {
      return row;
    }
  }

  return null;
}

export function dynamicDecisionInputFromRow(
  row: SnapshotLikeRow | null,
  symbol: string,
): DynamicDecisionInput | null {
  if (!row) {
    return null;
  }

  return {
    symbol,
    barCount: toFiniteOrNull(row.bar_count) ?? Number.NaN,
    S_UF: rowNumberField(row, "S_UF"),
    R_UF: rowNumberField(row, "R_UF"),
    D_k: rowNumberField(row, "D_k"),
    M_k: rowNumberField(row, "M_k"),
    R_rev_k: rowNumberField(row, "R_rev_k"),
    U_star_k: rowNumberField(row, "U_star_k"),
    C_k: rowNumberField(row, "C_k"),
    P_k: rowNumberField(row, "P_k"),
    B_k: rowNumberField(row, "B_k"),
  };
}

export function pressureTestCaseFromRows(
  rows: SnapshotLikeRow[],
  symbol: string,
  expectedDecision?: DecisionLabel,
  note?: string,
): PressureTestCase {
  const row = findTickerRow(rows, symbol);
  return {
    id: `symbol:${symbol.trim().toUpperCase()}`,
    symbol: symbol.trim().toUpperCase(),
    input: dynamicDecisionInputFromRow(row, symbol.trim().toUpperCase()),
    expectedDecision,
    note,
  };
}

export function runDynamicDecisionPressureTest(
  cases: PressureTestCase[],
  profile: DynamicDecisionProfile,
): PressureTestRun {
  const results: PressureTestCaseResult[] = [];

  let matchedExpectedCount = 0;
  let mismatchedExpectedCount = 0;
  let noExpectationCount = 0;

  const decisionCounts: Record<DecisionLabel, number> = {
    Accumulate: 0,
    Hold: 0,
    Avoid: 0,
  };

  const blockerCounts: Record<string, number> = {};

  for (const testCase of cases) {
    const result = computePrimitiveDynamicDecision(testCase.input, profile);
    decisionCounts[result.decision] += 1;
    blockerCounts[result.blockerCode] = (blockerCounts[result.blockerCode] ?? 0) + 1;

    let expectedDecisionMatched: boolean | null = null;
    if (testCase.expectedDecision) {
      expectedDecisionMatched = testCase.expectedDecision === result.decision;
      if (expectedDecisionMatched) {
        matchedExpectedCount += 1;
      } else {
        mismatchedExpectedCount += 1;
      }
    } else {
      noExpectationCount += 1;
    }

    results.push({
      id: testCase.id,
      symbol: testCase.symbol,
      expectedDecision: testCase.expectedDecision ?? null,
      expectedDecisionMatched,
      note: testCase.note ?? null,
      result,
    });
  }

  return {
    profileId: profile.profileId,
    results,
    summary: {
      totalCases: cases.length,
      matchedExpectedCount,
      mismatchedExpectedCount,
      noExpectationCount,
      decisionCounts,
      blockerCounts,
    },
  };
}
