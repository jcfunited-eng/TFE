import { readFile, stat } from "node:fs/promises";
import path from "node:path";
import { NextResponse } from "next/server";

import { getCurrentServerUser } from "@/lib/server-auth";
import { resolveWorkspaceRoot } from "@/lib/workspace-root";

const ROOT_DIR = resolveWorkspaceRoot();
const ARTIFACT_JSON_PATH = path.join(ROOT_DIR, "admin_rulebook_coverage_latest.json");
const ARTIFACT_MD_PATH = path.join(ROOT_DIR, "admin_rulebook_coverage_latest.md");

async function pathExists(filePath: string): Promise<boolean> {
  try {
    await stat(filePath);
    return true;
  } catch {
    return false;
  }
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

  try {
    const exists = await pathExists(ARTIFACT_JSON_PATH);
    if (!exists) {
      return NextResponse.json({
        exists: false,
        generated_at_utc: null,
        status: null,
        cp_profile: null,
        paths: {
          json: null,
          markdown: null,
        },
      });
    }

    const raw = await readFile(ARTIFACT_JSON_PATH, "utf-8");
    const payload = JSON.parse(raw) as Record<string, unknown>;
    const markdownExists = await pathExists(ARTIFACT_MD_PATH);

    return NextResponse.json({
      exists: true,
      ...payload,
      paths: {
        json: ARTIFACT_JSON_PATH,
        markdown: markdownExists ? ARTIFACT_MD_PATH : null,
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Failed to load admin rulebook coverage artifact.";
    return NextResponse.json(
      {
        exists: false,
        generated_at_utc: null,
        status: null,
        cp_profile: null,
        paths: {
          json: null,
          markdown: null,
        },
        error: message,
      },
      { status: 500 },
    );
  }
}
