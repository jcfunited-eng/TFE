import { readFile, stat } from "node:fs/promises";
import path from "node:path";
import { NextResponse } from "next/server";
import {
  ADMIN_REFRESH_PERSIST_KEYS,
  clampRefreshTextSnapshot,
  readAdminRefreshPersist,
  writeAdminRefreshPersist,
} from "@/lib/admin-refresh-persist";
import { getCurrentServerUser } from "@/lib/server-auth";
import { resolveWorkspaceRoot } from "@/lib/workspace-root";

const ROOT_DIR = resolveWorkspaceRoot();
const HISTORY_PATH = path.join(ROOT_DIR, "admin_refresh_history.jsonl");
const DEFAULT_LINES = 200;
const MIN_LINES = 20;
const MAX_LINES = 2000;

function normalizeLineCount(value: string | null): number {
  const n = Number(value);
  if (!Number.isFinite(n)) return DEFAULT_LINES;
  const whole = Math.floor(n);
  if (whole < MIN_LINES) return MIN_LINES;
  if (whole > MAX_LINES) return MAX_LINES;
  return whole;
}

type HistoryEntry = {
  logged_at_utc?: string;
  run_id?: string;
  phase?: string;
  status?: string;
  mode?: string;
  trigger_source?: string;
  requested_by?: string;
  pid?: number;
  rows_written?: number;
  elapsed_seconds?: number;
  refresh_report_status?: string;
  l5_learning?: string;
  optimizer_short_cycle?: string;
  optimizer_cycle_requested_runs?: number;
  optimizer_cycle_completed_runs?: number;
  optimizer_session_id?: string;
  optimizer_target_return_lift_pct?: number;
  optimizer_best_score?: number;
  optimizer_target_met?: boolean;
  epoch_library_confidence_schema?: string;
  epoch_library_status?: string;
  error?: string;
};

function parseHistoryEntries(text: string, count: number): HistoryEntry[] {
  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0);

  const tail = lines.length <= count ? lines : lines.slice(lines.length - count);
  const out: HistoryEntry[] = [];

  for (const line of tail) {
    try {
      const parsed = JSON.parse(line) as Record<string, unknown>;
      out.push({
        logged_at_utc: typeof parsed.logged_at_utc === "string" ? parsed.logged_at_utc : undefined,
        run_id: typeof parsed.run_id === "string" ? parsed.run_id : undefined,
        phase: typeof parsed.phase === "string" ? parsed.phase : undefined,
        status: typeof parsed.status === "string" ? parsed.status : undefined,
        mode: typeof parsed.mode === "string" ? parsed.mode : undefined,
        trigger_source: typeof parsed.trigger_source === "string" ? parsed.trigger_source : undefined,
        requested_by: typeof parsed.requested_by === "string" ? parsed.requested_by : undefined,
        pid: typeof parsed.pid === "number" ? parsed.pid : undefined,
        rows_written: typeof parsed.rows_written === "number" ? parsed.rows_written : undefined,
        elapsed_seconds: typeof parsed.elapsed_seconds === "number" ? parsed.elapsed_seconds : undefined,
        refresh_report_status: typeof parsed.refresh_report_status === "string" ? parsed.refresh_report_status : undefined,
        l5_learning: typeof parsed.l5_learning === "string" ? parsed.l5_learning : undefined,
        optimizer_short_cycle: typeof parsed.optimizer_short_cycle === "string" ? parsed.optimizer_short_cycle : undefined,
        optimizer_cycle_requested_runs:
          typeof parsed.optimizer_cycle_requested_runs === "number" ? parsed.optimizer_cycle_requested_runs : undefined,
        optimizer_cycle_completed_runs:
          typeof parsed.optimizer_cycle_completed_runs === "number" ? parsed.optimizer_cycle_completed_runs : undefined,
        optimizer_session_id: typeof parsed.optimizer_session_id === "string" ? parsed.optimizer_session_id : undefined,
        optimizer_target_return_lift_pct:
          typeof parsed.optimizer_target_return_lift_pct === "number"
            ? parsed.optimizer_target_return_lift_pct
            : undefined,
        optimizer_best_score: typeof parsed.optimizer_best_score === "number" ? parsed.optimizer_best_score : undefined,
        optimizer_target_met: typeof parsed.optimizer_target_met === "boolean" ? parsed.optimizer_target_met : undefined,
        epoch_library_confidence_schema:
          typeof parsed.epoch_library_confidence_schema === "string" ? parsed.epoch_library_confidence_schema : undefined,
        epoch_library_status: typeof parsed.epoch_library_status === "string" ? parsed.epoch_library_status : undefined,
        error: typeof parsed.error === "string" ? parsed.error : undefined,
      });
    } catch {
      // Skip malformed history lines.
    }
  }

  return out;
}

async function requireAdmin(request: Request): Promise<NextResponse | null> {
  const user = await getCurrentServerUser();
  if (!user) {
    return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  }

  if (user.role !== "admin") {
    return NextResponse.json({ error: "Admin role required." }, { status: 403 });
  }

  return null;
}

export async function GET(request: Request) {
  const denied = await requireAdmin(request);
  if (denied) return denied;

  const url = new URL(request.url);
  const linesRequested = normalizeLineCount(url.searchParams.get("lines"));

  try {
    const [raw, historyStat] = await Promise.all([readFile(HISTORY_PATH, "utf-8"), stat(HISTORY_PATH)]);
    const entries = parseHistoryEntries(raw, linesRequested);
    await writeAdminRefreshPersist(ADMIN_REFRESH_PERSIST_KEYS.historySnapshot, {
      path: HISTORY_PATH,
      raw_text: clampRefreshTextSnapshot(raw),
      updated_at_utc: historyStat.mtime.toISOString(),
    });
    return NextResponse.json({
      exists: true,
      path: HISTORY_PATH,
      linesRequested,
      entryCount: entries.length,
      updatedAtUtc: historyStat.mtime.toISOString(),
      entries,
    });
  } catch {
    const persisted = await readAdminRefreshPersist(ADMIN_REFRESH_PERSIST_KEYS.historySnapshot);
    const persistedRaw = typeof persisted?.raw_text === "string" ? persisted.raw_text : "";
    if (persistedRaw) {
      const entries = parseHistoryEntries(persistedRaw, linesRequested);
      return NextResponse.json({
        exists: true,
        path: typeof persisted?.path === "string" ? persisted.path : HISTORY_PATH,
        linesRequested,
        entryCount: entries.length,
        updatedAtUtc: typeof persisted?.updated_at_utc === "string" ? persisted.updated_at_utc : null,
        entries,
      });
    }

    return NextResponse.json({
      exists: false,
      path: HISTORY_PATH,
      linesRequested,
      entryCount: 0,
      updatedAtUtc: null,
      entries: [],
    });
  }
}
