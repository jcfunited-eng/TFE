import Link from "next/link";
import PortfolioAdvisorManager from "@/components/PortfolioAdvisorManager";
import PortfolioTFEManager from "@/components/PortfolioTFEManager";
import SiteFrame from "@/components/SiteFrame";
import { requireServerUser } from "@/lib/server-auth";
import { getUiConfig } from "@/lib/ui-config";
import styles from "./page.module.css";


const CHANNEL_LINKS = [
  { href: "/portfolio/ch3", code: "CH3", title: "Shadow Hunter", note: "Paper short book" },
  { href: "/portfolio/ch4", code: "CH4", title: "Structural Channel", note: "Frozen paper experiment" },
  { href: "/portfolio/ch6", code: "CH6", title: "Fast Harvest", note: "Paper daily-cash test" },
] as const;


export default async function PortfolioPage() {
  const user = await requireServerUser("/portfolio-advisor");
  const isAdmin = user.role === "admin";
  const config = await getUiConfig();

  return (
    <SiteFrame pageBackgroundImage={config.backgroundImages.portfolioAdvisor}>
      <section className="surface-card">
        <h1>Portfolio</h1>

        {isAdmin && (
          <div className={styles.channelSection}>
            <div className={styles.channelHeading}>
              <h2>Channel books</h2>
              <p>Read-only received records. These pages cannot place or alter an order.</p>
            </div>
            <div className={styles.channelLinks}>
              {CHANNEL_LINKS.map((channel) => (
                <Link key={channel.code} href={channel.href} className={styles.channelLink}>
                  <span className={styles.channelCode}>{channel.code}</span>
                  <strong>{channel.title}</strong>
                  <small>{channel.note}</small>
                  <span aria-hidden="true">→</span>
                </Link>
              ))}
            </div>
          </div>
        )}

        {isAdmin && (
          <div style={{ marginBottom: 40 }}>
            <div className="tfe-panel" style={{ padding: "12px 16px", marginBottom: 16, fontSize: "0.8rem", color: "#475569" }}>
              <strong>Broker custody is authoritative.</strong> Portfolio value, cash, invested value, open-position count,
              and unrealized P&amp;L below come from Alpaca. Missing broker values remain unavailable. A position marked
              <code style={{ margin: "0 4px" }}>BROKER_ONLY</code> is held at Alpaca without an open ledger owner; it is
              shown without assigning it to CH1, CH2, or CH3. Realized account P&amp;L is unavailable from the account
              endpoint; closed ledger records remain visible as ledger history, not broker custody truth.
            </div>
            <PortfolioTFEManager />
          </div>
        )}

        <details style={{ marginTop: 8 }}>
          <summary style={{
            cursor: "pointer",
            fontWeight: 600,
            fontSize: "0.88rem",
            color: "#6b7280",
            padding: "10px 0",
            userSelect: "none",
            listStyle: "none",
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}>
            <span>▸</span> Manual / What-if Scenario Tracker
          </summary>
          <div style={{ marginTop: 16 }}>
            <div className={styles.portfolioShell}>
              <aside className={`tfe-panel ${styles.portfolioRail} ${styles.portfolioLeft}`}>
                <h2>How This Works</h2>
                <p>
                  This tracker is fully manual and is not personal investment advice. Use it to test what-if
                  scenarios and to see how your own entries could impact your results.
                </p>
                <p>
                  Accuracy depends on what you enter and maintain here. Entries here are separate from
                  TFE-managed positions above.
                </p>
              </aside>

              <aside className={`tfe-panel ${styles.portfolioRail} ${styles.portfolioRight}`}>
                <h2>Decision Context</h2>
                <p>
                  The <strong>Decision</strong> column shows the same market-analysis signal used across
                  this website — not personalized to your manual entries.
                </p>
                <p>
                  Use this section to compare your manual cost basis and position sizing against current
                  market values and the shared UF signal view.
                </p>
              </aside>

              <section className={styles.portfolioMain}>
                <PortfolioAdvisorManager />
              </section>
            </div>
          </div>
        </details>
      </section>
    </SiteFrame>
  );
}
