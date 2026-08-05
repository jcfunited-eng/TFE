import SiteFrame from "@/components/SiteFrame";
import { getUiConfig } from "@/lib/ui-config";

const SUPPORT_EMAIL = "support@taofinancialengine.com";

export default async function SupportPage() {
  const config = await getUiConfig();

  return (
    <SiteFrame pageBackgroundImage={config.backgroundImages.support}>
      <section className="surface-card">
        <h1>Support</h1>
        <p>Support is currently provided by email only.</p>

        <h2>Contact</h2>
        <p>
          Email:{" "}
          <a href={`mailto:${SUPPORT_EMAIL}`} style={{ color: "#1f4d3a", fontWeight: 700 }}>
            {SUPPORT_EMAIL}
          </a>
        </p>

        <h2>Include This In Your Message</h2>
        <ul>
          <li>Your username or account email.</li>
          <li>Page name where the issue occurred.</li>
          <li>Ticker symbol (if relevant).</li>
          <li>Screenshot and time of issue.</li>
        </ul>

        <h2>Current Scope</h2>
        <ul>
          <li>App access and sign-in support.</li>
          <li>Watchlist and portfolio data issues.</li>
          <li>UI bugs and page behavior issues.</li>
        </ul>
      </section>
    </SiteFrame>
  );
}
