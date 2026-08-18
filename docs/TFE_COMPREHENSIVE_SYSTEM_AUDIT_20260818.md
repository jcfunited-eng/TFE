# TFE comprehensive system audit — 2026-08-18

## Decision

TFE is running, but it is not presently a custody-safe or fully truthful production system. The deterministic kernel was not changed. The highest-risk failures are outside L0–L4: exposed credentials, broker/ledger divergence, two competing refresh schedulers, non-transactional snapshot custody, misleading portfolio labels, fail-open administration controls, and deployed code that is materially behind both the local repository and production's own later commits.

CH2 remains untouched. CH3, CH4, and CH6 now have separate, linked, read-only page implementations in the repository. They have not been published, deployed, or connected to any order path.

This audit provides complete source-inventory coverage of the defined TFE web, API, execution, refresh, feed, snapshot, and DSF-AI static surfaces. It does **not** claim impossible “100% behavior proof”: authenticated browser behavior was not exercised with Joseph's account, winter scheduling has not occurred yet, and no destructive or real-money order test was authorized. Those boundaries are explicit below.

## Mandatory architecture honesty gate

1. **Requested architecture:** a deterministic, full-field TFE proving ground with frozen L0–L4 physics, domain governance at L5, truthful website/admin reporting, reliable refresh and snapshot custody, reconciled Alpaca execution, and separate CH3/CH4/CH6 portfolio pages.
2. **Current code reality:** L0–L4 exists and was not edited, but several active L5, execution, refresh, page, and publication mechanisms use reduced projections, duplicate authorities, fallback values, or fail-open behavior. Production, GitHub, and the local repository are not on one commit.
3. **Conflict with requested architecture:** **yes**. The conflicts are in governance, execution custody, refresh authority, validation truth, deployment state, and website claims—not a finding that the frozen kernel itself should be changed.
4. **Mechanisms not extended:** no L0–L4 file; no `decision_vector` compatibility projection; no CH1 reduced 3WA selector; no manual Alpaca order endpoint; no current snapshot overwrite/restore scheme; no demo Step 1 publication authority; no duplicate refresh scheduler; and no fail-open MFA path.
5. **Single exact next item:** contain the exposed authentication credentials by rotating them and moving the production authentication secret out of plaintext ECS environment variables into a managed secret reference.
6. **Full field or reduced approximation:** this audit evaluates custody and implementation truth. The existing CH1 strategist and the current Reconstruction proof program are reduced approximations; neither is accepted here as full-field proof.
7. **Exact lost structure:** CH1 reduces the field to a SPY `D_k` gate, fixed `s_n`/delta bands, bar count, previous `D_k`, and an optional species lookup. The Reconstruction proof program omits `C_k` from its returned L4 tuple, implements only one spike vertex at one scale, substitutes absolute curvature for declared signed curvature, and drops peer/topology and window-memory structure.

## Evidence basis

| Evidence class | Inspected |
|---|---|
| Requested/specification | User-supplied LaTeX, repository UF v1.3 Reconstruction, canonical appendix hashes, TFE handoff, Claude skills |
| Local source | 17 Next.js pages, 33 API routes, 17 execution programs, 11 execution test programs, refresh/rebuild/restore paths, deploy/startup files, 18 DSF-AI HTML pages, repository state |
| Deployed configuration | ECS service/task/image, task environment flags, ALB health check, CloudFront/S3 object inventory, EventBridge schedules, IAM-backed storage access |
| Live runtime | TFE and DSF-AI HTTP behavior, ECS processes/logs, production PostgreSQL rows, paper Alpaca account/positions/orders, current snapshot objects and validation records |
| GitHub | branch/commit relationship and deployment drift |

The Claude artifact links require a Claude-authenticated browser and returned only the generic shell or were blocked by `robots.txt`. Their repository equivalents were therefore treated as the auditable record, not the inaccessible previews.

## Critical findings

### 1. Credentials are exposed or stored incorrectly

- Repository remote URLs contained live GitHub personal access tokens. They must be considered compromised and rotated. Their values are deliberately omitted from this report.
- The production task definition places an authentication secret directly in plaintext environment configuration rather than a managed secret reference. Its value is deliberately omitted.
- Admin MFA is not provisioned in the deployed task. `web/src/lib/mfa.ts` explicitly fails open when its TOTP secret is absent, so an admin password alone is accepted.
- Dependency audit reports 16 known vulnerabilities: 2 critical, 12 high, 1 moderate, and 1 low. The direct critical exposure is the installed Clerk middleware route-protection bypass; the installed Next.js version also has middleware/proxy bypass, SSRF, and denial-of-service advisories. Supported fixed releases exist, but dependency replacement was not mixed into this audit.
- TFE and DSF-AI omit the standard HSTS, CSP, frame, referrer, and related security headers. TFE also exposes `x-powered-by`.

### 2. Alpaca and the TFE ledger disagree

Production is connected successfully to **paper Alpaca**, not live Alpaca. The live endpoint rejected the configured credentials. At inspection time the paper account was active, had 24 positions and no open orders; the TFE ledger exposed only 22 open positions.

The two broker positions missing from TFE's current ledger view were:

| Symbol | Broker position | Ledger state |
|---|---:|---|
| CWAN | 100 shares | marked closed as `delisted`, without exit fill or P&L |
| HTBK | 67 shares | marked closed as `delisted`, without exit fill or P&L |

Both symbols have repeated duplicate closure records in the archive and permanent-looking cooldown exclusions through 2099. The website's position endpoint queries the ledger rather than the broker, so it hides both real paper-broker holdings.

### 3. Portfolio numbers are not what their labels say

- Missing market marks are silently replaced by entry price in existing portfolio calculations, creating a displayed zero P&L instead of an unavailable value.
- “Cash on hand” is derived from funded capital minus ledger positions, not Alpaca cash.
- “Portfolio value” is funded capital plus movement from a reset baseline, not broker equity.
- The legal and help pages state that TFE does not execute or route trades, while the admin portfolio contains a direct Alpaca order route. That is a material product/legal contradiction.

### 4. Snapshot publication is not one atomic generation

- Plain snapshot JSON and the rebuild report are truncated and rewritten in place. Only the encrypted envelope uses atomic replacement.
- JSON, envelope, and report are uploaded as three independent overwrites without a shared generation manifest, receipt, or hash binding.
- Startup restores those three objects independently, directly into final paths. It reports success when any one object downloads, allowing mixed generations.
- The plain snapshot is uploaded before the refresh wrapper stamps its `publication_id`; the stamped local file is not uploaded again. S3 and the database can therefore name different publication custody.
- S3 versioning is disabled and no lifecycle policy provides rollback custody.
- S3 persistence failures are declared non-fatal. `admin-refresh-persist` also suppresses all database persistence failures.

### 5. Production authority includes demo identities

The deployed Step 1 cutover contract uses `normalized-package-demo`, `policy-set-demo`, `model-set-demo`, and `config-set-demo`. The active production publication pointer names a bundle with those identities. This is live code + environment + database authority, not merely a future document or test fixture.

## High findings

### Refresh and validation

- Two independent authorities initiate refreshes: EventBridge at 00:17 UTC and the in-container scheduler at 13:00 UTC. Sunday universe refresh is likewise scheduled twice. Production rows show the expected duplicate daily and Sunday runs.
- The startup connectivity probe requests nonexistent `/api/health` without the internal token and calls any HTTP response “connectivity OK.” It does not prove refresh authorization or health.
- The latest validation is labelled `pass` while 2,193 `ta_semantics_integrity` rows are flagged.
- UI filter behavior is labelled `pass` when its base URL and credentials are absent; the recorded reason itself says the behavior test was not run.
- The admin system status declares health primarily from publication-serving permission. It does not include Alpaca/ledger reconciliation, daemon liveness, MFA enforcement, semantic validation flags, or snapshot-generation integrity.
- A 2026-08-05 entry pass marked its date before work succeeded, then failed database authentication. Because the date was already recorded, it did not retry that day.

### Execution supervision and order custody

- Next.js is PID 1. Refresh, sentinel, and fundamentals processes are background children with no independent service supervisor or restart policy. ALB health checks only `/`, so it cannot detect a dead sentinel or refresh daemon.
- The sentinel's fixed 13:30–20:00 UTC market window matches US daylight time but will be one hour wrong during winter standard time.
- The sentinel records `lastEntryPassDate` before executing the pass. A transient failure can suppress the whole day; a persistence failure can instead duplicate it.
- Account-state fetches do not consistently check HTTP status, ignore shorts/open orders, use long market value only, and include a hardcoded $100,000 fallback.
- The same-day sell exclusion describes itself as fail-closed but does not check HTTP status; an Alpaca error object can be treated as an empty exclusion list.
- The direct manual-order endpoint has no idempotency key, broker/ledger transaction boundary, order timeout, buying-power gate, full risk gate, or post-order reconciliation. It can execute while automatic entries are halted. If broker placement succeeds and ledger insertion fails, it still reports success.
- The separate manual-trade endpoint creates a filled ledger position without creating a broker order.
- Execution mode can be changed through an admin database setting, including to `live`; the order route then chooses the live Alpaca base URL itself rather than honoring one controlled configured endpoint.
- The admin PEE1 endpoint spawns detached runners without a process lock. The current runner is audit-only, but duplicate process launch remains uncontrolled.
- Silent exception handling remains across the execution suite, including table absence and broker/process paths, so failure can disappear from operational status.

### CH1 is not a proven full-field channel

`3wa_strategist.mjs` is a reduced selector, not a full seven-field evaluation. Its optional `species_profiles` table does not exist in production; the code falls back to an empty map and continues. If the SPY `D_k` gate opens, ordinary Accumulate candidates may be returned as standard/1+3 signals. Since 2026-07-20, observed live runs remained closed because SPY `D_k=-1`; the absence of CH1 trades is therefore inactivity, not validation.

### Authentication and uploads

- Unauthenticated protected page/API probes consistently redirect, but the generated return URL names `https://0.0.0.0:3000/...`. The proxy constructs redirects from the internal request URL instead of trusted forwarded host/protocol values.
- Image upload endpoints write into the running container's local `public/uploads` directory. TFE has no persistent volume, so uploaded files and database paths can break at the next replacement or deployment.
- The global internal-token bypass exists at middleware level. Route-local authorization currently prevents a simple null-user bypass on inspected endpoints, but the broad bypass increases the consequence of any future route missing its own check.

### Deployment and repository drift

- Production runs image `manual-20260813T164628Z` from commit `055a5679…`.
- The local branch was 32 commits ahead of the deployed commit.
- GitHub's branch was two commits behind production and 61 commits behind the local branch at the audit point. GitHub is not the recoverable source of either current development or deployed truth.
- The ECS task has no volume and no container health check. Its only service health is the ALB root-page response.

## DSF-AI website findings

- Every link reachable from the live root returned HTTP 200.
- The S3 deployment is partial and stale relative to the repository. Multiple repository pages are absent from the live static prefix, including admin, battery, discovery, hardware derivation, predictions, and the static copies of GualaLoom/LoomScan.
- `/gualaloom.html` and `/loomscan.html` exist through a separate root deployment path, demonstrating split publication custody.
- The DSF-AI root links `/static/legal.html`, but that live object is a Guala operational/privacy notice dated 2026-07-28. The repository's DSF-AI terms/privacy page is a different document dated 2026-05-11. The public site therefore points to the wrong legal authority.
- Live `index.html`, `app.js`, and `style.css` are older than local files. The local index includes an Analysis Summary block that the live application does not contain.
- The deploy script's selection rules and the observed object set are not one reproducible full-site manifest.

## Complete page and route coverage ledger

### Next.js pages — 17/17 inventoried

| Surface | Result |
|---|---|
| `/` | Public page responds; year-long shared-cache policy is excessive for an actively changing entry surface. |
| `/sign-in`, `/account` | Clerk + local role/session bridge; admin MFA fails open when unconfigured. |
| `/recommendations` | Protected; relies on publication/runtime decision surfaces. |
| `/screener` | Protected; very large server route, snapshot/publication and quote-cache dependent. |
| `/watchlist` | Protected; user state plus chart/live-ingestion dependencies. |
| `/portfolio`, `/portfolio-advisor` | Same portfolio implementation; admin execution manager plus manual tracker. Existing totals and trade claims are misleading as described above. |
| `/portfolio/[channel]` | New repository-only CH3/CH4/CH6 read-only route; admin-only; SHA receipt required; not deployed. |
| `/admin-console` | Admin-only control surface; health summary is incomplete. |
| `/admin-console/auditor` | Admin-only ledger/execution trace; ledger cannot establish broker custody by itself. |
| `/admin-console/refresh-log` | Admin-only refresh history; duplicate authorities and swallowed persistence can make it incomplete. |
| `/admin-console/validation` | Admin-only; current pass semantics permit unexecuted/flagged checks. |
| `/help` | Incorrectly says TFE does not execute trades and supports manual tracking only. |
| `/legal` | Incorrectly says TFE does not accept, route, or execute orders. |
| `/support` | Static email support scope; no incident or execution escalation path. |
| `/theme-preview` | Protected presentation surface; no execution authority. |

### API routes — 33/33 inventoried

| Group | Routes | Audit result |
|---|---:|---|
| Admin audit/status | `auditor`, `exact-path-alignment`, `model-accuracy`, `recommendation-quality`, `rulebook-coverage`, `signal-filter`, `system-status`, `validation-dashboard`, `validation/latest` | Role checks exist. Several metrics are ledger/publication proxies rather than end-to-end truth; silent optional-table fallbacks remain. |
| Admin refresh | `refresh`, `refresh/history`, `refresh/log` | Role/internal-token checks exist. Route is 3,000+ lines, combines orchestration and publication, coexists with duplicate scheduling, and permits prepublish failure to be recorded while the legacy refresh still launches. |
| Admin mutation | `market-banner`, `market-banner/upload`, `ui-config`, `upload-image`, `test-users`, `pee1` | Role checks exist. Upload custody is ephemeral; PEE1 launch is detached/unlocked; test-user CRUD is production-capable. |
| Authentication | `auth/session`, `auth/sign-in`, `auth/sign-out` | Local authentication bridge works structurally; admin MFA is fail-open when secret is absent. |
| Portfolio execution | `pee1-config`, `pee1-manual-trade`, `pee1-place-order`, `pee1-positions`, `pee1-summary` | Admin checks exist. Broker/ledger split, phantom manual fills, order idempotency/transaction failures, and misleading summaries are material. |
| Portfolio/manual state | `portfolio` | Authenticated user CRUD; encrypted user envelope path plus runtime publication dependencies. |
| Recommendations | `recommendations/list`, `recommendations/quick-check` | Authenticated; publication/runtime decision dependent; reduced/fallback fields must not be mistaken for full-field authority. |
| Screener | `screener` | Authenticated; large multi-feed route with cached and live quote paths, so source/mark provenance must remain visible. |
| Watchlist | `watchlist`, `watchlist/chart` | Authenticated; user-state and live-ingestion/chart paths inspected. |
| Market banner | `market-banner` | Authenticated read; points to potentially ephemeral uploaded assets. |

### DSF-AI static HTML — 18/18 inventoried

Repository pages: `account`, `admin`, `battery`, `case-battery`, `case-fese`, `case-mgb2`, `case-pharma-dsc`, `case-vo2`, `discovery`, `gualaloom`, `hw-derive`, `index`, `legal`, `loomscan`, `pharma`, `predictions`, `validation-draft`, and `validation`.

The live static prefix contains only a subset. This ledger distinguishes repository presence from deployment presence; it does not label absent objects as published.

## Feed, refresh, and process coverage ledger

| Surface | Source reality | Live/runtime result |
|---|---|---|
| Alpaca account/order feed | REST account, order, position, and IEX snapshot calls across sentinel and APIs | Paper credentials active; live rejected; 24 broker positions vs 22 ledger positions |
| Market bars/universe | Massive/unified market services, database bars, ETF/index/crypto universe files, Yahoo index fallback | Latest snapshot contains 11,483 rows; source fallbacks and refresh provenance span multiple mechanisms |
| Quotes | Alpaca IEX plus quote-cache and route fallbacks | Existing portfolio paths can replace missing marks with entry values; new channel pages withhold incomplete totals |
| Fundamentals | recurring backfill with primary/fallback fetchers | Background loop alive at inspection; unsupervised, non-fatal failure policy |
| Snapshot | rebuild JSON + encrypted envelope + report, upload to S3, DB sync | Non-atomic generation; publication ID stamped after S3 upload; no version rollback |
| Refresh scheduling | EventBridge plus in-container loop | Duplicate daily and Sunday executions proven in DB history |
| Sentinel | daemon, monitor, strategists, bridges, circuit breaker, calendar | Process alive at inspection; ALB cannot supervise it; fixed UTC/DST and daily-marking defects |
| CH1 | `3wa_strategist` to Alpaca bridge | Reduced field; missing species table; inert under observed SPY gate; not validated |
| CH2 | strategist/ledger/broker path | Active paper positions; user law preserved; no code or halt change made |
| CH3 execution lane | production CH3 strategist/bridge | Automatic CH3 entries halted in deployed environment; historical closed ledger rows remain |
| CH3/CH4/CH6 experiment books | local authoritative JSON artifacts and local runners | Separate from broker execution; local loops were not continuously supervised; CH6 book and generated page had publication timing drift |
| Admin health | publication/runtime DB summaries | Can say healthy while broker custody, MFA, validation, or background processes are unhealthy |

## Completed Joint-Field Reconstruction status

The user-supplied attachment is byte-identical to `docs/UF_Spec_v1_3_JointField_Reconstruction_VERBATIM.tex` apart from final-newline handling, and the historical DOCX hash agrees with the provenance record. The document was originally produced by Codex and should no longer be described by the Claude skill as Joseph's authored canonical specification.

The correct status is exactly the user's current decision: **strong working document requiring additional proofs; non-canonical**.

`tools/ch3_joint_field_full.py` was not executed as proof because static inspection invalidates the claimed proof boundary before runtime:

- declared signed curvature is implemented as absolute curvature;
- `C_k` is absent from the returned L4 field;
- only one spike vertex and scale 8 are evaluated;
- “exact” dyadic normalization passes through floating division;
- peer/topology coupling and window memory are declared losses.

Running it could produce numbers, but those numbers would not prove the document's full joint-field construction. The Claude skill and handoff overstate both provenance and authority and must not be used as canonical governance.

## CH3, CH4, and CH6 linked pages

Repository implementation now provides:

- admin-only links from Portfolio to CH3 Shadow Hunter, CH4 Structural Channel, and CH6 Fast Harvest;
- one dedicated route per channel through `/portfolio/ch3`, `/portfolio/ch4`, and `/portfolio/ch6`;
- exact-byte private snapshot envelopes with SHA-256 receipts;
- task-role S3 reads without adding public endpoints or credentials;
- current Alpaca IEX marks with HTTP status checks and an eight-second timeout;
- withheld equity/unrealized totals if any required mark is absent;
- explicit read-only copy and no mutation/order controls.

The publisher, scheduler, and pages are code-complete but **not operationally delivered**. No S3 objects were written, no background publisher was started, no task definition was changed, and no deployment or GitHub push occurred. A production-grade supervisor/publication deployment must be designed before these pages can honestly be called live.

## Verification performed

- Existing execution suite: 11 programs, 173 assertions, all passing.
- Channel snapshot envelope tests: 4 passing.
- Channel publisher dry run: passed for CH3, CH4, and CH6 authoritative books.
- TypeScript compilation: passed.
- Targeted ESLint for all new/changed page code: passed.
- Production build: recorded separately in the commit handoff after completion.
- Live public HTTP checks: TFE unauthenticated behavior and every root-linked DSF-AI page checked.
- Runtime checks: ECS service/processes/logs, ALB, EventBridge, S3, CloudFront, database, and Alpaca paper account inspected read-only.

These tests prove the named boundaries only. The 173 execution assertions do not prove broker/ledger reconciliation, daemon supervision, snapshot atomicity, or authenticated UI behavior.

## Explicit exclusions and non-actions

- No L0–L4 code was changed.
- No trade was placed, cancelled, or altered.
- CH2 was not halted, changed, or used as a test surface.
- No production database row, S3 object, ECS task, EventBridge rule, CloudFront object, GitHub branch, or live page was changed.
- No secret value is recorded in this report.
- No claim is made that unauthenticated redirects prove authenticated page behavior.
- No Slack completion ping was possible because this workspace has no Slack connection or callable Slack mechanism.

## Recommended next item

**Credential containment:** rotate the exposed GitHub tokens and production authentication secret, then replace the plaintext ECS secret value with a managed secret reference and verify that old credentials are rejected. This is the single recommended next item because every later custody repair is unsafe while known credentials remain exposed.
