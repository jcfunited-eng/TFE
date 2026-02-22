import SiteFrame from "@/components/SiteFrame";
import { getUiConfig } from "@/lib/ui-config";

export default async function HelpPage() {
  const config = await getUiConfig();

  return (
    <SiteFrame pageBackgroundImage={config.backgroundImages.help}>
      <section className="surface-card">
        <h1>Help Center</h1>
        <p>Starter help content for common actions in Tao Financial Engine.</p>

        <h2>Quick Start</h2>
        <ul>
          <li>Open Recommendations to scan symbols and review Full Market Assessment.</li>
          <li>Use Watchlist to track symbols you want to revisit.</li>
          <li>Use Portfolio for manual entries and scenario checks.</li>
        </ul>

        <h2>What This App Does</h2>
        <ul>
          <li>Shows research-oriented signals: Accumulate, Hold, Avoid (Trim in portfolio view).</li>
          <li>Displays market chart context and UF confidence metrics where available.</li>
          <li>Supports manual portfolio tracking only.</li>
        </ul>

        <h2>What This App Does Not Do</h2>
        <ul>
          <li>It does not execute trades.</li>
          <li>It does not provide personalized investment advice.</li>
        </ul>
      </section>
    </SiteFrame>
  );
}
