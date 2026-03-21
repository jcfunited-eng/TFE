# TFE Subscription and Cart Specification

Version: 1.0
Status: Task 4 baseline

## 1) Purpose

Define exactly how TFE subscriptions and cart behavior work for launch and post-launch.

## 2) Plans and Prices

- Monthly Plan: `$9.99` per month.
- Annual Plan: `$99.99` per year.
- Launch Offer Plan: `$25` total for 3 years, limited to first 1,000 eligible users.

## 3) Launch Offer Rules

- Offer name: `Founding 1000`.
- Cap: maximum 1,000 accepted users.
- Price: `$25` one-time for 3 years of access.
- Condition: member must complete a monthly survey to maintain membership.
- If survey condition is not met, membership may be suspended based on policy.

## 4) Product Access Rules

- Active subscription = full tool access.
- Expired or inactive subscription = no premium tool access.
- Access includes future upgrades released during active subscription period.

## 5) Cart Scope (Launch)

The cart supports subscriptions only:

- Monthly
- Annual
- Founding 1000 (if still available)

The cart does not support equities, ETFs, or any tradable asset purchases.

## 6) Checkout Rules

- User selects one plan.
- Cart shows final price clearly before checkout.
- User must accept legal/disclaimer checkbox before payment submission.
- On successful payment, subscription status updates immediately in account.
- On failed payment, show plain-language error and keep cart contents.

## 7) Required Legal Statements at Checkout

Show these statements before payment:

- `For research use only.`
- `This is not financial advice.`
- `Use at your own risk.`
- `No guarantee of profit or protection from loss.`
- `This platform cannot be used to purchase or trade assets.`

For launch offer users also show:

- `Founding 1000 members agree to complete a monthly survey to maintain membership.`

## 8) Account Page Subscription Data

Account page must show:

- Current plan name.
- Plan status (active/inactive).
- Start date.
- Renewal/end date.
- Next billing date (if recurring plan).
- Founding 1000 survey status (if applicable).

## 9) Editing and Change Control Requirement

This system must remain editable:

- Before deployment: all plan, price, and copy values must be configurable.
- After deployment: values must still be editable without rebuilding core UF/SES logic.

Implementation requirement:

- Store pricing, offer caps, and legal text in configuration records (not hard-coded page text only).
- UI reads from config at runtime.
- Changes require admin update + audit log entry.

## 10) Deployment Safety Requirement

Deployments must support controlled changes:

- Staging environment for testing changes before production.
- Production updates via versioned releases.
- Rollback path for failed releases.

## 11) Visual Direction Requirement (Zen Theme)

Site visual direction must be:

- Zen-like, minimal, calm.
- Soft green and soft yellow palette.
- Clean spacing, low visual noise, readable typography.

Theme tokens to implement:

- Primary soft green.
- Secondary warm soft yellow.
- Neutral sand/light background.
- Accessible contrast for text and buttons.

## 12) Out-of-Scope (Task 4)

- Payment gateway provider selection.
- Tax/VAT jurisdiction logic.
- Invoice PDF generation.

## 13) Completion Criteria

Task 4 is complete when:

- Plans/pricing/offer rules are approved.
- Cart scope and checkout rules are approved.
- Editability before/after deployment requirement is approved.
- Zen theme requirement is approved.
