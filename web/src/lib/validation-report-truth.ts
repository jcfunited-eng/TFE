export type ValidationCheck = {
  name?: string;
  status?: string;
  details?: unknown;
};

export type ValidationReport = {
  status?: string;
  generated_at_utc?: string;
  run_id?: string | null;
  checks?: ValidationCheck[];
  blocking_reason?: string | null;
  validation_history?: unknown;
};

function objectValue(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;
}

function normalizedStatus(value: unknown): "pass" | "fail" | "not_run" {
  const status = String(value ?? "").trim().toLowerCase();
  if (status === "pass") return "pass";
  if (status === "not_run") return "not_run";
  return "fail";
}

function reconcileCheck(check: ValidationCheck): ValidationCheck {
  const name = String(check.name ?? "").trim();
  const details = objectValue(check.details);
  let status = normalizedStatus(check.status);

  if (name === "ta_semantics_integrity") {
    const flaggedRows = Number(details?.flagged_rows);
    const observedStatus = String(details?.observed_status ?? "").trim().toLowerCase();
    if ((Number.isFinite(flaggedRows) && flaggedRows > 0) || observedStatus === "flagged") {
      status = "fail";
    }
  }

  if (name === "ui_filter_behavior_integrity") {
    const configured = details?.configured;
    const reason = String(details?.reason ?? "").toLowerCase();
    if (configured === false || reason.includes("missing api filter validation")) {
      status = "not_run";
    }
  }

  if (name === "schedule_evidence" && details?.observed_pass === false) {
    status = "fail";
  }

  return { ...check, name, status };
}

export function reconcileValidationReport(value: unknown): ValidationReport | null {
  const source = objectValue(value);
  if (!source) return null;
  const sourceChecks = Array.isArray(source.checks) ? source.checks : [];
  const checks = sourceChecks
    .map((check) => objectValue(check))
    .filter((check): check is Record<string, unknown> => check !== null)
    .map((check) => reconcileCheck(check as ValidationCheck));
  const passing = checks.length > 0 && checks.every((check) => check.status === "pass");
  const firstBlocker = checks.find((check) => check.status !== "pass");
  const originalReason = String(source.blocking_reason ?? "").trim();

  return {
    ...(source as ValidationReport),
    status: passing ? "pass" : "fail",
    generated_at_utc: String(source.generated_at_utc ?? "").trim() || undefined,
    run_id: source.run_id === null ? null : String(source.run_id ?? "").trim() || null,
    checks,
    blocking_reason: passing
      ? null
      : originalReason || (firstBlocker ? `${firstBlocker.name}_${firstBlocker.status}` : "validation_checks_missing"),
  };
}
