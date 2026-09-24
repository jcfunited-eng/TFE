import assert from "node:assert/strict";
import {
  binaryValidationCheck,
  buildValidationCheck,
  taSemanticsValidationCheck,
  validationReportPassed,
  advisoryValidationCheck,
  isAdvisoryCheck,
} from "../validation_status.mjs";

assert.equal(binaryValidationCheck("executed", true).status, "pass");
assert.equal(binaryValidationCheck("failed", false).status, "fail");
assert.equal(buildValidationCheck("browser", "not_run").status, "not_run");
assert.throws(() => buildValidationCheck("browser", "flagged"));

const clean = taSemanticsValidationCheck({
  totalRows: 10,
  sma20WithValidAnchor: 10,
  sma50WithValidAnchor: 10,
  sma200WithValidAnchor: 10,
  rsi14WithinRange: 10,
});
assert.equal(clean.status, "pass");

const flagged = taSemanticsValidationCheck({
  totalRows: 10,
  sma20WithValidAnchor: 9,
  sma50WithValidAnchor: 10,
  sma200WithValidAnchor: 10,
  rsi14WithinRange: 10,
});
assert.equal(flagged.status, "fail");
assert.equal(flagged.details.enforcement, "blocking");

assert.equal(validationReportPassed([clean, binaryValidationCheck("second", true)]), true);
assert.equal(validationReportPassed([clean, flagged]), false);
assert.equal(validationReportPassed([clean, buildValidationCheck("browser", "not_run")]), false);
assert.equal(validationReportPassed([]), false);

// ADVISORY checks (2026-09-24): recorded with their real status, never decide
// the verdict. Blocking checks that cannot run still fail the report.
const advisoryNotRun = advisoryValidationCheck("ui_filter_behavior_integrity", "not_run", { reason: "no login" });
const advisoryFail = advisoryValidationCheck("ui_filter_behavior_integrity", "fail");
assert.equal(isAdvisoryCheck(advisoryNotRun), true);
assert.equal(isAdvisoryCheck(clean), false);
assert.equal(advisoryNotRun.details.enforcement, "advisory");
assert.equal(advisoryNotRun.details.reason, "no login");
assert.equal(validationReportPassed([clean, advisoryNotRun]), true);
assert.equal(validationReportPassed([clean, advisoryFail]), true);
assert.equal(validationReportPassed([clean, flagged, advisoryNotRun]), false);
assert.equal(validationReportPassed([clean, buildValidationCheck("browser", "not_run"), advisoryNotRun]), false);
assert.equal(validationReportPassed([advisoryNotRun]), false, "an all-advisory report has nothing blocking that passed");

console.log("validation status tests passed");
