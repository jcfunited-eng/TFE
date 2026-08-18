import Link from "next/link";
import type { ChannelBookView } from "@/lib/channel-books";
import styles from "@/app/portfolio/[channel]/page.module.css";


function dollars(value: number | null, signed = false): string {
  if (value === null || !Number.isFinite(value)) return "—";
  const prefix = signed ? (value >= 0 ? "+$" : "-$") : value < 0 ? "-$" : "$";
  return prefix + Math.abs(value).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}


function price(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "no quote";
  return "$" + value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 4 });
}


function percent(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}


function tone(value: number | null): string {
  if (value === null || value === 0) return styles.neutral;
  return value > 0 ? styles.positive : styles.negative;
}


export default function ChannelBookPage({ book }: { book: ChannelBookView }) {
  const wins = book.closed.filter((trade) => (trade.pnl ?? 0) > 0).length;
  const losses = book.closed.filter((trade) => (trade.pnl ?? 0) < 0).length;

  return (
    <section className={`surface-card ${styles.channelPage}`}>
      <div className={styles.headingRow}>
        <div>
          <Link href="/portfolio-advisor" className={styles.backLink}>← Portfolio</Link>
          <h1>{book.title}</h1>
          <p className={styles.subtitle}>Read-only channel record. This page cannot place, change, or close an order.</p>
        </div>
        <span className={styles.channelBadge}>{book.channel}</span>
      </div>

      <div className={styles.custody}>
        <strong>Book custody</strong>
        <span>source updated {book.sourceUpdatedAt}</span>
        <span>published {book.publishedAt}</span>
        <span>SHA-256 {book.sourceSha256}</span>
        <span>engine {book.engine || "not recorded"}</span>
      </div>

      <div className={styles.tiles}>
        <div className={styles.tile}><span>Equity</span><strong>{dollars(book.equity)}</strong></div>
        <div className={styles.tile}><span>{book.cash !== null && book.cash < 0 ? "Cash (margin borrowed)" : "Cash"}</span><strong>{dollars(book.cash)}</strong></div>
        <div className={styles.tile}><span>Realized</span><strong className={tone(book.realizedPnl)}>{dollars(book.realizedPnl, true)}</strong></div>
        <div className={styles.tile}><span>Unrealized</span><strong className={tone(book.unrealizedPnl)}>{dollars(book.unrealizedPnl, true)}</strong></div>
        <div className={styles.tile}><span>Open</span><strong>{book.positions.length}</strong></div>
        <div className={styles.tile}><span>Closed</span><strong>{book.closed.length}</strong><small>{wins} wins / {losses} losses</small></div>
      </div>

      <div className={styles.markNote}>
        <strong>Marks:</strong> {book.markSource}
        {book.markAsOf ? ` · latest received ${book.markAsOf}` : " · no mark timestamp received"}
        {book.unrealizedPnl === null ? " · totals requiring missing marks are withheld" : ""}
      </div>

      <section className={styles.tableCard}>
        <h2>Open positions <span>{book.positions.length}</span></h2>
        <div className={styles.tableWrap}>
          <table>
            <thead>
              <tr>
                <th>Ticker</th><th>Side</th><th>Shares</th><th>Entry</th><th>Current</th>
                <th>Unrealized</th><th>Return</th><th>Entered</th><th>Status</th>
              </tr>
            </thead>
            <tbody>
              {book.positions.length ? book.positions.map((position) => (
                <tr key={`${position.symbol}-${position.enteredAt}`}>
                  <td className={styles.ticker}>{position.symbol}</td>
                  <td>{position.side === -1 ? "SHORT" : "LONG"}</td>
                  <td>{position.shares.toLocaleString("en-US")}</td>
                  <td>{price(position.entryPrice)}</td>
                  <td>{price(position.currentPrice)}</td>
                  <td className={tone(position.unrealizedPnl)}>{dollars(position.unrealizedPnl, true)}</td>
                  <td className={tone(position.returnPct)}>{percent(position.returnPct)}</td>
                  <td>{position.enteredAt || "—"}</td>
                  <td>{position.status}</td>
                </tr>
              )) : (
                <tr><td colSpan={9} className={styles.empty}>No open positions.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className={styles.tableCard}>
        <h2>Closed record <span>{book.closed.length}</span></h2>
        <div className={styles.tableWrap}>
          <table>
            <thead>
              <tr>
                <th>Ticker</th><th>Side</th><th>Shares</th><th>Entry</th><th>Exit</th>
                <th>P&amp;L</th><th>Return</th><th>Reason</th><th>Exited</th>
              </tr>
            </thead>
            <tbody>
              {book.closed.length ? book.closed.map((trade, index) => (
                <tr key={`${trade.symbol}-${trade.exitedAt}-${index}`}>
                  <td className={styles.ticker}>{trade.symbol}</td>
                  <td>{trade.side === -1 ? "SHORT" : "LONG"}</td>
                  <td>{trade.shares ? trade.shares.toLocaleString("en-US") : "—"}</td>
                  <td>{price(trade.entryPrice)}</td>
                  <td>{price(trade.exitPrice)}</td>
                  <td className={tone(trade.pnl)}>{dollars(trade.pnl, true)}</td>
                  <td className={tone(trade.returnPct)}>{percent(trade.returnPct)}</td>
                  <td>{trade.reason || "—"}</td>
                  <td>{trade.exitedAt || "—"}</td>
                </tr>
              )) : (
                <tr><td colSpan={9} className={styles.empty}>No closed positions.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className={styles.rules}>
        <h2>Recorded channel law</h2>
        <ul>{book.rules.map((rule) => <li key={rule}>{rule}</li>)}</ul>
      </section>
    </section>
  );
}
