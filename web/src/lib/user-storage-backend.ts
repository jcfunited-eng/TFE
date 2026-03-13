export type StorageBackend = "file" | "postgres";

function hasPostgresCreds(): boolean {
  return String(process.env.PGHOST ?? process.env.TFE_DB_HOST ?? "").trim().length > 0
    && String(process.env.PGDATABASE ?? process.env.TFE_DB_NAME ?? "").trim().length > 0
    && String(process.env.PGUSER ?? process.env.TFE_DB_USER ?? "").trim().length > 0
    && String(process.env.PGPASSWORD ?? process.env.TFE_DB_PASSWORD ?? "").trim().length > 0;
}

function normalizeRequestedBackend(raw: string): "file" | "postgres" | "auto" | null {
  const value = raw.trim().toLowerCase();
  if (value === "file" || value === "postgres" || value === "auto") return value;
  return null;
}

export function resolveSharedStorageBackend(): StorageBackend {
  const explicitUserStore = normalizeRequestedBackend(String(process.env.TFE_USER_STORE_BACKEND ?? ""));
  const explicitUserData = normalizeRequestedBackend(String(process.env.TFE_USER_DATA_BACKEND ?? ""));
  const requested = explicitUserStore ?? explicitUserData ?? "auto";

  if (requested === "file") return "file";
  if (requested === "postgres") return "postgres";

  return hasPostgresCreds() ? "postgres" : "file";
}
