import { readFile, stat } from "node:fs/promises";
import path from "node:path";
import { NextResponse } from "next/server";
import { readSessionUserFromRequest } from "@/lib/auth-session";

const ROOT_DIR = path.resolve(process.cwd(), "..");
const LOG_PATH = path.join(ROOT_DIR, "admin_refresh_latest.log");
const DEFAULT_LINES = 120;
const MIN_LINES = 20;
const MAX_LINES = 500;

function normalizeLineCount(value: string | null): number {
  const n = Number(value);
  if (!Number.isFinite(n)) return DEFAULT_LINES;
  const whole = Math.floor(n);
  if (whole < MIN_LINES) return MIN_LINES;
  if (whole > MAX_LINES) return MAX_LINES;
  return whole;
}

function tailLines(text: string, count: number): string[] {
  const lines = text.split(/\r?\n/).filter((line) => line.trim().length > 0);
  if (lines.length <= count) return lines;
  return lines.slice(lines.length - count);
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

export async function GET(request: Request) {
  const denied = await requireAdmin(request);
  if (denied) return denied;

  const url = new URL(request.url);
  const linesRequested = normalizeLineCount(url.searchParams.get("lines"));

  try {
    const [raw, logStat] = await Promise.all([readFile(LOG_PATH, "utf-8"), stat(LOG_PATH)]);
    const lines = tailLines(raw, linesRequested);

    return NextResponse.json({
      exists: true,
      path: LOG_PATH,
      linesRequested,
      lineCount: lines.length,
      updatedAtUtc: logStat.mtime.toISOString(),
      lines,
    });
  } catch {
    return NextResponse.json({
      exists: false,
      path: LOG_PATH,
      linesRequested,
      lineCount: 0,
      updatedAtUtc: null,
      lines: [],
    });
  }
}
