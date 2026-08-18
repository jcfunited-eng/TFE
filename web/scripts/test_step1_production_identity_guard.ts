import assert from "node:assert/strict";
import {
  Step1AdminRefreshContractError,
  resolveStep1OrchestratorInputFromAdminRefreshRequest,
} from "../src/lib/step1/orchestrator";

const sourcePackageIdentities = [{
  sourcePackageId: "source-package-proof",
  sourceIdentity: "sha256:0123456789abcdef",
  acquisitionTimestampUtc: "2026-08-18T00:00:00Z",
  sourceClass: "proof_fixture",
  rawPayloadReference: "proof://fixture",
  integrityStatus: "complete",
}];

const base = {
  policySetId: "policy-set-proof",
  modelSetId: "model-set-proof",
  configSetId: "config-set-proof",
  bundleClass: "publication_candidate",
  dependencyClassificationRegister: { normalized_package: "classified" },
  sourcePackageIdentities,
  targetEnvironment: "production",
  assessmentRuleSetId: "assessment-rules-proof",
};

assert.throws(
  () => resolveStep1OrchestratorInputFromAdminRefreshRequest({
    requestBody: { ...base, normalizedPackageId: "normalized-package-demo" },
    requestedBy: "test",
    executionMode: "enabled",
    requestedMode: "snapshot",
    env: {},
  }),
  (error: unknown) => error instanceof Step1AdminRefreshContractError
    && error.code === "production_placeholder_identity_forbidden",
);

const accepted = resolveStep1OrchestratorInputFromAdminRefreshRequest({
  requestBody: { ...base, normalizedPackageId: "normalized-package-proof" },
  requestedBy: "test",
  executionMode: "enabled",
  requestedMode: "snapshot",
  env: {},
});
assert.equal(accepted.input.normalizedPackageId, "normalized-package-proof");

console.log("Step 1 production identity guard tests passed");
