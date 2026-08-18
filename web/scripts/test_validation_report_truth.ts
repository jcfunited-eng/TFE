import assert from "node:assert/strict";
import { reconcileValidationReport } from "../src/lib/validation-report-truth";

const legacyFalsePass = reconcileValidationReport({
  status: "pass",
  checks: [
    {
      name: "ta_semantics_integrity",
      status: "pass",
      details: { flagged_rows: 2193, observed_status: "flagged", enforcement: "flag_only_non_blocking" },
    },
    {
      name: "ui_filter_behavior_integrity",
      status: "pass",
      details: { configured: false, reason: "Missing API filter validation credentials/base URL." },
    },
  ],
});
assert.equal(legacyFalsePass?.status, "fail");
assert.equal(legacyFalsePass?.checks?.[0].status, "fail");
assert.equal(legacyFalsePass?.checks?.[1].status, "not_run");

const clean = reconcileValidationReport({
  status: "pass",
  checks: [
    { name: "ta_semantics_integrity", status: "pass", details: { flagged_rows: 0 } },
    { name: "ui_filter_behavior_integrity", status: "pass", details: { configured: true } },
    { name: "schedule_evidence", status: "pass", details: { observed_pass: true } },
  ],
});
assert.equal(clean?.status, "pass");
assert.equal(clean?.blocking_reason, null);

const empty = reconcileValidationReport({ status: "pass", checks: [] });
assert.equal(empty?.status, "fail");
assert.equal(empty?.blocking_reason, "validation_checks_missing");

console.log("validation report truth tests passed");
