import SiteFrame from "@/components/SiteFrame";
import { getUiConfig } from "@/lib/ui-config";

export default async function LegalPage() {
  const config = await getUiConfig();

  return (
    <SiteFrame pageBackgroundImage={config.backgroundImages.legal}>
      <section className="surface-card">
        <h1>Tao Financial Engine (TFE) — Important Disclosures & Disclaimer</h1>

        <p>
          Welcome to the Tao Financial Engine (TFE). TFE is a research product created to explore a proprietary,
          emerging class of AI methods for analyzing information and generating hypotheses. We aim to make it useful
          and easy to understand, but it is still experimental technology.
        </p>

        <h2>1) Research & informational use only (not advice)</h2>
        <p>
          TFE is provided for research, informational, and educational purposes only. Nothing on TFE, including
          signals, scores, watchlists, alerts, commentary, model outputs, explanations, or any other content, should
          be interpreted as:
        </p>
        <ul>
          <li>financial or investment advice,</li>
          <li>a recommendation to buy, sell, or hold any asset,</li>
          <li>personalized guidance tailored to your financial situation, or</li>
          <li>a substitute for professional advice.</li>
        </ul>
        <p>
          You should consult a qualified professional (for example, a licensed investment adviser, broker,
          accountant, or attorney) before making financial decisions.
        </p>

        <h2>2) No advisory relationship; no fiduciary duty</h2>
        <p>
          Your use of TFE does not create an advisory, fiduciary, or client relationship between you and TFE, its
          owners, operators, contributors, or affiliates. TFE does not provide suitability determinations, and we do
          not consider your investment objectives, risk tolerance, financial circumstances, or needs, unless
          explicitly stated in a separate written agreement.
        </p>

        <h2>3) No trade execution; not a broker, exchange, or wallet</h2>
        <p>
          TFE does not execute trades, accept orders, route orders, custody assets, manage funds, or facilitate
          transactions. TFE is not a brokerage, exchange, wallet provider, payment rail for investing, or trading
          venue.
        </p>
        <p>
          TFE is not intended to be used to make (and should not be relied upon to make) equities, cryptocurrency,
          derivatives, or any other financial instrument purchases or sales.
        </p>
        <p>
          If you decide to trade or invest, you should do so through your licensed broker, exchange, or other
          regulated provider, and you should verify all details independently.
        </p>

        <h2>4) No guarantees; use at your own risk</h2>
        <p>Any use of TFE outputs is entirely at your own risk. TFE:</p>
        <ul>
          <li>does not guarantee profits, returns, or outcomes of any kind,</li>
          <li>does not protect you from losses, and</li>
          <li>makes no promises that any output will be correct, complete, or profitable.</li>
        </ul>
        <p>
          Markets are volatile. Losses can exceed expectations, and in some products (e.g., margin, options,
          futures, leveraged tokens) losses can be rapid and significant.
        </p>

        <h2>5) Risk disclosure (equities, crypto, and other instruments)</h2>
        <p>
          Investing and trading involve substantial risk, including the potential loss of your entire investment.
          Crypto assets may involve additional risks such as extreme volatility, liquidity constraints, regulatory
          uncertainty, smart contract vulnerabilities, custody risks, and technology failures. Past performance
          (including any back tests or examples) does not guarantee future results.
        </p>
        <p>If you are uncomfortable with the risk of loss, you should not trade.</p>

        <h2>6) Data quality, timeliness, and model limitations</h2>
        <p>
          TFE may rely on third party data sources, public information, and automated processing. As a result:
        </p>
        <ul>
          <li>Data may be delayed, missing, incorrect, or out of date.</li>
          <li>Outputs may reflect assumptions and model behaviors that can change over time.</li>
          <li>AI systems can produce errors, hallucinations, or misleading explanations.</li>
        </ul>
        <p>
          You agree to independently verify any information before acting on it. Do not rely on TFE for time
          sensitive trading, emergency decisions, or decisions requiring guaranteed accuracy.
        </p>

        <h2>7) Back tests, simulations, and hypothetical results (if shown)</h2>
        <p>
          If TFE displays back tests, simulations, or hypothetical performance, those results are not actual trading
          results and may not reflect real market conditions (including slippage, fees, liquidity constraints,
          latency, execution quality, taxes, or changing market regimes). Hypothetical performance can be materially
          different from real world performance.
        </p>

        <h2>8) No solicitation; informational commentary only</h2>
        <p>
          Any mention of a specific asset, issuer, protocol, token, strategy, or market event is for informational
          purposes only and is not an offer, solicitation, or recommendation to buy or sell any security, commodity,
          digital asset, or other instrument where such an offer would be unlawful.
        </p>

        <h2>9) Privacy & payment information (subscriptions)</h2>
        <p>We take privacy seriously. As a general practice:</p>
        <ul>
          <li>
            We do not store full payment card numbers, bank credentials, or other sensitive payment credentials on
            our servers. Payments are typically processed by third party, PCI compliant payment processors.
          </li>
          <li>
            We may retain limited records necessary to operate the service (for example, contact details,
            subscription status, receipt IDs, timestamps, and amounts) for customer support, fraud prevention,
            accounting, and legal compliance.
          </li>
          <li>We do not sell your personal information.</li>
        </ul>
        <p>
          We do not share personal information with third parties for their own marketing purposes. We may share
          limited information with service providers strictly as needed to provide the service (e.g., payment
          processing, hosting, analytics) and/or when required by law.
        </p>

        <h2>10) All sales final; no refunds (except where required by law)</h2>
        <p>
          All purchases are final and non refundable, except where required by applicable law. Please review plan
          details carefully before purchasing.
        </p>

        <h2>11) No warranties; service availability</h2>
        <p>
          TFE is provided on an as-is and as-available basis. To the maximum extent permitted by law, we disclaim all
          warranties, express or implied, including merchantability, fitness for a particular purpose, and non
          infringement. We do not warrant that TFE will be uninterrupted, error free, secure, or free from harmful
          components.
        </p>

        <h2>12) Limitation of liability</h2>
        <p>
          To the maximum extent permitted by law, TFE and its owners, operators, affiliates, and contributors will
          not be liable for any indirect, incidental, special, consequential, exemplary, or punitive damages, or any
          loss of profits, revenue, data, goodwill, or trading losses, arising out of or related to your use of (or
          inability to use) TFE even if advised of the possibility of such damages.
        </p>

        <h2>13) User responsibility & compliance</h2>
        <p>
          You are responsible for complying with all laws and regulations that apply to you, including those relating
          to securities, commodities, digital assets, taxes, and data privacy. You agree not to use TFE in any manner
          that violates applicable law or regulations.
        </p>

        <h2>14) Changes to the service and these disclosures</h2>
        <p>
          We may update TFE features, models, data sources, and these disclosures from time to time. Continued use of
          TFE after updates means you accept the revised disclosures.
        </p>

        <h2>15) Contact</h2>
        <p>Questions about these disclosures can be directed to: support@taofinancialengine.com.</p>

        <hr />

        <p>
          <strong>Conflicts of interest / holdings:</strong> TFE, its owners, and/or contributors may hold positions
          in assets discussed. Such positions may change without notice.
        </p>

        <p>
          <strong>Third party links:</strong> Links to third party sites are provided for convenience only. We do not
          control or endorse third party content.
        </p>

        <p>
          <strong>Age requirement:</strong> TFE is not intended for use by anyone under 18.
        </p>
      </section>
    </SiteFrame>
  );
}
