import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";
import { buildExternalUrl } from "@/lib/external-url";

const isPublicRoute = createRouteMatcher(["/", "/sign-in(.*)"]);
const isAuthRoute = createRouteMatcher(["/account(.*)"]);

const INTERNAL_TOKEN_HEADER = "x-tfe-internal-refresh-token";

function hasInternalToken(request: Request): boolean {
  const token = request.headers.get(INTERNAL_TOKEN_HEADER);
  const expected = process.env.TFE_INTERNAL_REFRESH_TOKEN;
  if (!token || !expected) return false;
  return token === expected;
}

function requestedExternalUrl(request: Request): URL {
  const incoming = new URL(request.url);
  return buildExternalUrl(
    request,
    `${incoming.pathname}${incoming.search}`,
  );
}

function signInRedirect(request: Request): NextResponse {
  const signInUrl = buildExternalUrl(request, "/sign-in");
  signInUrl.searchParams.set(
    "redirect_url",
    requestedExternalUrl(request).toString(),
  );
  return NextResponse.redirect(signInUrl);
}

export default clerkMiddleware(async (auth, request) => {
  if (hasInternalToken(request)) {
    return NextResponse.next();
  }

  if (isAuthRoute(request)) {
    const { userId } = await auth();
    if (!userId) return signInRedirect(request);
    return NextResponse.next();
  }

  if (!isPublicRoute(request)) {
    const { userId } = await auth();
    if (!userId) return signInRedirect(request);
  }
});

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
