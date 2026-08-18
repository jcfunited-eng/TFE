import SiteFrame from "@/components/SiteFrame";
import { getUiConfig } from "@/lib/ui-config";

export default async function HelpPage() {
  const config = await getUiConfig();
  return (
    <SiteFrame pageBackgroundImage={config.backgroundImages.help}>
      <section className="surface-card">
        <h1>Help Center</h1>
        <p>TFE is the financial proving ground for deterministic structural-field physics.</p>

        <h2>Research pages</h2>
        <ul>
          <li>Use Recommendations and Screener to inspect published Accumulate, Hold, and Avoid states.</li>
          <li>Use Watchlist to retain symbols for later observation.</li>
          <li>Use Portfolio for manual scenario tracking; use linked CH2, CH3, CH4, and CH6 pages for channel-specific evidence.</li>
        </ul>

        <h2>Broker-connected administration</h2>
        <ul>
          <li>Ordinary member pages do not submit orders.</li>
          <li>Restricted admin tools can route paper orders to Alpaca and reconcile the TFE ledger to broker custody.</li>
          <li>Those tools are capable of live routing only if an authorized administrator deliberately changes execution mode.</li>
          <li>Always treat Alpaca&apos;s account, position, order, and confirmation records as broker custody truth.</li>
        </ul>

        <h2>Important limits</h2>
        <ul>
          <li>TFE does not provide personalized investment advice or guarantee outcomes.</li>
          <li>A channel result is research evidence, not proof that the full DSF field has been validated.</li>
          <li>Unavailable data and failed checks should remain unavailable or failed; do not interpret them as neutral or passing.</li>
        </ul>
      </section>
    </SiteFrame>
  );
}
