import { NextResponse } from "next/server";
import { getCurrentClerkUser } from "@/lib/server-auth";
import {
  operatorObservationErrorResponse,
  readOperatorObservation,
} from "@/lib/operator-observation-contract";

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

export async function GET(): Promise<NextResponse> {
  const user = await getCurrentClerkUser();
  if (!user) {
    return jsonNoStore(
      {
        schema: "tfe.guala.operator_observation.error.v1",
        error: "clerk_authentication_required",
      },
      401,
    );
  }
  if (user.role !== "admin") {
    return jsonNoStore(
      {
        schema: "tfe.guala.operator_observation.error.v1",
        error: "clerk_admin_required",
      },
      403,
    );
  }
  try {
    return jsonNoStore(await readOperatorObservation(), 200);
  } catch (error) {
    const failure = operatorObservationErrorResponse(error);
    return jsonNoStore(failure.body, failure.status);
  }
}
