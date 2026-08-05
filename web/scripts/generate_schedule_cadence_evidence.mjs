#!/usr/bin/env node

import path from "node:path";
import { existsSync } from "node:fs";
import { Pool } from "pg";

const DEFAULT_DB_PORT = 5432;
const DEFAULT_LOOKBACK_DAYS = 14;
const DEFAULT_TIMEZONE = "America/New_York";
const DEFAULT_DAILY_TARGET = "19:30";
const DEFAULT_WEEKLY_TARGET = "23:00";
const DEFAULT_DAILY_TOLERANCE_MINUTES = 75;
const DEFAULT_WEEKLY_TOLERANCE_MINUTES = 90;
const DEFAULT_WEEKLY_DAY = "Sunday";
const DEFAULT_MIN_DAILY_MATCHES = 1;
const DEFAULT_MIN_WEEKLY_MATCHES = 1;

function resolveWorkspaceRoot() {
  const configured = String(process.env.TFE_WORKSPACE_ROOT ?? "").trim();
  const candidates = [
    configured,
    process.cwd(),
    path.resolve(process.cwd(), ".."),
    path.resolve(process.cwd(), "../.."),
    "/workspaces/Tao_Financial_Engine",
  ]
    .map((value) => String(value || "").trim())
    .filter(Boolean)
    .map((value) => path.resolve(value));

  for (const candidate of candidates) {
    if (existsSync(path.join(candidate, "run_refresh_with_l5_learning.py"))) {
      return candidate;
    }
  }
  return path.resolve(process.cwd(), "..");
}

function isoNow() {
  return new Date().toISOString();
}

function readRequiredEnv(...names) {
  for (const name of names) {
    const value = String(process.env[name] ?? "").trim();
    if (value) return value;
  }
  throw new Error(`Missing required database env var: ${names.join(" or ")}.`);
}

function readPgPort() {
  const raw = String(process.env.PGPORT ?? process.env.TFE_DB_PORT ?? `${DEFAULT_DB_PORT}`).trim();
  const n = Number(raw);
  if (!Number.isFinite(n)) return DEFAULT_DB_PORT;
  const whole = Math.floor(n);
  if (whole < 1 || whole > 65535) return DEFAULT_DB_PORT;
  return whole;
}

function readBooleanEnv(name, fallback) {
  const raw = String(process.env[name] ?? "").trim().toLowerCase();
  if (!raw) return fallback;
  if (["1", "true", "yes", "on"].includes(raw)) return true;
  if (["0", "false", "no", "off"].includes(raw)) return false;
  return fallback;
}

function readPositiveIntEnv(name, fallback) {
  const raw = String(process.env[name] ?? "").trim();
  if (!raw) return fallback;
  const n = Number(raw);
  if (!Number.isFinite(n)) return fallback;
  const whole = Math.floor(n);
  if (whole <= 0) return fallback;
  return whole;
}

function readPgSslRejectUnauthorized() {
  return readBooleanEnv("TFE_DB_SSL_REJECT_UNAUTHORIZED", true);
}

function resolvePool() {
  const host = readRequiredEnv("PGHOST", "TFE_DB_HOST");
  const database = readRequiredEnv("PGDATABASE", "TFE_DB_NAME");
  const user = readRequiredEnv("PGUSER", "TFE_DB_USER");
  const password = readRequiredEnv("PGPASSWORD", "TFE_DB_PASSWORD");
  const port = readPgPort();
  const rejectUnauthorized = readPgSslRejectUnauthorized();

  return new Pool({
    host,
    database,
    user,
    password,
    port,
    max: 2,
    idleTimeoutMillis: 30_000,
    connectionTimeoutMillis: 8_000,
    ssl: { rejectUnauthorized },
    application_name: "tfe-schedule-cadence-evidence",
  });
}

function parseTargetTime(text, fallback) {
  const raw = String(text ?? "").trim();
  const source = raw || fallback;
  const m = source.match(/^(\d{1,2}):(\d{2})$/);
  if (!m) {
    throw new Error(`Invalid target time format '${source}'. Expected HH:MM.`);
  }
  const hour = Number(m[1]);
  const minute = Number(m[2]);
  if (!Number.isFinite(hour) || !Number.isFinite(minute) || hour < 0 || hour > 23 || minute < 0 || minute > 59) {
    throw new Error(`Invalid target time '${source}'.`);
  }
  return {
    label: `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`,
    minutes: (hour * 60) + minute,
  };
}

function minutesCircularDiff(a, b) {
  const diff = Math.abs(a - b);
  return Math.min(diff, 1440 - diff);
}

function buildLocalClockExtractor(timezone) {
  const dtf = new Intl.DateTimeFormat("en-US", {
    timeZone: timezone,
    weekday: "long",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });

  return (date) => {
    const parts = dtf.formatToParts(date);
    const byType = Object.create(null);
    for (const part of parts) {
      if (!byType[part.type]) byType[part.type] = part.value;
    }
    const year = String(byType.year ?? "").trim();
    const month = String(byType.month ?? "").trim();
    const day = String(byType.day ?? "").trim();
    const hour = Number(String(byType.hour ?? "0").trim());
    const minute = Number(String(byType.minute ?? "0").trim());
    const second = Number(String(byType.second ?? "0").trim());
    const weekday = String(byType.weekday ?? "").trim();

    return {
      weekday,
      date_local: `${year}-${month}-${day}`,
      time_local: `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}:${String(second).padStart(2, "0")}`,
      minute_of_day: (hour * 60) + minute,
    };
  };
}

function normalizeText(value) {
  return String(value ?? "").trim();
}

function normalizeLower(value) {
  return normalizeText(value).toLowerCase();
}

function isTerminalGoodStatus(reportStatus) {
  const s = normalizeLower(reportStatus);
  return s === "ok" || s === "no_rows_written";
}

function summarizeRows(rows, maxRows = 60) {
  if (rows.length <= maxRows) return rows;
  return rows.slice(0, maxRows);
}

async function main() {
  const root = resolveWorkspaceRoot();
  const timezone = normalizeText(process.env.TFE_CADENCE_TIMEZONE) || DEFAULT_TIMEZONE;
  const lookbackDays = readPositiveIntEnv("TFE_CADENCE_LOOKBACK_DAYS", DEFAULT_LOOKBACK_DAYS);
  const dailyToleranceMinutes = readPositiveIntEnv("TFE_CADENCE_DAILY_TOLERANCE_MINUTES", DEFAULT_DAILY_TOLERANCE_MINUTES);
  const weeklyToleranceMinutes = readPositiveIntEnv("TFE_CADENCE_WEEKLY_TOLERANCE_MINUTES", DEFAULT_WEEKLY_TOLERANCE_MINUTES);
  const minDailyMatches = readPositiveIntEnv("TFE_CADENCE_MIN_DAILY_MATCHES", DEFAULT_MIN_DAILY_MATCHES);
  const minWeeklyMatches = readPositiveIntEnv("TFE_CADENCE_MIN_WEEKLY_MATCHES", DEFAULT_MIN_WEEKLY_MATCHES);
  const weeklyDay = normalizeText(process.env.TFE_CADENCE_WEEKLY_DAY) || DEFAULT_WEEKLY_DAY;
  const dailyTarget = parseTargetTime(process.env.TFE_CADENCE_DAILY_TARGET_LOCAL_HHMM, DEFAULT_DAILY_TARGET);
  const weeklyTarget = parseTargetTime(process.env.TFE_CADENCE_WEEKLY_TARGET_LOCAL_HHMM, DEFAULT_WEEKLY_TARGET);

  const pool = resolvePool();
  const client = await pool.connect();

  try {
    const queryResult = await client.query(
      `
        SELECT
          run_id,
          mode,
          trigger_source,
          requested_by,
          completed_at,
          report_status,
          optimizer_short_cycle,
          optimizer_target_met,
          epoch_library_status,
          epoch_library_confidence_schema
        FROM runtime_refresh_runs
        WHERE completed_at >= (NOW() - ($1::text || ' days')::interval)
        ORDER BY completed_at DESC NULLS LAST
      `,
      [String(lookbackDays)],
    );

    const localClock = buildLocalClockExtractor(timezone);
    const rows = [];
    for (const raw of queryResult.rows) {
      const completedAt = raw.completed_at ? new Date(raw.completed_at) : null;
      if (!(completedAt instanceof Date) || Number.isNaN(completedAt.getTime())) continue;

      const local = localClock(completedAt);
      const row = {
        run_id: normalizeText(raw.run_id),
        mode: normalizeText(raw.mode),
        trigger_source: normalizeText(raw.trigger_source),
        requested_by: normalizeText(raw.requested_by),
        report_status: normalizeText(raw.report_status),
        completed_at_utc: completedAt.toISOString(),
        completed_local_date: local.date_local,
        completed_local_time: local.time_local,
        completed_local_weekday: local.weekday,
        optimizer_short_cycle: normalizeText(raw.optimizer_short_cycle),
        optimizer_target_met: raw.optimizer_target_met === null ? null : Boolean(raw.optimizer_target_met),
        epoch_library_status: normalizeText(raw.epoch_library_status),
        epoch_library_confidence_schema: normalizeText(raw.epoch_library_confidence_schema),
      };
      rows.push({ ...row, _minute_of_day: local.minute_of_day });
    }

    const scheduledRows = rows.filter((row) => normalizeLower(row.trigger_source) === "scheduled");
    const scheduledSnapshotRows = scheduledRows.filter((row) => normalizeLower(row.mode) === "snapshot");
    const scheduledUniverseRows = scheduledRows.filter((row) => normalizeLower(row.mode) === "universe_snapshot");

    const dailyMatches = [];
    for (const row of scheduledSnapshotRows) {
      if (!isTerminalGoodStatus(row.report_status)) continue;
      const diff = minutesCircularDiff(row._minute_of_day, dailyTarget.minutes);
      if (diff > dailyToleranceMinutes) continue;
      dailyMatches.push({
        ...row,
        local_target_hhmm: dailyTarget.label,
        local_diff_minutes: diff,
      });
    }

    const weeklyMatches = [];
    for (const row of scheduledUniverseRows) {
      if (!isTerminalGoodStatus(row.report_status)) continue;
      if (normalizeLower(row.completed_local_weekday) !== normalizeLower(weeklyDay)) continue;
      const diff = minutesCircularDiff(row._minute_of_day, weeklyTarget.minutes);
      if (diff > weeklyToleranceMinutes) continue;
      weeklyMatches.push({
        ...row,
        local_target_hhmm: weeklyTarget.label,
        local_diff_minutes: diff,
      });
    }

    const uniqueDailyDates = new Set(dailyMatches.map((row) => row.completed_local_date));
    const dailyPass = uniqueDailyDates.size >= minDailyMatches;
    const weeklyPass = weeklyMatches.length >= minWeeklyMatches;
    const pass = dailyPass && weeklyPass;

    const recentRows = summarizeRows(
      scheduledRows.map(({ _minute_of_day, ...rest }) => rest),
      50,
    );

    const payload = {
      status: pass ? "pass" : "fail",
      generated_at_utc: isoNow(),
      workspace_root: root,
      policy: {
        timezone,
        lookback_days: lookbackDays,
        daily_target_local_hhmm: dailyTarget.label,
        daily_tolerance_minutes: dailyToleranceMinutes,
        weekly_day_local: weeklyDay,
        weekly_target_local_hhmm: weeklyTarget.label,
        weekly_tolerance_minutes: weeklyToleranceMinutes,
        min_daily_matches: minDailyMatches,
        min_weekly_matches: minWeeklyMatches,
      },
      observed: {
        scheduled_rows_total: scheduledRows.length,
        scheduled_snapshot_rows: scheduledSnapshotRows.length,
        scheduled_universe_snapshot_rows: scheduledUniverseRows.length,
        daily_matches: dailyMatches.length,
        daily_match_dates: Array.from(uniqueDailyDates).sort(),
        weekly_matches: weeklyMatches.length,
      },
      checks: [
        {
          name: "daily_schedule_window",
          status: dailyPass ? "pass" : "fail",
          details: {
            required_unique_dates: minDailyMatches,
            observed_unique_dates: uniqueDailyDates.size,
            sample_matches: summarizeRows(dailyMatches.map(({ _minute_of_day, ...rest }) => rest), 20),
          },
        },
        {
          name: "weekly_schedule_window",
          status: weeklyPass ? "pass" : "fail",
          details: {
            required_matches: minWeeklyMatches,
            observed_matches: weeklyMatches.length,
            sample_matches: summarizeRows(weeklyMatches.map(({ _minute_of_day, ...rest }) => rest), 20),
          },
        },
      ],
      scheduled_recent_rows: recentRows,
      blocking_reason: pass ? null : (!dailyPass ? "daily_schedule_window_missing" : "weekly_schedule_window_missing"),
    };

    process.stdout.write(`${JSON.stringify(payload)}\n`);

    if (!pass) {
      process.exit(1);
    }
  } finally {
    client.release();
    await pool.end();
  }
}

main().catch((error) => {
  const payload = {
    status: "fail",
    generated_at_utc: isoNow(),
    checks: [],
    blocking_reason: error instanceof Error ? error.message : "schedule_cadence_unhandled_error",
  };
  process.stdout.write(`${JSON.stringify(payload)}\n`);
  process.exit(1);
});
