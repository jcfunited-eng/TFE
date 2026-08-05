import { existsSync } from "node:fs";
import path from "node:path";

const ROOT_MARKERS = ["run_refresh_with_l5_learning.py", "uf_snapshot.json", "TFE_TODO_LIST.md"];
const WORKSPACE_HINT = "/workspaces/Tao_Financial_Engine";

function uniqueCandidates(values: string[]): string[] {
  const out: string[] = [];
  const seen = new Set<string>();

  for (const raw of values) {
    const trimmed = String(raw || "").trim();
    if (!trimmed) continue;
    const resolved = path.resolve(trimmed);
    if (seen.has(resolved)) continue;
    seen.add(resolved);
    out.push(resolved);
  }

  return out;
}

function hasAllRootMarkers(candidate: string): boolean {
  return ROOT_MARKERS.every((marker) => existsSync(path.join(candidate, marker)));
}

function hasPrimaryRefreshMarker(candidate: string): boolean {
  return existsSync(path.join(candidate, "run_refresh_with_l5_learning.py"));
}

export function resolveWorkspaceRoot(): string {
  const configuredRoot = String(process.env.TFE_WORKSPACE_ROOT ?? "").trim();
  const candidates = uniqueCandidates([
    configuredRoot,
    process.cwd(),
    path.resolve(process.cwd(), ".."),
    path.resolve(process.cwd(), "../.."),
    WORKSPACE_HINT,
  ]);

  for (const candidate of candidates) {
    if (hasAllRootMarkers(candidate)) {
      return candidate;
    }
  }

  for (const candidate of candidates) {
    if (hasPrimaryRefreshMarker(candidate)) {
      return candidate;
    }
  }

  return path.resolve(process.cwd(), "..");
}
