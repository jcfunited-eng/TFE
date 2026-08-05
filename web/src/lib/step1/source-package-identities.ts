import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";

import { sha256Text, stableJsonStringify } from "./schema";
import type { Step1SourcePackageIdentityInput } from "./run-request";

const TARGETED_SELECTOR_SCRIPT_RELATIVE_PATH = path.join("web", "scripts", "read_runtime_selector_rows.mjs");
const WEB_USER_DATA_ROOT = "web_user_data";
const RUNTIME_SELECTOR_MAX_BUFFER_BYTES = 128 * 1024 * 1024;
const COMMAND_ERROR_SNIPPET_MAX_CHARS = 2000;

function slugify(value: string): string {
  const text = String(value ?? "").trim().toLowerCase().replace(/[^a-z0-9]+/g, "_");
  return text.replace(/^_+|_+$/g, "") || "unknown";
}

function sha256Buffer(value: Buffer): string {
  return createHash("sha256").update(value).digest("hex");
}

function requireText(value: unknown, fieldName: string): string {
  const text = String(value ?? "").trim();
  if (!text) {
    throw new Error(`${fieldName} is required to synthesize exact source package identities.`);
  }
  return text;
}

function requireIsoTimestamp(value: unknown, fieldName: string): string {
  const text = requireText(value, fieldName);
  const parsed = Date.parse(text);
  if (!Number.isFinite(parsed)) {
    throw new Error(`${fieldName} must be a valid ISO timestamp to synthesize exact source package identities.`);
  }
  return new Date(parsed).toISOString();
}

function readPgPort(env: NodeJS.ProcessEnv): string {
  const raw = String(env.PGPORT ?? env.TFE_DB_PORT ?? "5432").trim();
  const parsed = Number(raw);
  if (!Number.isFinite(parsed)) return "5432";
  const whole = Math.floor(parsed);
  if (whole < 1 || whole > 65535) return "5432";
  return `${whole}`;
}

function buildRuntimeSelectorPayloadReference(env: NodeJS.ProcessEnv, sourceTable: string, runId: string): string {
  const host = requireText(env.PGHOST ?? env.TFE_DB_HOST, "PGHOST");
  const database = requireText(env.PGDATABASE ?? env.TFE_DB_NAME, "PGDATABASE");
  const port = readPgPort(env);
  return `postgres://${host}:${port}/${database}#${sourceTable}?run_id=${encodeURIComponent(runId)}`;
}

function parseSelectorPayload(raw: string): Record<string, unknown> {
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new Error("payload is not an object");
    }
    return parsed as Record<string, unknown>;
  } catch (error) {
    throw new Error(
      `runtime selector payload could not be parsed while synthesizing exact source package identities. ${
        error instanceof Error ? error.message : "unknown parse failure"
      }`,
    );
  }
}

function normalizeCommandOutput(value: unknown): string {
  if (Buffer.isBuffer(value)) {
    return value.toString("utf8").trim();
  }
  return String(value ?? "").trim();
}

function summarizeCommandOutput(value: unknown, label: string): string | null {
  const text = normalizeCommandOutput(value);
  if (!text) {
    return null;
  }
  if (text.length <= COMMAND_ERROR_SNIPPET_MAX_CHARS) {
    return `${label}=${text}`;
  }
  const omittedChars = text.length - COMMAND_ERROR_SNIPPET_MAX_CHARS;
  return `${label}=${text.slice(0, COMMAND_ERROR_SNIPPET_MAX_CHARS)}...[truncated ${omittedChars} chars]`;
}

function describeSelectorCommandFailure(error: unknown): string {
  const details: string[] = [];
  if (error instanceof Error && String(error.message).trim()) {
    details.push(String(error.message).trim());
  }

  const stdoutDetail = summarizeCommandOutput((error as { stdout?: unknown }).stdout, "stdout");
  const stderrDetail = summarizeCommandOutput((error as { stderr?: unknown }).stderr, "stderr");
  if (stderrDetail) {
    details.push(stderrDetail);
  } else if (stdoutDetail) {
    details.push(stdoutDetail);
  }

  if (details.length === 0) {
    return "unknown selector failure";
  }
  return details.join("; ");
}

function resolveRuntimeSelectorRowsSourcePackage(
  workspaceRoot: string,
  env: NodeJS.ProcessEnv,
): Step1SourcePackageIdentityInput {
  const scriptPath = path.join(workspaceRoot, TARGETED_SELECTOR_SCRIPT_RELATIVE_PATH);
  if (!existsSync(scriptPath)) {
    throw new Error(`runtime selector script is missing: ${scriptPath}`);
  }

  let raw = "";
  try {
    raw = execFileSync(process.execPath, [scriptPath], {
      encoding: "utf8",
      env: {
        ...process.env,
        ...env,
        TFE_WORKSPACE_ROOT: workspaceRoot,
      },
      stdio: ["ignore", "pipe", "pipe"],
      timeout: 90_000,
      maxBuffer: RUNTIME_SELECTOR_MAX_BUFFER_BYTES,
    }).trim();
  } catch (error) {
    throw new Error(
      `runtime selector rows could not be loaded while synthesizing exact source package identities. ${
        describeSelectorCommandFailure(error)
      }`,
    );
  }

  const payload = parseSelectorPayload(raw);
  if (payload.ok !== true) {
    throw new Error(
      `runtime selector rows did not report ok=true while synthesizing exact source package identities. reason=${
        String(payload.reason ?? "unknown")
      }`,
    );
  }

  const runId = requireText(payload.run_id, "runtime selector run_id");
  const sourceTable = requireText(payload.source_table, "runtime selector source_table");
  const generatedAtUtc = requireIsoTimestamp(payload.generated_at_utc, "runtime selector generated_at_utc");
  const rows = Array.isArray(payload.rows) ? payload.rows : null;
  if (!rows || rows.length === 0) {
    throw new Error("runtime selector rows were empty while synthesizing exact source package identities.");
  }

  const digest = sha256Text(
    stableJsonStringify({
      run_id: runId,
      source_table: sourceTable,
      generated_at_utc: generatedAtUtc,
      rows,
    }),
  );

  return {
    sourcePackageId: `source_package_v1_runtime_selector_rows_${slugify(sourceTable)}_${slugify(runId)}_${digest.slice(0, 12)}`,
    sourceIdentity: `sha256:${digest}`,
    acquisitionTimestampUtc: generatedAtUtc,
    sourceClass: "runtime_selector_rows",
    rawPayloadReference: buildRuntimeSelectorPayloadReference(env, sourceTable, runId),
    integrityStatus: "complete",
  };
}

function resolveWebUserDataRoot(workspaceRoot: string): string | null {
  const candidates = [
    path.join(workspaceRoot, WEB_USER_DATA_ROOT),
    path.join(process.cwd(), WEB_USER_DATA_ROOT),
    path.join(process.cwd(), "..", WEB_USER_DATA_ROOT),
    path.join("/app", WEB_USER_DATA_ROOT),
    path.join("/workspaces", "Tao_Financial_Engine", WEB_USER_DATA_ROOT),
  ];

  for (const candidate of candidates) {
    if (existsSync(candidate)) {
      return path.resolve(candidate);
    }
  }

  return null;
}

function buildTenantEnvelopeSourcePackage(params: {
  filePath: string;
  sourceClass: "tenant_watchlist_envelope" | "tenant_portfolio_envelope";
  username: string;
}): Step1SourcePackageIdentityInput {
  const resolvedPath = path.resolve(params.filePath);
  const payload = readFileSync(resolvedPath);
  const digest = sha256Buffer(payload);
  const acquisitionTimestampUtc = statSync(resolvedPath).mtime.toISOString();

  return {
    sourcePackageId: `source_package_v1_${params.sourceClass}_${slugify(params.username)}_${digest.slice(0, 12)}`,
    sourceIdentity: `sha256:${digest}`,
    acquisitionTimestampUtc,
    sourceClass: params.sourceClass,
    rawPayloadReference: resolvedPath,
    integrityStatus: "encrypted_present",
  };
}

function collectTenantEnvelopeSourcePackages(workspaceRoot: string): Step1SourcePackageIdentityInput[] {
  const root = resolveWebUserDataRoot(workspaceRoot);
  if (!root) {
    return [];
  }

  const out: Step1SourcePackageIdentityInput[] = [];
  for (const entry of readdirSync(root, { withFileTypes: true })) {
    if (!entry.isDirectory() || entry.name.startsWith(".")) {
      continue;
    }

    const userDir = path.join(root, entry.name);
    const watchlistPath = path.join(userDir, "watchlist.ses.json");
    if (existsSync(watchlistPath)) {
      out.push(
        buildTenantEnvelopeSourcePackage({
          filePath: watchlistPath,
          sourceClass: "tenant_watchlist_envelope",
          username: entry.name,
        }),
      );
    }

    const portfolioPath = path.join(userDir, "portfolio_manual.ses.json");
    if (existsSync(portfolioPath)) {
      out.push(
        buildTenantEnvelopeSourcePackage({
          filePath: portfolioPath,
          sourceClass: "tenant_portfolio_envelope",
          username: entry.name,
        }),
      );
    }
  }

  return out;
}

function assertAdminTrackedSymbolsCanBeRepresentedExactly(env: NodeJS.ProcessEnv): void {
  const raw = String(env.TFE_ADMIN_TRACKED_SYMBOLS ?? "").trim();
  if (!raw) {
    return;
  }
  throw new Error(
    "TFE_ADMIN_TRACKED_SYMBOLS is populated, but it does not carry exact acquisition metadata. "
    + "Supply sourcePackageIdentities explicitly or add a durable admin-tracked-symbols source artifact.",
  );
}

export function resolveStep1AdminRefreshSourcePackageIdentities(params: {
  workspaceRoot: string;
  requestedMode: string;
  env?: NodeJS.ProcessEnv;
}): Step1SourcePackageIdentityInput[] | undefined {
  if (String(params.requestedMode).trim() !== "snapshot") {
    return undefined;
  }

  const env = params.env ?? process.env;
  assertAdminTrackedSymbolsCanBeRepresentedExactly(env);

  return [
    resolveRuntimeSelectorRowsSourcePackage(params.workspaceRoot, env),
    ...collectTenantEnvelopeSourcePackages(params.workspaceRoot),
  ];
}
