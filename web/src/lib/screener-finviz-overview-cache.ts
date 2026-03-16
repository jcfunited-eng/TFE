import { existsSync, readFileSync, statSync } from "node:fs";
import path from "node:path";

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

type FinvizOverviewLoadResult = {
  rows: Record<string, ScreenerFinvizOverviewRow>;
  sourcePath: string | null;
  failures: AttemptFailure[];
};

type FinvizOverviewRuntime = {
  cacheKey: string;
  sourcePath: string;
  rows: Record<string, ScreenerFinvizOverviewRow>;
};

const CACHE_FILENAME = "screener-finviz-overview-cache.json";

let FINVIZ_OVERVIEW_CACHE: FinvizOverviewRuntime | null = null;

function uniquePaths(values: string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];

  for (const value of values) {
    const normalized = path.normalize(value);
    if (seen.has(normalized)) continue;
    seen.add(normalized);
    out.push(normalized);
  }

  return out;
}

function finvizOverviewCandidates(): string[] {
  const cwd = process.cwd();
  return uniquePaths([
    path.resolve(cwd, "data", CACHE_FILENAME),
    path.resolve(cwd, "web", "data", CACHE_FILENAME),
    path.resolve(cwd, "..", "web", "data", CACHE_FILENAME),
    path.resolve(cwd, "..", "..", "web", "data", CACHE_FILENAME),
    path.resolve("/workspaces/Tao_Financial_Engine/web/data", CACHE_FILENAME),
  ]);
}

function cacheKeyFor(filePath: string): string {
  const stats = statSync(filePath);
  return `${path.normalize(filePath)}|${Math.floor(stats.mtimeMs)}|${stats.size}`;
}

function normalizeRows(raw: unknown): Record<string, ScreenerFinvizOverviewRow> {
  const out: Record<string, ScreenerFinvizOverviewRow> = {};

  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    return out;
  }

  const bag = raw as Record<string, unknown>;
  const candidateRows = bag.rows && typeof bag.rows === "object" && !Array.isArray(bag.rows)
    ? (bag.rows as Record<string, unknown>)
    : bag;

  for (const [key, value] of Object.entries(candidateRows)) {
    const ticker = String(key ?? "").trim().toUpperCase();
    if (!ticker) continue;
    if (!value || typeof value !== "object" || Array.isArray(value)) continue;
    out[ticker] = value as ScreenerFinvizOverviewRow;
  }

  return out;
}

export function loadScreenerFinvizOverviewCache(): FinvizOverviewLoadResult {
  const candidates = finvizOverviewCandidates();
  const failures: AttemptFailure[] = [];

  for (const candidate of candidates) {
    if (!existsSync(candidate)) {
      failures.push({ path: candidate, reason: "Cache file not found." });
      continue;
    }

    try {
      const key = cacheKeyFor(candidate);
      if (FINVIZ_OVERVIEW_CACHE && FINVIZ_OVERVIEW_CACHE.cacheKey === key) {
        return {
          rows: FINVIZ_OVERVIEW_CACHE.rows,
          sourcePath: FINVIZ_OVERVIEW_CACHE.sourcePath,
          failures,
        };
      }

      const text = readFileSync(candidate, "utf-8");
      const parsed = JSON.parse(text) as unknown;
      const rows = normalizeRows(parsed);
      if (Object.keys(rows).length === 0) {
        failures.push({ path: candidate, reason: "Parsed cache file but no overview rows were found." });
        continue;
      }

      FINVIZ_OVERVIEW_CACHE = {
        cacheKey: key,
        sourcePath: candidate,
        rows,
      };

      return {
        rows,
        sourcePath: candidate,
        failures,
      };
    } catch (error) {
      const reason = error instanceof Error ? error.message : "Unknown read/parse failure.";
      failures.push({ path: candidate, reason });
    }
  }

  return {
    rows: {},
    sourcePath: null,
    failures,
  };
}
