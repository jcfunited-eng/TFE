import { spawn } from "node:child_process";
import path from "node:path";
import { NextResponse } from "next/server";
import { getCurrentServerUser } from "@/lib/server-auth";
import { resolveWorkspaceRoot } from "@/lib/workspace-root";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const user = await getCurrentServerUser();
  if (!user) return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  if (user.role !== "admin") return NextResponse.json({ error: "Admin role required." }, { status: 403 });

  let body: { action?: unknown } = {};
  try { body = await request.json() as { action?: unknown }; } catch { /* empty body ok */ }

  const action = String(body.action ?? "run").trim();
  if (action !== "run") {
    return NextResponse.json({ error: `Unknown action: ${action}` }, { status: 400 });
  }

  const root = resolveWorkspaceRoot();
  const scriptPath = path.resolve(root, "web/scripts/execution/pee1_runner.mjs");

  // Inherit all process env (DB creds, Alpaca keys already in ECS task definition)
  const child = spawn(
    process.env.TFE_NODE_BIN ?? "node",
    ["--env-file-if-exists=/dev/null", scriptPath],
    {
      env: {
        ...process.env,
        PGSSLMODE: "require",
      },
      detached: true,
      stdio: "ignore",
    }
  );

  const pid = child.pid ?? null;
  child.unref();

  console.log(`[PEE1-API] Runner launched | pid=${pid} | by=${user.username}`);

  return NextResponse.json({
    ok: true,
    pid,
    launched_at: new Date().toISOString(),
    launched_by: user.username,
    message: "PEE-1 runner launched. Check the trade auditor for results in ~30 seconds.",
  });
}
