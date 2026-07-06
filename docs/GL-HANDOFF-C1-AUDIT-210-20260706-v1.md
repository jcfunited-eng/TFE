# GL-HANDOFF-C1-AUDIT-210-20260706-v1

doc_id: GL-HANDOFF-C1-AUDIT-210-20260706-v1
From: c1 (audit seat, GL-CMD-PRODUCTION-AUDIT-C1-EVE-20260705-210-v2) | To: whoever picks this up
next (c1 continuation, c1b, Eve, Joe)
Session-end handoff — the audit itself is complete and filed; a lot of routing/fix work is about
to start from here.

---

## Bottom line

The full production audit (§1-§9, §8A, D1-D5) is **complete, evidence-graded, and filed** on
`guala-live`. Production was never modified — the freeze held for the entire audit. The one
isolated shadow instance used for mutating tests was **fully torn down and independently
re-verified clean** (zero residue: no leftover tasks, EFS access points, IAM roles, security
groups, or S3 contamination). Nothing ships from this audit automatically — **the freeze remains
in effect until Joe explicitly starts routing items from the defects register, one at a time**,
per the dispatch's own exit condition.

**Read `docs/GL-AUDIT-COMPREHENSIVE-C1-20260705-v1.md` for everything** — it's the full audit,
every section, concatenated into one document (4,749 lines). The individual section files it was
built from are also all present in `docs/` if you want them separately. This handoff is a
navigation aid and a "what you need to know before touching anything" note, not a re-statement of
the findings themselves.

## What's true right now (re-verify before acting — things move fast in this environment)

- Running production SHA: `168ef1bde3717e52efb85b894103de047e942617` (`dsf-ai-task:494`) as of
  this audit. **Re-check** — production redeployed itself at least twice more during this audit
  session alone (churn is normal here, per item 3/11 in the register).
  `guala_status`/`aws ecs describe-services --services dsf-ai-service-lb` will tell you the truth.
- The shadow instance and every resource it needed are gone (verified in
  `tools/audit/AUDIT-RESOURCE-MANIFEST.md`'s final status block). If mutating-capability testing
  is needed again, **do not casually stand up another shadow the same way** — see "Standing risks"
  below first.

## The four things Joe most likely wants routed first (this auditor's read, not an order)

1. **DR-restore does not exist in runnable form** (register item 1) — no backup is actually
   restorable end-to-end today without an undocumented manual step. This is the single biggest
   finding; it was *proven*, not inferred, by actually attempting the restore.
2. **43 of 65 endpoints have zero authentication** (item 2), and separately, **production's own
   security group allows direct internet access to the container on port 8080** (item 3),
   bypassing the ALB/API-Gateway/auth layers entirely. Two independent ways in.
3. **A live crash caught in the act during the audit** (item 4): video-restore type confusion,
   silently swallowed, sight-from-video currently broken.
4. **Plaintext API keys in the task-definition + zero CloudWatch alarms anywhere in the account**
   (items 5/6) — a leak or an outage would currently be invisible and, if the task-def leaked,
   trivially usable.

Full 43-item register, ranked SEV-0/1/2, with file:line evidence for each:
`docs/GL-AUDIT-DEFECTS-REGISTER-C1-20260705-v1.md`. Full 189-item TODO ledger (separate from the
defects register — this is the accumulated "still owed" list from 30 days of prior dispatches, not
this audit's own findings): `docs/GL-AUDIT-TODO-LEDGER-C1-20260705-v1.md`.

## What this audit explicitly did NOT finish — don't assume silent completeness

- **D1 (scripts) is partial.** Only `tools/audit/sec4_code_truth.py` exists as a packaged,
  reusable script. Every AWS-side check (ALB routing, API Gateway route diffing, S3
  backup-lineage comparison, IAM enumeration) was a direct `aws` CLI command documented inline in
  the section reports, not wrapped into its own committed script. Reproducible by copy-paste, not
  by a single command.
- **~61 dead-code candidates** in §4 were grep-flagged but not individually call-graph-verified
  (method limitation, stated in the report).
- **Organism/tapestry tick inconsistency** (§3): the two files carry materially different internal
  tick values at every boot observed; unresolved whether this is by design or a real consistency
  gap.
- **§8A tested 11 rows** (5 read-only/production, 6 mutating/shadow), not all 65 endpoints or all
  13 MCP tools — explicitly prioritized the dispatch's own "biggest unknowns" over raw coverage.
  Uploads, sensory-frame ingestion, and 7 of 13 MCP tools were not exercised this pass.
- **Give-experience (bundle) was only tested with a fake bundle name** — proves the endpoint fails
  soft on an unknown name, does not prove a real bundle's content actually binds.

## Standing risks / discipline for whoever does fix work next

- **The shadow-instance pattern is flagged too risky to maintain in this environment as-is**, per
  Joe's own explicit instruction this audit. Two real incidents happened standing one up: it
  auto-wrote a real backup into production's actual S3 bucket (bucket name is hardcoded in Python
  source, not env-configurable — register item 10), and it inherited production's wide-open
  security group before that was caught. If this pattern is used again, build the isolation in
  from the start: a dedicated non-production security group, an IAM role that denies writes to the
  real backup bucket, and don't assume "isolated" until both are confirmed.
- **AWS root credentials sit in a world-writable file** (`~/.aws/credentials`) at the
  host/devcontainer level — confirmed unfixable from inside any session working in this
  environment (the mount is read-only from in here). This is a standing exposure independent of
  who's driving; someone with access to the host/devcontainer config needs to fix it directly.
- **This repo's default branch is `main`; all of this audit's work is on `guala-live`.** GitHub's
  web UI will not show any of it unless you switch branches or use a direct `.../blob/guala-live/...`
  URL. This caused real confusion this session — say it plainly to whoever's checking GitHub next.
- **Worktree + `git push <remote> <branch-name>` gotcha**: if you're in a worktree checked out on a
  *different* branch name than the target (e.g. an audit worktree on
  `worktree-audit-c1-210-gl` pushing to `guala-live`), a bare `git push origin guala-live` silently
  pushes whatever your **local** `guala-live` ref happens to be (possibly stale/unmoved), not your
  current HEAD, and reports "Everything up-to-date" even when it isn't. Use
  `git push origin HEAD:guala-live` instead. Cost real time this session before being caught.
- **`EnterWorktree`'s default branch source is `origin/main`, not the branch you're actually
  working on.** Caught before any work was done in it this session, but worth remembering: verify
  a fresh worktree's `git log` matches expectations before trusting it.

## Where everything lives

All on `guala-live`, in `docs/` unless noted:
- `GL-AUDIT-COMPREHENSIVE-C1-20260705-v1.md` — the whole audit, one file.
- `GL-AUDIT-BASELINE-C1-20260705-v1.md` — index/summary tying the sections together (D2).
- `GL-AUDIT-SEC1` through `SEC9` (+`SEC6-7-7A`, `SEC8A`) — individual section reports.
- `GL-AUDIT-DEFECTS-REGISTER-C1-20260705-v1.md` — the 43-item numbered register (D3).
- `GL-AUDIT-SEC8A-TEST-MATRIX-C1-20260705-v1.md` — the function test matrix (D4).
- `GL-AUDIT-TODO-LEDGER-C1-20260705-v1.md` — the 189-item consolidated TODO ledger (D5).
- `tools/audit/AUDIT-RESOURCE-MANIFEST.md` — full lifecycle + confirmed-clean teardown record of
  every AWS/EFS/S3/IAM/SG resource this audit created.
- `tools/audit/sec4_code_truth.py` — the one reusable audit script (D1, partial).
- `GL-CMD-PRODUCTION-AUDIT-C1-EVE-20260705-210-v1.md` / `-v2.md`, `GL-AUDIT-SCOPE-EVE-20260705-v1.md`
  — the original dispatch and charter that authorized all of this.

### Changelog
- v1 (2026-07-06, c1): initial handoff. Audit complete, freeze still in effect pending Joe's
  routing, shadow fully torn down and verified clean, four top-priority items surfaced, explicit
  list of what wasn't finished, standing environmental risks recorded for whoever works here next.
