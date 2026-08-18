"use client";

import { useEffect, useState } from "react";
import styles from "./AdminConsoleClient.module.css";

type ValidationCheck = {
  name?: string;
  status?: "pass" | "fail" | "not_run" | string;
  details?: Record<string, unknown>;
};

type ValidationReport = {
  status?: string;
  generated_at_utc?: string;
  blocking_reason?: string | null;
  checks?: ValidationCheck[];
};

type LatestResponse = {
  exists?: boolean;
  report?: ValidationReport | null;
  error?: string;
};

function displayName(name: string | undefined): string {
  return String(name ?? "unnamed_check").replaceAll("_", " ");
}

export default function ValidationGatePanel() {
  const [payload, setPayload] = useState<LatestResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    fetch("/api/admin/validation/latest", { cache: "no-store" })
      .then(async (response) => {
        const body = await response.json() as LatestResponse;
        if (!response.ok) throw new Error(body.error || `HTTP ${response.status}`);
        if (active) setPayload(body);
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : String(reason));
      });
    return () => { active = false; };
  }, []);

  if (error) {
    return <div className={styles.notice + " " + styles.noticeWarn}>Validation gate unavailable: {error}</div>;
  }
  if (!payload) {
    return <div className={styles.notice + " " + styles.noticeInfo}>Loading latest validation gate...</div>;
  }
  if (!payload.exists || !payload.report) {
    return <div className={styles.notice + " " + styles.noticeWarn}>No validation gate has been run for this deployment.</div>;
  }

  const report = payload.report;
  const checks = Array.isArray(report.checks) ? report.checks : [];
  const passed = report.status === "pass" && checks.length > 0 && checks.every((check) => check.status === "pass");

  return (
    <section className={styles.panel} aria-label="Latest validation gate">
      <div className={styles.panelHeader}>
        <strong>Latest Validation Gate</strong>
        <span className={passed ? styles.chipGood : styles.chipWarn}>{passed ? "PASS" : "NOT PASSING"}</span>
      </div>
      <p className={styles.inlineMsg}>
        {report.generated_at_utc ? `Generated ${new Date(report.generated_at_utc).toLocaleString()}. ` : ""}
        {report.blocking_reason ? `Blocking reason: ${report.blocking_reason}.` : "Every recorded check passed."}
      </p>
      <div className={styles.scrollWrap}>
        <table className={styles.table}>
          <thead><tr><th>Check</th><th>Observed status</th></tr></thead>
          <tbody>
            {checks.length > 0 ? checks.map((check, index) => (
              <tr key={`${check.name ?? "check"}-${index}`}>
                <td>{displayName(check.name)}</td>
                <td>{String(check.status ?? "not_run").toUpperCase()}</td>
              </tr>
            )) : (
              <tr><td>validation checks</td><td>NOT RUN</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
