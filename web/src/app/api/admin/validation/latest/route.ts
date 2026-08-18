import { NextResponse } from "next/server";

import { getCurrentServerUser } from "@/lib/server-auth";
import { resolveRuntimePostgresPool } from "@/lib/runtime-db";
import { reconcileValidationReport } from "@/lib/validation-report-truth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

async function requireAdmin(): Promise<NextResponse | null> {
  const user = await getCurrentServerUser();
  if (!user) return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  if (user.role !== "admin") return NextResponse.json({ error: "Admin role required." }, { status: 403 });
  return null;
}

export async function GET() {
  const denied = await requireAdmin();
  if (denied) return denied;

  try {
    const pool = resolveRuntimePostgresPool();
    const table = await pool.query<{ table_name: string | null }>(
      "SELECT to_regclass('public.runtime_validation_reports')::text AS table_name",
    );
    if (!table.rows[0]?.table_name) {
      return NextResponse.json({ exists: false, source: "postgres", report: null });
    }

    const latest = await pool.query<{ report_json: unknown }>(
      `SELECT report_json
       FROM runtime_validation_reports
       ORDER BY generated_at_utc DESC, created_at DESC
       LIMIT 1`,
    );
    if (latest.rows.length === 0) {
      return NextResponse.json({ exists: false, source: "postgres", report: null });
    }

    const report = reconcileValidationReport(latest.rows[0].report_json);
    if (!report) {
      return NextResponse.json(
        { exists: false, source: "postgres", report: null, error: "Latest validation report has an invalid shape." },
        { status: 500 },
      );
    }

    return NextResponse.json(
      { exists: true, source: "postgres", report },
      { headers: { "Cache-Control": "no-store" } },
    );
  } catch (error) {
    return NextResponse.json(
      {
        exists: false,
        source: "postgres",
        report: null,
        error: error instanceof Error ? error.message : "Validation history query failed.",
      },
      { status: 503 },
    );
  }
}
