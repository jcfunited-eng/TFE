# TFE comprehensive system audit — final remediation record — 2026-08-18

## Decision

The audited non-security repair set is deployed. TFE now serves one receipt-verified immutable UF snapshot generation, uses Alpaca paper custody as portfolio authority, supervises its runtime processes, reports operational health from process/database/snapshot evidence, and exposes separate read-only CH3, CH4, and CH6 pages linked from Portfolio.

This does not make CH1, CH3, CH4, or CH6 proven trading physics. It makes their custody and public claims substantially more truthful. CH2 selection and exit physics were not changed.

Security work was explicitly deferred by Joseph. Authenticated browser behavior was not exercised with Joseph's account, and no order was placed, cancelled, or altered.

## Architecture honesty gate

1. **Requested architecture:** frozen L0–L4, deterministic L5 governance, truthful pages and administration, authoritative paper-broker custody, one refresh authority, immutable snapshot publication, and separate channel pages.
2. **Current code and production reality:** the non-security custody/runtime implementation is deployed at commit `0b1fc142fe09ad8da4761694cde91c37bab09c9c`; ECS task revision 606 runs image `manual-20260818T054720Z` with digest `sha256:c2e3e1baad1c963261658e30b64ca782ed16d66e527e5c35ec0e4462b5a53ccc`.
3. **Conflict with requested architecture:** **yes, at the physics boundary.** CH1 remains a reduced selector. CH3 and CH6 remain reduced spike-fade experiments. The Completed Joint-Field Reconstruction remains a strong working document requiring more proof, not canonical authority.
4. **Mechanisms not extended:** L0–L4; the `decision_vector` compatibility projection; the demo Step-1 production contract; mutable snapshot overwrites; manual broker ordering; ledger-only fills; detached execution launch; randomized stealth execution; or the duplicate circuit breaker.
5. **Single exact next item:** declare and forward-test a full-field eligibility/refutation experiment for CH3 without changing CH2 or CH6 production behavior.
6. **Full field or reduced approximation:** the deployment and custody work adds no field evaluator. CH1, CH3, and CH6 are explicitly reduced approximations.
7. **Lost field structure:** their active selection logic does not jointly preserve and evaluate `D_k`, `M_k`, `R_rev_k`, `U_star_k`, `C_k`, `P_k`, and `B_k`, including their time evolution, contradictions, topology, peer context, and system energy.

## Coverage and proof boundary

Source inventory covered all 17 Next.js page files, all 35 API routes, all 19 top-level execution programs, all 15 current execution/validation tests, snapshot rebuild/restore/publication, EventBridge scheduling, ECS startup and supervision, Alpaca paper reads, PostgreSQL health, S3 channel books, and all 33 objects in the DSF-AI static manifest.

Production checks covered ECS task/image/commit identity, CloudWatch startup logs, immutable snapshot restoration, database health, supervisor heartbeat, ALB target health, and public responses for root, Portfolio, CH3, CH4, CH6, Admin Console, refresh log, validation, Screener, Recommendations, Watchlist, Help, Legal, and Support.

This is complete inventory coverage of the defined surfaces, not a claim that every possible runtime state has occurred. Protected page content still requires an authenticated browser session; winter market-time behavior must be observed when winter occurs; and real/paper order mutation was not used as a test method.

## Production receipts

| Boundary | Verified result |
|---|---|
| Git/source identity | `0b1fc142fe09ad8da4761694cde91c37bab09c9c` |
| ECS | `tfe-web-task:606`, one running task, task and container `HEALTHY` |
| Image | `manual-20260818T054720Z`, digest `sha256:c2e3e1baad1c963261658e30b64ca782ed16d66e527e5c35ec0e4462b5a53ccc` |
| Snapshot generation | `snapshot_pub_v2_76d4edfbb3c9460cab59b8a1` |
| Snapshot payload | 11,483 rows; strict JSON; plaintext and encrypted payload independently compared |
| Snapshot artifacts | snapshot, SES envelope, and rebuild report verified against one manifest before restore |
| Runtime health | process heartbeat `true`; database `true`; snapshot receipts `true` |
| Load balancing | ALB and ECS container health both use `/api/health`; expected status exactly 200 |
| Channel books | CH3, CH4, and CH6 source bytes decoded from S3 and matched local SHA-256 receipts |
| DSF-AI static site | 33/33 manifest objects downloaded from the public site and matched by hash and size |

## Completed repairs

### Portfolio and Alpaca custody

- Portfolio positions, cash, equity, buying power, and exposure now come from Alpaca paper custody rather than an incomplete ledger projection.
- Shorts and long positions are included in gross exposure.
- Open buy commitments are included in entry-capital accounting.
- Missing marks no longer become entry-price zero-P&L claims.
- Broker HTTP status, timeout, and response-shape checks fail closed.
- Paper-only execution is enforced across active bridges, routes, sentinel, and auditor paths.
- The direct manual Alpaca order route and ledger-only filled-trade route return explicit refusals.
- Detached runner launch, randomized stealth execution, and the duplicate standalone circuit breaker were retired.
- `auto_tfe_enabled=false` now actually prevents new entries; configuration-read failure also prevents entries.

Historical broker/ledger divergence remains visible as history rather than being erased. Broker custody is authoritative for current holdings.

### Snapshot, refresh, and runtime

- Snapshot JSON, encrypted envelope, and rebuild report publish under one immutable generation prefix.
- A manifest binds every artifact by SHA-256 and byte length; `current.json` is written last.
- Startup restores into temporary custody, verifies every receipt, and fails before the screener starts if the generation is incomplete.
- The legacy mutable snapshot upload lane is disabled; the independent bar-cache export remains.
- One legacy `NO_DATA` price encoded as `NaN` was converted at the transport boundary to JSON `null`; the SES envelope was regenerated and independently decrypted against the exact normalized payload. Kernel work was not altered.
- EventBridge is the sole refresh schedule authority; the duplicate in-container scheduler is removed.
- Runtime children are supervised, and daily entry custody is tied to New York market dates rather than fixed UTC hours.
- The daily completion mark is written only after successful completion.
- Validation reports fail closed when a required test is absent, unexecuted, or semantically flagged.
- Operational health requires process heartbeat, database availability, and verified snapshot receipts.

### Pages, admin, feeds, and publication truth

- Portfolio links to `/portfolio/ch3`, `/portfolio/ch4`, and `/portfolio/ch6`.
- Each channel page is read-only, reads its own private S3 book envelope, verifies the embedded exact-byte SHA receipt, fetches marks with bounded status-checked requests, and withholds totals when marks are incomplete.
- CH1 missing species custody now fails its pass instead of continuing through an empty fallback.
- Only executable `3WA` output is handed to the CH1 execution lane; W1/SPY observations are labelled `W1_SPY`, not silently treated as 3WA orders.
- The existing 3.5% CH1 allocation remains exact but is explicitly labelled reduced and noncanonical.
- Invented conviction scoring and hardcoded unreceipted backtest claims were removed from active page claims.
- Market-banner state no longer substitutes `D_k=-1` for unavailable data or calls an absent feed “locked.”
- Admin validation and health panels now expose failures rather than converting absence into success.
- Uploaded UI assets are stored as immutable S3 objects and served through a bounded asset route rather than container-local ephemeral storage.
- Help/legal/execution disclosures now distinguish the paper execution sandbox from customer brokerage execution.
- Demo Step-1 identities and cutover authority were removed from production environment control.

### DSF-AI static publication

- One bounded publisher now owns the DSF-AI static manifest.
- Root ownership is limited to `index.html`, `robots.txt`, and `sitemap.xml`; other DSF static objects live under `/static`.
- Managed `/static` publication uses exact synchronization, re-download hash/size verification, and CloudFront invalidation.
- The separate root GualaLoom and LoomScan deployments were not overwritten.
- The stale/partial pages and incorrect DSF legal-object source were corrected.

## CH3 and CH6: measured capability verdict

The pages are no longer the main problem. The engines are.

WETO was in fact sold short. CH3 shorted it at `$8.22`; it later exited at `$17.47`, a `-112.53%` short return and `-$3,080.25`. CH6 took the same event at smaller size and lost `-$2,247.75`. The failure was not “forgetting to short the spike.” The failure was assuming that a large uncovered spike was exhausted merely because it was large and uncovered.

CH6's closed record makes the asymmetry plain:

- 10 profitable harvests produced `+$1,663.74`.
- 2 anomaly cuts lost `-$2,396.74`.
- Realized result was therefore `-$733.00`, despite 10 profitable closures against 2 losing closures.

That is a high-win-rate, negative-expectancy mechanism. One discontinuous short squeeze can erase many 5% harvests. A software rule that checks `-20%` every five minutes cannot guarantee a 20% loss cap across overnight, weekend, halt, or gap discontinuities. WETO proves that distinction: the rule existed, but the executable price jumped beyond it.

The selection defect is structural. CH3/CH6 select event magnitude, volume, price, and herd coverage, but do not establish full-field exhaustion. They cannot distinguish a terminal spike from genuine price discovery, persistent demand, a new regime, or a squeeze with unavailable borrow/liquidity. CH6 then takes small gains quickly while retaining the full discontinuous loss tail. CH3's larger/margin deployment amplifies the same defect.

My recommendation is to keep CH3 new entries halted and not extend CH6 until a declared, forward-only full-field eligibility/refutation test proves that it can separate exhaustion from continuation. This recommendation does not authorize changing CH6 or CH2.

## CH2 opinion and boundary

CH2 is now represented from paper-broker custody instead of ledger-only current state. Its selection and exit laws were not changed, halted, or used for mutation testing. The audit establishes improved operational custody; it does not establish CH2 predictive merit or the 85% physics floor.

## Completed Joint-Field Reconstruction status

The user-supplied attachment matches `docs/UF_Spec_v1_3_JointField_Reconstruction_VERBATIM.tex` apart from final-newline handling. Its correct status is Joseph's current decision: **strong working document requiring additional proofs; non-canonical**.

The present `tools/ch3_joint_field_full.py` does not yet prove the full construction because its current implementation omits `C_k` from the returned L4 tuple, evaluates one spike vertex at one scale, substitutes absolute curvature for declared signed curvature, and does not retain the full peer/topology and window-memory structure. Those are implementation/proof gaps, not a finding that the working document lacks merit.

## Deliberately unresolved

- Security remediation was deferred: credential rotation/storage, fail-open MFA, dependency advisories, security headers, internal-token breadth, auth redirect construction, and related hardening remain open.
- Authenticated page behavior was not tested with Joseph's account.
- The CH3/CH4/CH6 research-book generators remain local experimental processes rather than a durable cloud service. Their pages are live and their last exact books are published, but automatic future book generation cannot honestly be called production-durable yet. Moving CH6's runner changes Joseph-owned runtime custody and requires his explicit approval.
- Production still has `CH3_ENTRIES_HALTED=1`. It was preserved because enabling a paper order path is a material execution-state change, not a passive website repair.
- Git commits are local on `guala-live`; no origin push was authorized.
- No Slack completion ping had been possible at the time this report was written unless the repository notification transport succeeds during final handoff.

## Verification

- 15/15 current execution and validation programs passed.
- Snapshot-generation tests: 5/5 passed.
- TypeScript, targeted ESLint, and Node 22 production build passed in the strict deployment gate.
- CodeBuild succeeded and pushed the exact production image.
- ECS task and container health are `HEALTHY`.
- Public operational health returned 200 with all required checks true.
- All named public routes returned HTTP 200; protected content remains an authenticated-session boundary.
- No L0–L4 file was changed.
- No real or paper order was placed, cancelled, or altered as part of this audit.
