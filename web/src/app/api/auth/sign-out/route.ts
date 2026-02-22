import { NextResponse } from "next/server";
import { clearSessionCookie } from "@/lib/auth-session";
import { buildExternalUrl } from "@/lib/external-url";

function sanitizeSignOutNextPath(value: string | null | undefined): string {
  const raw = String(value ?? "").trim();

  if (!raw) return "/sign-in";
  if (raw === "/sign-in") return "/sign-in";
  if (!raw.startsWith("/")) return "/account";
  if (raw.startsWith("//")) return "/account";
  if (raw.startsWith("/api")) return "/account";
  if (raw.startsWith("/_next")) return "/account";

  return raw;
}

function buildRedirectResponse(request: Request, nextValue: string | null | undefined): NextResponse {
  const redirectPath = sanitizeSignOutNextPath(nextValue);
  const target = buildExternalUrl(request, redirectPath);
  const response = NextResponse.redirect(target);
  clearSessionCookie(response);
  return response;
}

export async function GET(request: Request) {
  const url = new URL(request.url);
  return buildRedirectResponse(request, url.searchParams.get("next"));
}

export async function POST(request: Request) {
  const url = new URL(request.url);

  let nextValue: string | null = url.searchParams.get("next");

  if (!nextValue) {
    const contentType = String(request.headers.get("content-type") ?? "").toLowerCase();
    if (!contentType.includes("application/json")) {
      try {
        const form = await request.formData();
        nextValue = String(form.get("next") ?? "");
      } catch {
        nextValue = null;
      }
    }
  }

  if (String(request.headers.get("content-type") ?? "").toLowerCase().includes("application/json")) {
    const response = NextResponse.json({ signedOut: true });
    clearSessionCookie(response);
    return response;
  }

  return buildRedirectResponse(request, nextValue);
}
