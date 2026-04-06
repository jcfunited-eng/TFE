import { auth, currentUser } from "@clerk/nextjs/server";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { readSessionUserFromToken, sanitizeNextPath, SESSION_COOKIE_NAME } from "@/lib/auth-session";
import type { UserRole, UserSummary } from "@/lib/user-store";

// ---------------------------------------------------------------------------
// Clerk → UserSummary bridge
//
// Reads the Clerk session and maps it to the UserSummary shape used throughout
// the app. Role and test-user flag are read from Clerk publicMetadata so they
// can be set per-user in the Clerk dashboard without a code deploy.
// ---------------------------------------------------------------------------

async function getUserSummaryFromClerk(): Promise<UserSummary | null> {
  const { userId } = await auth();
  if (!userId) return null;

  const user = await currentUser();
  if (!user) return null;

  const meta = (user.publicMetadata ?? {}) as {
    role?: unknown;
    is_test_user?: unknown;
    access_expires_at?: unknown;
  };

  const role: UserRole = meta.role === "admin" ? "admin" : "member";
  const isTestUser = meta.is_test_user === true;
  const accessExpiresAt =
    typeof meta.access_expires_at === "string" ? meta.access_expires_at : null;

  const username =
    user.username ??
    user.primaryEmailAddress?.emailAddress ??
    userId;

  const createdAt = user.createdAt
    ? new Date(user.createdAt).toISOString()
    : new Date().toISOString();

  return {
    username,
    role,
    is_active: true,
    is_test_user: isTestUser,
    access_expires_at: accessExpiresAt,
    created_at: createdAt,
  };
}

// ---------------------------------------------------------------------------
// Public API — unchanged signatures, Clerk-first with legacy cookie fallback
// ---------------------------------------------------------------------------

export async function getCurrentServerUser(): Promise<UserSummary | null> {
  const clerkUser = await getUserSummaryFromClerk();
  if (clerkUser) return clerkUser;

  // Legacy TFE session cookie — used when Clerk is not active for a request.
  const cookieStore = await cookies();
  const token = cookieStore.get(SESSION_COOKIE_NAME)?.value;
  if (!token) return null;
  return readSessionUserFromToken(token);
}

export async function requireServerUser(currentPath: string): Promise<UserSummary> {
  const user = await getCurrentServerUser();
  if (user) return user;

  const safeNext = sanitizeNextPath(currentPath);
  redirect(`/sign-in?next=${encodeURIComponent(safeNext)}`);
}

export async function requireServerAdminUser(currentPath: string): Promise<UserSummary> {
  const user = await requireServerUser(currentPath);
  if (user.role === "admin") return user;

  redirect("/account?error=admin_required");
}
