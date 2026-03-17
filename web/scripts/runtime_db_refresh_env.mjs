#!/usr/bin/env node

import { spawn, spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const DEFAULT_DB_PORT = 5432;
const MODULE_DIR = path.dirname(fileURLToPath(import.meta.url));
const SECRET_HELPER_PATH = path.join(MODULE_DIR, "resolve_runtime_db_secret.py");

function readOptionalEnv(env, ...names) {
  for (const name of names) {
    const value = env[name];
    if (typeof value === "string" && value.trim().length > 0) {
      return value.trim();
    }
  }
  return null;
}

function readRequiredEnv(env, ...names) {
  const value = readOptionalEnv(env, ...names);
  if (value) return value;
  throw new Error(`Missing required database env var: ${names.join(" or ")}.`);
}

function readPgPort(env) {
  const raw = String(env.PGPORT ?? env.TFE_DB_PORT ?? `${DEFAULT_DB_PORT}`).trim();
  const parsed = Number(raw);
  if (!Number.isFinite(parsed)) return DEFAULT_DB_PORT;
  const whole = Math.floor(parsed);
  if (whole < 1 || whole > 65535) return DEFAULT_DB_PORT;
  return whole;
}

function resolvePgSslRejectUnauthorized(env) {
  const raw = String(env.TFE_DB_SSL_REJECT_UNAUTHORIZED ?? "true").trim().toLowerCase();
  if (["1", "true", "yes", "on"].includes(raw)) return true;
  if (["0", "false", "no", "off"].includes(raw)) return false;
  return true;
}

function normalizeSecretArn(value) {
  const text = String(value ?? "").trim();
  if (!text) return null;
  if (text.endsWith(":password::")) return text.slice(0, -":password::".length);
  if (text.endsWith(":username::")) return text.slice(0, -":username::".length);
  return text;
}

function summarizeOutput(value, label) {
  const text = String(value ?? "").trim();
  if (!text) return null;
  if (text.length <= 1200) return `${label}=${text}`;
  return `${label}=${text.slice(0, 1200)}...[truncated ${text.length - 1200} chars]`;
}

function loadFreshSecretCredentials(env) {
  const secretArn = normalizeSecretArn(env.TFE_RUNTIME_DB_SECRET_ARN);
  if (!secretArn) return null;

  const pythonBin = String(env.TFE_PYTHON_BIN ?? "python3").trim() || "python3";
  const completed = spawnSync(
    pythonBin,
    [SECRET_HELPER_PATH, secretArn],
    {
      env,
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
      timeout: 20_000,
    },
  );

  if (completed.status !== 0) {
    const details = [
      `resolve_runtime_db_secret_failed exit_code=${completed.status ?? "null"}`,
      summarizeOutput(completed.stdout, "stdout"),
      summarizeOutput(completed.stderr, "stderr"),
    ].filter(Boolean);
    throw new Error(details.join("; "));
  }

  let parsed;
  try {
    parsed = JSON.parse(String(completed.stdout ?? ""));
  } catch (error) {
    throw new Error(
      `resolve_runtime_db_secret_invalid_json: ${
        error instanceof Error ? error.message : "unknown parse failure"
      }`,
    );
  }

  const username = parsed?.username;
  const password = parsed?.password;
  if (typeof username !== "string" || username.length === 0) {
    throw new Error("resolve_runtime_db_secret_missing_username");
  }
  if (typeof password !== "string" || password.length === 0) {
    throw new Error("resolve_runtime_db_secret_missing_password");
  }

  return { username, password, secretArn };
}

export function resolveRuntimeDbConfig(baseEnv = process.env) {
  const env = { ...baseEnv };
  const host = readRequiredEnv(env, "PGHOST", "TFE_DB_HOST");
  const database = readRequiredEnv(env, "PGDATABASE", "TFE_DB_NAME");
  const port = readPgPort(env);
  const rejectUnauthorized = resolvePgSslRejectUnauthorized(env);
  const secretCredentials = loadFreshSecretCredentials(env);

  if (secretCredentials) {
    return {
      host,
      database,
      port,
      rejectUnauthorized,
      user: secretCredentials.username,
      password: secretCredentials.password,
      credentialSource: "aws_secretsmanager",
      secretArn: secretCredentials.secretArn,
    };
  }

  return {
    host,
    database,
    port,
    rejectUnauthorized,
    user: readRequiredEnv(env, "PGUSER", "TFE_DB_USER"),
    password: readRequiredEnv(env, "PGPASSWORD", "TFE_DB_PASSWORD"),
    credentialSource: "env",
    secretArn: null,
  };
}

export function buildFreshRuntimeDbEnv(baseEnv = process.env) {
  const config = resolveRuntimeDbConfig(baseEnv);
  return {
    ...baseEnv,
    PGHOST: config.host,
    PGDATABASE: config.database,
    PGPORT: `${config.port}`,
    PGUSER: config.user,
    PGPASSWORD: config.password,
    TFE_DB_HOST: config.host,
    TFE_DB_NAME: config.database,
    TFE_DB_PORT: `${config.port}`,
    TFE_DB_USER: config.user,
    TFE_DB_PASSWORD: config.password,
  };
}

export async function runNodeScriptWithFreshRuntimeDbEnv(scriptPath, args, baseEnv = process.env) {
  const env = buildFreshRuntimeDbEnv(baseEnv);
  return await new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [scriptPath, ...args], {
      env,
      stdio: "inherit",
    });

    child.on("error", reject);
    child.on("exit", (code, signal) => {
      if (signal) {
        process.kill(process.pid, signal);
        return;
      }
      resolve(code ?? 1);
    });
  });
}
