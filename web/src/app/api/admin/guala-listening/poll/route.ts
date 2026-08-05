import { NextResponse } from "next/server";
import { getCurrentClerkUser } from "@/lib/server-auth";
import {
  operatorErrorResponse,
  parsePollBrowserRequest,
  pollOperatorListening,
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
    const taskId = await parsePollBrowserRequest(request);
    return jsonNoStore(await pollOperatorListening(taskId), 200);
  } catch (error) {
    const failure = operatorErrorResponse(error);
    return jsonNoStore(failure.body, failure.status);
  }
}
