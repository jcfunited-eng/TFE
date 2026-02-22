import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { readSessionUserFromToken, sanitizeNextPath, SESSION_COOKIE_NAME } from "@/lib/auth-session";
import type { UserSummary } from "@/lib/user-store";

export async function getCurrentServerUser(): Promise<UserSummary | null> {
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
