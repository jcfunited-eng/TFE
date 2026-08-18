import { NextResponse } from "next/server";
import { getCurrentServerUser } from "@/lib/server-auth";

export const dynamic = "force-dynamic";

/**
 * Runtime execution and fill auditing are owned by the supervised sentinel.
 * Starting detached duplicate runners from an HTTP request is not a valid
 * process-custody boundary.
 */
export async function POST() {
  const user = await getCurrentServerUser();
  if (!user) return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  if (user.role !== "admin") return NextResponse.json({ error: "Admin role required." }, { status: 403 });

  return NextResponse.json(
    {
      error: "detached_pee1_runner_disabled",
      message: "PEE-1 is continuously supervised by the runtime. Detached launches are disabled.",
    },
    { status: 409 },
  );
}
