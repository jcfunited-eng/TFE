"use client";

import { useMemo, useState } from "react";
import type { ChannelClosedView } from "@/lib/channel-books";
import styles from "@/app/portfolio/[channel]/page.module.css";

type SortKey =
  | "symbol" | "side" | "shares" | "entryPrice" | "exitPrice"
  | "pnl" | "returnPct" | "reason" | "exitedAt";

const COLUMNS: { key: SortKey; label: string }[] = [
  { key: "symbol", label: "Ticker" },
  { key: "side", label: "Side" },
  { key: "shares", label: "Shares" },
  { key: "entryPrice", label: "Entry" },
  { key: "exitPrice", label: "Exit" },
  { key: "pnl", label: "P&L" },
  { key: "returnPct", label: "Return" },
  { key: "reason", label: "Reason" },
  { key: "exitedAt", label: "Exited" },
];

function dollars(value: number | null, signed = false): string {
  if (value === null || !Number.isFinite(value)) return "—";
  const prefix = signed ? (value >= 0 ? "+$" : "-$") : value < 0 ? "-$" : "$";
  return prefix + Math.abs(value).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function price(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  return "$" + value.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  });
}

function percent(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}

function cellColor(value: number | null): React.CSSProperties {
  if (value === null || !Number.isFinite(value) || value === 0) return {};
  return { color: value > 0 ? "var(--gain, #15803d)" : "var(--loss, #b91c1c)" };
}

export default function ClosedRecordTable({ trades }: { trades: ChannelClosedView[] }) {
  const [sortKey, setSortKey] = useState<SortKey>("exitedAt");
  const [descending, setDescending] = useState(true);

  const sorted = useMemo(() => {
    const rows = [...trades];
    rows.sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      let cmp: number;
      if (typeof av === "number" && typeof bv === "number") {
        cmp = av - bv;
      } else {
        cmp = String(av ?? "").localeCompare(String(bv ?? ""));
      }
      return descending ? -cmp : cmp;
    });
    return rows;
  }, [trades, sortKey, descending]);

  const onSort = (key: SortKey) => {
    if (key === sortKey) {
      setDescending((d) => !d);
    } else {
      setSortKey(key);
      setDescending(true);
    }
  };

  return (
    <table>
      <thead>
        <tr>
          {COLUMNS.map(({ key, label }) => (
            <th
              key={key}
              onClick={() => onSort(key)}
              style={{ cursor: "pointer", userSelect: "none", whiteSpace: "nowrap" }}
              title="Click to sort"
            >
              {label}{sortKey === key ? (descending ? " ▼" : " ▲") : ""}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {sorted.length ? sorted.map((trade, index) => (
          <tr key={`${trade.symbol}-${trade.exitedAt}-${index}`}>
            <td className={styles.ticker}>{trade.symbol}</td>
            <td>{trade.side === -1 ? "SHORT" : "LONG"}</td>
            <td>{trade.shares ? trade.shares.toLocaleString("en-US") : "—"}</td>
            <td>{price(trade.entryPrice)}</td>
            <td>{price(trade.exitPrice)}</td>
            <td style={cellColor(trade.pnl)}>{dollars(trade.pnl, true)}</td>
            <td style={cellColor(trade.returnPct)}>{percent(trade.returnPct)}</td>
            <td>{trade.reason || "—"}</td>
            <td>{trade.exitedAt || "—"}</td>
          </tr>
        )) : (
          <tr><td colSpan={9} className={styles.empty}>No closed positions.</td></tr>
        )}
      </tbody>
    </table>
  );
}
