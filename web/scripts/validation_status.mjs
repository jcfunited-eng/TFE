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

export function validationReportPassed(checks) {
  return Array.isArray(checks)
    && checks.length > 0
    && checks.every((check) => check?.status === "pass");
}
