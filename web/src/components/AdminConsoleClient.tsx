"use client";

import { useEffect, useMemo, useState } from "react";
import SiteFrame from "@/components/SiteFrame";
import styles from "@/components/AdminConsoleClient.module.css";

type UiBackgroundImages = {
  home: string;
  help: string;
  support: string;
  signIn: string;
  account: string;
  recommendations: string;
  watchlist: string;
  portfolioAdvisor: string;
  legal: string;
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
  pid?: number;
  requested_mode?: RefreshMode;
  started_at?: string;
  completed_at?: string;
  last_error?: string;
  report_generated_at_utc?: string;
  last_report?: RefreshReport;
};

type AdminUserSummary = {
  username: string;
  role: "admin" | "member";
  is_active: boolean;
  is_test_user: boolean;
  access_expires_at: string | null;
  created_at: string;
};

type SystemFileStatus = {
  key: string;
  path: string;
  exists: boolean;
  sizeBytes: number | null;
  mtimeUtc: string | null;
  modeOctal: string | null;
  isPrivate: boolean | null;
};

type SystemDirectoryStatus = {
  key: string;
  path: string;
  exists: boolean;
  entryCount: number | null;
  modeOctal: string | null;
};

type RefreshPolicyCheck = {
  key: string;
  ok: boolean;
  detail: string;
};

type RefreshPolicyHealth = {
  healthy: boolean;
  policyMap: {
    snapshot: string;
    universe_snapshot: string;
  };
  lastRequestedMode: RefreshMode | "unknown";
  lastError: string | null;
  checks: RefreshPolicyCheck[];
};

type SystemStatusPayload = {
  generatedAtUtc: string;
  users: {
    count: number;
    sourcePath: string;
  };
  auth: {
    adminMfaEnabled: boolean;
    activeAdminCount: number;
    activeMemberCount: number;
    activeDefaultAccounts: string[];
  };
  security: {
    allSecretsPrivate: boolean;
    secrets: SystemFileStatus[];
  };
  sesCore: {
    modulePath: string;
    modulePresent: boolean;
    moduleFileCount: number;
  };
  artifacts: SystemFileStatus[];
  directories: SystemDirectoryStatus[];
  reportSummary?: RefreshReport | null;
  refreshPolicy?: RefreshPolicyHealth | null;
};

type RefreshLogPayload = {
  exists: boolean;
  path: string;
  linesRequested: number;
  lineCount: number;
  updatedAtUtc: string | null;
  lines: string[];
};

type NoticeTone = "info" | "good" | "warn" | "error";

type NoticeState = {
  tone: NoticeTone;
  text: string;
};

const DEFAULT_IMAGES: UiBackgroundImages = {
  home: "/landing-zen.jpg",
  help: "/landing-zen.jpg",
  support: "/landing-zen.jpg",
  signIn: "/landing-zen.jpg",
  account: "/landing-zen.jpg",
  recommendations: "/landing-zen.jpg",
  watchlist: "/landing-zen.jpg",
  portfolioAdvisor: "/landing-zen.jpg",
  legal: "/landing-zen.jpg",
  adminConsole: "/landing-zen.jpg",
};

const PAGE_OPTIONS: Array<{ key: keyof UiBackgroundImages; label: string }> = [
  { key: "home", label: "Home" },
  { key: "help", label: "Help" },
  { key: "support", label: "Support" },
  { key: "signIn", label: "Sign In" },
  { key: "account", label: "Account" },
  { key: "recommendations", label: "Recommendations" },
  { key: "watchlist", label: "Watchlist" },
  { key: "portfolioAdvisor", label: "Portfolio" },
  { key: "legal", label: "Legal" },
  { key: "adminConsole", label: "Admin Console" },
];

const LOG_LINE_COUNT = 160;
const OPTIONAL_ARTIFACT_KEYS = new Set([
  "ingestion_verify",
  "audit_ab",
  "ab_adaptive_vs_fixed",
  "tau_d_filtered",
  "tau_d_full",
  "refresh_log",
]);

function modeLabel(mode: RefreshMode | undefined): string {
  if (mode === "universe_snapshot") return "Universe + Snapshot";
  if (mode === "snapshot") return "Snapshot";
  return "Not set";
}

function formatIso(iso: string | null | undefined): string {
  if (!iso) return "n/a";
  const value = Date.parse(iso);
  if (!Number.isFinite(value)) return iso;
  return new Date(value).toLocaleString();
}

function formatBytes(value: number | null | undefined): string {
  const n = Number(value ?? NaN);
  if (!Number.isFinite(n) || n < 0) return "n/a";
  if (n < 1024) return `${n} B`;
  const kb = n / 1024;
  if (kb < 1024) return `${kb.toFixed(1)} KB`;
  const mb = kb / 1024;
  if (mb < 1024) return `${mb.toFixed(1)} MB`;
  const gb = mb / 1024;
  return `${gb.toFixed(2)} GB`;
}

function displayPath(value: string): string {
  if (!value) return "n/a";
  const marker = "/workspaces/Tao_Financial_Engine/";
  if (value.includes(marker)) {
    return value.slice(value.indexOf(marker) + marker.length);
  }
  return value;
}

function isManagedSecretPath(value: string): boolean {
  return value.startsWith("aws-secretsmanager:") || value.startsWith("postgres://");
}

export default function AdminConsolePage() {
  const [images, setImages] = useState<UiBackgroundImages>(DEFAULT_IMAGES);
  const [notice, setNotice] = useState<NoticeState>({
    tone: "info",
    text: "Loading TFE admin command deck...",
  });

  const [savingImages, setSavingImages] = useState(false);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [syncingDeck, setSyncingDeck] = useState(false);
  const [uploadTarget, setUploadTarget] = useState<keyof UiBackgroundImages>("home");
  const [uploadFile, setUploadFile] = useState<File | null>(null);

  const [refreshStatus, setRefreshStatus] = useState<RefreshStatus | null>(null);
  const [refreshBusy, setRefreshBusy] = useState<RefreshMode | null>(null);
  const [refreshLog, setRefreshLog] = useState<RefreshLogPayload | null>(null);

  const [systemStatus, setSystemStatus] = useState<SystemStatusPayload | null>(null);

  const [testUsers, setTestUsers] = useState<AdminUserSummary[]>([]);
  const [testUsersSource, setTestUsersSource] = useState("");
  const [testUserUsername, setTestUserUsername] = useState("");
  const [testUserPassword, setTestUserPassword] = useState("");
  const [testUserPasswordConfirm, setTestUserPasswordConfirm] = useState("");
  const [showCreatePasswords, setShowCreatePasswords] = useState(false);
  const [testUserRole, setTestUserRole] = useState<"admin" | "member">("member");
  const [testUserExpiresDays, setTestUserExpiresDays] = useState("");
  const [testUserBusy, setTestUserBusy] = useState(false);
  const [resetUserUsername, setResetUserUsername] = useState("");
  const [resetUserPassword, setResetUserPassword] = useState("");
  const [resetUserPasswordConfirm, setResetUserPasswordConfirm] = useState("");
  const [showResetPasswords, setShowResetPasswords] = useState(false);
  const [resetUserBusy, setResetUserBusy] = useState(false);
  const [userActionBusy, setUserActionBusy] = useState<string | null>(null);
  const [userTableQuery, setUserTableQuery] = useState("");
  const [userTablePage, setUserTablePage] = useState(1);
  const [userTablePageSize, setUserTablePageSize] = useState(25);

  const refreshRunning = Boolean(refreshStatus?.running);

  const securityHeadline = useMemo(() => {
    if (!systemStatus) return "Loading";
    return systemStatus.security.allSecretsPrivate ? "Hardened" : "Action Needed";
  }, [systemStatus]);

  const userCount = useMemo(() => {
    if (testUsers.length > 0) return testUsers.length;
    return systemStatus?.users.count ?? 0;
  }, [testUsers, systemStatus]);

  const rowsWritten = useMemo(() => {
    return (
      refreshStatus?.last_report?.rows_written ??
      systemStatus?.reportSummary?.rows_written ??
      null
    );
  }, [refreshStatus, systemStatus]);

  const filteredTestUsers = useMemo(() => {
    const query = userTableQuery.trim().toLowerCase();
    if (!query) return testUsers;
    return testUsers.filter((user) => user.username.toLowerCase().includes(query));
  }, [testUsers, userTableQuery]);

  const userTablePageCount = useMemo(() => {
    if (filteredTestUsers.length === 0) return 1;
    return Math.ceil(filteredTestUsers.length / userTablePageSize);
  }, [filteredTestUsers.length, userTablePageSize]);

  const activeUserTablePage = useMemo(() => {
    return Math.min(userTablePage, userTablePageCount);
  }, [userTablePage, userTablePageCount]);

  const pagedTestUsers = useMemo(() => {
    const start = (activeUserTablePage - 1) * userTablePageSize;
    return filteredTestUsers.slice(start, start + userTablePageSize);
  }, [activeUserTablePage, filteredTestUsers, userTablePageSize]);

  const userTableDisplayStart = useMemo(() => {
    if (filteredTestUsers.length === 0) return 0;
    return (activeUserTablePage - 1) * userTablePageSize + 1;
  }, [activeUserTablePage, filteredTestUsers.length, userTablePageSize]);

  const userTableDisplayEnd = useMemo(() => {
    if (filteredTestUsers.length === 0) return 0;
    return Math.min(activeUserTablePage * userTablePageSize, filteredTestUsers.length);
  }, [activeUserTablePage, filteredTestUsers.length, userTablePageSize]);

  const refreshPolicyHeadline = useMemo(() => {
    if (!systemStatus?.refreshPolicy) return "Unknown";
    return systemStatus.refreshPolicy.healthy ? "Healthy" : "Action Needed";
  }, [systemStatus]);

  function pushNotice(tone: NoticeTone, text: string) {
    setNotice({ tone, text });
  }

  async function loadUiConfig(): Promise<void> {
    const response = await fetch("/api/admin/ui-config", { cache: "no-store" });
    if (!response.ok) {
      throw new Error("Failed to load UI config.");
    }

    const data = (await response.json()) as UiConfig;
    if (data.backgroundImages) {
      setImages(data.backgroundImages);
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

  async function loadSystemStatus(): Promise<void> {
    const response = await fetch("/api/admin/system-status", { cache: "no-store" });
    if (!response.ok) {
      throw new Error("Failed to load system status.");
    }

    const data = (await response.json()) as SystemStatusPayload;
    setSystemStatus(data);
  }

  async function loadTestUsers(): Promise<void> {
    const response = await fetch("/api/admin/test-users", { cache: "no-store" });
    if (!response.ok) {
      const data = (await response.json()) as { error?: string };
      throw new Error(data.error || "Failed to load test users.");
    }

    const data = (await response.json()) as {
      users?: AdminUserSummary[];
      source?: string;
    };

    setTestUsers(Array.isArray(data.users) ? data.users : []);
    setTestUsersSource(data.source ?? "");
  }

  async function reloadDeck(showNotice = false): Promise<void> {
    if (showNotice) {
      pushNotice("info", "Refreshing all admin panels...");
    }

    setSyncingDeck(true);
    try {
      await Promise.all([loadUiConfig(), loadRefreshStatus(), loadRefreshLog(), loadSystemStatus(), loadTestUsers()]);
      if (showNotice) {
        pushNotice("good", "Admin command deck synchronized.");
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Refresh failed.";
      pushNotice("error", message);
    }
    setSyncingDeck(false);
  }

  useEffect(() => {
    void reloadDeck(false);

    const pollTimer = window.setInterval(() => {
      void Promise.all([loadRefreshStatus(), loadRefreshLog()]).catch(() => {
        // polling failures are surfaced by manual refresh controls
      });
    }, 5000);

    return () => {
      window.clearInterval(pollTimer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (userTablePage > userTablePageCount) {
      setUserTablePage(userTablePageCount);
    }
  }, [userTablePage, userTablePageCount]);

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

      await Promise.all([loadRefreshStatus(), loadRefreshLog(), loadSystemStatus()]);
    } catch {
      pushNotice("error", "Refresh start failed.");
    }

    setRefreshBusy(null);
  }

  async function onCreateTestUser(): Promise<void> {
    const username = testUserUsername.trim().toLowerCase();
    const password = testUserPassword;
    const confirmPassword = testUserPasswordConfirm;

    if (!username) {
      pushNotice("warn", "Test username is required.");
      return;
    }

    if (!password) {
      pushNotice("warn", "Test password is required.");
      return;
    }

    if (!confirmPassword) {
      pushNotice("warn", "Confirm password is required.");
      return;
    }

    if (password !== confirmPassword) {
      pushNotice("warn", "Create password and confirm password must match.");
      return;
    }

    setTestUserBusy(true);

    try {
      const expiresInDays = testUserExpiresDays.trim() ? Number(testUserExpiresDays.trim()) : null;

      const response = await fetch("/api/admin/test-users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username,
          password,
          role: testUserRole,
          expiresInDays,
        }),
      });

      const data = (await response.json()) as {
        created?: AdminUserSummary;
        users?: AdminUserSummary[];
        source?: string;
        error?: string;
      };

      if (!response.ok || !data.created || !Array.isArray(data.users)) {
        pushNotice("error", data.error || "Test user creation failed.");
        setTestUserBusy(false);
        return;
      }

      setTestUsers(data.users);
      setTestUsersSource(data.source ?? "");
      setTestUserPassword("");
      setTestUserPasswordConfirm("");
      setTestUserExpiresDays("");

      await loadSystemStatus();
      pushNotice("good", `Test user created: ${data.created.username}`);
    } catch {
      pushNotice("error", "Test user creation failed.");
    }

    setTestUserBusy(false);
  }

  async function onResetUserPassword(): Promise<void> {
    const username = resetUserUsername.trim().toLowerCase();
    const password = resetUserPassword;
    const confirmPassword = resetUserPasswordConfirm;

    if (!username) {
      pushNotice("warn", "Reset username is required.");
      return;
    }

    if (!password) {
      pushNotice("warn", "New password is required.");
      return;
    }

    if (!confirmPassword) {
      pushNotice("warn", "Confirm password is required.");
      return;
    }

    if (password !== confirmPassword) {
      pushNotice("warn", "New password and confirm password must match.");
      return;
    }

    setResetUserBusy(true);

    try {
      const response = await fetch("/api/admin/test-users", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username,
          password,
        }),
      });

      const data = (await response.json()) as {
        updated?: AdminUserSummary;
        users?: AdminUserSummary[];
        source?: string;
        error?: string;
      };

      if (!response.ok || !data.updated || !Array.isArray(data.users)) {
        pushNotice("error", data.error || "Password reset failed.");
        setResetUserBusy(false);
        return;
      }

      setTestUsers(data.users);
      setTestUsersSource(data.source ?? "");
      setResetUserPassword("");
      setResetUserPasswordConfirm("");
      await loadSystemStatus();
      pushNotice("good", `Password reset for: ${data.updated.username}`);
    } catch {
      pushNotice("error", "Password reset failed.");
    }

    setResetUserBusy(false);
  }

  async function onToggleUserActive(user: AdminUserSummary, nextActive: boolean): Promise<void> {
    const label = `${nextActive ? "enable" : "disable"}:${user.username}`;
    setUserActionBusy(label);

    try {
      const response = await fetch("/api/admin/test-users", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: user.username,
          isActive: nextActive,
        }),
      });

      const data = (await response.json()) as {
        updated?: AdminUserSummary;
        users?: AdminUserSummary[];
        source?: string;
        error?: string;
      };

      if (!response.ok || !data.updated || !Array.isArray(data.users)) {
        pushNotice("error", data.error || "User status update failed.");
        setUserActionBusy(null);
        return;
      }

      setTestUsers(data.users);
      setTestUsersSource(data.source ?? "");
      await loadSystemStatus();
      pushNotice("good", `${nextActive ? "Enabled" : "Disabled"} account: ${data.updated.username}`);
    } catch {
      pushNotice("error", "User status update failed.");
    }

    setUserActionBusy(null);
  }

  async function onRemoveUser(user: AdminUserSummary): Promise<void> {
    const confirmed = window.confirm(`Remove account '${user.username}'? This cannot be undone.`);
    if (!confirmed) return;

    const label = `remove:${user.username}`;
    setUserActionBusy(label);

    try {
      const response = await fetch(`/api/admin/test-users?username=${encodeURIComponent(user.username)}`, {
        method: "DELETE",
      });

      const data = (await response.json()) as {
        removed?: AdminUserSummary;
        users?: AdminUserSummary[];
        source?: string;
        error?: string;
      };

      if (!response.ok || !data.removed || !Array.isArray(data.users)) {
        pushNotice("error", data.error || "User removal failed.");
        setUserActionBusy(null);
        return;
      }

      setTestUsers(data.users);
      setTestUsersSource(data.source ?? "");
      await loadSystemStatus();
      pushNotice("good", `Removed account: ${data.removed.username}`);
    } catch {
      pushNotice("error", "User removal failed.");
    }

    setUserActionBusy(null);
  }

  async function onUploadImage(): Promise<void> {
    if (!uploadFile) {
      pushNotice("warn", "Choose an image file before upload.");
      return;
    }

    setUploadingImage(true);
    pushNotice("info", "Uploading image...");

    try {
      const form = new FormData();
      form.append("file", uploadFile);
      form.append("pageKey", uploadTarget);

      const response = await fetch("/api/admin/upload-image", {
        method: "POST",
        body: form,
      });

      const data = (await response.json()) as { path?: string; error?: string };
      if (!response.ok || !data.path) {
        pushNotice("error", data.error || "Upload failed.");
        setUploadingImage(false);
        return;
      }

      setImages((prev) => ({ ...prev, [uploadTarget]: data.path as string }));
      setUploadFile(null);
      pushNotice("good", `Upload complete for ${PAGE_OPTIONS.find((p) => p.key === uploadTarget)?.label}. Save backgrounds to persist.`);
    } catch {
      pushNotice("error", "Upload failed.");
    }

    setUploadingImage(false);
  }

  async function onSaveBackgrounds(): Promise<void> {
    setSavingImages(true);
    pushNotice("info", "Saving page background paths...");

    try {
      const response = await fetch("/api/admin/ui-config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ backgroundImages: images }),
      });

      const data = (await response.json()) as UiConfig & { error?: string };
      if (!response.ok) {
        pushNotice("error", data.error || "Save failed.");
        setSavingImages(false);
        return;
      }

      if (data.backgroundImages) {
        setImages(data.backgroundImages);
      }

      pushNotice("good", "Background paths saved.");
    } catch {
      pushNotice("error", "Save failed.");
    }

    setSavingImages(false);
  }

  function updateField(key: keyof UiBackgroundImages, value: string) {
    setImages((prev) => ({ ...prev, [key]: value }));
  }

  return (
    <SiteFrame pageBackgroundImage={images.adminConsole}>
      <section className={styles.deck}>
        <header className={styles.hero}>
          <div>
            <p className={styles.kicker}>Tao Financial Engine</p>
            <h1 className={styles.title}>Admin Command Deck</h1>
            <p className={styles.subtitle}>
              One place to run market refresh jobs, manage secure test access, verify SES-core posture, and control UI assets.
            </p>
          </div>

          <div className={styles.heroActionRow}>
            <button className={styles.primaryButton} type="button" onClick={() => void reloadDeck(true)} disabled={syncingDeck}>
              {syncingDeck ? "Syncing..." : "Sync All Panels"}
            </button>
            <button className={styles.ghostButton} type="button" onClick={() => window.location.reload()}>
              Hard Refresh Page
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

        <div className={styles.metrics}>
          <article className={styles.metricCard}>
            <div className={styles.metricLabel}>Refresh Engine</div>
            <div className={styles.metricValue}>{refreshRunning ? "Running" : "Idle"}</div>
            <div className={styles.metricHint}>Mode: {modeLabel(refreshStatus?.requested_mode)}</div>
          </article>

          <article className={styles.metricCard}>
            <div className={styles.metricLabel}>Latest Snapshot Rows</div>
            <div className={styles.metricValue}>{rowsWritten ?? "n/a"}</div>
            <div className={styles.metricHint}>Last generated: {formatIso(refreshStatus?.last_report?.generated_at_utc)}</div>
          </article>

          <article className={styles.metricCard}>
            <div className={styles.metricLabel}>Total Users</div>
            <div className={styles.metricValue}>{userCount}</div>
            <div className={styles.metricHint}>Source: {displayPath(testUsersSource || systemStatus?.users.sourcePath || "")}</div>
          </article>

          <article className={styles.metricCard}>
            <div className={styles.metricLabel}>Security Posture</div>
            <div className={styles.metricValue}>{securityHeadline}</div>
            <div className={styles.metricHint}>SES-core module files: {systemStatus?.sesCore.moduleFileCount ?? "n/a"}</div>
          </article>
        </div>

        <div className={styles.gridTwo}>
          <article className={styles.panel}>
            <header className={styles.panelHeader}>
              <h2 className={styles.panelTitle}>Market Operations</h2>
              <p className={styles.panelSub}>Run UF snapshot jobs and monitor progress in real time.</p>
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

              <button className={styles.secondaryButton} type="button" onClick={() => void loadRefreshStatus().then(() => loadRefreshLog())}>
                Poll Now
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
                <div className={styles.kvLabel}>Started</div>
                <div className={styles.kvValue}>{formatIso(refreshStatus?.started_at)}</div>
              </div>
              <div className={styles.kvItem}>
                <div className={styles.kvLabel}>Completed</div>
                <div className={styles.kvValue}>{formatIso(refreshStatus?.completed_at)}</div>
              </div>
              <div className={styles.kvItem}>
                <div className={styles.kvLabel}>Report</div>
                <div className={styles.kvValue}>{refreshStatus?.last_report?.status || "n/a"}</div>
              </div>
            </div>

            {systemStatus?.refreshPolicy ? (
              <div className={styles.keyValueGrid}>
                <div className={styles.kvItem}>
                  <div className={styles.kvLabel}>Refresh Policy</div>
                  <div className={styles.kvValue}>
                    <span className={systemStatus.refreshPolicy.healthy ? styles.chipGood : styles.chipWarn}>{refreshPolicyHeadline}</span>
                  </div>
                </div>
                <div className={styles.kvItem}>
                  <div className={styles.kvLabel}>Policy Map</div>
                  <div className={styles.kvValue}>
                    snapshot={systemStatus.refreshPolicy.policyMap.snapshot} | universe={systemStatus.refreshPolicy.policyMap.universe_snapshot}
                  </div>
                </div>
                <div className={styles.kvItem}>
                  <div className={styles.kvLabel}>Last Mode</div>
                  <div className={styles.kvValue}>{modeLabel(systemStatus.refreshPolicy.lastRequestedMode === "unknown" ? undefined : systemStatus.refreshPolicy.lastRequestedMode)}</div>
                </div>
                <div className={styles.kvItem}>
                  <div className={styles.kvLabel}>Last Error</div>
                  <div className={styles.kvValue}>{systemStatus.refreshPolicy.lastError || "none"}</div>
                </div>
              </div>
            ) : null}

            {systemStatus?.refreshPolicy?.checks?.length ? (
              <div className={styles.scrollWrap} style={{ maxHeight: 180 }}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>Policy Check</th>
                      <th>Status</th>
                      <th>Detail</th>
                    </tr>
                  </thead>
                  <tbody>
                    {systemStatus.refreshPolicy.checks.map((check) => (
                      <tr key={check.key}>
                        <td>{check.key}</td>
                        <td>
                          <span className={check.ok ? styles.chipGood : styles.chipWarn}>{check.ok ? "ok" : "issue"}</span>
                        </td>
                        <td>{check.detail}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}

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
          </article>

          <article className={styles.panel}>
            <header className={styles.panelHeader}>
              <h2 className={styles.panelTitle}>Security + SES-Core</h2>
              <p className={styles.panelSub}>Live hardening visibility for secrets, artifacts, and SES-core module readiness.</p>
            </header>

            <div className={styles.keyValueGrid}>
              <div className={styles.kvItem}>
                <div className={styles.kvLabel}>Secret Files</div>
                <div className={styles.kvValue}>
                  <span className={systemStatus?.security.allSecretsPrivate ? styles.chipGood : styles.chipBad}>
                    {systemStatus?.security.allSecretsPrivate ? "Owner-only" : "Needs hardening"}
                  </span>
                </div>
              </div>
              <div className={styles.kvItem}>
                <div className={styles.kvLabel}>SES-Core Module</div>
                <div className={styles.kvValue}>
                  {systemStatus?.sesCore.modulePresent ? "Present" : "Missing"} ({systemStatus?.sesCore.moduleFileCount ?? 0} files)
                </div>
              </div>
              <div className={styles.kvItem}>
                <div className={styles.kvLabel}>UF Report Status</div>
                <div className={styles.kvValue}>{systemStatus?.reportSummary?.status || "n/a"}</div>
              </div>
              <div className={styles.kvItem}>
                <div className={styles.kvLabel}>Admin MFA</div>
                <div className={styles.kvValue}>
                  <span className={systemStatus?.auth.adminMfaEnabled ? styles.chipGood : styles.chipWarn}>
                    {systemStatus?.auth.adminMfaEnabled ? "Enabled" : "Not configured"}
                  </span>
                </div>
              </div>
              <div className={styles.kvItem}>
                <div className={styles.kvLabel}>Default Accounts</div>
                <div className={styles.kvValue}>
                  {systemStatus?.auth.activeDefaultAccounts?.length
                    ? systemStatus.auth.activeDefaultAccounts.join(", ")
                    : "none active"}
                </div>
              </div>
              <div className={styles.kvItem}>
                <div className={styles.kvLabel}>System Scan Time</div>
                <div className={styles.kvValue}>{formatIso(systemStatus?.generatedAtUtc)}</div>
              </div>
            </div>

            <div className={styles.scrollWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Secret</th>
                    <th>Mode</th>
                    <th>Size</th>
                    <th>Updated</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {(systemStatus?.security.secrets ?? []).map((item) => (
                    <tr key={item.key}>
                      <td title={item.path}>{displayPath(item.path)}</td>
                      <td>{item.modeOctal ? `0${item.modeOctal}` : isManagedSecretPath(item.path) ? "managed" : "n/a"}</td>
                      <td>{item.sizeBytes !== null ? formatBytes(item.sizeBytes) : isManagedSecretPath(item.path) ? "managed" : "n/a"}</td>
                      <td>{formatIso(item.mtimeUtc)}</td>
                      <td>
                        <span
                          className={
                            item.exists && item.isPrivate
                              ? styles.chipGood
                              : item.exists
                                ? styles.chipWarn
                                : styles.chipBad
                          }
                        >
                          {item.exists ? (item.isPrivate ? "Secure" : "Too open") : "Missing"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className={styles.artifactGrid}>
              {(systemStatus?.artifacts ?? []).map((item) => (
                <div className={styles.artifactCard} key={item.key}>
                  <div className={styles.artifactTitle}>{item.key}</div>
                  <div className={styles.artifactPath} title={item.path}>
                    {displayPath(item.path)}
                  </div>
                  <div className={styles.artifactMeta}>
                    <span>{item.exists ? "Present" : OPTIONAL_ARTIFACT_KEYS.has(item.key) ? "Missing (optional)" : "Missing"}</span>
                    <span>{formatBytes(item.sizeBytes)}</span>
                  </div>
                </div>
              ))}
            </div>
          </article>
        </div>

        <div className={styles.gridTwo}>
          <article className={styles.panel}>
            <header className={styles.panelHeader}>
              <h2 className={styles.panelTitle}>Test Access Control</h2>
              <p className={styles.panelSub}>Create tenant test accounts and validate role-based permissions quickly.</p>
            </header>

            <div className={styles.formGrid}>
              <label className={styles.field}>
                <span>Username</span>
                <input
                  className={styles.input}
                  type="text"
                  value={testUserUsername}
                  onChange={(event) => setTestUserUsername(event.target.value)}
                  placeholder="qa_user_01"
                />
              </label>

              <label className={styles.field}>
                <span>Password</span>
                <input
                  className={styles.input}
                  type={showCreatePasswords ? "text" : "password"}
                  value={testUserPassword}
                  onChange={(event) => setTestUserPassword(event.target.value)}
                  placeholder="Minimum 10 characters"
                  autoComplete="new-password"
                />
              </label>

              <label className={styles.field}>
                <span>Confirm Password</span>
                <input
                  className={styles.input}
                  type={showCreatePasswords ? "text" : "password"}
                  value={testUserPasswordConfirm}
                  onChange={(event) => setTestUserPasswordConfirm(event.target.value)}
                  placeholder="Re-enter password"
                  autoComplete="new-password"
                />
              </label>

              <label className={styles.field}>
                <span>Role</span>
                <select
                  className={styles.select}
                  value={testUserRole}
                  onChange={(event) => setTestUserRole(event.target.value === "admin" ? "admin" : "member")}
                >
                  <option value="member">member</option>
                  <option value="admin">admin</option>
                </select>
              </label>

              <label className={styles.field}>
                <span>Access Days (optional)</span>
                <input
                  className={styles.input}
                  type="number"
                  min={1}
                  step={1}
                  value={testUserExpiresDays}
                  onChange={(event) => setTestUserExpiresDays(event.target.value)}
                  placeholder="Blank = no expiry"
                />
              </label>
            </div>

            <label className={styles.inlineMsg} style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
              <input
                type="checkbox"
                checked={showCreatePasswords}
                onChange={(event) => setShowCreatePasswords(event.target.checked)}
              />
              Show create password while typing
            </label>

            <div className={styles.buttonRow}>
              <button className={styles.opButton} type="button" onClick={() => void onCreateTestUser()} disabled={testUserBusy}>
                {testUserBusy ? "Creating..." : "Create Test User"}
              </button>
            </div>

            <div className={styles.formGrid}>
              <label className={styles.field}>
                <span>Reset Username</span>
                <input
                  className={styles.input}
                  type="text"
                  value={resetUserUsername}
                  onChange={(event) => setResetUserUsername(event.target.value)}
                  placeholder="existing_user"
                />
              </label>

              <label className={styles.field}>
                <span>New Password</span>
                <input
                  className={styles.input}
                  type={showResetPasswords ? "text" : "password"}
                  value={resetUserPassword}
                  onChange={(event) => setResetUserPassword(event.target.value)}
                  placeholder="Minimum 10 characters"
                  autoComplete="new-password"
                />
              </label>

              <label className={styles.field}>
                <span>Confirm New Password</span>
                <input
                  className={styles.input}
                  type={showResetPasswords ? "text" : "password"}
                  value={resetUserPasswordConfirm}
                  onChange={(event) => setResetUserPasswordConfirm(event.target.value)}
                  placeholder="Re-enter new password"
                  autoComplete="new-password"
                />
              </label>
            </div>

            <label className={styles.inlineMsg} style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
              <input
                type="checkbox"
                checked={showResetPasswords}
                onChange={(event) => setShowResetPasswords(event.target.checked)}
              />
              Show reset password while typing
            </label>

            <div className={styles.buttonRow}>
              <button className={styles.opButton} type="button" onClick={() => void onResetUserPassword()} disabled={resetUserBusy}>
                {resetUserBusy ? "Resetting..." : "Reset Password"}
              </button>
            </div>

            <p className={styles.inlineMsg}>User store: {displayPath(testUsersSource || systemStatus?.users.sourcePath || "")}</p>

            <div className={styles.tableControls}>
              <label className={styles.tableControlField}>
                <span>Search username</span>
                <input
                  className={styles.input}
                  type="text"
                  value={userTableQuery}
                  onChange={(event) => {
                    setUserTableQuery(event.target.value);
                    setUserTablePage(1);
                  }}
                  placeholder="Filter users by username"
                />
              </label>

              <label className={styles.tableControlField}>
                <span>Rows per page</span>
                <select
                  className={styles.select}
                  value={String(userTablePageSize)}
                  onChange={(event) => {
                    const parsed = Number(event.target.value);
                    if (!Number.isFinite(parsed)) return;
                    setUserTablePageSize(parsed);
                    setUserTablePage(1);
                  }}
                >
                  <option value="10">10</option>
                  <option value="25">25</option>
                  <option value="50">50</option>
                  <option value="100">100</option>
                </select>
              </label>

              <div className={styles.tablePager}>
                <span className={styles.inlineMsg}>
                  Showing {userTableDisplayStart}-{userTableDisplayEnd} of {filteredTestUsers.length}
                </span>
                <button
                  className={styles.ghostButton}
                  type="button"
                  onClick={() => setUserTablePage((prev) => Math.max(1, prev - 1))}
                  disabled={activeUserTablePage <= 1}
                >
                  Prev
                </button>
                <button
                  className={styles.ghostButton}
                  type="button"
                  onClick={() => setUserTablePage((prev) => Math.min(userTablePageCount, prev + 1))}
                  disabled={activeUserTablePage >= userTablePageCount}
                >
                  Next
                </button>
                <span className={styles.inlineMsg}>
                  Page {activeUserTablePage} / {userTablePageCount}
                </span>
              </div>
            </div>

            <div className={`${styles.scrollWrap} ${styles.userTableWrap}`}>
              <table className={`${styles.table} ${styles.userTable}`}>
                <thead>
                  <tr>
                    <th>Username</th>
                    <th>Role</th>
                    <th>Active</th>
                    <th>Test</th>
                    <th>Expires</th>
                    <th>Created</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {pagedTestUsers.length === 0 ? (
                    <tr>
                      <td colSpan={7}>No users match the current filter.</td>
                    </tr>
                  ) : (
                    pagedTestUsers.map((user) => (
                      <tr key={user.username}>
                        <td>{user.username}</td>
                        <td>{user.role}</td>
                        <td>{user.is_active ? "Yes" : "No"}</td>
                        <td>{user.is_test_user ? "Yes" : "No"}</td>
                        <td>{formatIso(user.access_expires_at)}</td>
                        <td>{formatIso(user.created_at)}</td>
                        <td>
                          <div className={styles.buttonRow}>
                            <button
                              className={styles.secondaryButton}
                              type="button"
                              onClick={() => void onToggleUserActive(user, !user.is_active)}
                              disabled={userActionBusy === `${user.is_active ? "disable" : "enable"}:${user.username}`}
                            >
                              {user.is_active ? "Disable" : "Enable"}
                            </button>
                            <button
                              className={styles.ghostButton}
                              type="button"
                              onClick={() => void onRemoveUser(user)}
                              disabled={userActionBusy === `remove:${user.username}`}
                            >
                              Remove
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </article>

          <article className={styles.panel}>
            <header className={styles.panelHeader}>
              <h2 className={styles.panelTitle}>UI Asset Control</h2>
              <p className={styles.panelSub}>Upload and map per-page background art used across the TFE experience.</p>
            </header>

            <div className={styles.formGrid}>
              <label className={styles.field}>
                <span>Upload target page</span>
                <select
                  className={styles.select}
                  value={uploadTarget}
                  onChange={(event) => setUploadTarget(event.target.value as keyof UiBackgroundImages)}
                >
                  {PAGE_OPTIONS.map((option) => (
                    <option key={option.key} value={option.key}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className={styles.field}>
                <span>Image file (JPG/PNG/WEBP, max 8MB)</span>
                <input
                  className={styles.input}
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={(event) => setUploadFile(event.target.files?.[0] || null)}
                />
              </label>
            </div>

            <div className={styles.buttonRow}>
              <button className={styles.opButton} type="button" onClick={() => void onUploadImage()} disabled={uploadingImage}>
                {uploadingImage ? "Uploading..." : "Upload to Target"}
              </button>

              <button className={styles.primaryButton} type="button" onClick={() => void onSaveBackgrounds()} disabled={savingImages}>
                {savingImages ? "Saving..." : "Save All Background Paths"}
              </button>
            </div>

            <div className={styles.assetList}>
              {PAGE_OPTIONS.map((option) => (
                <div className={styles.assetRow} key={option.key}>
                  <label className={styles.assetLabel} htmlFor={`bg-${option.key}`}>
                    {option.label}
                  </label>
                  <input
                    id={`bg-${option.key}`}
                    className={styles.assetInput}
                    type="text"
                    value={images[option.key]}
                    onChange={(event) => updateField(option.key, event.target.value)}
                  />
                  <div className={styles.assetPreview}>
                    {images[option.key] ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img className={styles.assetThumb} src={images[option.key]} alt={`${option.label} preview`} />
                    ) : (
                      <span className={styles.pathText}>No image</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </article>
        </div>
      </section>
    </SiteFrame>
  );
}
