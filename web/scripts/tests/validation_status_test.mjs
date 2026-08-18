import assert from "node:assert/strict";
import {
  binaryValidationCheck,
  buildValidationCheck,
  taSemanticsValidationCheck,
  validationReportPassed,
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

console.log("validation status tests passed");
