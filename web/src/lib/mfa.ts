import { createHmac, timingSafeEqual } from "node:crypto";

const TOTP_PERIOD_SECONDS = 30;
const TOTP_DIGITS = 6;

function normalizeBase32(input: string): string {
  return input.toUpperCase().replace(/[^A-Z2-7]/g, "");
}

function decodeBase32(input: string): Buffer {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  const clean = normalizeBase32(input);
  if (!clean) return Buffer.alloc(0);

  let bits = "";
  for (const char of clean) {
    const index = alphabet.indexOf(char);
    if (index < 0) continue;
    bits += index.toString(2).padStart(5, "0");
  }

  const bytes: number[] = [];
  for (let i = 0; i + 8 <= bits.length; i += 8) {
    bytes.push(Number.parseInt(bits.slice(i, i + 8), 2));
  }

  return Buffer.from(bytes);
}

function codeForCounter(secret: Buffer, counter: number): string {
  const msg = Buffer.alloc(8);
  msg.writeBigUInt64BE(BigInt(counter));

  const hmac = createHmac("sha1", secret).update(msg).digest();
  const offset = hmac[hmac.length - 1] & 0x0f;
  const binary =
    ((hmac[offset] & 0x7f) << 24) |
    ((hmac[offset + 1] & 0xff) << 16) |
    ((hmac[offset + 2] & 0xff) << 8) |
    (hmac[offset + 3] & 0xff);

  const code = binary % 10 ** TOTP_DIGITS;
  return String(code).padStart(TOTP_DIGITS, "0");
}

function secureEquals(a: string, b: string): boolean {
  const aBytes = Buffer.from(a, "utf-8");
  const bBytes = Buffer.from(b, "utf-8");
  if (aBytes.length !== bBytes.length) return false;
  return timingSafeEqual(aBytes, bBytes);
}

export function readAdminMfaTotpSecret(): string {
  return String(process.env.TFE_ADMIN_MFA_TOTP_SECRET ?? "").trim();
}

export function isAdminMfaEnabled(): boolean {
  return readAdminMfaTotpSecret().length > 0;
}

export function normalizeMfaCode(value: unknown): string {
  return String(value ?? "").replace(/\s+/g, "").trim();
}

export function verifyAdminTotpCode(code: unknown): boolean {
  const secretText = readAdminMfaTotpSecret();
  if (!secretText) return true;

  const normalizedCode = normalizeMfaCode(code);
  if (!/^\d{6}$/.test(normalizedCode)) return false;

  const secret = decodeBase32(secretText);
  if (secret.length < 10) return false;

  const counterNow = Math.floor(Date.now() / 1000 / TOTP_PERIOD_SECONDS);
  for (let delta = -1; delta <= 1; delta += 1) {
    const expected = codeForCounter(secret, counterNow + delta);
    if (secureEquals(expected, normalizedCode)) return true;
  }

  return false;
}
