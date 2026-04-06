import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

const isPublicRoute = createRouteMatcher(["/", "/sign-in(.*)"]);
const isAuthRoute = createRouteMatcher(["/account(.*)"]);

export default clerkMiddleware(async (auth, request) => {
  // /account sub-routes are used internally by Clerk's UserProfile component.
  // They require an active session but must not be blocked by the middleware redirect.
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
