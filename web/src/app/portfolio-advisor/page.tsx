import PortfolioAdvisorManager from "@/components/PortfolioAdvisorManager";
import PortfolioTFEManager from "@/components/PortfolioTFEManager";
import SiteFrame from "@/components/SiteFrame";
import { requireServerUser } from "@/lib/server-auth";
import { getUiConfig } from "@/lib/ui-config";
import styles from "./page.module.css";

export default async function PortfolioPage() {
  await requireServerUser("/portfolio-advisor");
  const config = await getUiConfig();

  return (
    <SiteFrame pageBackgroundImage={config.backgroundImages.portfolioAdvisor}>
      <section className="surface-card">
        <h1>Portfolio</h1>

        {/* ── TFE Automated Portfolio Manager ─────────────────────────── */}
        <div style={{ marginBottom: 40 }}>
          <PortfolioTFEManager />
        </div>

        {/* ── Manual / Scenario Tracker ─────────────────────────────────── */}
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
