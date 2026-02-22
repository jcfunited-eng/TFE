# TFE TODO LIST (Plain Action Format)

## Format Constraint (User-Approved)
- Always present this list as a flat numbered list in plain language.
- Do not bury critical status in long prose blocks.

## Status Key
- `OPEN`: not complete.
- `PARTIAL`: started but not closed.
- `DONE`: complete.
- `EXCEPTION`: approved out-of-scope / non-blocking unless user reverses.

## Completion Log (Removed From Active Queue)
- `DONE` Former items 1-6 completed and removed on 2026-02-21 UTC.
  - Gap-02 closure verification.
  - Gap-03 closure verification.
  - Gap-04 closure with legacy-read sunset policy.
  - Gap-08 closure with provider-boundary key handling.
  - UF-Core conformance hardening track closure for this release cycle.
  - SES-Core security posture closure for this release cycle.
- `DONE` Account lifecycle operations patch deployed on 2026-02-21 UTC.
  - Admin API/UI support for account disable.
  - Admin API/UI support for account removal.
  - Unused test-user cleanup operation.

## Active TODO Queue
1. `PARTIAL` Deterministic performance objective track (former Item 3 / +200% target work).
2. `PARTIAL` Portfolio allocator/rebalancer expansion (former Item 4), currently blocked by Item 1 closure quality gates.
3. `PARTIAL` Account security baseline (admin credential finalization, unused user cleanup, MFA activation/rotation, account security audit controls).
4. `OPEN` Billing foundation (Stripe checkout + billing portal + webhook security).
5. `OPEN` Subscription product setup (monthly/yearly/trials/coupons/tax/invoices).
6. `OPEN` Entitlement enforcement across premium UI + APIs.
7. `PARTIAL` End-user account UX (self-service reset/profile/session management).
8. `OPEN` Formal release workflow (staging lane, rollback drill, weekly triage cadence).
9. `PARTIAL` Tenant + SES operational hardening (rotation policy, access checks, audit coverage, isolation tests).
10. `PARTIAL` Automated refresh policy operations (daily targeted + weekly full + alerting).
11. `OPEN` Legal/ethical redirect monetization policy.
12. `OPEN` Domain migration plan (`www.gotfeai.com`).
13. `OPEN` Go-live awareness/promotion plan.
14. `OPEN` Documentation track (LaTeX admin manual + UF/SES spec revisions).
15. `OPEN` Portfolio benchmark ledger (same dollars/same dates: TFE vs SPY) with immutable export.
16. `OPEN` Production optimizer lane (offline horse race + gated promotion + rollback pointer).
17. `OPEN` Curated index universe lane (select high-signal indexes, validate provider entitlement + bar quality, then refresh universe+snapshot).
18. `PARTIAL` SCE standalone boundary enforcement in TFE runtime (keep non-approved SCE coupling out).
19. `OPEN` Account lifecycle governance controls (disable/remove approval policy, retention policy, and account restore procedure).
20. `OPEN` Regulatory controls design lane (21 CFR Part 11 and SOX-style controls: audit trail, sign-off workflow, change control evidence, and records integrity).

## Approved Exceptions (Non-Blocking)
1. `EXCEPTION` Section-23 enforcement activation for TFE runtime (monitor-only accepted unless user reverses).
2. `EXCEPTION` SafeMode forced enforcement path in live TFE runtime (monitor-only accepted unless user reverses).
3. `EXCEPTION` SCE-specific KAT/NIST/Dieharder runtime gating in TFE path (out-of-scope unless user reverses).
