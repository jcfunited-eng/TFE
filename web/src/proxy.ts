import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

const isPublicRoute = createRouteMatcher(["/", "/sign-in(.*)", "/api/health", "/api/assets(.*)"]);
const isAuthRoute = createRouteMatcher(["/account(.*)"]);
const INTERNAL_TOKEN_HEADER = "x-tfe-internal-refresh-token";

function hasInternalToken(request: Request): boolean {
  const token = request.headers.get(INTERNAL_TOKEN_HEADER);
  const expected = process.env.TFE_INTERNAL_REFRESH_TOKEN;
  return Boolean(token && expected && token === expected);
}

export default clerkMiddleware(async (auth, request) => {
  if (hasInternalToken(request)) return NextResponse.next();
  if (isAuthRoute(request)) {
    const { userId } = await auth();
    if (!userId) {
      const signInUrl = new URL("/sign-in", request.url);
      signInUrl.searchParams.set("redirect_url", request.url);
      return NextResponse.redirect(signInUrl);
    }
    return NextResponse.next();
  }
  if (!isPublicRoute(request)) {
    const { userId } = await auth();
    if (!userId) {
      const signInUrl = new URL("/sign-in", request.url);
      signInUrl.searchParams.set("redirect_url", request.url);
      return NextResponse.redirect(signInUrl);
    }
  }
});

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
