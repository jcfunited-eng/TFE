import { existsSync, readFileSync, statSync } from "node:fs";
import path from "node:path";

export type ScreenerProfileOverrideRow = {
  companyName?: string | null;
  sector?: string | null;
  industry?: string | null;
  country?: string | null;
  exchange?: string | null;
  quoteType?: string | null;
  assetType?: string | null;
  updatedAtUtc?: string | null;
};

type AttemptFailure = {
  path: string;
  reason: string;
};

type ProfileOverrideLoadResult = {
  rows: Record<string, ScreenerProfileOverrideRow>;
  sourcePath: string | null;
  failures: AttemptFailure[];
};

type ProfileOverrideRuntime = {
  cacheKey: string;
  sourcePath: string;
  rows: Record<string, ScreenerProfileOverrideRow>;
};

const OVERRIDE_FILENAME = "screener-profile-overrides.json";

let PROFILE_OVERRIDE_CACHE: ProfileOverrideRuntime | null = null;

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

function profileOverrideCandidates(): string[] {
  const cwd = process.cwd();
  return uniquePaths([
    path.resolve(cwd, "data", OVERRIDE_FILENAME),
    path.resolve(cwd, "web", "data", OVERRIDE_FILENAME),
    path.resolve(cwd, "..", "web", "data", OVERRIDE_FILENAME),
    path.resolve(cwd, "..", "..", "web", "data", OVERRIDE_FILENAME),
    path.resolve("/workspaces/Tao_Financial_Engine/web/data", OVERRIDE_FILENAME),
  ]);
}

function cacheKeyFor(filePath: string): string {
  const stats = statSync(filePath);
  return `${path.normalize(filePath)}|${Math.floor(stats.mtimeMs)}|${stats.size}`;
}

function normalizeOverrideRows(raw: unknown): Record<string, ScreenerProfileOverrideRow> {
  const out: Record<string, ScreenerProfileOverrideRow> = {};

  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    return out;
  }

  const bag = raw as Record<string, unknown>;
  const rows = bag.rows && typeof bag.rows === "object" && !Array.isArray(bag.rows) ? (bag.rows as Record<string, unknown>) : bag;

  for (const [key, value] of Object.entries(rows)) {
    const ticker = String(key ?? "").trim().toUpperCase();
    if (!ticker) continue;
    if (!value || typeof value !== "object" || Array.isArray(value)) continue;
    out[ticker] = value as ScreenerProfileOverrideRow;
  }

  return out;
}

export function loadScreenerProfileOverrides(): ProfileOverrideLoadResult {
  const candidates = profileOverrideCandidates();
  const failures: AttemptFailure[] = [];

  for (const candidate of candidates) {
    if (!existsSync(candidate)) {
      failures.push({ path: candidate, reason: "Override file not found." });
      continue;
    }

    try {
      const cacheKey = cacheKeyFor(candidate);
      if (PROFILE_OVERRIDE_CACHE && PROFILE_OVERRIDE_CACHE.cacheKey === cacheKey) {
        return {
          rows: PROFILE_OVERRIDE_CACHE.rows,
          sourcePath: PROFILE_OVERRIDE_CACHE.sourcePath,
          failures,
        };
      }

      const text = readFileSync(candidate, "utf-8");
      const parsed = JSON.parse(text) as unknown;
      const rows = normalizeOverrideRows(parsed);

      PROFILE_OVERRIDE_CACHE = {
        cacheKey,
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
