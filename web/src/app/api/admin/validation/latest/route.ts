import { readFile } from "node:fs/promises";
import path from "node:path";
import { NextResponse } from "next/server";

import { readSessionUserFromRequest } from "@/lib/auth-session";
import { resolveWorkspaceRoot } from "@/lib/workspace-root";

const ROOT_DIR = resolveWorkspaceRoot();
const VALIDATION_REPORT_PATH = path.join(ROOT_DIR, "validation-report-v1.json");

type ValidationCheck = {
  name?: string;
  status?: string;
  details?: unknown;
};

type ValidationReport = {
  status?: string;
  generated_at_utc?: string;
  run_id?: string | null;
  checks?: ValidationCheck[];
  blocking_reason?: string | null;
};

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

function normalizeReport(value: unknown): ValidationReport | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as ValidationReport;
}

export async function GET(request: Request) {
  const denied = await requireAdmin(request);
  if (denied) return denied;

  try {
    const raw = await readFile(VALIDATION_REPORT_PATH, "utf-8");
    const parsed = JSON.parse(raw) as unknown;
    const report = normalizeReport(parsed);
    if (!report) {
      return NextResponse.json(
        {
          exists: false,
          path: VALIDATION_REPORT_PATH,
          error: "validation-report-v1.json exists but has invalid JSON shape.",
        },
        { status: 500 },
      );
    }

    return NextResponse.json({
      exists: true,
      path: VALIDATION_REPORT_PATH,
      report,
    });
  } catch {
    return NextResponse.json({
      exists: false,
      path: VALIDATION_REPORT_PATH,
      report: null,
    });
  }
}
