# TFE Admin Console Specification

Version: 1.1
Status: Approved add-on to Task 4

## 1) Purpose

Define an administrator-only console for managing users, access, surveys, and research metrics for UF-Core and SES-Core performance evaluation.

## 2) Access Control (Mandatory)

- Admin Console must be visible only to authenticated users with admin role.
- Non-admin users must never see admin navigation items.
- Direct URL access by non-admin users must return access denied.
- All admin actions must be logged with actor, timestamp, and action details.

## 3) Navigation Placement

- Do not include Admin Console in normal public/user menu.
- Admin Console appears only after admin authentication check passes.

## 4) Core Admin Functions

### 4.1 User Access Management

Admin can:

- View user account list.
- View current subscription plan/status.
- Activate or suspend access.
- Mark survey compliance status for Founding 1000 users.

Every change must create an audit event.

### 4.2 Test User Management (Bypass Mode)

Admin can:

- Create test users for QA/research validation.
- Mark user type as `test_user`.
- Grant access that is not bound by subscription status.
- Grant access that is not bound by survey requirements.
- Set expiration date/time for test-user access.
- Revoke test-user access immediately.

Mandatory controls:

- Test users must be clearly labeled everywhere as `TEST USER`.
- Test users must be excluded from paid member counts and billing metrics.
- Test user creation, extension, and revocation must be fully audited.

### 4.3 Subscription Operations View

Admin can view:

- Active monthly users.
- Active annual users.
- Founding 1000 count and remaining slots.
- Failed payments requiring follow-up.

Admin cannot execute stock transactions (explicitly prohibited).

### 4.4 Survey Results Review

Admin can view:

- Monthly survey completion rate.
- Overdue survey users.
- Basic trend summary across months.

The console must support exporting survey summary data.

### 4.5 UF/SES Research Metrics Dashboard

Admin can view system-level research metrics, including:

- Count of ticker evaluations.
- Distribution of advisor outputs (`Accumulate`, `Hold`, `Trim`).
- UF stability summary metrics (`S_UF`, `R_UF`, stability score aggregates).
- SES envelope operation health (encrypt/decrypt success/failure counts).
- Chain-of-custody event volume and error counts.

Metrics are for research operations only, not investment guarantees.

### 4.6 Audit and Traceability

Admin can view:

- Configuration changes (pricing, legal text, offer caps).
- Access status changes.
- Survey status overrides.
- Test-user access creation/expiry/revocation history.
- System error events tied to admin operations.

Audit entries must be immutable once written.

## 5) Required Admin Disclaimers

Admin Console must display:

- `Research operations dashboard only.`
- `This system does not provide financial advice.`
- `This system does not execute trades or purchases.`

## 6) Security and Safety Requirements

- Role check must be server-side enforced.
- Session timeout required for admin sessions.
- Sensitive admin actions require confirmation.
- Failed access attempts must be logged.
- Test-user bypass permissions must be limited to admins only.

## 7) Visual and UX Direction

- Follow TFE minimal Zen design direction.
- Soft green/yellow theme with high readability.
- Keep dashboard dense enough for operations but plain-language labels only.

## 8) Out-of-Scope for This Task

- Full identity provider integration details.
- Payment processor admin APIs.
- Advanced BI chart engine selection.

## 9) Completion Criteria

This task is complete when:

- Admin-only access rules are approved.
- User/survey/subscription/test-user operations are approved.
- UF/SES research metrics list is approved.
- Audit/traceability and security requirements are approved.
