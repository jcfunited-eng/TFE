import PortfolioAdvisorManager from "@/components/PortfolioAdvisorManager";
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

        <div className={styles.portfolioShell}>
          <aside className={`tfe-panel ${styles.portfolioRail} ${styles.portfolioLeft}`}>
            <h2>How This Page Works</h2>
            <p>
              This portfolio is fully manual and is not personal investment advice. Use it to test what-if scenarios and to see how your
              own entries could impact your results.
            </p>
            <p>
              Accuracy depends on what you enter and maintain here. If units, cost, or symbols are not maintained by you, the outputs on
              this page will be wrong and should not be used to make decisions.
            </p>
          </aside>

          <aside className={`tfe-panel ${styles.portfolioRail} ${styles.portfolioRight}`}>
            <h2>Decision Context</h2>
            <p>
              The <strong>Decision</strong> column is not personalized to your portfolio history. It is the same market-analysis signal used
              across this website and shown in portfolio context.
            </p>
            <p>
              Use this page to compare your manual cost basis and position sizing against current market values and the shared UF signal
              view.
            </p>
          </aside>

          <section className={styles.portfolioMain}>
            <PortfolioAdvisorManager />
          </section>
        </div>
      </section>
    </SiteFrame>
  );
}
