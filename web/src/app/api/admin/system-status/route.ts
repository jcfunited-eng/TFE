import { readdir, readFile, stat } from "node:fs/promises";
import path from "node:path";
import { NextResponse } from "next/server";

import { readSessionUserFromRequest } from "@/lib/auth-session";
import { listUsers } from "@/lib/user-store";
import { isAdminMfaEnabled } from "@/lib/mfa";

type FileStatus = {
  key: string;
  path: string;
  exists: boolean;
  sizeBytes: number | null;
  mtimeUtc: string | null;
  modeOctal: string | null;
  isPrivate: boolean | null;
};

type DirectoryStatus = {
  key: string;
  path: string;
  exists: boolean;
  entryCount: number | null;
  modeOctal: string | null;
};

type RefreshReportSummary = {
  generated_at_utc?: string;
  status?: string;
  elapsed_seconds?: number;
  rows_written?: number;
  skipped_count?: number;
};

type RefreshMode = "snapshot" | "universe_snapshot";

type RefreshStatusRecord = {
  running: boolean;
  pid?: number;
  requested_mode?: RefreshMode;
  started_at?: string;
  completed_at?: string;
  last_error?: string;
  report_generated_at_utc?: string;
  last_report?: RefreshReportSummary;
};

type RefreshPolicyCheck = {
  key: string;
  ok: boolean;
  detail: string;
};

type RefreshPolicyHealth = {
  healthy: boolean;
  policyMap: {
    snapshot: string;
    universe_snapshot: string;
  };
  lastRequestedMode: RefreshMode | "unknown";
  lastError: string | null;
  checks: RefreshPolicyCheck[];
};

type WebDataProtectionSummary = {
  scannedUserDirs: number;
  encryptedWatchlists: number;
  encryptedPortfolios: number;
  legacyWatchlists: number;
  legacyPortfolios: number;
};

const ROOT_DIR = path.resolve(process.cwd(), "..");

const SECRET_FILES = [
  { key: "session_secret", relativePath: "tfe_session_secret.bin" },
  { key: "ses_root_key", relativePath: "tfe_root_key.bin" },
  { key: "user_store", relativePath: "tfe_users.json" },
] as const;

const ARTIFACT_FILES = [
  { key: "uf_snapshot_envelope", relativePath: "uf_snapshot.ses.json" },
  { key: "uf_snapshot_report", relativePath: "uf_snapshot_rebuild_report.json" },
  { key: "ingestion_verify", relativePath: "ingestion_pipeline_verification_latest.json" },
  { key: "audit_ab", relativePath: "real_world_uf_audit_from_ab_sample.json" },
  { key: "ab_adaptive_vs_fixed", relativePath: "ab_adaptive_vs_fixed_report.json" },
  { key: "tau_d_filtered", relativePath: "tau_d_calibration_filtered_dt_report.json" },
  { key: "tau_d_full", relativePath: "tau_d_calibration_full_universe_report.json" },
  { key: "refresh_status", relativePath: "admin_refresh_status.json" },
  { key: "refresh_log", relativePath: "admin_refresh_latest.log" },
] as const;

const DATA_DIRECTORIES = [
  { key: "web_user_data", relativePath: "web_user_data" },
  { key: "encrypted_portfolios", relativePath: "tfe_encrypted_portfolios" },
  { key: "ses_core", relativePath: "ses_core" },
] as const;

function toModeOctal(mode: number): string {
  return (mode & 0o777).toString(8).padStart(3, "0");
}

function isOwnerOnlyMode(mode: number): boolean {
  return (mode & 0o077) === 0;
}

function managedSecretStatus(key: string, sourcePath: string): FileStatus {
  return {
    key,
    path: sourcePath,
    exists: true,
    sizeBytes: null,
    mtimeUtc: null,
    modeOctal: null,
    isPrivate: true,
  };
}

function usesAwsManagedRootSecret(): boolean {
  const env = String(process.env.TFE_ENV ?? "").trim().toLowerCase();
  const secretId = String(process.env.TFE_SES_ROOT_SECRET_ID ?? "").trim();
  return env === "aws" && secretId.length > 0;
}

function usesPostgresUserStore(): boolean {
  const backend = String(process.env.TFE_USER_STORE_BACKEND ?? "file").trim().toLowerCase();
  return backend === "postgres";
}

function awsSecretPath(): string {
  const secretId = String(process.env.TFE_SES_ROOT_SECRET_ID ?? "").trim();
  return `aws-secretsmanager:${secretId || "configured"}`;
}

function postgresStorePath(): string {
  const host = String(process.env.PGHOST ?? "").trim();
  const db = String(process.env.PGDATABASE ?? "").trim();

  if (host && db) return `postgres://${host}/${db}`;
  if (host) return `postgres://${host}`;
  return "postgres://configured";
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

async function readFileStatus(key: string, absolutePath: string): Promise<FileStatus> {
  try {
    const fileStat = await stat(absolutePath);
    const modeOctal = toModeOctal(fileStat.mode);
    return {
      key,
      path: absolutePath,
      exists: true,
      sizeBytes: fileStat.size,
      mtimeUtc: fileStat.mtime.toISOString(),
      modeOctal,
      isPrivate: isOwnerOnlyMode(fileStat.mode),
    };
  } catch {
    return {
      key,
      path: absolutePath,
      exists: false,
      sizeBytes: null,
      mtimeUtc: null,
      modeOctal: null,
      isPrivate: null,
    };
  }
}

async function resolveSecretStatuses(): Promise<FileStatus[]> {
  const sessionSecret = await readFileStatus(
    SECRET_FILES[0].key,
    path.join(ROOT_DIR, SECRET_FILES[0].relativePath),
  );

  const rootKey = usesAwsManagedRootSecret()
    ? managedSecretStatus(SECRET_FILES[1].key, awsSecretPath())
    : await readFileStatus(SECRET_FILES[1].key, path.join(ROOT_DIR, SECRET_FILES[1].relativePath));

  const userStore = usesPostgresUserStore()
    ? managedSecretStatus(SECRET_FILES[2].key, postgresStorePath())
    : await readFileStatus(SECRET_FILES[2].key, path.join(ROOT_DIR, SECRET_FILES[2].relativePath));

  return [sessionSecret, rootKey, userStore];
}

async function readDirectoryStatus(key: string, absolutePath: string): Promise<DirectoryStatus> {
  try {
    const dirStat = await stat(absolutePath);
    if (!dirStat.isDirectory()) {
      return {
        key,
        path: absolutePath,
        exists: false,
        entryCount: null,
        modeOctal: null,
      };
    }

    const entries = await readdir(absolutePath);
    return {
      key,
      path: absolutePath,
      exists: true,
      entryCount: entries.length,
      modeOctal: toModeOctal(dirStat.mode),
    };
  } catch {
    return {
      key,
      path: absolutePath,
      exists: false,
      entryCount: null,
      modeOctal: null,
    };
  }
}

async function readRefreshReportSummary(): Promise<RefreshReportSummary | null> {
  const reportPath = path.join(ROOT_DIR, "uf_snapshot_rebuild_report.json");
  try {
    const raw = await readFile(reportPath, "utf-8");
    const parsed = JSON.parse(raw) as Record<string, unknown>;

    return {
      generated_at_utc: typeof parsed.generated_at_utc === "string" ? parsed.generated_at_utc : undefined,
      status: typeof parsed.status === "string" ? parsed.status : undefined,
      elapsed_seconds: typeof parsed.elapsed_seconds === "number" ? parsed.elapsed_seconds : undefined,
      rows_written: typeof parsed.rows_written === "number" ? parsed.rows_written : undefined,
      skipped_count: typeof parsed.skipped_count === "number" ? parsed.skipped_count : undefined,
    };
  } catch {
    return null;
  }
}

async function readRefreshStatusRecord(rootDir: string): Promise<RefreshStatusRecord | null> {
  const statusPath = path.join(rootDir, "admin_refresh_status.json");

  try {
    const raw = await readFile(statusPath, "utf-8");
    const parsed = JSON.parse(raw) as RefreshStatusRecord;
    if (typeof parsed !== "object" || parsed === null) return null;
    if (typeof parsed.running !== "boolean") return null;
    return parsed;
  } catch {
    return null;
  }
}

function artifactExists(artifacts: FileStatus[], key: string): boolean {
  return artifacts.some((item) => item.key === key && item.exists);
}

async function evaluateRefreshPolicyHealth(
  rootDir: string,
  artifactStatuses: FileStatus[],
  reportSummary: RefreshReportSummary | null,
): Promise<RefreshPolicyHealth> {
  const status = await readRefreshStatusRecord(rootDir);
  const refreshScriptPath = path.join(rootDir, "run_refresh_with_l5_learning.py");
  let refreshScriptPresent = false;
  const refreshStatusArtifactExists = artifactExists(artifactStatuses, "refresh_status");
  const refreshLogArtifactExists = artifactExists(artifactStatuses, "refresh_log");
  const snapshotEnvelopeArtifactExists = artifactExists(artifactStatuses, "uf_snapshot_envelope");
  const refreshRunning = Boolean(status?.running);
  const lastRequestedMode: RefreshMode | "unknown" = status?.requested_mode ?? "unknown";
  const reportStatus = String(reportSummary?.status ?? "unknown");
  const reportRowsWritten = typeof reportSummary?.rows_written === "number" ? reportSummary.rows_written : null;
  const targetedNoChangeAllowed =
    lastRequestedMode === "snapshot" &&
    reportStatus === "no_rows_written" &&
    snapshotEnvelopeArtifactExists;
  const universeNoRowsFailure =
    lastRequestedMode === "universe_snapshot" &&
    reportStatus === "no_rows_written";

  try {
    const scriptStat = await stat(refreshScriptPath);
    refreshScriptPresent = scriptStat.isFile();
  } catch {
    refreshScriptPresent = false;
  }

  const checks: RefreshPolicyCheck[] = [
    {
      key: "refresh-script-present",
      ok: refreshScriptPresent,
      detail: refreshScriptPresent ? "Refresh wrapper script is present." : "Refresh wrapper script is missing.",
    },
    {
      key: "refresh-status-artifact",
      ok: refreshStatusArtifactExists || !refreshRunning,
      detail: refreshStatusArtifactExists
        ? "Refresh status artifact exists."
        : refreshRunning
          ? "Refresh status artifact is missing while refresh is running."
          : "Refresh status artifact is not present while idle (informational).",
    },
    {
      key: "refresh-log-artifact",
      ok: refreshLogArtifactExists || !refreshRunning,
      detail: refreshLogArtifactExists
        ? "Refresh log artifact exists."
        : refreshRunning
          ? "Refresh log artifact is missing while refresh is running."
          : "Refresh log artifact is not present while idle (informational).",
    },
    {
      key: "snapshot-envelope-artifact",
      ok: snapshotEnvelopeArtifactExists,
      detail: snapshotEnvelopeArtifactExists
        ? "Snapshot envelope artifact exists."
        : "Snapshot envelope artifact is missing.",
    },
    {
      key: "latest-report-status",
      ok: reportStatus === "ok" || targetedNoChangeAllowed,
      detail: reportStatus === "ok"
        ? "Latest snapshot rebuild report is OK."
        : targetedNoChangeAllowed
          ? "Latest targeted snapshot wrote no rows; existing snapshot remains valid."
          : `Latest snapshot rebuild report status is ${reportStatus}.`,
    },
    {
      key: "latest-report-rows",
      ok: (typeof reportRowsWritten === "number" && reportRowsWritten > 0) || targetedNoChangeAllowed,
      detail: typeof reportRowsWritten === "number" && reportRowsWritten > 0
        ? `Latest snapshot wrote ${reportRowsWritten} rows.`
        : targetedNoChangeAllowed
          ? "Targeted snapshot wrote 0 rows because no eligible updates were found."
          : "Latest snapshot rebuild report does not show rows written > 0.",
    },
    {
      key: "mode-aware-empty-write-guard",
      ok: !universeNoRowsFailure,
      detail: universeNoRowsFailure
        ? "Universe snapshot wrote 0 rows; this is a production failure."
        : "Empty-write guard passed for current refresh mode.",
    },
  ];

  const healthy = checks.every((check) => check.ok);

  return {
    healthy,
    policyMap: {
      snapshot: "targeted_pfsc",
      universe_snapshot: "full_universe + force_refresh_universe",
    },
    lastRequestedMode,
    lastError: status?.last_error ?? null,
    checks,
  };
}

async function scanWebDataProtection(rootDir: string): Promise<WebDataProtectionSummary> {
  const summary: WebDataProtectionSummary = {
    scannedUserDirs: 0,
    encryptedWatchlists: 0,
    encryptedPortfolios: 0,
    legacyWatchlists: 0,
    legacyPortfolios: 0,
  };

  const userDataRoot = path.join(rootDir, "web_user_data");

  let userEntries: string[];
  try {
    userEntries = await readdir(userDataRoot);
  } catch {
    return summary;
  }

  for (const entryName of userEntries) {
    if (entryName.startsWith(".")) continue;

    const userDir = path.join(userDataRoot, entryName);
    let userDirStat;
    try {
      userDirStat = await stat(userDir);
    } catch {
      continue;
    }

    if (!userDirStat.isDirectory()) continue;

    summary.scannedUserDirs += 1;

    let files: string[];
    try {
      files = await readdir(userDir);
    } catch {
      continue;
    }

    if (files.includes("watchlist.ses.json")) summary.encryptedWatchlists += 1;
    if (files.includes("portfolio_manual.ses.json")) summary.encryptedPortfolios += 1;
    if (files.includes("watchlist.csv")) summary.legacyWatchlists += 1;
    if (files.includes("portfolio_manual.json")) summary.legacyPortfolios += 1;
  }

  return summary;
}

export async function GET(request: Request) {
  const denied = await requireAdmin(request);
  if (denied) return denied;

  const secretStatuses = await resolveSecretStatuses();

  const artifactStatuses = await Promise.all(
    ARTIFACT_FILES.map((entry) => readFileStatus(entry.key, path.join(ROOT_DIR, entry.relativePath))),
  );

  const directoryStatuses = await Promise.all(
    DATA_DIRECTORIES.map((entry) => readDirectoryStatus(entry.key, path.join(ROOT_DIR, entry.relativePath))),
  );

  const allSecretsPrivate = secretStatuses.every((item) => item.exists && item.isPrivate === true);

  const usersResult = await listUsers();
  const activeAdminCount = usersResult.users.filter((user) => user.role === "admin" && user.is_active).length;
  const activeMemberCount = usersResult.users.filter((user) => user.role === "member" && user.is_active).length;
  const activeDefaultAccounts = usersResult.users
    .filter((user) => user.is_active && (user.username === "admin" || user.username === "member"))
    .map((user) => user.username);
  const sesCoreDir = directoryStatuses.find((entry) => entry.key === "ses_core");
  const reportSummary = await readRefreshReportSummary();
  const refreshPolicy = await evaluateRefreshPolicyHealth(ROOT_DIR, artifactStatuses, reportSummary);
  const webDataProtection = await scanWebDataProtection(ROOT_DIR);

  return NextResponse.json({
    generatedAtUtc: new Date().toISOString(),
    environment: {
      nodeEnv: process.env.NODE_ENV ?? "development",
      webProcessCwd: process.cwd(),
      rootDir: ROOT_DIR,
    },
    users: {
      count: usersResult.users.length,
      sourcePath: usersResult.filePath,
    },
    auth: {
      adminMfaEnabled: isAdminMfaEnabled(),
      activeAdminCount,
      activeMemberCount,
      activeDefaultAccounts,
    },
    security: {
      allSecretsPrivate,
      secrets: secretStatuses,
    },
    sesCore: {
      modulePath: path.join(ROOT_DIR, "ses_core"),
      modulePresent: Boolean(sesCoreDir?.exists),
      moduleFileCount: sesCoreDir?.entryCount ?? 0,
    },
    artifacts: artifactStatuses,
    directories: directoryStatuses,
    reportSummary,
    refreshPolicy,
    webDataProtection,
  });
}
