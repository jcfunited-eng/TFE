import { writeFileSync } from "node:fs";
import path from "node:path";

import { createSessionToken } from "../src/lib/auth-session";
import { getUserByUsername, listUsers } from "../src/lib/user-store";
import { GET as getExactPathAlignment } from "../src/app/api/admin/exact-path-alignment/route";

async function resolveAdminUser() {
  const direct = await getUserByUsername("admin");
  if (direct && direct.role === "admin") return direct;

  const listing = await listUsers();
  const found = listing.users.find((user) => user.role === "admin");
  if (found) return found;

  throw new Error("No admin user available for exact-path-alignment route check.");
}

async function main() {
  const root = "/workspaces/Tao_Financial_Engine";
  const outputPath = path.join(root, "exact_path_alignment_admin_route_check_latest.json");
  const adminUser = await resolveAdminUser();
  const session = await createSessionToken(adminUser);
  const request = new Request("http://localhost/api/admin/exact-path-alignment", {
    method: "GET",
    headers: {
      cookie: `tfe_session=${session.token}`,
    },
  });

  const response = await getExactPathAlignment(request);
  const payload = await response.json();

  const out = {
    generated_at_utc: new Date().toISOString(),
    status_code: response.status,
    ok: response.ok,
    admin_username: adminUser.username,
    exists: payload?.exists === true,
    phase1_pass: payload?.phase1?.pass ?? null,
    phase2_ready: payload?.phase2?.ready ?? null,
    phase3_ready: payload?.phase3?.ready ?? null,
    phase3_executed: payload?.phase3?.executed ?? null,
    recommendation: payload?.recommendation ?? null,
    payload,
  };

  writeFileSync(outputPath, `${JSON.stringify(out, null, 2)}\n`, "utf8");
  process.stdout.write(`${JSON.stringify({ status: "ok", output_path: outputPath, status_code: response.status })}\n`);
}

main().catch((error) => {
  const message = error instanceof Error ? error.message : String(error);
  process.stderr.write(`${message}\n`);
  process.exitCode = 1;
});
