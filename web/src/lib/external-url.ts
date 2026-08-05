const PUBLIC_BASE_ENV = "TFE_PUBLIC_BASE_URL";

function parseRequiredConfiguredPublicBaseUrl(): URL {
  const configured = String(process.env[PUBLIC_BASE_ENV] ?? "").trim();
  if (!configured) {
    throw new Error(`${PUBLIC_BASE_ENV} is required`);
  }

  let parsed: URL;
  try {
    parsed = new URL(configured);
  } catch {
    throw new Error(`${PUBLIC_BASE_ENV} must be an absolute URL`);
  }

  if (parsed.protocol !== "https:") {
    throw new Error(`${PUBLIC_BASE_ENV} must use https`);
  }
  if (
    parsed.username ||
    parsed.password ||
    parsed.search ||
    parsed.hash ||
    (parsed.pathname !== "" && parsed.pathname !== "/")
  ) {
    throw new Error(`${PUBLIC_BASE_ENV} must contain only an https origin`);
  }
  if (
    parsed.hostname === "0.0.0.0" ||
    parsed.hostname === "::" ||
    parsed.hostname === "[::]"
  ) {
    throw new Error(`${PUBLIC_BASE_ENV} cannot use an unspecified host`);
  }

  return new URL(parsed.origin);
}

export function requireExternalOrigin(): URL {
  return parseRequiredConfiguredPublicBaseUrl();
}

export function resolveExternalOrigin(request: Request): URL {
  void request;
  return requireExternalOrigin();
}

export function buildExternalUrl(request: Request, pathOrRelativeUrl: string): URL {
  return new URL(pathOrRelativeUrl, resolveExternalOrigin(request));
}
