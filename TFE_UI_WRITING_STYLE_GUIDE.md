# Tao Financial Engine (TFE) UI Writing Style Guide

Version: 1.0
Status: Approved baseline from Task 1 and Task 2

## 1) Core UI Writing Principles

- Keep it minimal.
- Use plain English.
- Show the decision first.
- Avoid financial jargon by default.
- Use helper text to explain what each action does.
- Use links to external research sites for deeper analysis.

## 2) Voice and Tone

- Clear, short, direct.
- Friendly but not casual.
- No hype language.
- No fear language.
- No claims of guaranteed outcomes.

## 3) Decision-First Rule

For ticker lookups and recommendations:

- First line shows only the signal:
  - `Accumulate`
  - `Hold`
  - `Trim`
- Second line shows a one-sentence plain-language explanation.
- Optional third line offers external research links.

## 4) Required Helper Text Pattern

Use this pattern near key inputs and outputs:

- `What this does:` one sentence.
- `What you get:` one sentence.
- `What this does not do:` one sentence.

Example:

- `What this does: Looks up a ticker and returns a simple AI signal.`
- `What you get: Accumulate, Hold, or Trim with a short explanation.`
- `What this does not do: It does not place trades or execute purchases.`

## 5) Jargon Control Rule

Default UI must avoid terms like:

- alpha
- beta
- Sharpe
- stochastic
- volatility clustering
- factor exposure

If advanced terms are needed, place them behind a clearly labeled link:

- `Need deeper analysis? View external research tools.`

## 6) External Research Link Rule

Place this text under decision sections:

- `Need deeper analysis and charting? Use external research tools.`

Important:

- External links are research-only references.
- TFE remains decision-first and minimal.

## 7) Mandatory Compliance Messaging

These messages must appear in Legal page and near decision outputs:

- `For research use only.`
- `This is not financial advice.`
- `Use at your own risk.`
- `No guarantee of profit or protection from loss.`
- `This platform cannot be used to purchase or trade assets.`

## 8) Page-Level Writing Targets

### Home

Goal:

- Fast first impression and quick ticker check.

Must show:

- One-line value statement.
- Ticker input helper text.
- Decision-first output format.
- Compliance short text.

### Account

Goal:

- Clear account and subscription status.

Must show:

- Current plan.
- Renewal date.
- Survey requirement status (for launch offer users).
- Billing helper text in plain language.

### Recommendations

Goal:

- Quick discovery without complexity.

Must show:

- Top 5 under $50.
- Top 10 by asset class.
- Add to Watchlist actions.
- External research link text.

### Watchlist

Goal:

- Simple tracking and quick decisions.

Must show:

- Symbol list.
- Latest signal per symbol.
- Last update time.
- Remove action.

### Portfolio Advisor

Goal:

- Manual portfolio support with simple advisor output.

Must show:

- Manual holding entry/update.
- Per-position and total view.
- Advisor signals in plain English.
- Clear statement that no trades are executed.

### Legal

Goal:

- Plain-language legal clarity.

Must show:

- Research-only and no-advice language.
- No-trading-execution statement.
- Risk and no-guarantee statement.
- Launch-offer condition text for first 1000 users.

## 9) Launch Offer Text Standard

Use this exact baseline text until legal finalization:

- `Launch Offer: First 1,000 members can access 3 years for $25, subject to terms.`
- `Condition: Members in this offer agree to complete a monthly survey to maintain membership.`

## 10) Copy Review Checklist (Use Before Release)

- Is the decision shown first?
- Is the language plain and short?
- Is jargon removed or moved behind external links?
- Is compliance text visible?
- Is there any wording that implies guaranteed outcomes?

If any answer fails, copy is not release-ready.
