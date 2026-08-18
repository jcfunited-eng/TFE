import "server-only";

import { createHash } from "node:crypto";
import {
  GetObjectCommand,
  HeadObjectCommand,
  PutObjectCommand,
  S3Client,
} from "@aws-sdk/client-s3";

const DEFAULT_BUCKET = "tfe-codebuild-src-418384447921-us-east-1";
const ASSET_PREFIX = "runtime-ui-assets/images";
export const UI_CONFIG_KEY = "runtime-ui-assets/config/ui-config.json";

let client: S3Client | null = null;

function s3(): S3Client {
  if (!client) client = new S3Client({});
  return client;
}

function bucket(): string {
  return String(process.env.TFE_UI_ASSET_BUCKET ?? DEFAULT_BUCKET).trim() || DEFAULT_BUCKET;
}

function sha256(bytes: Uint8Array): string {
  return createHash("sha256").update(bytes).digest("hex");
}

function isMissing(error: unknown): boolean {
  if (!error || typeof error !== "object") return false;
  const value = error as { name?: unknown; $metadata?: { httpStatusCode?: unknown } };
  return value.name === "NoSuchKey" || value.name === "NotFound" || value.$metadata?.httpStatusCode === 404;
}

async function bodyBytes(body: unknown): Promise<Uint8Array> {
  if (
    body
    && typeof body === "object"
    && "transformToByteArray" in body
    && typeof (body as { transformToByteArray?: unknown }).transformToByteArray === "function"
  ) {
    return (body as { transformToByteArray: () => Promise<Uint8Array> }).transformToByteArray();
  }
  throw new Error("S3 object body cannot be converted to bytes");
}

export function usesDurableUiStorage(): boolean {
  return String(process.env.TFE_ENV ?? "").trim().toLowerCase() === "aws"
    || String(process.env.AWS_EXECUTION_ENV ?? "").trim().length > 0
    || String(process.env.TFE_UI_ASSET_BUCKET ?? "").trim().length > 0;
}

export async function readDurableUiConfig(): Promise<Uint8Array | null> {
  try {
    const response = await s3().send(new GetObjectCommand({ Bucket: bucket(), Key: UI_CONFIG_KEY }));
    return bodyBytes(response.Body);
  } catch (error) {
    if (isMissing(error)) return null;
    throw error;
  }
}

export async function writeDurableUiConfig(bytes: Uint8Array): Promise<void> {
  const digest = sha256(bytes);
  await s3().send(new PutObjectCommand({
    Bucket: bucket(),
    Key: UI_CONFIG_KEY,
    Body: bytes,
    ContentType: "application/json",
    CacheControl: "no-store",
    Metadata: { sha256: digest },
  }));
  const receipt = await s3().send(new HeadObjectCommand({ Bucket: bucket(), Key: UI_CONFIG_KEY }));
  if (receipt.Metadata?.sha256 !== digest || Number(receipt.ContentLength) !== bytes.byteLength) {
    throw new Error("durable UI configuration receipt mismatch");
  }
}

export async function putDurableUiAsset(
  bytes: Uint8Array,
  contentType: string,
  extension: string,
): Promise<string> {
  const digest = sha256(bytes);
  const fileName = `${digest}.${extension}`;
  const key = `${ASSET_PREFIX}/${fileName}`;
  try {
    await s3().send(new PutObjectCommand({
      Bucket: bucket(),
      Key: key,
      Body: bytes,
      ContentType: contentType,
      CacheControl: "public, max-age=31536000, immutable",
      Metadata: { sha256: digest },
      IfNoneMatch: "*",
    }));
  } catch (error) {
    const receipt = await s3().send(new HeadObjectCommand({ Bucket: bucket(), Key: key }));
    if (receipt.Metadata?.sha256 !== digest || Number(receipt.ContentLength) !== bytes.byteLength) {
      throw error;
    }
  }
  const receipt = await s3().send(new HeadObjectCommand({ Bucket: bucket(), Key: key }));
  if (receipt.Metadata?.sha256 !== digest || Number(receipt.ContentLength) !== bytes.byteLength) {
    throw new Error("durable UI asset receipt mismatch");
  }
  return `/api/assets/${fileName}`;
}

export async function getDurableUiAsset(fileName: string): Promise<{
  bytes: Uint8Array;
  contentType: string;
  digest: string;
} | null> {
  const match = /^([a-f0-9]{64})\.(jpg|png|webp)$/.exec(fileName);
  if (!match) return null;
  const expectedDigest = match[1];
  try {
    const response = await s3().send(new GetObjectCommand({
      Bucket: bucket(),
      Key: `${ASSET_PREFIX}/${fileName}`,
    }));
    const bytes = await bodyBytes(response.Body);
    if (sha256(bytes) !== expectedDigest || response.Metadata?.sha256 !== expectedDigest) {
      throw new Error("durable UI asset failed its content receipt");
    }
    return {
      bytes,
      contentType: response.ContentType ?? "application/octet-stream",
      digest: expectedDigest,
    };
  } catch (error) {
    if (isMissing(error)) return null;
    throw error;
  }
}
