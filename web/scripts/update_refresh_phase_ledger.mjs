#!/usr/bin/env node

import path from "node:path";
import { fileURLToPath } from "node:url";

import { runNodeScriptWithFreshRuntimeDbEnv } from "./runtime_db_refresh_env.mjs";

const MODULE_DIR = path.dirname(fileURLToPath(import.meta.url));
const IMPL_PATH = path.join(MODULE_DIR, "update_refresh_phase_ledger_impl.mjs");

try {
  const exitCode = await runNodeScriptWithFreshRuntimeDbEnv(IMPL_PATH, process.argv.slice(2), process.env);
  process.exit(exitCode);
} catch (error) {
  console.error(String(error instanceof Error ? error.stack || error.message : error));
  process.exit(1);
}
