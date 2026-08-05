import { NextResponse } from "next/server";
import { createTestUser, listUsers, removeUser, resetUserPassword, setUserActive } from "@/lib/user-store";
import { getCurrentServerUser } from "@/lib/server-auth";

type CreateBody = {
  username?: unknown;
  password?: unknown;
  role?: unknown;
  expiresInDays?: unknown;
};

type ResetBody = {
  username?: unknown;
  password?: unknown;
};

type ActivationBody = {
  username?: unknown;
  isActive?: unknown;
};

async function requireAdmin(request: Request): Promise<NextResponse | null> {
  const user = await getCurrentServerUser();
  if (!user) {
    return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  }

  if (user.role !== "admin") {
    return NextResponse.json({ error: "Admin role required." }, { status: 403 });
  }

  return null;
}

export async function GET(request: Request) {
  const denied = await requireAdmin(request);
  if (denied) return denied;

  const result = await listUsers();
  return NextResponse.json({ users: result.users, source: result.filePath });
}

export async function POST(request: Request) {
  const denied = await requireAdmin(request);
  if (denied) return denied;

  let body: CreateBody;

  try {
    body = (await request.json()) as CreateBody;
  } catch {
    return NextResponse.json({ error: "Invalid JSON body." }, { status: 400 });
  }

  try {
    const result = await createTestUser({
      username: body.username,
      password: body.password,
      role: body.role,
      expiresInDays: body.expiresInDays,
    });

    return NextResponse.json({
      created: result.created,
      users: result.users,
      source: result.filePath,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Failed to create test user.";
    const lower = message.toLowerCase();

    if (lower.includes("already exists")) {
      return NextResponse.json({ error: message }, { status: 409 });
    }

    if (
      lower.includes("required") ||
      lower.includes("password") ||
      lower.includes("username") ||
      lower.includes("chars")
    ) {
      return NextResponse.json({ error: message }, { status: 400 });
    }

    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function PUT(request: Request) {
  const denied = await requireAdmin(request);
  if (denied) return denied;

  let body: ResetBody;

  try {
    body = (await request.json()) as ResetBody;
  } catch {
    return NextResponse.json({ error: "Invalid JSON body." }, { status: 400 });
  }

  try {
    const result = await resetUserPassword({
      username: body.username,
      password: body.password,
    });

    return NextResponse.json({
      updated: result.updated,
      users: result.users,
      source: result.filePath,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Failed to reset user password.";
    const lower = message.toLowerCase();

    if (lower.includes("not found")) {
      return NextResponse.json({ error: message }, { status: 404 });
    }

    if (
      lower.includes("required") ||
      lower.includes("password") ||
      lower.includes("username") ||
      lower.includes("chars")
    ) {
      return NextResponse.json({ error: message }, { status: 400 });
    }

    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function PATCH(request: Request) {
  const denied = await requireAdmin(request);
  if (denied) return denied;

  let body: ActivationBody;

  try {
    body = (await request.json()) as ActivationBody;
  } catch {
    return NextResponse.json({ error: "Invalid JSON body." }, { status: 400 });
  }

  try {
    const result = await setUserActive({
      username: body.username,
      isActive: body.isActive,
    });

    return NextResponse.json({
      updated: result.updated,
      users: result.users,
      source: result.filePath,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Failed to update user status.";
    const lower = message.toLowerCase();

    if (lower.includes("not found")) {
      return NextResponse.json({ error: message }, { status: 404 });
    }

    if (
      lower.includes("required") ||
      lower.includes("username") ||
      lower.includes("chars") ||
      lower.includes("last active admin")
    ) {
      return NextResponse.json({ error: message }, { status: 400 });
    }

    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function DELETE(request: Request) {
  const denied = await requireAdmin(request);
  if (denied) return denied;

  const sessionUser = await getCurrentServerUser();
  if (!sessionUser) {
    return NextResponse.json({ error: "Authentication required." }, { status: 401 });
  }

  const url = new URL(request.url);
  const username = url.searchParams.get("username");

  try {
    const result = await removeUser({
      username,
      requestingUsername: sessionUser.username,
    });

    return NextResponse.json({
      removed: result.removed,
      users: result.users,
      source: result.filePath,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Failed to remove user.";
    const lower = message.toLowerCase();

    if (lower.includes("not found")) {
      return NextResponse.json({ error: message }, { status: 404 });
    }

    if (
      lower.includes("required") ||
      lower.includes("username") ||
      lower.includes("chars") ||
      lower.includes("last active admin") ||
      lower.includes("currently signed-in")
    ) {
      return NextResponse.json({ error: message }, { status: 400 });
    }

    return NextResponse.json({ error: message }, { status: 500 });
  }
}
