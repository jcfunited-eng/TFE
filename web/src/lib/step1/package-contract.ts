import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

import {
  deterministicTimestampFromDigest,
  sha256Text,
  stableJsonStringify,
  type Step1AssessmentArtifactReference,
  type Step1SourcePackageIdentityRecord,
} from "./schema";

export const STEP1_SOURCE_PACKAGE_MANIFEST_VERSION = 1;
export const STEP1_NORMALIZED_PACKAGE_MANIFEST_VERSION = 1;
export const STEP1_SOURCE_PACKAGE_MANIFESTS_RELATIVE_DIR = path.join("step1", "source_packages");
export const STEP1_NORMALIZED_PACKAGE_MANIFEST_RELATIVE_PATH = path.join("step1", "normalized_package", "manifest.json");

export type Step1SourcePackageManifest = {
  source_package_manifest_version: typeof STEP1_SOURCE_PACKAGE_MANIFEST_VERSION;
  source_package_id: string;
  source_identity: string;
  acquisition_timestamp_utc: string;
  source_class: string;
  raw_payload_reference: string;
  integrity_status: string;
};

export type Step1SourcePackageManifestReference = {
  source_package_id: string;
  manifest_path: string;
  manifest_digest_sha256: string;
};

export type Step1NormalizedPackageManifest = {
  normalized_package_manifest_version: typeof STEP1_NORMALIZED_PACKAGE_MANIFEST_VERSION;
  normalized_package_manifest_id: string;
  normalized_package_id: string;
  deterministic_manifest_timestamp_utc: string;
  source_package_identities: Step1SourcePackageIdentityRecord[];
  source_package_manifest_references: Step1SourcePackageManifestReference[];
};

export type Step1WrittenSourcePackageManifest = {
  manifest: Step1SourcePackageManifest;
  manifestPath: string;
  manifestDigestSha256: string;
};

export type Step1WrittenNormalizedPackageManifest = {
  manifest: Step1NormalizedPackageManifest;
  manifestPath: string;
  manifestDigestSha256: string;
};

export type Step1WrittenPackageContractArtifacts = {
  sourcePackageManifests: Step1WrittenSourcePackageManifest[];
  normalizedPackageManifest: Step1WrittenNormalizedPackageManifest;
};

function sortSourcePackageIdentities(
  sourcePackageIdentities: Step1SourcePackageIdentityRecord[],
): Step1SourcePackageIdentityRecord[] {
  return [...sourcePackageIdentities].sort((left, right) => {
    const byId = left.source_package_id.localeCompare(right.source_package_id);
    if (byId !== 0) return byId;
    return left.source_identity.localeCompare(right.source_identity);
  });
}

export function resolveStep1SourcePackageManifestPath(
  workspaceRoot: string,
  runId: string,
  sourcePackageId: string,
): string {
  return path.join(workspaceRoot, "artifacts", "runs", runId, STEP1_SOURCE_PACKAGE_MANIFESTS_RELATIVE_DIR, `${sourcePackageId}.json`);
}

export function resolveStep1NormalizedPackageManifestPath(workspaceRoot: string, runId: string): string {
  return path.join(workspaceRoot, "artifacts", "runs", runId, STEP1_NORMALIZED_PACKAGE_MANIFEST_RELATIVE_PATH);
}

export function buildSourcePackageManifest(
  sourcePackageIdentity: Step1SourcePackageIdentityRecord,
): Step1SourcePackageManifest {
  return {
    source_package_manifest_version: STEP1_SOURCE_PACKAGE_MANIFEST_VERSION,
    source_package_id: sourcePackageIdentity.source_package_id,
    source_identity: sourcePackageIdentity.source_identity,
    acquisition_timestamp_utc: sourcePackageIdentity.acquisition_timestamp_utc,
    source_class: sourcePackageIdentity.source_class,
    raw_payload_reference: sourcePackageIdentity.raw_payload_reference,
    integrity_status: sourcePackageIdentity.integrity_status,
  };
}

export function buildNormalizedPackageManifest(params: {
  normalizedPackageId: string;
  sourcePackageManifests: Step1WrittenSourcePackageManifest[];
}): Step1NormalizedPackageManifest {
  const sourcePackageIdentities = sortSourcePackageIdentities(
    params.sourcePackageManifests.map((entry) => ({
      source_package_id: entry.manifest.source_package_id,
      source_identity: entry.manifest.source_identity,
      acquisition_timestamp_utc: entry.manifest.acquisition_timestamp_utc,
      source_class: entry.manifest.source_class,
      raw_payload_reference: entry.manifest.raw_payload_reference,
      integrity_status: entry.manifest.integrity_status,
    })),
  );
  const sourcePackageManifestReferences = [...params.sourcePackageManifests]
    .sort((left, right) => left.manifest.source_package_id.localeCompare(right.manifest.source_package_id))
    .map((entry) => ({
      source_package_id: entry.manifest.source_package_id,
      manifest_path: entry.manifestPath,
      manifest_digest_sha256: entry.manifestDigestSha256,
    }));
  const canonicalInput = {
    normalized_package_id: params.normalizedPackageId,
    source_package_identities: sourcePackageIdentities,
    source_package_manifest_references: sourcePackageManifestReferences,
  };
  const digest = sha256Text(stableJsonStringify(canonicalInput));

  return {
    normalized_package_manifest_version: STEP1_NORMALIZED_PACKAGE_MANIFEST_VERSION,
    normalized_package_manifest_id: `normalized_package_manifest_v1_${digest.slice(0, 24)}`,
    normalized_package_id: params.normalizedPackageId,
    deterministic_manifest_timestamp_utc: deterministicTimestampFromDigest(digest),
    source_package_identities: sourcePackageIdentities,
    source_package_manifest_references: sourcePackageManifestReferences,
  };
}

export async function writeStep1PackageContractArtifacts(params: {
  workspaceRoot: string;
  runId: string;
  normalizedPackageId: string;
  sourcePackageIdentities: Step1SourcePackageIdentityRecord[];
}): Promise<Step1WrittenPackageContractArtifacts> {
  const sortedSourcePackageIdentities = sortSourcePackageIdentities(params.sourcePackageIdentities);
  const sourcePackageManifests: Step1WrittenSourcePackageManifest[] = [];

  for (const sourcePackageIdentity of sortedSourcePackageIdentities) {
    const manifest = buildSourcePackageManifest(sourcePackageIdentity);
    const manifestPath = resolveStep1SourcePackageManifestPath(
      params.workspaceRoot,
      params.runId,
      sourcePackageIdentity.source_package_id,
    );
    const manifestBody = `${JSON.stringify(manifest, null, 2)}\n`;
    await mkdir(path.dirname(manifestPath), { recursive: true });
    await writeFile(manifestPath, manifestBody, "utf8");
    sourcePackageManifests.push({
      manifest,
      manifestPath,
      manifestDigestSha256: sha256Text(manifestBody),
    });
  }

  const normalizedManifest = buildNormalizedPackageManifest({
    normalizedPackageId: params.normalizedPackageId,
    sourcePackageManifests,
  });
  const normalizedPackageManifestPath = resolveStep1NormalizedPackageManifestPath(params.workspaceRoot, params.runId);
  const normalizedManifestBody = `${JSON.stringify(normalizedManifest, null, 2)}\n`;
  await mkdir(path.dirname(normalizedPackageManifestPath), { recursive: true });
  await writeFile(normalizedPackageManifestPath, normalizedManifestBody, "utf8");

  return {
    sourcePackageManifests,
    normalizedPackageManifest: {
      manifest: normalizedManifest,
      manifestPath: normalizedPackageManifestPath,
      manifestDigestSha256: sha256Text(normalizedManifestBody),
    },
  };
}

export function buildPhaseEPackageArtifactReferences(params: {
  normalizedPackageId: string;
  normalizedPackageManifest: Step1WrittenNormalizedPackageManifest;
  sourcePackageManifests: Step1WrittenSourcePackageManifest[];
  dependencyClassificationRegister: Record<string, unknown>;
  candidateInputDigestSha256: string;
}): Step1AssessmentArtifactReference[] {
  return [
    {
      artifact_kind: "normalized_package_identity",
      artifact_id: params.normalizedPackageId,
      artifact_path: params.normalizedPackageManifest.manifestPath,
      artifact_digest_sha256: params.normalizedPackageManifest.manifestDigestSha256,
    },
    {
      artifact_kind: "normalized_package_manifest",
      artifact_id: params.normalizedPackageManifest.manifest.normalized_package_manifest_id,
      artifact_path: params.normalizedPackageManifest.manifestPath,
      artifact_digest_sha256: params.normalizedPackageManifest.manifestDigestSha256,
    },
    ...params.sourcePackageManifests.map((entry) => ({
      artifact_kind: "source_package_manifest",
      artifact_id: entry.manifest.source_package_id,
      artifact_path: entry.manifestPath,
      artifact_digest_sha256: entry.manifestDigestSha256,
    })),
    {
      artifact_kind: "dependency_classification_register",
      artifact_id: "dependency_classification_register",
      artifact_path: null,
      artifact_digest_sha256: sha256Text(stableJsonStringify(params.dependencyClassificationRegister)),
    },
    {
      artifact_kind: "candidate_input_digest",
      artifact_id: "candidate_input_digest",
      artifact_path: null,
      artifact_digest_sha256: params.candidateInputDigestSha256,
    },
  ];
}
