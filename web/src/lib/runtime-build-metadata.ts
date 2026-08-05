import { readFile } from "node:fs/promises";
import path from "node:path";

import { resolveWorkspaceRoot } from "@/lib/workspace-root";

type RuntimeBuildMetadataStatus = "ok" | "missing" | "mismatch" | "invalid";

type DeployMetadataFile = {
  generated_at_utc?: unknown;
  git_commit_sha?: unknown;
  source_archive_s3?: unknown;
  source_deploy_s3?: unknown;
  image_tag?: unknown;
  image_uri?: unknown;
  deploy_timestamp_utc?: unknown;
};

export type RuntimeBuildMetadata = {
  status: RuntimeBuildMetadataStatus;
  metadataPath: string;
  gitCommitSha: string | null;
  fileGitCommitSha: string | null;
  envGitCommitSha: string | null;
  sourceArchiveS3: string | null;
  sourceDeployS3: string | null;
  imageTag: string | null;
  imageUri: string | null;
  deployTimestampUtc: string | null;
  generatedAtUtc: string | null;
  issues: string[];
};

const ROOT_DIR = resolveWorkspaceRoot();
const DEPLOY_METADATA_FILENAME = "tfe_deploy_metadata.json";
const FULL_GIT_SHA_PATTERN = /^[0-9a-f]{40}$/i;

function textOrNull(value: unknown): string | null {
  const text = String(value ?? "").trim();
  return text ? text : null;
}

function normalizeGitCommitSha(value: unknown): string | null {
  const text = textOrNull(value);
  if (!text) return null;
  if (!FULL_GIT_SHA_PATTERN.test(text)) return null;
  return text.toLowerCase();
}

function parseDeployMetadata(raw: string): DeployMetadataFile | null {
  try {
    const parsed = JSON.parse(raw) as DeployMetadataFile;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return null;
    return parsed;
  } catch {
    return null;
  }
}

export async function loadRuntimeBuildMetadata(): Promise<RuntimeBuildMetadata> {
  const metadataPath = path.join(ROOT_DIR, DEPLOY_METADATA_FILENAME);
  const envGitCommitSha = normalizeGitCommitSha(process.env.TFE_GIT_COMMIT_SHA);
  const envSourceArchiveS3 = textOrNull(process.env.TFE_SOURCE_ARCHIVE_S3);
  const envSourceDeployS3 = textOrNull(process.env.TFE_SOURCE_DEPLOY_S3);
  const envImageTag = textOrNull(process.env.TFE_DEPLOY_IMAGE_TAG);
  const envImageUri = textOrNull(process.env.TFE_DEPLOY_IMAGE_URI);
  const envDeployTimestampUtc = textOrNull(process.env.TFE_DEPLOY_TIMESTAMP_UTC);
  const issues: string[] = [];

  let filePayload: DeployMetadataFile | null = null;
  try {
    const raw = await readFile(metadataPath, "utf-8");
    filePayload = parseDeployMetadata(raw);
    if (!filePayload) {
      issues.push("metadata_file_invalid_json_object");
    }
  } catch {
    issues.push("metadata_file_missing");
  }

  const fileGitCommitSha = normalizeGitCommitSha(filePayload?.git_commit_sha);
  if (filePayload && !fileGitCommitSha) {
    issues.push("metadata_file_missing_or_invalid_git_commit_sha");
  }
  if (!envGitCommitSha) {
    issues.push("env_git_commit_sha_missing_or_invalid");
  }
  if (fileGitCommitSha && envGitCommitSha && fileGitCommitSha !== envGitCommitSha) {
    issues.push("git_commit_sha_mismatch_between_file_and_env");
  }

  const gitCommitSha = fileGitCommitSha ?? envGitCommitSha;
  let status: RuntimeBuildMetadataStatus = "ok";
  if (!gitCommitSha) {
    status = "missing";
  } else if (issues.includes("git_commit_sha_mismatch_between_file_and_env")) {
    status = "mismatch";
  } else if (issues.some((issue) => issue.startsWith("metadata_file_invalid"))) {
    status = "invalid";
  } else if (issues.includes("metadata_file_missing_or_invalid_git_commit_sha")) {
    status = "invalid";
  } else if (issues.length > 0) {
    status = "missing";
  }

  return {
    status,
    metadataPath,
    gitCommitSha,
    fileGitCommitSha,
    envGitCommitSha,
    sourceArchiveS3: textOrNull(filePayload?.source_archive_s3) ?? envSourceArchiveS3,
    sourceDeployS3: textOrNull(filePayload?.source_deploy_s3) ?? envSourceDeployS3,
    imageTag: textOrNull(filePayload?.image_tag) ?? envImageTag,
    imageUri: textOrNull(filePayload?.image_uri) ?? envImageUri,
    deployTimestampUtc: textOrNull(filePayload?.deploy_timestamp_utc) ?? envDeployTimestampUtc,
    generatedAtUtc: textOrNull(filePayload?.generated_at_utc),
    issues,
  };
}
