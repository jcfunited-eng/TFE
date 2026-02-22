import { spawn } from "node:child_process";
import { timingSafeEqual } from "node:crypto";
import { closeSync, openSync } from "node:fs";
import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { NextResponse } from "next/server";
import { readSessionUserFromRequest } from "@/lib/auth-session";
import { primeSnapshotRowsCache } from "@/lib/uf-snapshot";

type RefreshMode = "snapshot" | "universe_snapshot";

type RefreshReport = {
  generated_at_utc?: string;
  elapsed_seconds?: number;
  rows_written?: number;
  skipped_count?: number;
  status?: string;
};

type RefreshStatusRecord = {
  running: boolean;
  pid?: number;
  requested_mode?: RefreshMode;
  started_at?: string;
  completed_at?: string;
  last_error?: string;
  report_generated_at_utc?: string;
  last_report?: RefreshReport;
};

const ROOT_DIR = path.resolve(process.cwd(), "..");
const STATUS_PATH = path.join(ROOT_DIR, "admin_refresh_status.json");
const LOG_PATH = path.join(ROOT_DIR, "admin_refresh_latest.log");
const REPORT_PATH = path.join(ROOT_DIR, "uf_snapshot_rebuild_report.json");
const INTERNAL_TOKEN_HEADER = "x-tfe-internal-refresh-token";
const REFRESH_SCRIPT = String(process.env.TFE_REFRESH_SCRIPT ?? "run_refresh_with_l5_learning.py").trim() || "run_refresh_with_l5_learning.py";

function nowIso(): string {
  return new Date().toISOString();
}

function isRefreshMode(value: unknown): value is RefreshMode {
  return value === "snapshot" || value === "universe_snapshot";
}

async function isRefreshProcessAlive(pid: number | undefined): Promise<boolean> {
  if (typeof pid !== "number" || pid <= 0) return false;

  try {
    process.kill(pid, 0);
  } catch {
    return false;
  }

  const scriptPath = REFRESH_SCRIPT;
  const scriptBasename = path.basename(scriptPath);
  const markers = new Set<string>([scriptPath, scriptBasename]);
  if (scriptBasename.endsWith(".py")) {
    markers.add(scriptBasename.slice(0, -3));
  }

  try {
    const raw = await readFile(`/proc/${pid}/cmdline`, "utf-8");
    const cmdline = raw.replace(/\u0000/g, " ").trim();
    if (!cmdline) {
      // Empty cmdline often indicates a dead/zombie process; treat as not alive
      // for refresh ownership so stale status can clear safely.
      return false;
    }
    for (const marker of markers) {
      if (marker && cmdline.includes(marker)) {
        return true;
      }
    }
    return false;
  } catch {
    // /proc may be unavailable in some runtimes; keep kill(0) as fallback.
    return true;
  }
}

function resolvePythonBin(): string {
  const configured = String(process.env.TFE_PYTHON_BIN ?? "").trim();
  if (configured) return configured;
  return "python3";
}

function hasValidInternalToken(request: Request): boolean {
  const expected = String(process.env.TFE_INTERNAL_REFRESH_TOKEN ?? "");
  if (!expected) return false;

  const provided = String(request.headers.get(INTERNAL_TOKEN_HEADER) ?? "");
  if (!provided) return false;

  const expectedBytes = Buffer.from(expected, "utf-8");
  const providedBytes = Buffer.from(provided, "utf-8");

  if (expectedBytes.length !== providedBytes.length) return false;

  return timingSafeEqual(expectedBytes, providedBytes);
}

async function readStatusRecord(): Promise<RefreshStatusRecord | null> {
  try {
    const raw = await readFile(STATUS_PATH, "utf-8");
    const parsed = JSON.parse(raw) as RefreshStatusRecord;
    if (typeof parsed !== "object" || parsed === null) return null;
    return parsed;
  } catch {
    return null;
  }
}

async function writeStatusRecord(record: RefreshStatusRecord): Promise<void> {
  await writeFile(STATUS_PATH, JSON.stringify(record, null, 2), "utf-8");
}

async function readReportSummary(): Promise<RefreshReport | null> {
  try {
    const raw = await readFile(REPORT_PATH, "utf-8");
    const report = JSON.parse(raw) as Record<string, unknown>;
    if (typeof report !== "object" || report === null) return null;

    return {
      generated_at_utc: typeof report.generated_at_utc === "string" ? report.generated_at_utc : undefined,
      elapsed_seconds: typeof report.elapsed_seconds === "number" ? report.elapsed_seconds : undefined,
      rows_written: typeof report.rows_written === "number" ? report.rows_written : undefined,
      skipped_count: typeof report.skipped_count === "number" ? report.skipped_count : undefined,
      status: typeof report.status === "string" ? report.status : undefined,
    };
  } catch {
    return null;
  }
}

async function normalizeStatus(): Promise<RefreshStatusRecord> {
  const existing = await readStatusRecord();
  const base: RefreshStatusRecord = existing ?? { running: false };
  const report = await readReportSummary();
  const startedAtMs = Number.isFinite(Date.parse(String(base.started_at ?? "")))
    ? Date.parse(String(base.started_at ?? ""))
    : Number.NaN;
  const reportGeneratedMs = Number.isFinite(Date.parse(String(report?.generated_at_utc ?? "")))
    ? Date.parse(String(report?.generated_at_utc ?? ""))
    : Number.NaN;
  const reportIsFromCurrentRun =
    base.running &&
    Number.isFinite(startedAtMs) &&
    Number.isFinite(reportGeneratedMs) &&
    reportGeneratedMs >= startedAtMs;

  if (reportIsFromCurrentRun) {
    const normalized: RefreshStatusRecord = {
      ...base,
      running: false,
      completed_at: nowIso(),
      report_generated_at_utc: report?.generated_at_utc,
      last_report: report ?? base.last_report,
      last_error:
        report && report.status && report.status !== "ok"
          ? "Refresh finished with non-ok report status. Check report/log."
          : undefined,
    };
    await writeStatusRecord(normalized);
    return normalized;
  }

  if (base.running && !(await isRefreshProcessAlive(base.pid))) {
    const normalized: RefreshStatusRecord = {
      ...base,
      running: false,
      completed_at: nowIso(),
      report_generated_at_utc: report?.generated_at_utc,
      last_report: report ?? base.last_report,
      last_error:
        report && report.status && report.status !== "ok"
          ? "Refresh finished with non-ok report status. Check report/log."
          : base.last_error ?? "Cleared stale refresh state because refresh process is no longer active.",
    };
    await writeStatusRecord(normalized);
    return normalized;
  }

  if (!base.running && report) {
    const normalized: RefreshStatusRecord = {
      ...base,
      report_generated_at_utc: report.generated_at_utc,
      last_report: report,
    };
    await writeStatusRecord(normalized);
    return normalized;
  }

  return base;
}

function buildRefreshArgs(mode: RefreshMode): string[] {
  const args = [REFRESH_SCRIPT];

  if (mode === "snapshot") {
    args.push("--refresh-mode", "targeted_pfsc");
    return args;
  }

  args.push("--refresh-mode", "full_universe", "--force-refresh-universe");
  return args;
}

async function requireAdmin(request: Request): Promise<NextResponse | null> {
  const user = await readSessionUserFromRequest(request);
  if (!user) {
    return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  }

  if (user.role !== "admin") {
    return NextResponse.json({ error: "Admin role required." }, { status: 403 });
  }

  return null;
}

async function resolveRequestedMode(request: Request): Promise<{ mode?: unknown; parseError?: string }> {
  const url = new URL(request.url);
  const fromQuery = url.searchParams.get("mode");
  if (fromQuery) {
    return { mode: fromQuery };
  }

  let text = "";
  try {
    text = await request.text();
  } catch {
    return { parseError: "Failed to read request body." };
  }

  const trimmed = text.trim();
  if (!trimmed) {
    return { mode: undefined };
  }

  try {
    const parsed = JSON.parse(trimmed) as { mode?: unknown };
    return { mode: parsed.mode };
  } catch {
    return { parseError: "Invalid JSON body." };
  }
}

export async function GET(request: Request) {
  const denied = await requireAdmin(request);
  if (denied) return denied;

  const status = await normalizeStatus();
  if (!status.running && status.last_report?.status === "ok") {
    primeSnapshotRowsCache();
  }
  return NextResponse.json({ status, refreshScript: REFRESH_SCRIPT });
}

export async function POST(request: Request) {
  const internalAuthorized = hasValidInternalToken(request);
  if (!internalAuthorized) {
    const denied = await requireAdmin(request);
    if (denied) return denied;
  }

  const modeInput = await resolveRequestedMode(request);
  if (modeInput.parseError) {
    return NextResponse.json({ error: modeInput.parseError }, { status: 400 });
  }

  const modeValue = modeInput.mode;
  if (!isRefreshMode(modeValue)) {
    return NextResponse.json(
      { error: "mode must be 'snapshot' or 'universe_snapshot' (query or JSON body)." },
      { status: 400 },
    );
  }

  const currentStatus = await normalizeStatus();
  if (currentStatus.running) {
    return NextResponse.json({ error: "A refresh job is already running.", status: currentStatus }, { status: 409 });
  }

  const args = buildRefreshArgs(modeValue);
  const pythonBin = resolvePythonBin();

  try {
    const logFd = openSync(LOG_PATH, "a");

    const child = spawn(pythonBin, args, {
      cwd: ROOT_DIR,
      detached: true,
      stdio: ["ignore", logFd, logFd],
      env: {
        ...process.env,
        PYTHONUNBUFFERED: String(process.env.PYTHONUNBUFFERED ?? "1"),
      },
    });

    closeSync(logFd);
    child.unref();

    const nextStatus: RefreshStatusRecord = {
      running: true,
      pid: child.pid,
      requested_mode: modeValue,
      started_at: nowIso(),
      completed_at: undefined,
      last_error: undefined,
      report_generated_at_utc: currentStatus.report_generated_at_utc,
      last_report: currentStatus.last_report,
    };

    await writeStatusRecord(nextStatus);

    return NextResponse.json({ status: nextStatus, internalAuthorized, refreshScript: REFRESH_SCRIPT });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Failed to start refresh.";
    const failedStatus: RefreshStatusRecord = {
      running: false,
      requested_mode: modeValue,
      started_at: nowIso(),
      completed_at: nowIso(),
      last_error: message,
      report_generated_at_utc: currentStatus.report_generated_at_utc,
      last_report: currentStatus.last_report,
    };

    await writeStatusRecord(failedStatus);
    return NextResponse.json({ error: message, status: failedStatus, refreshScript: REFRESH_SCRIPT }, { status: 500 });
  }
}
