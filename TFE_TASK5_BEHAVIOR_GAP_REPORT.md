# TFE Task 5 Behavior Gap Report

Version: 1.0
Date: 2026-02-13
Scope: Compare current code behavior vs approved specs:
- `TFE_UI_WRITING_STYLE_GUIDE.md`
- `TFE_SUBSCRIPTION_AND_CART_SPEC.md`
- `TFE_ADMIN_CONSOLE_SPEC.md`
- Approved page map (Home, Account, Recommendations, Watchlist, Portfolio Advisor, Legal)

## Critical Gaps

1) No auth/roles/admin gating implemented.

- Current state:
  - No login/auth role enforcement in app flow.
  - No admin-only page exists.
- Evidence:
  - `app.py:34` simple sidebar radio without auth checks.
  - `pages/3_Recommendations.py:116` includes "Admin Snapshot Controls" visible in normal user page.
- Spec impact:
  - Violates `TFE_ADMIN_CONSOLE_SPEC.md` admin-only access requirement.

2) No subscription/cart/checkout system exists.

- Current state:
  - No cart, no plan selection workflow, no checkout flow, no billing status model.
- Evidence:
  - Repo search found no implemented subscription/checkout logic in app pages.
- Spec impact:
  - Violates `TFE_SUBSCRIPTION_AND_CART_SPEC.md` sections 2-8.

3) Required legal/disclaimer UX not implemented.

- Current state:
  - Legal page is missing.
  - Required checkout and decision disclaimers are not present as specified.
- Evidence:
  - No `Legal` page file.
  - `app.py` and active pages do not show the mandatory legal text set.
- Spec impact:
  - Violates writing and subscription specs.

## High Gaps

4) Page map is not aligned to approved structure.

- Current state:
  - Existing pages include diagnostics and multiple legacy pages.
  - Missing required `Account` and `Legal` pages.
- Evidence:
  - `pages/0_Universe_Diagnostics.py`
  - `pages/1_Dashboard.py`
  - `pages/5_Portfolio_Insights.py`
  - Missing dedicated account/legal implementation.
- Spec impact:
  - Violates approved Task 2 page map.

5) Decision language mismatch.

- Current state:
  - Watchlist outputs `BUY/HOLD/SELL`.
  - Recommendations outputs `BUY/HOLD/AVOID`.
- Evidence:
  - `pages/3_Watchlist.py:57` classification rules return BUY/SELL/HOLD.
  - `pages/3_Recommendations.py:39` classify to BUY/HOLD/AVOID.
- Spec impact:
  - Violates required user-facing decision vocabulary (`Accumulate/Hold/Trim`).

6) UI writing style mismatch (jargon-heavy experience still active).

- Current state:
  - Ticker lookup emphasizes chart-heavy indicators and finance jargon (RSI, MACD, momentum).
- Evidence:
  - `pages/2_Ticker_Lookup.py` sections for RSI, MACD, multi-chart insight.
- Spec impact:
  - Violates minimal plain-English, decision-first style guide.

7) Top recommendation requirement mismatch.

- Current state:
  - Recommendations page shows "Top 5 Hot Picks — Stocks under $30".
- Evidence:
  - `pages/3_Recommendations.py` hardcoded under `$30` logic.
- Spec impact:
  - Does not match approved requirement: top 5 under $50.

## Medium Gaps

8) No centralized config model for editable plans/legal text.

- Current state:
  - No runtime configuration record for pricing/caps/legal copy.
- Spec impact:
  - Violates post-deployment editability requirement.

9) No test-user bypass capability.

- Current state:
  - No `test_user` role/type logic, no bypass flags, no expiry/revocation flow.
- Spec impact:
  - Violates `TFE_ADMIN_CONSOLE_SPEC.md` v1.1 section 4.2.

10) Theme system not implemented.

- Current state:
  - No explicit zen soft green/yellow theme token layer found in app code.
- Spec impact:
  - Violates approved visual direction baseline.

## Immediate Priority Fix Order (strict)

1. Implement authentication + server-side role model and admin gating.
2. Implement approved page map skeleton with required pages (including Account + Legal + Admin Console).
3. Implement decision vocabulary normalization (Accumulate/Hold/Trim).
4. Implement subscription/cart model baseline and account status display.
5. Implement disclaimer/legal surfaces in decision + checkout + legal page.

