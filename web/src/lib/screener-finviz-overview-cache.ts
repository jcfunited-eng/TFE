export type ScreenerFinvizOverviewRow = {
  companyName?: string | null;
  sector?: string | null;
  industry?: string | null;
  country?: string | null;
  marketCap?: number | string | null;
  updatedAtUtc?: string | null;
};

type AttemptFailure = {
  path: string;
  reason: string;
};

export type ScreenerFinvizOverviewLoadResult = {
  rows: Record<string, ScreenerFinvizOverviewRow>;
  sourcePath: string | null;
  failures: AttemptFailure[];
};

export function loadScreenerFinvizOverviewCache(): ScreenerFinvizOverviewLoadResult {
  return {
    rows: {},
    sourcePath: null,
    failures: [],
  };
}
