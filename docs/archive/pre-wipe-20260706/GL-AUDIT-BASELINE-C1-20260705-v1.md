> **SUPERSEDED — DO NOT TREAT AS CURRENT TRUTH.**
> This document describes substrate state as of pre-wipe (2026-07-06
> wipe operation, GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1).
> The substrate described here no longer exists. Preserved as
> historical record only.
> For current substrate state, run the harness against production.

---

# GL-AUDIT-BASELINE-C1-20260705-v1

doc_id: GL-AUDIT-BASELINE-C1-20260705-v1 (Deliverable D2)
Part of: GL-CMD-PRODUCTION-AUDIT-C1-EVE-20260705-210-v2 — the consolidated baseline.
Author: c1 | Freeze respected throughout — read-only against production; mutating tests
exclusively against an isolated, torn-down-at-exit shadow instance. This document indexes and
summarizes the nine section reports; it does not repeat their evidence — follow the links for
detail. Running SHA audited: `168ef1bde3717e52efb85b894103de047e942617` (`dsf-ai-task:494`).

## Bottom line

Every layer the dispatch asked for was audited, evidence-graded, and filed. The single most
important finding: **Guala's disaster-recovery restore procedure does not exist in runnable
form today** — proven, not inferred, by actually attempting the restore this audit was chartered
to validate (§0.6/§3, defects register item 1). A second, independently severe finding: **43 of
65 HTTP endpoints, including the entire chat/upload/sensory/save surface, have no authentication
at all** (§5, item 2), and separately, **production's own network security group allows direct
internet access to the container on port 8080**, bypassing every routing/timeout/auth layer above
it (found while isolating the audit's own shadow, item 3). A live crash was caught in the act
during this audit (§6/7/7A, item 4). Full defects register: 43 numbered items,
`docs/GL-AUDIT-DEFECTS-REGISTER-C1-20260705-v1.md` (D3).

## Section-by-section index

| § | Title | File | Headline |
|---|---|---|---|
| 1 | Runtime truth | `GL-AUDIT-SEC1-RUNTIME-TRUTH-C1-20260705-v1.md` | Running SHA matches origin tip modulo docs-only commits (zero code drift); manual/root-only deploy pipeline; `/ready` vs `guala_ready` health-check gap discovered |
| 2 | AWS truth | `GL-AUDIT-SEC2-AWS-TRUTH-C1-20260705-v1.md` (v2, corrected) | Full ALB/API-Gateway/Lambda topology mapped for the first time; plaintext secrets; two-backup-mechanism divergence; zero alarms; API-Gateway-timeout finding later refined by §5 |
| 3 | State truth | `GL-AUDIT-SEC3-STATE-TRUTH-C1-20260705-v1.md` (v2, corrected) | 15-file open/parse pass clean; wave_atlas.npz backup gap quantified; **DR restore proven broken, then proven fixable only via undocumented manual step** — the audit's top finding |
| 4 | Code truth | `GL-AUDIT-SEC4-CODE-TRUTH-C1-20260705-v1.md` | 65 endpoints/32 env-vars/90 except:pass/6 test failures, all re-verified from scratch; several pre-audit numbers corrected; dead hemisphere subsystem and dead boot functions found |
| 5 | Interface truth | `GL-AUDIT-SEC5-INTERFACE-TRUTH-C1-20260705-v1.md` | 43/65 endpoints unauthenticated (top security finding); API-Gateway-timeout severity corrected (real chat UI structurally avoids it); two real breakages (teacher/feedback routes) found |
| 6/7/7A | Learner/sensory/environment truth | `GL-AUDIT-SEC6-7-7A-LEARNER-SENSORY-ENV-C1-20260705-v1.md` | **Live crash caught in the act** (video restore type confusion); sight-snapshot bug found already fixed; V3 world-sim confirmed absent; learner feeds mostly text-only |
| 8 | Behavioral baseline | `GL-AUDIT-SEC8-BEHAVIORAL-BASELINE-C1-20260705-v1.md` | The BEFORE column for every future claim; extends the "empty senses during active sensory activity" pattern to the audio leg |
| 8A | Function test matrix | `GL-AUDIT-SEC8A-TEST-MATRIX-C1-20260705-v1.md` (D4) | 11 real evidence-backed rows (5 read-only/production, 6 mutating/shadow), 0 failures; every mutating row carries its required DR-workaround provenance annotation |
| 9 | 30-day documentation sweep | `GL-AUDIT-SEC9-DOC-SWEEP-C1-20260705-v1.md` + `GL-AUDIT-TODO-LEDGER-C1-20260705-v1.md` (D5) | 528 docs classified; uncommitted-worktree claim contradicted; a voided report traced to its root cause; 189-item consolidated TODO ledger |

## What changed between first filing and final filing (the adversarial-verification discipline in
## action, per §0.3's own law: nothing inherited, re-verify everything)

- The API-Gateway-timeout finding was filed as "SEVERE" in §2's first pass, then independently
  refuted-and-refined by both §5's own evidence and a separate adversarial verification workflow:
  the specific route feared (`/v7/converse`) gets zero real traffic; the real chat UI was already
  re-architected around the 30s wall. Both §2 and §3's text were edited in place to carry this
  correction rather than leaving a stale severe claim standing.
- The wave_atlas.npz finding's exact numbers held up byte-for-byte under independent
  re-verification, but its attribution to ticket `-207` was wrong — corrected to the true, earlier,
  currently-dormant `-59`/`-85` ticket, materially lowering its present-day urgency.
- The stuck-restore finding was the one claim that got *stronger*, not weaker, under scrutiny:
  independent verification found the root cause of why it was never caught (the one restore-drill
  tool that exists bypasses the exact code path that fails), and Eve's own explicit authorization
  to attempt the workaround turned "restore looks broken" into "restore is proven broken, and here
  is the exact undocumented step that's the only thing standing between backup and a working
  system."
- Two security findings were caught only because this audit's own shadow-instance work triggered
  them: the S3-backup-destination-is-hardcoded gap (item 10) and the wide-open security group
  (item 3) were both found, and both were fixed for the audit's own resource, without ever
  modifying production. Both are also process lessons: the auditor made these two mistakes before
  catching them, not before creating them — recorded honestly in the resource manifest and in the
  changelog of this document, not smoothed over.

## Deliverables status

- **D1** (scripts, `tools/audit/`): `sec4_code_truth.py` (env/deadcode/stubs/todo/exceptpass/
  constants sub-commands, reusable, documented in §4). **Partial** — most AWS-facing checks this
  audit ran were direct `aws` CLI invocations documented inline in each section report (fully
  reproducible by copy-paste, per the exact commands shown) rather than packaged as standalone
  scripts. Honest gap: a fuller D1 would wrap the AWS-side checks (ALB routing, API Gateway route
  diffing, S3 backup-lineage comparison, IAM role enumeration) into their own committed scripts too
  — not done this pass, flagged rather than implied complete.
- **D2** (this document): complete.
- **D3** (defects register): complete, 43 numbered items.
- **D4** (test matrix): complete, 11 rows, explicit list of what wasn't tested.
- **D5** (TODO ledger): complete, 189 items, via §9.

## Exit condition

Per the dispatch's own exit criteria: D1-D5 filed (this document plus links above); every layer
evidence-graded; the one explicit remaining `NOT MEASURED` items are named plainly in each section
report (organism/tapestry tick-consistency question in §3; ~61 unverified dead-code candidates in
§4; several routes/tools not individually exercised in §8A) rather than silently implied complete.
Nothing ships from this audit — the register is the queue, Joe routes it, one item at a time.

### Changelog
- v1 (2026-07-05, c1): initial and final baseline. All nine layers filed and cross-indexed; the
  three corrections made under adversarial verification recorded plainly rather than only in the
  underlying section files.
