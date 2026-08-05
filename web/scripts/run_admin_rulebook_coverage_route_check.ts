import { writeFileSync } from "node:fs";
import path from "node:path";

import { createSessionToken } from "../src/lib/auth-session";
import { GET as getRulebookCoverage } from "../src/app/api/admin/rulebook-coverage/route";
import { getUserByUsername, listUsers } from "../src/lib/user-store";

async function resolveAdminUser() {
  const direct = await getUserByUsername("admin");
  if (direct && direct.role === "admin") return direct;

  const listing = await listUsers();
  const found = listing.users.find((user) => user.role === "admin");
  if (found) return found;

  throw new Error("No admin user available for rulebook-coverage route check.");
}

async function main() {
  const root = "/workspaces/Tao_Financial_Engine";
  const outputPath = path.join(root, "admin_rulebook_coverage_route_check_latest.json");
  const adminUser = await resolveAdminUser();
  const session = await createSessionToken(adminUser);
  const request = new Request("http://localhost/api/admin/rulebook-coverage", {
    method: "GET",
    headers: {
      cookie: `tfe_session=${session.token}`,
    },
  });

  const response = await getRulebookCoverage(request);
  const payload = await response.json();

  const out = {
    generated_at_utc: new Date().toISOString(),
    status_code: response.status,
    ok: response.ok,
    admin_username: adminUser.username,
    exists: payload?.exists === true,
    analysis_name: payload?.analysis_name ?? null,
    status: payload?.status ?? null,
    cp_profile: payload?.cp_profile ?? null,
    runtime_total_rows: payload?.runtime_contexts?.eligibility_view_context?.total_snapshot_rows ?? null,
    paths: payload?.paths ?? null,
  };

  writeFileSync(outputPath, `${JSON.stringify(out, null, 2)}\n`, "utf8");
  process.stdout.write(`${JSON.stringify({ status: "ok", output_path: outputPath, status_code: response.status })}\n`);
}

main().catch((error) => {
  const message = error instanceof Error ? error.message : String(error);
  process.stderr.write(`${message}\n`);
  process.exitCode = 1;
});
