import SiteFrame from "@/components/SiteFrame";
import { getUiConfig } from "@/lib/ui-config";

export default async function LegalPage() {
  const config = await getUiConfig();
  return (
    <SiteFrame pageBackgroundImage={config.backgroundImages.legal}>
      <section className="surface-card">
        <h1>Tao Financial Engine — Disclosures and Terms</h1>
        <p>Last updated: August 18, 2026</p>

        <p>
          Tao Financial Engine (TFE) is a research system for testing deterministic structural-field physics against
          hostile time-series data. Financial markets are its first proving ground; TFE is not presented as a promise
          to beat the market or as a substitute for professional judgment.
        </p>

        <h2>1) Research and information, not personalized advice</h2>
        <p>
          TFE outputs—including Accumulate, Hold, Avoid, structural fields, channel pages, alerts, explanations,
          simulations, and performance records—are research and informational outputs. They are not personalized
          investment, legal, accounting, or tax advice and do not account for a user&apos;s financial circumstances.
        </p>

        <h2>2) No advisory or fiduciary relationship</h2>
        <p>
          Use of TFE does not by itself create an investment-advisory, fiduciary, brokerage-client, or professional
          services relationship with TFE, its owners, operators, or contributors. Consult appropriately licensed
          professionals before making financial decisions.
        </p>

        <h2>3) Restricted execution tools and broker custody</h2>
        <p>
          TFE contains restricted administrative execution tools used to test its structural decisions through an
          Alpaca account. Production is presently configured for Alpaca paper trading. Those tools can route orders
          to Alpaca and are technically capable of using a live Alpaca endpoint if an authorized administrator
          deliberately changes the execution configuration. They are not a public self-service trading feature.
        </p>
        <p>
          TFE does not itself custody securities or customer funds. Order execution, account records, and asset
          custody belong to the connected broker. Alpaca states that its Paper Trading API uses simulated funds and
          does not transact real securities; brokerage services are provided by Alpaca Clearing. Review the current
          <a href="https://alpaca.markets/disclosures" target="_blank" rel="noreferrer"> Alpaca disclosures</a> and
          account agreements before using any broker-connected function.
        </p>

        <h2>4) Execution and automation risk</h2>
        <p>
          Automated and API-driven orders can be duplicated, delayed, rejected, partially filled, filled at unexpected
          prices, or affected by stale data, software failure, connectivity loss, corporate actions, market closures,
          and configuration errors. Paper results do not prove live execution performance. Never assume an order,
          cancellation, stop, or position change occurred without checking the broker&apos;s own records.
        </p>

        <h2>5) No guarantees</h2>
        <ul>
          <li>No output, channel, backtest, or paper result guarantees profit or avoidance of loss.</li>
          <li>Losses may be rapid and may exceed expectations, particularly with margin or leveraged products.</li>
          <li>Past and hypothetical performance do not guarantee future results.</li>
        </ul>

        <h2>6) Data and model limitations</h2>
        <p>
          Third-party market data may be delayed, incomplete, stale, or incorrect. Structural calculations can be
          affected by missing bars, corporate actions, provider differences, and software defects. Explanatory text
          may also be wrong. Independently verify source data and broker state before acting.
        </p>

        <h2>7) Simulations and displayed performance</h2>
        <p>
          Backtests, paper books, and hypothetical results may omit or imperfectly represent liquidity, slippage,
          fees, taxes, borrow availability, latency, halts, rejected orders, and changing market regimes. Channel and
          ledger results must not be described as broker-account performance unless reconciled to broker records.
        </p>

        <h2>8) No solicitation</h2>
        <p>
          References to securities, issuers, strategies, or market events are not an offer, solicitation, or promise
          to buy or sell an instrument. Users remain responsible for their own decisions and legal compliance.
        </p>

        <h2>9) Privacy and third-party services</h2>
        <p>
          TFE uses third-party services for functions including authentication, hosting, market data, and broker API
          access. Each provider has its own terms and privacy practices. TFE does not intentionally store full payment
          card numbers or broker secret keys in user-facing records and does not sell personal information.
        </p>

        <h2>10) Availability and warranties</h2>
        <p>
          TFE is provided on an as-is and as-available basis. To the maximum extent permitted by law, no warranty is
          made that it will be uninterrupted, secure, error-free, complete, or fit for a particular purpose.
        </p>

        <h2>11) Limitation of liability</h2>
        <p>
          To the maximum extent permitted by law, TFE and its owners, operators, affiliates, and contributors are not
          liable for indirect, incidental, special, consequential, exemplary, or punitive damages, or losses of
          profits, revenue, data, goodwill, or trading capital arising from use or inability to use TFE.
        </p>

        <h2>12) Contact and eligibility</h2>
        <p>
          TFE is not intended for anyone under 18. Questions may be sent to
          <a href="mailto:support@taofinancialengine.com"> support@taofinancialengine.com</a>.
        </p>

        <hr />
        <p><strong>Conflicts:</strong> TFE owners or contributors may hold positions in assets discussed.</p>
        <p><strong>Third-party links:</strong> Links are provided for reference; TFE does not control their content.</p>
      </section>
    </SiteFrame>
  );
}
