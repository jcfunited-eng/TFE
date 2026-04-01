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
  screener: string;
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
  snapshotSummary?: {
    rowCount: number;
    sourcePath: string | null;
    sourceMtimeUtc: string | null;
  } | null;
  refreshPolicy?: RefreshPolicyHealth | null;
};

type ModelAccuracyHorizon = {
  horizon_days: number;
  evaluations: number | null;
  beat_benchmark_pct: number | null;
  beat_benchmark_raw_pct: number | null;
  action_mean_return_pct: number | null;
  excess_mean_return_pct: number | null;
  excess_positive_rate_pct: number | null;
  mapped_rate_pct: number | null;
};

type ModelAccuracyPayload = {
  exists: boolean;
  source?: string;
  reportPath: string;
  currentEvalPath: string | null;
  generatedAtUtc: string | null;
  reportUpdatedAtUtc?: string | null;
  updatedAtUtc: string | null;
  liveEligible?: boolean;
  liveEpochStartUtc?: string | null;
  daysSinceLiveEpoch?: number | null;
  liveMinDays?: number | null;
  horizons: ModelAccuracyHorizon[];
  methodology?: string;
  message?: string;
  warning?: string;
  error?: string;
};

type RecommendationQualityWinner = {
  variant_name: string | null;
  source_mode: string | null;
  eval_mode: string | null;
  min_bars: number | null;
  policy_path: string | null;
  gates: {
    gate_5day: boolean;
    gate_20day: boolean;
    gate_60day: boolean;
    gate_sp_plus_4_proxy_avg: boolean;
    gate_coverage: boolean;
    gate_fallback: boolean;
    quality_gate_count: number;
    reliability_gate_count: number;
    total_gate_count: number;
  };
  horizon_outcome_over_index_pct: {
    "5": number | null;
    "20": number | null;
    "60": number | null;
  };
  avg_outcome_over_index_pct: number | null;
  coverage_rate: number | null;
  fallback_rate: number | null;
  reason: string | null;
};

type Cp2AuditContext = {
  profile: string | null;
  decisionPhysics: string | null;
  totalRows: number | null;
  evaluatedRows: number | null;
  fallbackRows: number | null;
  accumulateDecisionsInWindow: number | null;
  historyWindowDays: number | null;
  reasonCodeDistribution: Record<string, number> | null;
};

type RecommendationQualityPayload = {
  exists: boolean;
  status: string | null;
  generatedAtUtc: string | null;
  cpProfile: string | null;
  laneDir: string | null;
  summaryPath: string | null;
  rankedTablePath: string | null;
  methodology: string | null;
  targets: {
    target_5: number | null;
    target_20: number | null;
    target_60: number | null;
    target_avg: number | null;
    target_coverage: number | null;
    target_fallback_max: number | null;
  };
  winner: RecommendationQualityWinner | null;
  cp2?: Cp2AuditContext | null;
  error?: string;
};

type SignalFilterSector = {
  sector: string;
  count: number;
  pct: number;
};

type SignalFilterFieldStats = {
  min: number | null;
  p25: number | null;
  median: number | null;
  p75: number | null;
  max: number | null;
  populated: number;
  populationPct: number;
};

type SignalLaneResult = {
  label: string;
  thresholds: Record<string, number>;
  backtestWinRate: number;
  backtestN: number;
  survivors: number;
  survivorSymbols: string[];
  sectorConcentration: SignalFilterSector[];
};

type SignalLaneAResult = SignalLaneResult & { fnStats: SignalFilterFieldStats };

type SignalFilterPayload = {
  generatedAtUtc: string;
  totalAccumulate: number;
  laneA: SignalLaneAResult;
  laneB: SignalLaneResult;
  baselineWinRate: number;
  error?: string;
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
  screener: "/landing-zen.jpg",
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
  { key: "screener", label: "Screener" },
  { key: "watchlist", label: "Watchlist" },
  { key: "portfolioAdvisor", label: "Portfolio" },
  { key: "legal", label: "Legal" },
  { key: "adminConsole", label: "Admin Console" },
];

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

function parseIsoMs(iso: string | null | undefined): number | null {
  if (!iso) return null;
  const value = Date.parse(iso);
  if (!Number.isFinite(value)) return null;
  return value;
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

function formatPercent(value: number | null | undefined, digits = 1): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return "n/a";
  return `${n.toFixed(digits)}%`;
}

function clampPercent(value: number | null | undefined): number {
  const n = Number(value);
  if (!Number.isFinite(n)) return 0;
  if (n <= 0) return 0;
  if (n >= 100) return 100;
  return n;
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
  const [killBusy, setKillBusy] = useState(false);
  const [showKillConfirm, setShowKillConfirm] = useState(false);
  const [modelAccuracy, setModelAccuracy] = useState<ModelAccuracyPayload | null>(null);
  const [recommendationQuality, setRecommendationQuality] = useState<RecommendationQualityPayload | null>(null);
  const [signalFilter, setSignalFilter] = useState<SignalFilterPayload | null>(null);

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
  const killRequested = Boolean(refreshStatus?.kill_requested);

  const securityHeadline = useMemo(() => {
    if (!systemStatus) return "Loading";
    return systemStatus.security.allSecretsPrivate ? "Hardened" : "Action Needed";
  }, [systemStatus]);

  const userCount = useMemo(() => {
    if (testUsers.length > 0) return testUsers.length;
    return systemStatus?.users.count ?? 0;
  }, [testUsers, systemStatus]);

  const rowsWritten = useMemo(() => {
    const candidates: Array<{ rows: number | null | undefined; generatedAt: string | null | undefined }> = [
      {
        rows: systemStatus?.snapshotSummary?.rowCount,
        generatedAt: systemStatus?.snapshotSummary?.sourceMtimeUtc,
      },
      {
        rows: refreshStatus?.last_report?.rows_written,
        generatedAt: refreshStatus?.last_report?.generated_at_utc ?? refreshStatus?.report_generated_at_utc,
      },
      {
        rows: systemStatus?.reportSummary?.rows_written,
        generatedAt: systemStatus?.reportSummary?.generated_at_utc,
      },
    ];

    let selectedRows: number | null = null;
    let selectedTime = Number.NEGATIVE_INFINITY;

    for (const candidate of candidates) {
      const rows = Number(candidate.rows);
      if (!Number.isFinite(rows) || rows < 0) continue;
      const timestamp = parseIsoMs(candidate.generatedAt);
      const compareTime = timestamp ?? Number.NEGATIVE_INFINITY;
      if (compareTime >= selectedTime) {
        selectedRows = rows;
        selectedTime = compareTime;
      }
    }

    if (selectedRows !== null) return selectedRows;
    return null;
  }, [refreshStatus, systemStatus]);

  const latestSnapshotGeneratedAt = useMemo(() => {
    const candidates = [
      systemStatus?.snapshotSummary?.sourceMtimeUtc,
      refreshStatus?.last_report?.generated_at_utc,
      refreshStatus?.report_generated_at_utc,
      systemStatus?.reportSummary?.generated_at_utc,
      refreshStatus?.completed_at,
    ].filter((value): value is string => Boolean(value));

    let selected: string | null = null;
    let selectedTime = Number.NEGATIVE_INFINITY;

    for (const candidate of candidates) {
      const timestamp = parseIsoMs(candidate);
      if (timestamp === null) continue;
      if (timestamp >= selectedTime) {
        selected = candidate;
        selectedTime = timestamp;
      }
    }

    return selected;
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

  async function loadModelAccuracy(): Promise<void> {
    const response = await fetch("/api/admin/model-accuracy", { cache: "no-store" });
    if (!response.ok) {
      throw new Error("Failed to load model accuracy.");
    }

    const data = (await response.json()) as ModelAccuracyPayload;
    setModelAccuracy(data);
  }

  async function loadRecommendationQuality(): Promise<void> {
    const response = await fetch("/api/admin/recommendation-quality", { cache: "no-store" });
    if (!response.ok) {
      throw new Error("Failed to load recommendation quality.");
    }

    const data = (await response.json()) as RecommendationQualityPayload;
    setRecommendationQuality(data);
  }

  async function loadSignalFilter(): Promise<void> {
    const response = await fetch("/api/admin/signal-filter", { cache: "no-store" });
    if (!response.ok) return;
    const data = (await response.json()) as SignalFilterPayload;
    setSignalFilter(data);
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
      await Promise.all([
        loadUiConfig(),
        loadRefreshStatus(),
        loadModelAccuracy(),
        loadRecommendationQuality(),
        loadSignalFilter(),
        loadSystemStatus(),
        loadTestUsers(),
      ]);
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
      void Promise.all([loadRefreshStatus(), loadModelAccuracy(), loadRecommendationQuality(), loadSystemStatus()]).catch(() => {
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

      await Promise.all([loadRefreshStatus(), loadSystemStatus()]);
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
      await Promise.all([loadRefreshStatus(), loadSystemStatus()]);
    } catch (error) {
      pushNotice("error", error instanceof Error ? error.message : "Kill request failed.");
    } finally {
      setKillBusy(false);
    }
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
            <div className={styles.metricHint}>Last generated: {formatIso(latestSnapshotGeneratedAt)}</div>
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

              <button
                className={styles.secondaryButton}
                type="button"
                onClick={() => void Promise.all([loadRefreshStatus(), loadModelAccuracy(), loadSystemStatus()])}
              >
                Poll Now
              </button>

              <button
                className={styles.ghostButton}
                type="button"
                onClick={() => (window.location.href = "/admin-console/refresh-log")}
              >
                Open Dedicated Refresh Log Page
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
                <div className={styles.kvLabel}>Kill State</div>
                <div className={styles.kvValue}>
                  {killRequested
                    ? `Requested by ${refreshStatus?.kill_requested_by ?? "admin"}`
                    : "Clear"}
                </div>
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

            <div className={styles.accuracyPanel}>
              <div className={styles.logMeta}>
                <strong>Realized Decision Accuracy (5 / 20 / 60 Day)</strong>
                <span>
                  {modelAccuracy?.liveEligible === false
                    ? modelAccuracy?.message || "Live maturity gate active"
                    : modelAccuracy?.exists
                      ? `Updated: ${formatIso(modelAccuracy?.updatedAtUtc)}`
                      : "No accuracy report yet"}
                </span>
              </div>

              {modelAccuracy?.exists && modelAccuracy.horizons?.length ? (
                <div className={styles.accuracyGrid}>
                  {modelAccuracy.horizons.map((horizon) => (
                    <div key={horizon.horizon_days} className={styles.accuracyTile}>
                      <div className={styles.accuracyHorizon}>{horizon.horizon_days}D</div>
                      <div className={styles.accuracyValue}>{formatPercent(horizon.beat_benchmark_pct, 1)}</div>
                      <div className={styles.accuracyGauge}>
                        <span className={styles.accuracyGaugeFill} style={{ width: `${clampPercent(horizon.beat_benchmark_pct)}%` }} />
                      </div>
                      <div className={styles.accuracyMeta}>
                        n={horizon.evaluations ?? "n/a"} | alpha={formatPercent(horizon.excess_mean_return_pct, 2)} | win={formatPercent(horizon.excess_positive_rate_pct, 1)}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className={styles.inlineMsg}>
                  No realized horizon accuracy file available yet. Run a refresh with L5 learning to generate it.
                  {modelAccuracy?.liveEligible === false && modelAccuracy?.liveEpochStartUtc
                    ? ` Live epoch start: ${formatIso(modelAccuracy.liveEpochStartUtc)}.`
                    : ""}
                  {modelAccuracy?.error ? ` (${modelAccuracy.error})` : ""}
                </p>
              )}

              {modelAccuracy?.warning ? <p className={styles.inlineMsg}>Warning: {modelAccuracy.warning}</p> : null}
              {modelAccuracy?.methodology ? <p className={styles.inlineMsg}>Method: {modelAccuracy.methodology}</p> : null}
            </div>

            <div className={styles.qualityPanel}>
              <div className={styles.logMeta}>
                <strong>Recommendation Quality Status (Beat S&P 500)</strong>
                <span>
                  {recommendationQuality?.exists
                    ? `Updated: ${formatIso(recommendationQuality.generatedAtUtc)}`
                    : "No quality audit summary yet"}
                </span>
              </div>

              {recommendationQuality?.exists && recommendationQuality.winner ? (
                <>
                  <div className={styles.qualityGrid}>
                    <div className={styles.qualityTile}>
                      <div className={styles.qualityLabel}>5D</div>
                      <div className={styles.qualityValue}>{formatPercent(recommendationQuality.winner.horizon_outcome_over_index_pct["5"], 1)}</div>
                      <div className={styles.qualityTarget}>
                        Target {formatPercent(recommendationQuality.targets.target_5, 1)}
                      </div>
                    </div>
                    <div className={styles.qualityTile}>
                      <div className={styles.qualityLabel}>20D</div>
                      <div className={styles.qualityValue}>{formatPercent(recommendationQuality.winner.horizon_outcome_over_index_pct["20"], 1)}</div>
                      <div className={styles.qualityTarget}>
                        Target {formatPercent(recommendationQuality.targets.target_20, 1)}
                      </div>
                    </div>
                    <div className={styles.qualityTile}>
                      <div className={styles.qualityLabel}>60D</div>
                      <div className={styles.qualityValue}>{formatPercent(recommendationQuality.winner.horizon_outcome_over_index_pct["60"], 1)}</div>
                      <div className={styles.qualityTarget}>
                        Target {formatPercent(recommendationQuality.targets.target_60, 1)}
                      </div>
                    </div>
                    <div className={styles.qualityTile}>
                      <div className={styles.qualityLabel}>Avg</div>
                      <div className={styles.qualityValue}>{formatPercent(recommendationQuality.winner.avg_outcome_over_index_pct, 1)}</div>
                      <div className={styles.qualityTarget}>
                        Target {formatPercent(recommendationQuality.targets.target_avg, 1)}
                      </div>
                    </div>
                  </div>

                  <div className={styles.keyValueGrid}>
                    <div className={styles.kvItem}>
                      <div className={styles.kvLabel}>Coverage</div>
                      <div className={styles.kvValue}>{formatPercent((recommendationQuality.winner.coverage_rate ?? 0) * 100, 1)}</div>
                    </div>
                    <div className={styles.kvItem}>
                      <div className={styles.kvLabel}>Fallback</div>
                      <div className={styles.kvValue}>{formatPercent((recommendationQuality.winner.fallback_rate ?? 0) * 100, 1)}</div>
                    </div>
                    <div className={styles.kvItem}>
                      <div className={styles.kvLabel}>Profile</div>
                      <div className={styles.kvValue}>
                        {recommendationQuality.winner.variant_name || "n/a"} | {recommendationQuality.winner.min_bars ?? "n/a"} bars
                      </div>
                    </div>
                    <div className={styles.kvItem}>
                      <div className={styles.kvLabel}>Evaluated</div>
                      <div className={styles.kvValue}>
                        {recommendationQuality.cp2?.evaluatedRows?.toLocaleString() ?? recommendationQuality.winner.gates.total_gate_count}
                      </div>
                    </div>
                  </div>

                  <div className={styles.qualityChipRow}>
                    <span className={recommendationQuality.winner.gates.gate_5day ? styles.chipGood : styles.chipWarn}>5D gate</span>
                    <span className={recommendationQuality.winner.gates.gate_20day ? styles.chipGood : styles.chipWarn}>20D gate</span>
                    <span className={recommendationQuality.winner.gates.gate_60day ? styles.chipGood : styles.chipWarn}>60D gate</span>
                    <span className={recommendationQuality.winner.gates.gate_sp_plus_4_proxy_avg ? styles.chipGood : styles.chipWarn}>Avg gate</span>
                    <span className={recommendationQuality.winner.gates.gate_coverage ? styles.chipGood : styles.chipWarn}>Coverage gate</span>
                    <span className={recommendationQuality.winner.gates.gate_fallback ? styles.chipGood : styles.chipWarn}>Fallback gate</span>
                  </div>

                  {recommendationQuality.winner.reason ? (
                    <p className={styles.inlineMsg}>{recommendationQuality.winner.reason}</p>
                  ) : null}
                </>
              ) : (
                <p className={styles.inlineMsg}>
                  No recommendation quality summary is available yet.
                  {recommendationQuality?.error ? ` (${recommendationQuality.error})` : ""}
                </p>
              )}

              {recommendationQuality?.methodology ? (
                <p className={styles.inlineMsg}>Method: {recommendationQuality.methodology}</p>
              ) : null}

              {recommendationQuality?.summaryPath ? (
                <p className={styles.inlineMsg}>Source: {displayPath(recommendationQuality.summaryPath)}</p>
              ) : null}
            </div>

            {refreshStatus?.last_error ? <p className={`${styles.inlineMsg} ${styles.msgError}`}>Refresh error: {refreshStatus.last_error}</p> : null}

            <p className={styles.inlineMsg}>
              Refresh log and history are rendered only on the dedicated <strong>/admin-console/refresh-log</strong> page.
            </p>
          </article>

          <article className={styles.panel}>
            <header className={styles.panelHeader}>
              <h2 className={styles.panelTitle}>Signal Lanes</h2>
              <p className={styles.panelSub}>
                Two validated signal lanes from quarantine forensics (Mar 2021–Mar 2026). Baseline DSF Accumulate 20d win rate: {signalFilter ? `${signalFilter.baselineWinRate}%` : "54.4%"}.
              </p>
              {signalFilter?.generatedAtUtc ? (
                <p className={styles.panelSub}>Updated: {formatIso(signalFilter.generatedAtUtc)} · Total Accumulate: {signalFilter.totalAccumulate.toLocaleString()}</p>
              ) : null}
            </header>

            {signalFilter?.error ? (
              <p className={`${styles.inlineMsg} ${styles.msgError}`}>{signalFilter.error}</p>
            ) : signalFilter ? (
              <>
                {/* Lane A — F_n Established */}
                <p className={styles.inlineMsg}>
                  <strong>Lane A — {signalFilter.laneA.label}</strong>
                </p>
                <div className={styles.kvGrid}>
                  <div className={styles.kvRow}>
                    <div className={styles.kvLabel}>Backtest win rate</div>
                    <div className={styles.kvValue}>{signalFilter.laneA.backtestWinRate}% (n={signalFilter.laneA.backtestN.toLocaleString()})</div>
                  </div>
                  <div className={styles.kvRow}>
                    <div className={styles.kvLabel}>Live survivors</div>
                    <div className={styles.kvValue}>{signalFilter.laneA.survivors.toLocaleString()}</div>
                  </div>
                  {signalFilter.laneA.fnStats.median !== null ? (
                    <div className={styles.kvRow}>
                      <div className={styles.kvLabel}>F_n (median · p75)</div>
                      <div className={styles.kvValue}>{signalFilter.laneA.fnStats.median.toFixed(3)} · {signalFilter.laneA.fnStats.p75?.toFixed(3)}</div>
                    </div>
                  ) : null}
                </div>
                {signalFilter.laneA.sectorConcentration.length > 0 ? (
                  <>
                    <p className={styles.inlineMsg}>Sector concentration:</p>
                    {signalFilter.laneA.sectorConcentration.map((s) => (
                      <div key={s.sector} className={styles.kvRow}>
                        <div className={styles.kvLabel}>{s.sector}</div>
                        <div className={styles.kvValue}>{s.count} ({s.pct}%)</div>
                      </div>
                    ))}
                  </>
                ) : null}
                {signalFilter.laneA.survivors > 0 ? (
                  <p className={styles.inlineMsg}>
                    <strong>Symbols:</strong> {signalFilter.laneA.survivorSymbols.join(", ")}
                  </p>
                ) : null}

                {/* Lane B — New Listing */}
                <p className={styles.inlineMsg} style={{ marginTop: "0.75rem" }}>
                  <strong>Lane B — {signalFilter.laneB.label}</strong>
                </p>
                <div className={styles.kvGrid}>
                  <div className={styles.kvRow}>
                    <div className={styles.kvLabel}>Backtest win rate</div>
                    <div className={styles.kvValue}>{signalFilter.laneB.backtestWinRate}% (n={signalFilter.laneB.backtestN.toLocaleString()})</div>
                  </div>
                  <div className={styles.kvRow}>
                    <div className={styles.kvLabel}>Live survivors</div>
                    <div className={styles.kvValue}>{signalFilter.laneB.survivors.toLocaleString()}{signalFilter.laneB.survivors === 0 ? " — run Universe + Snapshot to populate" : ""}</div>
                  </div>
                </div>
                {signalFilter.laneB.sectorConcentration.length > 0 ? (
                  <>
                    <p className={styles.inlineMsg}>Sector concentration:</p>
                    {signalFilter.laneB.sectorConcentration.map((s) => (
                      <div key={s.sector} className={styles.kvRow}>
                        <div className={styles.kvLabel}>{s.sector}</div>
                        <div className={styles.kvValue}>{s.count} ({s.pct}%)</div>
                      </div>
                    ))}
                  </>
                ) : null}
                {signalFilter.laneB.survivors > 0 ? (
                  <p className={styles.inlineMsg}>
                    <strong>Symbols:</strong> {signalFilter.laneB.survivorSymbols.join(", ")}
                  </p>
                ) : null}
              </>
            ) : (
              <p className={styles.inlineMsg}>Loading signal lanes...</p>
            )}
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
        {showKillConfirm ? (
          <div className={styles.modalBackdrop} role="presentation">
            <div className={styles.modalCard} role="dialog" aria-modal="true" aria-labelledby="kill-run-title">
              <h3 id="kill-run-title" className={styles.modalTitle}>Kill Active Run</h3>
              <p className={styles.modalText}>
                Are you sure you want to halt the active refresh run
                {refreshStatus?.run_id ? ` (${refreshStatus.run_id})` : ""}?
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
    </SiteFrame>
  );
}
