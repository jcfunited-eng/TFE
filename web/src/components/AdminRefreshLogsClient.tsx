"use client";

import { useEffect, useState } from "react";
import SiteFrame from "@/components/SiteFrame";
import styles from "@/components/AdminConsoleClient.module.css";

type UiBackgroundImages = {
  adminConsole: string;
};

type UiConfig = {
  backgroundImages: UiBackgroundImages;
};

type RefreshMode = "snapshot" | "universe_snapshot";

type RefreshReport = {
  generated_at_utc?: string;
  elapsed_seconds?: number;
  rows_written?: number;
  skipped_count?: number;
  status?: string;
};

type RefreshStatus = {
  running: boolean;
  run_id?: string;
  pid?: number;
  requested_mode?: RefreshMode;
  requested_by?: string;
  started_at?: string;
  completed_at?: string;
  last_error?: string;
  report_generated_at_utc?: string;
  last_report?: RefreshReport;
  kill_requested?: boolean;
  kill_requested_at?: string;
  kill_requested_by?: string;
  kill_acknowledged_at?: string;
};

type RefreshLogPayload = {
  exists: boolean;
  path: string;
  linesRequested: number;
  lineCount: number;
  updatedAtUtc: string | null;
  lines: string[];
};

type RefreshHistoryEntry = {
  logged_at_utc?: string;
  run_id?: string;
  phase?: string;
  status?: string;
  mode?: string;
  trigger_source?: string;
  requested_by?: string;
  rows_written?: number;
  elapsed_seconds?: number;
  refresh_report_status?: string;
  l5_learning?: string;
  optimizer_short_cycle?: string;
  optimizer_cycle_requested_runs?: number;
  optimizer_cycle_completed_runs?: number;
  optimizer_session_id?: string;
  optimizer_target_return_lift_pct?: number;
  optimizer_best_score?: number;
  optimizer_target_met?: boolean;
  epoch_library_confidence_schema?: string;
  epoch_library_status?: string;
  error?: string;
};

type RefreshHistoryPayload = {
  exists: boolean;
  path: string;
  linesRequested: number;
  entryCount: number;
  updatedAtUtc: string | null;
  entries: RefreshHistoryEntry[];
};

type NoticeTone = "info" | "good" | "warn" | "error";

type NoticeState = {
  tone: NoticeTone;
  text: string;
};

const DEFAULT_BACKGROUND_IMAGE = "/landing-zen.jpg";
const LOG_LINE_COUNT = 160;
const HISTORY_LINE_COUNT = 400;

function modeLabel(mode: RefreshMode | undefined): string {
  if (mode === "universe_snapshot") return "Universe + Snapshot";
  if (mode === "snapshot") return "Snapshot";
  return "Not set";
}

function triggerSourceLabel(value: string | undefined): string {
  if (value === "manual") return "Manual";
  if (value === "scheduled") return "Scheduled";
  if (value === "program") return "Program";
  return "Unknown";
}

function formatIso(iso: string | null | undefined): string {
  if (!iso) return "n/a";
  const value = Date.parse(iso);
  if (!Number.isFinite(value)) return iso;
  return new Date(value).toLocaleString();
}

function refreshHistoryDetail(entry: RefreshHistoryEntry): string {
  if (entry.error) return entry.error;

  const details: string[] = [];
  if (entry.refresh_report_status) details.push(`report=${entry.refresh_report_status}`);
  if (entry.l5_learning) details.push(`l5=${entry.l5_learning}`);
  if (entry.optimizer_short_cycle) details.push(`optimizer=${entry.optimizer_short_cycle}`);
  if (typeof entry.optimizer_best_score === "number") details.push(`best=${entry.optimizer_best_score.toFixed(3)}`);
  if (typeof entry.optimizer_target_return_lift_pct === "number") {
    details.push(`target>=${entry.optimizer_target_return_lift_pct.toFixed(1)}`);
  }
  if (typeof entry.optimizer_target_met === "boolean") details.push(`target_met=${entry.optimizer_target_met ? "yes" : "no"}`);
  if (entry.epoch_library_confidence_schema) details.push(`epoch_schema=${entry.epoch_library_confidence_schema}`);
  if (entry.epoch_library_status) details.push(`epoch=${entry.epoch_library_status}`);
  if (entry.optimizer_session_id) details.push(`session=${entry.optimizer_session_id}`);

  return details.join(" | ") || "-";
}

export default function AdminRefreshLogsClient() {
  const [backgroundImage, setBackgroundImage] = useState(DEFAULT_BACKGROUND_IMAGE);
  const [notice, setNotice] = useState<NoticeState>({
    tone: "info",
    text: "Loading refresh-log console...",
  });
  const [syncing, setSyncing] = useState(false);
  const [refreshBusy, setRefreshBusy] = useState<RefreshMode | null>(null);
  const [killBusy, setKillBusy] = useState(false);
  const [showKillConfirm, setShowKillConfirm] = useState(false);
  const [refreshStatus, setRefreshStatus] = useState<RefreshStatus | null>(null);
  const [refreshLog, setRefreshLog] = useState<RefreshLogPayload | null>(null);
  const [refreshHistory, setRefreshHistory] = useState<RefreshHistoryPayload | null>(null);

  const refreshRunning = Boolean(refreshStatus?.running);
  const killRequested = Boolean(refreshStatus?.kill_requested);

  function pushNotice(tone: NoticeTone, text: string) {
    setNotice({ tone, text });
  }

  function downloadJsonFile(fileName: string, payload: unknown): void {
    const blob = new Blob([`${JSON.stringify(payload, null, 2)}\n`], { type: "application/json" });
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = fileName;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.URL.revokeObjectURL(url);
  }

  async function loadUiConfig(): Promise<void> {
    const response = await fetch("/api/admin/ui-config", { cache: "no-store" });
    if (!response.ok) {
      throw new Error("Failed to load UI config.");
    }

    const data = (await response.json()) as UiConfig;
    const imagePath = String(data.backgroundImages?.adminConsole ?? "").trim();
    if (imagePath) {
      setBackgroundImage(imagePath);
    }
  }

  async function loadRefreshStatus(): Promise<void> {
    const response = await fetch("/api/admin/refresh", { cache: "no-store" });
    if (!response.ok) {
      throw new Error("Failed to load refresh status.");
    }

    const data = (await response.json()) as { status?: RefreshStatus };
    setRefreshStatus(data.status ?? null);
  }

  async function loadRefreshLog(): Promise<void> {
    const response = await fetch(`/api/admin/refresh/log?lines=${LOG_LINE_COUNT}`, { cache: "no-store" });
    if (!response.ok) {
      throw new Error("Failed to load refresh log.");
    }

    const data = (await response.json()) as RefreshLogPayload;
    setRefreshLog(data);
  }

  async function loadRefreshHistory(): Promise<void> {
    const response = await fetch(`/api/admin/refresh/history?lines=${HISTORY_LINE_COUNT}`, { cache: "no-store" });
    if (!response.ok) {
      throw new Error("Failed to load refresh history.");
    }

    const data = (await response.json()) as RefreshHistoryPayload;
    setRefreshHistory(data);
  }

  async function reloadPanel(showNotice = false): Promise<void> {
    if (showNotice) {
      pushNotice("info", "Refreshing refresh-log panel...");
    }

    setSyncing(true);
    try {
      await Promise.all([loadUiConfig(), loadRefreshStatus(), loadRefreshLog(), loadRefreshHistory()]);
      if (showNotice) {
        pushNotice("good", "Refresh-log panel synchronized.");
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Panel refresh failed.";
      pushNotice("error", message);
    }
    setSyncing(false);
  }

  useEffect(() => {
    void reloadPanel(false);

    const pollTimer = window.setInterval(() => {
      void Promise.all([loadRefreshStatus(), loadRefreshLog(), loadRefreshHistory()]).catch(() => {
        // polling failures are surfaced by manual refresh controls
      });
    }, 5000);

    return () => {
      window.clearInterval(pollTimer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function onTriggerRefresh(mode: RefreshMode): Promise<void> {
    setRefreshBusy(mode);
    pushNotice("info", `${modeLabel(mode)} refresh requested...`);

    try {
      const response = await fetch("/api/admin/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode }),
      });

      const data = (await response.json()) as { status?: RefreshStatus; error?: string };
      if (!response.ok) {
        pushNotice("error", data.error || "Refresh start failed.");
        setRefreshBusy(null);
        return;
      }

      setRefreshStatus(data.status ?? null);
      pushNotice("good", `${modeLabel(mode)} refresh started. Use log tail for live progress.`);

      await Promise.all([loadRefreshStatus(), loadRefreshLog(), loadRefreshHistory()]);
    } catch {
      pushNotice("error", "Refresh start failed.");
    }

    setRefreshBusy(null);
  }

  async function onConfirmKillActiveRun(): Promise<void> {
    setKillBusy(true);
    pushNotice("warn", "Kill request is being sent to the active refresh run...");

    try {
      const response = await fetch("/api/admin/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "kill_active_run" }),
      });

      const data = (await response.json()) as {
        status?: RefreshStatus;
        error?: string;
        killDump?: unknown;
        downloadFileName?: string;
      };

      if (!response.ok) {
        pushNotice("error", data.error || "Kill request failed.");
        return;
      }

      setRefreshStatus(data.status ?? null);
      setShowKillConfirm(false);
      if (data.killDump && data.downloadFileName) {
        downloadJsonFile(data.downloadFileName, data.killDump);
      }
      pushNotice("good", "Kill request recorded. The run log snapshot has been downloaded.");
      await Promise.all([loadRefreshStatus(), loadRefreshLog(), loadRefreshHistory()]);
    } catch (error) {
      pushNotice("error", error instanceof Error ? error.message : "Kill request failed.");
    } finally {
      setKillBusy(false);
    }
  }

  return (
    <SiteFrame pageBackgroundImage={backgroundImage}>
      <div className={styles.logViewportRoot}>
        <div className={styles.logViewportShield} aria-hidden="true" />
        <div className={styles.logViewportContent}>
          <section className={`${styles.deck} ${styles.deckLog}`}>
          <header className={styles.hero}>
            <div>
              <p className={styles.kicker}>Tao Financial Engine</p>
              <h1 className={styles.title}>Admin Refresh Logs</h1>
              <p className={styles.subtitle}>Dedicated route for refresh status lifecycle, live log tail, and refresh history records.</p>
            </div>

            <div className={styles.heroActionRow}>
              <button className={styles.primaryButton} type="button" onClick={() => void reloadPanel(true)} disabled={syncing}>
                {syncing ? "Syncing..." : "Sync Log Panels"}
              </button>
              <button className={styles.ghostButton} type="button" onClick={() => (window.location.href = "/admin-console")}>
                Back To Admin Console
              </button>
              <button
                className={styles.dangerButton}
                type="button"
                onClick={() => setShowKillConfirm(true)}
                disabled={!refreshRunning || killBusy || killRequested}
              >
                {killRequested ? "Kill Requested" : "KILL ACTIVE RUN"}
              </button>
            </div>
          </header>

          <div
            className={`${styles.notice} ${
              notice.tone === "good"
                ? styles.noticeGood
                : notice.tone === "warn"
                  ? styles.noticeWarn
                  : notice.tone === "error"
                    ? styles.noticeError
                    : styles.noticeInfo
            }`}
          >
            {notice.text}
          </div>

          <article className={styles.panel}>
            <header className={styles.panelHeader}>
              <h2 className={styles.panelTitle}>Refresh Lifecycle</h2>
              <p className={styles.panelSub}>Run refresh jobs and verify status/log/history reconciliation on one page.</p>
            </header>

            <div className={styles.buttonRow}>
              <button
                className={styles.opButton}
                type="button"
                onClick={() => void onTriggerRefresh("snapshot")}
                disabled={Boolean(refreshBusy) || refreshRunning}
              >
                ⟳ Snapshot Refresh
              </button>

              <button
                className={styles.opButton}
                type="button"
                onClick={() => void onTriggerRefresh("universe_snapshot")}
                disabled={Boolean(refreshBusy) || refreshRunning}
              >
                ↻ Universe + Snapshot
              </button>

              <button
                className={styles.secondaryButton}
                type="button"
                onClick={() => void Promise.all([loadRefreshStatus(), loadRefreshLog(), loadRefreshHistory()])}
              >
                Poll Now
              </button>

              <button
                className={styles.dangerButton}
                type="button"
                onClick={() => setShowKillConfirm(true)}
                disabled={!refreshRunning || killBusy || killRequested}
              >
                {killRequested ? "Kill Requested" : "KILL ACTIVE RUN"}
              </button>
            </div>

            {refreshRunning ? (
              <div className={styles.progressBar} role="status" aria-label="Refresh in progress">
                <span className={styles.progressBarInner} />
              </div>
            ) : null}

            <div className={styles.keyValueGrid}>
              <div className={styles.kvItem}>
                <div className={styles.kvLabel}>State</div>
                <div className={styles.kvValue}>{refreshRunning ? "Running" : "Idle"}</div>
              </div>
              <div className={styles.kvItem}>
                <div className={styles.kvLabel}>Run ID</div>
                <div className={styles.kvValue}>{refreshStatus?.run_id ?? "n/a"}</div>
              </div>
              <div className={styles.kvItem}>
                <div className={styles.kvLabel}>Mode</div>
                <div className={styles.kvValue}>{modeLabel(refreshStatus?.requested_mode)}</div>
              </div>
              <div className={styles.kvItem}>
                <div className={styles.kvLabel}>Requested By</div>
                <div className={styles.kvValue}>{refreshStatus?.requested_by ?? "n/a"}</div>
              </div>
              <div className={styles.kvItem}>
                <div className={styles.kvLabel}>Started</div>
                <div className={styles.kvValue}>{formatIso(refreshStatus?.started_at)}</div>
              </div>
              <div className={styles.kvItem}>
                <div className={styles.kvLabel}>Completed</div>
                <div className={styles.kvValue}>{formatIso(refreshStatus?.completed_at)}</div>
              </div>
              <div className={styles.kvItem}>
                <div className={styles.kvLabel}>Report Status</div>
                <div className={styles.kvValue}>{refreshStatus?.last_report?.status || "n/a"}</div>
              </div>
              <div className={styles.kvItem}>
                <div className={styles.kvLabel}>Rows Written</div>
                <div className={styles.kvValue}>{refreshStatus?.last_report?.rows_written ?? "n/a"}</div>
              </div>
              <div className={styles.kvItem}>
                <div className={styles.kvLabel}>Kill State</div>
                <div className={styles.kvValue}>
                  {killRequested ? `Requested by ${refreshStatus?.kill_requested_by ?? "admin"}` : "Clear"}
                </div>
              </div>
            </div>

            {refreshStatus?.last_error ? <p className={`${styles.inlineMsg} ${styles.msgError}`}>Refresh error: {refreshStatus.last_error}</p> : null}

            <div className={styles.logBox}>
              <div className={styles.logMeta}>
                <strong>Refresh Log Tail</strong>
                <span>{refreshLog?.exists ? `Updated: ${formatIso(refreshLog?.updatedAtUtc)}` : "No log yet"}</span>
              </div>
              <pre className={styles.logPre}>
                {refreshLog?.exists
                  ? refreshLog.lines.join("\n") || "Log exists but currently empty."
                  : "No refresh log file found yet. Run a refresh to generate logs."}
              </pre>
            </div>

            <div className={styles.logBox} style={{ marginTop: 12 }}>
              <div className={styles.logMeta}>
                <strong>Refresh History Report</strong>
                <span>{refreshHistory?.exists ? `Updated: ${formatIso(refreshHistory?.updatedAtUtc)}` : "No history yet"}</span>
              </div>
              <div className={styles.scrollWrap} style={{ maxHeight: 320 }}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>Phase</th>
                      <th>Source</th>
                      <th>Mode</th>
                      <th>By</th>
                      <th>Status</th>
                      <th>Rows</th>
                      <th>Elapsed</th>
                      <th>Detail</th>
                    </tr>
                  </thead>
                  <tbody>
                    {refreshHistory?.entries?.length ? (
                      [...refreshHistory.entries].reverse().map((entry, index) => (
                        <tr key={`${entry.run_id ?? "run"}-${entry.phase ?? "phase"}-${entry.logged_at_utc ?? "time"}-${index}`}>
                          <td>{formatIso(entry.logged_at_utc)}</td>
                          <td>{entry.phase ?? "n/a"}</td>
                          <td>{triggerSourceLabel(entry.trigger_source)}</td>
                          <td>{modeLabel(entry.mode === "snapshot" || entry.mode === "universe_snapshot" ? entry.mode : undefined)}</td>
                          <td>{entry.requested_by ?? "n/a"}</td>
                          <td>{entry.status ?? "n/a"}</td>
                          <td>{entry.rows_written ?? "n/a"}</td>
                          <td>{typeof entry.elapsed_seconds === "number" ? `${entry.elapsed_seconds.toFixed(2)}s` : "n/a"}</td>
                          <td>{refreshHistoryDetail(entry)}</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={9}>No refresh history entries recorded yet.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </article>

          {showKillConfirm ? (
            <div className={styles.modalBackdrop} role="presentation">
              <div className={styles.modalCard} role="dialog" aria-modal="true" aria-labelledby="kill-run-title">
                <h3 id="kill-run-title" className={styles.modalTitle}>Kill Active Run</h3>
                <p className={styles.modalText}>
                  Are you sure you want to halt the active refresh run
                  {refreshStatus?.run_id ? ` (${refreshStatus.run_id})` : ""}
                  ?
                </p>
                <p className={styles.modalText}>
                  This records the kill flag in Postgres and downloads the current log state as JSON.
                </p>
                <div className={styles.buttonRow}>
                  <button
                    className={styles.dangerButton}
                    type="button"
                    onClick={() => void onConfirmKillActiveRun()}
                    disabled={killBusy}
                  >
                    {killBusy ? "Sending Kill Request..." : "Yes, Kill Active Run"}
                  </button>
                  <button
                    className={styles.ghostButton}
                    type="button"
                    onClick={() => setShowKillConfirm(false)}
                    disabled={killBusy}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          ) : null}
          </section>
        </div>
      </div>
    </SiteFrame>
  );
}
