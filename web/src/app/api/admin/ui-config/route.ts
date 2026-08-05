import { NextResponse } from "next/server";
import { UI_PAGE_KEYS, getUiConfig, setUiConfig, type UiBackgroundImages } from "@/lib/ui-config";
import { getCurrentServerUser } from "@/lib/server-auth";

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

  const config = await getUiConfig();
  return NextResponse.json(config);
}

export async function PUT(request: Request) {
  const denied = await requireAdmin(request);
  if (denied) return denied;

  let body: unknown;

  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body." }, { status: 400 });
  }

  const payload = body as {
    backgroundImages?: unknown;
    homeBackgroundImage?: unknown;
  };

  // Backward compatibility for old single field payload.
  if (typeof payload.homeBackgroundImage === "string") {
    const saved = await setUiConfig({ home: payload.homeBackgroundImage });
    return NextResponse.json(saved);
  }

  if (typeof payload.backgroundImages !== "object" || payload.backgroundImages === null) {
    return NextResponse.json({ error: "backgroundImages must be an object." }, { status: 400 });
  }

  const next: Partial<UiBackgroundImages> = {};
  const source = payload.backgroundImages as Record<string, unknown>;

  for (const key of UI_PAGE_KEYS) {
    if (key in source) {
      next[key] = source[key] as string;
    }
  }

  const saved = await setUiConfig(next);
  return NextResponse.json(saved);
}
