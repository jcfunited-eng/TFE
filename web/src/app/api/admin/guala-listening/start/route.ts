import { NextResponse } from "next/server";
import { getCurrentClerkUser } from "@/lib/server-auth";
import {
  operatorErrorResponse,
  parseStartBrowserRequest,
  startOperatorListening,
} from "@/lib/operator-listening-contract";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function jsonNoStore(body: unknown, status: number): NextResponse {
  return NextResponse.json(body, {
    status,
    headers: {
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
    },
  });
}

export async function POST(request: Request): Promise<NextResponse> {
  const user = await getCurrentClerkUser();
  if (!user) {
    return jsonNoStore(
      {
        schema: "tfe.guala.operator_listening.error.v1",
        error: "clerk_authentication_required",
      },
      401,
    );
  }
  if (user.role !== "admin") {
    return jsonNoStore(
      {
        schema: "tfe.guala.operator_listening.error.v1",
        error: "clerk_admin_required",
      },
      403,
    );
  }

  try {
    const action = await parseStartBrowserRequest(request);
    return jsonNoStore(await startOperatorListening(action), 202);
  } catch (error) {
    const failure = operatorErrorResponse(error);
    return jsonNoStore(failure.body, failure.status);
  }
}
