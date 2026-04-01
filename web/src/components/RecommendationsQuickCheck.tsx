"use client";

import { useEffect, useState, useMemo } from "react";

type SignalClass = "3WA" | "W1" | "standard";

type RecommendationRow = {
  ticker: string;
  sector: string;
  marketCap: number;
  currentRatio: number;
  freeCashFlow: number;
  grossMargin: number;
  grossProfit: number;
  operatingCashFlow: number;
  revenues: number;
  decision: "Accumulate";
  decisionReason: string;
  isNewListing?: boolean;
  signalClass?: SignalClass;
};

type RecommendationsPayload = {
  totalAccumulate: number;
  buckets: {
    titans: RecommendationRow[];
    heavyweights: RecommendationRow[];
    midTier: RecommendationRow[];
    hunters: RecommendationRow[];
  };
  error?: string;
};

type SortKey = keyof Pick<
  RecommendationRow,
  "ticker" | "sector" | "marketCap" | "currentRatio" | "freeCashFlow" | "grossMargin"
>;
type SortDir = "asc" | "desc";

function formatMoney(value: number): string {
  if (!Number.isFinite(value) || value === 0) return "—";
  if (Math.abs(value) >= 1_000_000_000_000) return `${(value / 1_000_000_000_000).toFixed(2)}T`;
  if (Math.abs(value) >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(2)}B`;
  if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  return value.toFixed(2);
}

function formatRatio(value: number): string {
  if (!Number.isFinite(value) || value === 0) return "—";
  return value.toFixed(2);
}

function formatPercent(value: number): string {
  if (!Number.isFinite(value) || value === 0) return "—";
  return `${(value * 100).toFixed(2)}%`;
}

const PAGE_SIZE = 25;

const COLUMNS: { key: SortKey; label: string }[] = [
  { key: "ticker", label: "Ticker" },
  { key: "sector", label: "Sector" },
  { key: "marketCap", label: "Market Cap" },
  { key: "currentRatio", label: "Current Ratio" },
  { key: "freeCashFlow", label: "Free Cash Flow" },
  { key: "grossMargin", label: "Gross Margin" },
];

function compareRows(a: RecommendationRow, b: RecommendationRow, key: SortKey, dir: SortDir): number {
  const aVal = a[key];
  const bVal = b[key];
  let cmp = 0;
  if (typeof aVal === "string" && typeof bVal === "string") {
    cmp = aVal.localeCompare(bVal);
  } else {
    const aNum = Number(aVal);
    const bNum = Number(bVal);
    if (!Number.isFinite(aNum) && !Number.isFinite(bNum)) cmp = 0;
    else if (!Number.isFinite(aNum)) cmp = 1;
    else if (!Number.isFinite(bNum)) cmp = -1;
    else cmp = aNum - bNum;
  }
  return dir === "asc" ? cmp : -cmp;
}

function SortIcon({ active, dir }: { active: boolean; dir: SortDir }) {
  if (!active) return <span style={{ opacity: 0.3, marginLeft: 4 }}>↕</span>;
  return <span style={{ marginLeft: 4 }}>{dir === "asc" ? "↑" : "↓"}</span>;
}

function BucketTable({
  title,
  rows,
  search,
}: {
  title: string;
  rows: RecommendationRow[];
  search: string;
}) {
  const [sortKey, setSortKey] = useState<SortKey>("marketCap");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [page, setPage] = useState(1);

  const query = search.trim().toLowerCase();

  const filtered = useMemo(() => {
    if (!query) return rows;
    return rows.filter(
      (r) =>
        r.ticker.toLowerCase().includes(query) ||
        r.sector.toLowerCase().includes(query),
    );
  }, [rows, query]);

  const sorted = useMemo(
    () => [...filtered].sort((a, b) => compareRows(a, b, sortKey, sortDir)),
    [filtered, sortKey, sortDir],
  );

  const totalPages = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE));
  const clampedPage = Math.min(page, totalPages);
  const pageRows = sorted.slice((clampedPage - 1) * PAGE_SIZE, clampedPage * PAGE_SIZE);

  function handleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
    setPage(1);
  }

  function handlePageInput(e: React.ChangeEvent<HTMLInputElement>) {
    const n = parseInt(e.target.value, 10);
    if (Number.isFinite(n) && n >= 1 && n <= totalPages) setPage(n);
  }

  const matchLabel =
    query && filtered.length !== rows.length
      ? ` — ${filtered.length} match${filtered.length === 1 ? "" : "es"}`
      : "";

  return (
    <section className="section-stack">
      <h2>{title}</h2>
      <div className="tfe-muted" style={{ marginBottom: 8 }}>
        {rows.length} result{rows.length === 1 ? "" : "s"}
        {matchLabel}
      </div>
      <div style={{ overflowX: "auto" }}>
        <table className="tfe-table">
          <thead>
            <tr>
              {COLUMNS.map((col) => (
                <th
                  key={col.key}
                  onClick={() => handleSort(col.key)}
                  style={{ cursor: "pointer", userSelect: "none", whiteSpace: "nowrap" }}
                >
                  {col.label}
                  <SortIcon active={sortKey === col.key} dir={sortDir} />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pageRows.map((row) => (
              <tr key={`${title}-${row.ticker}`}>
                <td>
                  {row.ticker}
                  {row.signalClass === "3WA" ? (
                    <span style={{ marginLeft: 6, fontSize: "0.65rem", fontWeight: 700, color: "#fff", background: "#7c3aed", borderRadius: 3, padding: "1px 4px", verticalAlign: "middle", letterSpacing: "0.04em" }} title="Three-Wave Alignment — Structure A + SPY expansion. Backtest: 84.5% win.">3WA</span>
                  ) : row.signalClass === "W1" || row.isNewListing ? (
                    <span style={{ marginLeft: 6, fontSize: "0.65rem", fontWeight: 700, color: "#fff", background: "#16a34a", borderRadius: 3, padding: "1px 4px", verticalAlign: "middle", letterSpacing: "0.04em" }} title="Wave 1 — New listing in structural ground state. Backtest: 72.1% win.">NEW</span>
                  ) : null}
                </td>
                <td>{row.sector}</td>
                <td>{formatMoney(row.marketCap)}</td>
                <td>{formatRatio(row.currentRatio)}</td>
                <td>{formatMoney(row.freeCashFlow)}</td>
                <td>{formatPercent(row.grossMargin)}</td>
              </tr>
            ))}
            {pageRows.length === 0 ? (
              <tr>
                <td colSpan={6}>{query ? "No matches." : "No Accumulate results."}</td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 8, flexWrap: "wrap" }}>
          <button
            className="tfe-btn-secondary"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={clampedPage <= 1}
          >
            ← Prev
          </button>
          <span className="tfe-muted">
            Page{" "}
            <input
              type="number"
              min={1}
              max={totalPages}
              value={clampedPage}
              onChange={handlePageInput}
              style={{ width: 48, textAlign: "center" }}
            />{" "}
            of {totalPages}
          </span>
          <button
            className="tfe-btn-secondary"
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={clampedPage >= totalPages}
          >
            Next →
          </button>
        </div>
      )}
    </section>
  );
}

export default function RecommendationsQuickCheck() {
  const [payload, setPayload] = useState<RecommendationsPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch("/api/recommendations/list", {
          method: "GET",
          cache: "no-store",
        });
        const data = (await response.json()) as RecommendationsPayload;
        if (!response.ok) {
          if (!cancelled) {
            setPayload(null);
            setError(data.error ?? "Failed to load recommendations.");
          }
          return;
        }
        if (!cancelled) {
          setPayload(data);
        }
      } catch {
        if (!cancelled) {
          setPayload(null);
          setError("Failed to load recommendations.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return <p className="tfe-muted">Loading verified L5 research tool...</p>;
  }

  if (error || !payload) {
    return <p className="tfe-error">{error ?? "Recommendations unavailable."}</p>;
  }

  const allRows = [
    ...payload.buckets.titans,
    ...payload.buckets.heavyweights,
    ...payload.buckets.midTier,
    ...payload.buckets.hunters,
  ];
  const query = search.trim().toLowerCase();
  const matchCount = query
    ? allRows.filter(
        (r) =>
          r.ticker.toLowerCase().includes(query) ||
          r.sector.toLowerCase().includes(query),
      ).length
    : null;

  return (
    <div className="section-stack">
      <section className="surface-card">
        <h2>Strict L5 Kernel</h2>
        <div className="tfe-summary-grid" style={{ marginTop: 8 }}>
          <div className="tfe-summary-card">
            <div className="k">Accumulate</div>
            <div className="v">{payload.totalAccumulate}</div>
          </div>
          <div className="tfe-summary-card">
            <div className="k">The Titans</div>
            <div className="v">{payload.buckets.titans.length}</div>
          </div>
          <div className="tfe-summary-card">
            <div className="k">The Heavyweights</div>
            <div className="v">{payload.buckets.heavyweights.length}</div>
          </div>
          <div className="tfe-summary-card">
            <div className="k">The Mid-Tier</div>
            <div className="v">{payload.buckets.midTier.length}</div>
          </div>
          <div className="tfe-summary-card">
            <div className="k">The Hunters</div>
            <div className="v">{payload.buckets.hunters.length}</div>
          </div>
        </div>
      </section>

      <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <input
          type="search"
          placeholder="Search by ticker or sector…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ flex: "1 1 240px", maxWidth: 360 }}
        />
        {matchCount !== null && (
          <span className="tfe-muted">
            {matchCount} result{matchCount === 1 ? "" : "s"} across all buckets
          </span>
        )}
      </div>

      <BucketTable title="The Titans" rows={payload.buckets.titans} search={search} />
      <BucketTable title="The Heavyweights" rows={payload.buckets.heavyweights} search={search} />
      <BucketTable title="The Mid-Tier" rows={payload.buckets.midTier} search={search} />
      <BucketTable title="The Hunters" rows={payload.buckets.hunters} search={search} />
    </div>
  );
}
