import { createHmac, randomBytes, timingSafeEqual } from "node:crypto";
import { promises as fs } from "node:fs";
import path from "node:path";
import type { NextResponse } from "next/server";
import { getUserByUsername, isUserAccessExpired, type UserSummary } from "@/lib/user-store";

export const SESSION_COOKIE_NAME = "tfe_session";

type SessionTokenPayload = {
  v: number;
  username: string;
  iat: number;
  exp: number;
};

const SESSION_VERSION = 1;
const DEFAULT_TTL_SECONDS = 12 * 60 * 60;
const SECRET_FILE_NAME = "tfe_session_secret.bin";

let cachedSecret: Buffer | null = null;
let cachedSecretPromise: Promise<Buffer> | null = null;

function toBase64Url(data: Buffer): string {
  return data.toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function fromBase64Url(text: string): Buffer {
  const normalized = text.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized + "=".repeat((4 - (normalized.length % 4)) % 4);
  return Buffer.from(padded, "base64");
}

function normalizeTtlSeconds(value: unknown): number {
  const n = Number(value);
  if (!Number.isFinite(n)) return DEFAULT_TTL_SECONDS;
  const whole = Math.floor(n);
  if (whole < 300) return 300;
  if (whole > 30 * 24 * 60 * 60) return 30 * 24 * 60 * 60;
  return whole;
}

function secretCandidates(): string[] {
  const cwd = process.cwd();
  const primary = path.basename(cwd) === "web" ? path.resolve(cwd, "..", SECRET_FILE_NAME) : path.resolve(cwd, SECRET_FILE_NAME);
  return [
    primary,
    path.resolve(cwd, SECRET_FILE_NAME),
    path.resolve(cwd, "..", SECRET_FILE_NAME),
    path.resolve("/workspaces/Tao_Financial_Engine", SECRET_FILE_NAME),
  ];
}

async function resolveSecretPath(): Promise<string> {
  const candidates = secretCandidates();

  for (const candidate of candidates) {
    try {
      await fs.access(candidate);
      return candidate;
    } catch {
      // keep checking
    }
  }

  return candidates[0];
}

async function loadOrCreateSecretFromFile(): Promise<Buffer> {
  const filePath = await resolveSecretPath();

  try {
    const existing = await fs.readFile(filePath);
    if (existing.length >= 32) {
      return existing;
    }
  } catch {
    // create below
  }

  const next = randomBytes(32);
  await fs.writeFile(filePath, next, { mode: 0o600 });
  return next;
}

async function resolveSessionSecret(): Promise<Buffer> {
  if (cachedSecret) return cachedSecret;
  if (cachedSecretPromise) return cachedSecretPromise;

  cachedSecretPromise = (async () => {
    const fromEnv = String(process.env.TFE_SESSION_SECRET ?? "").trim();

    if (fromEnv) {
      const envBytes = Buffer.from(fromEnv, "utf-8");
      if (envBytes.length >= 32) {
        cachedSecret = envBytes;
        return envBytes;
      }

      const stretched = createHmac("sha256", "tfe-session-secret-stretch").update(envBytes).digest();
      cachedSecret = stretched;
      return stretched;
    }

    const fromFile = await loadOrCreateSecretFromFile();
    cachedSecret = fromFile;
    return fromFile;
  })();

  const resolved = await cachedSecretPromise;
  cachedSecretPromise = null;
  return resolved;
}

function extractCookieValue(cookieHeader: string | null, cookieName: string): string | null {
  if (!cookieHeader) return null;

  const parts = cookieHeader.split(";");
  for (const part of parts) {
    const trimmed = part.trim();
    if (!trimmed) continue;

    const equals = trimmed.indexOf("=");
    if (equals <= 0) continue;

    const name = trimmed.slice(0, equals).trim();
    if (name !== cookieName) continue;

    return trimmed.slice(equals + 1).trim();
  }

  return null;
}

function isValidTokenPayload(payload: unknown): payload is SessionTokenPayload {
  if (!payload || typeof payload !== "object") return false;

  const value = payload as Record<string, unknown>;

  if (Number(value.v) !== SESSION_VERSION) return false;
  if (typeof value.username !== "string" || !value.username.trim()) return false;

  const iat = Number(value.iat);
  const exp = Number(value.exp);

  if (!Number.isFinite(iat) || !Number.isFinite(exp)) return false;
  if (!(exp > iat)) return false;

  return true;
}

function signPayload(payloadB64: string, secret: Buffer): string {
  const digest = createHmac("sha256", secret).update(payloadB64).digest();
  return toBase64Url(digest);
}

function secureCompareText(a: string, b: string): boolean {
  const aBytes = Buffer.from(a, "utf-8");
  const bBytes = Buffer.from(b, "utf-8");
  if (aBytes.length !== bBytes.length) return false;
  return timingSafeEqual(aBytes, bBytes);
}

function cookieSecureFlag(): boolean {
  return process.env.NODE_ENV === "production";
}

export function sanitizeNextPath(value: unknown, options?: { allowSignIn?: boolean }): string {
  const raw = String(value ?? "").trim();
  const allowSignIn = Boolean(options?.allowSignIn);

  if (!raw.startsWith("/")) return "/account";
  if (raw.startsWith("//")) return "/account";
  if (raw.startsWith("/api")) return "/account";
  if (raw.startsWith("/_next")) return "/account";
  if (raw === "/sign-in" && !allowSignIn) return "/account";
  return raw;
}

export async function createSessionToken(user: UserSummary): Promise<{ token: string; expiresAtEpochSeconds: number }> {
  const secret = await resolveSessionSecret();
  const ttlSeconds = normalizeTtlSeconds(process.env.TFE_SESSION_TTL_SECONDS);
  const nowSeconds = Math.floor(Date.now() / 1000);
  const payload: SessionTokenPayload = {
    v: SESSION_VERSION,
    username: user.username,
    iat: nowSeconds,
    exp: nowSeconds + ttlSeconds,
  };

  const payloadB64 = toBase64Url(Buffer.from(JSON.stringify(payload), "utf-8"));
  const signatureB64 = signPayload(payloadB64, secret);
  return {
    token: `${payloadB64}.${signatureB64}`,
    expiresAtEpochSeconds: payload.exp,
  };
}

export async function readSessionUserFromToken(token: string | null | undefined): Promise<UserSummary | null> {
  const raw = String(token ?? "").trim();
  if (!raw) return null;

  const dotIndex = raw.indexOf(".");
  if (dotIndex <= 0 || dotIndex >= raw.length - 1) return null;

  const payloadB64 = raw.slice(0, dotIndex);
  const signatureB64 = raw.slice(dotIndex + 1);

  const secret = await resolveSessionSecret();
  const expectedSig = signPayload(payloadB64, secret);

  if (!secureCompareText(signatureB64, expectedSig)) {
    return null;
  }

  let parsedPayload: unknown;

  try {
    const payloadBytes = fromBase64Url(payloadB64);
    parsedPayload = JSON.parse(payloadBytes.toString("utf-8"));
  } catch {
    return null;
  }

  if (!isValidTokenPayload(parsedPayload)) return null;

  const nowSeconds = Math.floor(Date.now() / 1000);
  if (parsedPayload.exp <= nowSeconds) return null;

  let user: UserSummary | null;
  try {
    user = await getUserByUsername(parsedPayload.username);
  } catch {
    // Session lookup failures (for example transient DB outages) must not crash page render.
    // Treat as signed-out and let auth-gated routes respond with their normal 401/redirect flow.
    return null;
  }
  if (!user) return null;
  if (!user.is_active) return null;
  if (isUserAccessExpired(user.access_expires_at)) return null;

  return user;
}

export async function readSessionUserFromRequest(request: Request): Promise<UserSummary | null> {
  const cookieHeader = request.headers.get("cookie");
  const token = extractCookieValue(cookieHeader, SESSION_COOKIE_NAME);
  return readSessionUserFromToken(token);
}

export function setSessionCookie(response: NextResponse, token: string, expiresAtEpochSeconds: number): void {
  response.cookies.set({
    name: SESSION_COOKIE_NAME,
    value: token,
    httpOnly: true,
    sameSite: "lax",
    secure: cookieSecureFlag(),
    path: "/",
    expires: new Date(expiresAtEpochSeconds * 1000),
  });
}

export function clearSessionCookie(response: NextResponse): void {
  response.cookies.set({
    name: SESSION_COOKIE_NAME,
    value: "",
    httpOnly: true,
    sameSite: "lax",
    secure: cookieSecureFlag(),
    path: "/",
    expires: new Date(0),
  });
}
