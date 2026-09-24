const VALID_CHECK_STATUSES = new Set(["pass", "fail", "not_run"]);

export function buildValidationCheck(name, status, details = {}) {
  const normalizedName = String(name ?? "").trim();
  const normalizedStatus = String(status ?? "").trim().toLowerCase();
  if (!normalizedName) throw new Error("validation check name is required");
  if (!VALID_CHECK_STATUSES.has(normalizedStatus)) {
    throw new Error(`unsupported validation check status: ${normalizedStatus || "<empty>"}`);
  }
  return { name: normalizedName, status: normalizedStatus, details };
}

export function binaryValidationCheck(name, passed, details = {}) {
  return buildValidationCheck(name, passed === true ? "pass" : "fail", details);
}

export function taSemanticsValidationCheck({
  totalRows,
  sma20WithValidAnchor,
  sma50WithValidAnchor,
  sma200WithValidAnchor,
  rsi14WithinRange,
  details = {},
}) {
  const observedPass = Number.isInteger(totalRows)
    && totalRows > 0
    && sma20WithValidAnchor === totalRows
    && sma50WithValidAnchor === totalRows
    && sma200WithValidAnchor === totalRows
    && rsi14WithinRange === totalRows;
  return binaryValidationCheck("ta_semantics_integrity", observedPass, {
    ...details,
    observed_status: observedPass ? "pass" : "fail",
    enforcement: "blocking",
  });
}

// An ADVISORY check is recorded with its real status but never decides the
// verdict. Joseph 2026-09-24, on ui_filter_behavior_integrity (a website
// screener-filter test that needs a site login no container has ever
// carried, so it sat at not_run and stamped every nightly run FAILED since
// 09-16 while all seventeen data checks passed): "do what you think you need
// to do." The 2026-08-18 rule — a check that cannot run counts as failed —
// still holds for every blocking check.
export function advisoryValidationCheck(name, status, details = {}) {
  return buildValidationCheck(name, status, { ...details, enforcement: "advisory" });
}

export function isAdvisoryCheck(check) {
  return check?.details?.enforcement === "advisory";
}

export function validationReportPassed(checks) {
  if (!Array.isArray(checks)) return false;
  const blocking = checks.filter((check) => !isAdvisoryCheck(check));
  return blocking.length > 0
    && blocking.every((check) => check?.status === "pass");
}
