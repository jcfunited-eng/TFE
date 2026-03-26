"use client";

import { useEffect, useState } from "react";

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

function formatMoney(value: number): string {
  if (!Number.isFinite(value)) return "N/A";
  if (Math.abs(value) >= 1_000_000_000_000) return `${(value / 1_000_000_000_000).toFixed(2)}T`;
  if (Math.abs(value) >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(2)}B`;
  if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  return value.toFixed(2);
}

function BucketTable({ title, rows }: { title: string; rows: RecommendationRow[] }) {
  return (
    <section className="section-stack">
      <h2>{title}</h2>
      <div className="tfe-muted" style={{ marginBottom: 8 }}>
        {rows.length} result{rows.length === 1 ? "" : "s"}
      </div>
      <div style={{ overflowX: "auto" }}>
        <table className="tfe-table">
          <thead>
            <tr>
              <th>Ticker</th>
              <th>Sector</th>
              <th>Market Cap</th>
              <th>Current Ratio</th>
              <th>Free Cash Flow</th>
              <th>Gross Margin</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={`${title}-${row.ticker}`}>
                <td>{row.ticker}</td>
                <td>{row.sector}</td>
                <td>{formatMoney(row.marketCap)}</td>
                <td>{row.currentRatio.toFixed(2)}</td>
                <td>{formatMoney(row.freeCashFlow)}</td>
                <td>{(row.grossMargin * 100).toFixed(2)}%</td>
              </tr>
            ))}
            {rows.length === 0 ? (
              <tr>
                <td colSpan={6}>No Accumulate results.</td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default function RecommendationsQuickCheck() {
  const [payload, setPayload] = useState<RecommendationsPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

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

      <BucketTable title="The Titans" rows={payload.buckets.titans} />
      <BucketTable title="The Heavyweights" rows={payload.buckets.heavyweights} />
      <BucketTable title="The Mid-Tier" rows={payload.buckets.midTier} />
      <BucketTable title="The Hunters" rows={payload.buckets.hunters} />
    </div>
  );
}
