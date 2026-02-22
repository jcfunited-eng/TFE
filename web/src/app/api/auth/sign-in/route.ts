import { NextResponse } from "next/server";
import { authenticateUser } from "@/lib/user-store";
import { createSessionToken, sanitizeNextPath, setSessionCookie } from "@/lib/auth-session";
import { buildExternalUrl } from "@/lib/external-url";
import { isAdminMfaEnabled, verifyAdminTotpCode } from "@/lib/mfa";

type CredentialsInput = {
  username: string;
  password: string;
  mfaCode: string;
  nextPath: string;
  mode: "json" | "form";
};

function resolveFailureResponse(request: Request, nextPath: string, mode: "json" | "form", errorCode: string): NextResponse {
  if (mode === "json") {
    return NextResponse.json({ error: errorCode }, { status: 401 });
  }

  const redirectUrl = buildExternalUrl(request, "/sign-in");
  redirectUrl.searchParams.set("next", sanitizeNextPath(nextPath));
  redirectUrl.searchParams.set("error", errorCode);
  return NextResponse.redirect(redirectUrl);
}

async function parseCredentials(request: Request): Promise<CredentialsInput | null> {
  const contentType = String(request.headers.get("content-type") ?? "").toLowerCase();

  if (contentType.includes("application/json")) {
    try {
      const body = (await request.json()) as {
        username?: unknown;
        password?: unknown;
        mfaCode?: unknown;
        next?: unknown;
      };

      const username = String(body.username ?? "").trim();
      const password = String(body.password ?? "");
      const mfaCode = String(body.mfaCode ?? "").trim();
      const nextPath = sanitizeNextPath(body.next);

      return {
        username,
        password,
        mfaCode,
        nextPath,
        mode: "json",
      };
    } catch {
      return null;
    }
  }

  try {
    const form = await request.formData();
    const username = String(form.get("username") ?? "").trim();
    const password = String(form.get("password") ?? "");
    const mfaCode = String(form.get("mfaCode") ?? "").trim();
    const nextPath = sanitizeNextPath(form.get("next"));

    return {
      username,
      password,
      mfaCode,
      nextPath,
      mode: "form",
    };
  } catch {
    return null;
  }
}

export async function POST(request: Request) {
  const parsed = await parseCredentials(request);

  if (!parsed) {
    return NextResponse.json({ error: "invalid_request" }, { status: 400 });
  }

  const { username, password, mfaCode, nextPath, mode } = parsed;

  if (!username || !password) {
    return resolveFailureResponse(request, nextPath, mode, "missing_credentials");
  }

  const user = await authenticateUser({ username, password });

  if (!user) {
    return resolveFailureResponse(request, nextPath, mode, "invalid_credentials");
  }

  const requiresAdminMfa = user.role === "admin" && isAdminMfaEnabled();
  if (requiresAdminMfa && !mfaCode) {
    return resolveFailureResponse(request, nextPath, mode, "mfa_required");
  }

  if (requiresAdminMfa && !verifyAdminTotpCode(mfaCode)) {
    return resolveFailureResponse(request, nextPath, mode, "invalid_mfa");
  }

  const session = await createSessionToken(user);

  if (mode === "json") {
    const response = NextResponse.json({
      signedIn: true,
      user: {
        username: user.username,
        role: user.role,
        is_test_user: user.is_test_user,
      },
      next: nextPath,
    });
    setSessionCookie(response, session.token, session.expiresAtEpochSeconds);
    return response;
  }

  const response = NextResponse.redirect(buildExternalUrl(request, nextPath));
  setSessionCookie(response, session.token, session.expiresAtEpochSeconds);
  return response;
}
