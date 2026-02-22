import { NextResponse } from "next/server";
import { readSessionUserFromRequest } from "@/lib/auth-session";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function noStoreJson(body: unknown, init?: ResponseInit): NextResponse {
  const response = NextResponse.json(body, init);
  response.headers.set("Cache-Control", "no-store, max-age=0");
  return response;
}

export async function GET(request: Request) {
  const user = await readSessionUserFromRequest(request);

  if (!user) {
    return noStoreJson({ error: "not_authenticated" }, { status: 401 });
  }

  return noStoreJson({
    authenticated: true,
    user: {
      username: user.username,
      role: user.role,
      is_test_user: user.is_test_user,
      access_expires_at: user.access_expires_at,
    },
  });
}
