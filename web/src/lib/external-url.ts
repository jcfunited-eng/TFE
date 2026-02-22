function isSafeHostHeader(value: string): boolean {
  return /^[a-z0-9.-]+(?::\d{1,5})?$/i.test(value);
}

function normalizeProto(value: string | null): "http" | "https" {
  const raw = String(value ?? "").trim().toLowerCase();
  if (raw === "http" || raw === "https") return raw;
  return "https";
}

function parseConfiguredPublicBaseUrl(): URL | null {
  const configured = String(process.env.TFE_PUBLIC_BASE_URL ?? "").trim();
  if (!configured) return null;

  try {
    return new URL(configured);
  } catch {
    return null;
  }
}

export function resolveExternalOrigin(request: Request): URL {
  const configured = parseConfiguredPublicBaseUrl();
  if (configured) {
    return configured;
  }

  const proto = normalizeProto(request.headers.get("x-forwarded-proto"));
  const forwardedHost = String(request.headers.get("x-forwarded-host") ?? "").trim();
  const hostHeader = String(request.headers.get("host") ?? "").trim();
  const host = forwardedHost || hostHeader;

  if (host && isSafeHostHeader(host)) {
    return new URL(`${proto}://${host}`);
  }

  return new URL(request.url);
}

export function buildExternalUrl(request: Request, pathOrRelativeUrl: string): URL {
  return new URL(pathOrRelativeUrl, resolveExternalOrigin(request));
}
