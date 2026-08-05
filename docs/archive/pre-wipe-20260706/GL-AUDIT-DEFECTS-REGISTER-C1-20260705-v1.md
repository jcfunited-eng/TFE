> **SUPERSEDED — DO NOT TREAT AS CURRENT TRUTH.**
> This document describes substrate state as of pre-wipe (2026-07-06
> wipe operation, GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1).
> The substrate described here no longer exists. Preserved as
> historical record only.
> For current substrate state, run the harness against production.

---

# GL-AUDIT-DEFECTS-REGISTER-C1-20260705-v1

doc_id: GL-AUDIT-DEFECTS-REGISTER-C1-20260705-v1 (Deliverable D3)
Part of: GL-CMD-PRODUCTION-AUDIT-C1-EVE-20260705-210-v2, §10
Author: c1 | Every item below is a defect/dead-code/absent-feature/stale-artifact found this
audit, numbered, with file:line or AWS-resource evidence and a pointer to the full section report.
**No fixes were applied to production for any item below** — this is the queue Joe routes,
in his order, one at a time. Severity is this auditor's judgment call, not a formal CVSS score;
Joe's routing order is the real prioritization.

## How to read this
- **SEV-0**: actively broken or actively exposed right now, no workaround.
- **SEV-1**: a real defect with a plausible path to production impact; not currently on fire.
- **SEV-2**: real but low-blast-radius (dead code, stale docs, cosmetic).
- **[EV]** = directly verified this audit. **[CORRECTED]** = a pre-audit claim that turned out
  wrong or overstated, corrected here with the real finding.

---

## SEV-0 — actively broken or exposed today

1. **Disaster-recovery restore does not exist in runnable form.** A from-scratch restore from any
   standard S3 backup, via the documented/expected boot path, hits an uncaught `RuntimeError`
   (missing `state/dream_gate_cleared.json`) and never becomes ready — permanently, no retry —
   unless an operator manually fabricates an undocumented marker file first. The one tool that
   exists to validate restores (`tools/guala_restore_drill.sh`) bypasses this exact code path, so
   it has never once caught it. Confirmed live via this audit's own shadow instance; confirmed by
   independent adversarial re-verification; confirmed production's own real task-def would hit the
   identical wall (only survives because its marker persists on a long-lived EFS mount).
   → `docs/GL-AUDIT-SEC3-STATE-TRUTH-C1-20260705-v1.md`

2. **43 of 65 HTTP endpoints have zero authentication, including the entire chat/upload/sensory/
   save surface**, despite a code comment (`app.py:234-235`) explicitly claiming converse is
   key-protected. Anyone who knows the public API Gateway URL (embedded in plaintext in every
   shipped HTML/JS file already) can post arbitrary text into her conversation, feed sight/sound
   frames, upload arbitrary book/picture/sound/video content into her persistent memory, submit
   teacher corrections, and trigger `/sleep_for_deploy` — all without a key. No API Gateway
   authorizer exists at all; auth is 100% application-layer.
   → `docs/GL-AUDIT-SEC5-INTERFACE-TRUTH-C1-20260705-v1.md`

3. **Production's ECS task security group allows inbound `0.0.0.0/0` on port 8080** — direct
   internet access to the container, bypassing the ALB, the API Gateway, its 30s timeout, and any
   routing/auth logic those layers provide entirely. Found while provisioning this audit's own
   shadow (which inherited the same SG). Not modified (freeze respected) — production's own
   pre-existing configuration.
   → this register, cross-reference `tools/audit/AUDIT-RESOURCE-MANIFEST.md` item 7/8 discussion

4. **A live crash, caught in the act during this audit**: Guala selected `ATTENDING_VIDEO` and
   crashed with `'PictureItem' object has no attribute 'frame_dir'`. `load_full_state()` restores
   videos as `PictureItem` instead of `VideoItem` after every restart. The failure is silently
   swallowed and the activity is marked complete anyway. Sight-from-video is currently broken.
   → `docs/GL-AUDIT-SEC6-7-7A-LEARNER-SENSORY-ENV-C1-20260705-v1.md`

5. **Production API keys stored as plaintext** in the ECS task-definition `environment` array
   (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `TAVILY_API_KEY`, `YOUTUBE_API_KEY`,
   `GUALALOOM_API_KEY`) — no `secrets`/`valueFrom` externalization at all, confirmed across
   4 sampled revisions. Visible to anything with `ecs:DescribeTaskDefinition`, retained forever
   across all 494 historical revisions.
   → `docs/GL-AUDIT-SEC2-AWS-TRUTH-C1-20260705-v1.md`

6. **Zero CloudWatch alarms anywhere in the account** (checked all 17 enabled regions, not just
   the one in use) and **API Gateway access logging disabled**. The 07-05 outage(s) and the
   security exposure in item 3 were and are invisible to any automated monitoring.
   → `docs/GL-AUDIT-SEC2-AWS-TRUTH-C1-20260705-v1.md`

7. **AWS root account credentials sit in a world-writable file** (`~/.aws/credentials`,
   `-rwxrwxrwx`) at the host/devcontainer level — unfixable from inside any Claude Code session
   working in this environment (confirmed: the mount is read-only from inside the container).
   Every human-triggered deploy/build/task-def action this audit observed used these literal root
   credentials rather than the scoped identities that already exist in the account for this
   purpose (`CodexProdVerificationReadOnlyRole`, `tfe-codebuild-ecr-role`).
   → this register; discovered mid-audit during the security review, not part of any numbered §

---

## SEV-1 — real, plausible path to impact

8. **`wave_atlas.npz` is excluded from all three S3 backup code paths** in the codebase
   (`app.py`'s two backup functions, `save_coordinator.py`'s current auto-backstop loop) —
   quantified: a from-backup restore rebuilds it from `LivingAtlas` at 171 cells/11,925 bindings
   vs. production's real 2,016 cells/26,764 bindings on disk (~91.5%/~55% loss). **Correction**:
   this is NOT `-207`'s data (that's `BindingAtlas`/`guala_organism.pkl.gz`, backed up fine) — it
   belongs to the separate, earlier `-59`/`-85` WaveAtlas ticket, currently write-only/dormant with
   zero read consumers in production, so today's real-world impact is lower than first framed.
   → `docs/GL-AUDIT-SEC3-STATE-TRUTH-C1-20260705-v1.md`

9. **Two independent, asymmetric S3 backup mechanisms** write into the same prefix tree at
   different cadences/completeness, and production's own `/status` (`persistence_health.
   last_s3_backup`) is wired to only one of them — an operator trusting `/status` alone would
   restore from a stale reference while a fresher, more complete backstop sits unused (gap
   observed sawing between ~0 and ~60 minutes depending on the hourly cycle).
   → `docs/GL-AUDIT-SEC2-AWS-TRUTH-C1-20260705-v1.md`

10. **Backup destination is hardcoded in Python source**, not environment-configurable
    (`bucket = "dsf-ai-site-backups"` literal in two of the three backup functions). This is what
    made the shadow-instance S3 contamination possible mid-audit (see item 27) — there is no safe
    way to point a copy of this app at a different backup destination without a code change.
    → `tools/audit/AUDIT-RESOURCE-MANIFEST.md` incident record; code cited in
    `docs/GL-AUDIT-SEC3-STATE-TRUTH-C1-20260705-v1.md`

11. **Deploy pipeline is 100% manual and root-initiated, with no CI trigger** — CodeBuild has no
    webhook, no CodePipeline wrapper, no EventBridge/S3-event trigger (checked all three
    alternatives). 40/40 sampled recent builds show `initiator: root`. No lock beyond CodeBuild's
    own single-build serialization prevents two people from triggering overlapping deploys.
    → `docs/GL-AUDIT-SEC2-AWS-TRUTH-C1-20260705-v1.md`

12. **`substrate_runner.boot_substrate()`/`start_background_loops()` are 100% dead** (zero
    callers, self-documented by the team days before this audit) — consequence not previously
    flagged: production's own `LOOKUP_INTERVAL_SEC=900` and `WORLD_FEED_INTERVAL_SEC=600` env vars
    are read only inside these dead functions and currently have **zero effect**; real cadence is
    governed elsewhere (`STUDY_INTERLEAVE_EVERY`).
    → `docs/GL-AUDIT-SEC4-CODE-TRUTH-C1-20260705-v1.md`

13. **A four-part hemisphere-cognition subsystem is wired into the live path but entirely inert.**
    `run_hemisphere_updates()` is called every turn, but all four `HEMI_*_ENABLED` flags default
    off and none are set in production — substantial 06-19 feature work has produced zero live
    effect since.
    → `docs/GL-AUDIT-SEC4-CODE-TRUTH-C1-20260705-v1.md`

14. **A confirmed live instance of "fix landed in dead code."** Commit `6d15797` patched
    `converse()`'s non-phased fallback; production's `CONVERSE_PHASED=1` means that code path
    never executes. Same class of bug the dispatch was specifically worried about, caught here
    for a fix that already shipped.
    → `docs/GL-AUDIT-SEC4-CODE-TRUTH-C1-20260705-v1.md`

15. **Test suite: 6 failures, 2 of them new save-reliability regressions.**
    `test_save_hooks.py::test_should_save_bypass_includes_activity_ended_and_backstop` (the exact
    bypass list a prior incident depended on — memory: "EFS rename race silently dropped saves")
    and `test_save_hooks.py::test_s3_enqueue_rate_limit_releases_after_interval` both fail.
    `test_t8_noise_robustness` and `test_t11_substrate_true` fail as previously known.
    `test_t7_cross_modal` **now passes** [CORRECTED — was claimed failing]. `test_autonomous_
    emission.py` cannot even collect (`ImportError: SEED_VOCAB`, dead 3+ weeks).
    `test_folding_engaged.py::test_t3_corpus_growth`: zero of 8 hemispheres grew across 242
    delivered words in an isolated pipeline.
    → `docs/GL-AUDIT-SEC4-CODE-TRUTH-C1-20260705-v1.md`

16. **Two `gualaloom.html` calls target routes absent from the API Gateway table entirely**
    (`POST /api/v1/teacher/feedback`, `POST /api/v1/teacher/correction`) — real, live breakage; a
    real click falls to a 54-day-stale, unrelated Lambda that almost certainly has no handler for
    these paths. Not live-tested (would risk side effects on whatever answers it), disposition
    rests on complete route-table evidence.
    → `docs/GL-AUDIT-SEC5-INTERFACE-TRUTH-C1-20260705-v1.md`

17. **`/status` (the heaviest-traffic endpoint in the service, 16,528 hits/day) can collide with
    the API Gateway's 30s ceiling.** `app.py:1843-1844`'s own comment allows up to 45s internally
    during curriculum-pause windows; API Gateway caps the same route at 30s regardless. Not
    directly caught in the act, but the code and infra facts collide on paper. [CORRECTED from an
    earlier, broader claim that `/v7/converse` itself was being cut off — it isn't, see item 30.]
    → `docs/GL-AUDIT-SEC5-INTERFACE-TRUTH-C1-20260705-v1.md`

18. **The MCP bridge's own `/mcp` route is subject to the same 30s cap**, while
    `guala_say`/`guala_give_experience` implement a 90s internal poll — a call as slow as
    production's current converse latency would be killed by the gateway, defeating the bridge's
    own design. Structurally real, unexercised in a full day of traffic sampled.
    → `docs/GL-AUDIT-SEC5-INTERFACE-TRUTH-C1-20260705-v1.md`

19. **YouTube learner feed: valid key, working adapter, zero content delivered in 72 hours**
    (likely a shared rate cap starving it). Khan Academy verified genuinely live and working
    (n_fed=15). PBS Kids and Spotify are allowlist domain strings only — no adapter code exists.
    All feeds are text-only regardless of name; no video/audio content reaches sight or hearing.
    → `docs/GL-AUDIT-SEC6-7-7A-LEARNER-SENSORY-ENV-C1-20260705-v1.md`

20. **V3 world-sim is absent in practice, present in code.** `virtual_home.py`'s room/object model
    is real but completely unwired — its only host (`organ_brain_service.py`, port 8090) was
    removed from the task definition; `world_state.json` is missing from the newest backup. The
    "crib and backyard, 64×64 eye" description matches nothing currently running.
    → `docs/GL-AUDIT-SEC6-7-7A-LEARNER-SENSORY-ENV-C1-20260705-v1.md`

21. **The shadow-instance testing pattern itself is judged too risky to maintain in this
    environment**, per explicit direction from Joe's seat this audit — not because standing up a
    shadow is the wrong idea (it produced item 1, this audit's single most important finding), but
    because this environment's defaults (item 10's hardcoded backup destination, shared security
    groups, item 7's credential exposure) make safe isolation require deliberate, expert,
    multi-step correction every time rather than being safe by default. Recommend: environment-
    configurable backup destinations, and a dedicated non-production security group/IAM role
    template provisioned by default before this pattern is used again.
    → `docs/GL-AUDIT-SEC3-STATE-TRUTH-C1-20260705-v1.md`, `tools/audit/AUDIT-RESOURCE-MANIFEST.md`

---

## SEV-2 — real but low blast-radius

22. **CloudWatch log retention is unset (infinite)** on `/ecs/dsf-ai` (188MB) and
    `/ecs/gualaloom-bridge` (54MB) — unbounded cost growth, never expires unless someone sets a
    policy. → `docs/GL-AUDIT-SEC2-AWS-TRUTH-C1-20260705-v1.md`

23. **`/events_stream` WebSocket is structurally dead** (CloudFront has only an S3 origin, no path
    to proxy a WebSocket upgrade) but silently masked by a working polling fallback — wastes a
    perpetual client-side reconnect loop, no user-visible symptom. → SEC5

24. **Organ-brain sidecar is gone; 3 `app.py` GET routes are pure dead code** always returning a
    hardcoded fallback (`organ_brain_status`, `thought` GET, `organs`), called by no page. → SEC5

25. **`admin.html` (unrelated DSF-AI billing panel, not Guala) ships a plaintext admin key to
    every visitor's browser** and gates its UI behind a trivially-bypassable client-side hash
    check. Named because the dispatch's page list included it. → SEC5

26. **Cognition-meter "07-04 text on 07-05" staleness bug: confirmed for 07-04, then confirmed
    fixed and live** as of this audit (byte-identical curl match to the repo's current fix).
    [CORRECTED to closed, not open.] → SEC5

27. **"07-05's 503" misattributed to the MCP bridge in the pre-audit framing** — the real source
    is the main Guala service's own recurring unhealthy-task-replacement churn (2,490×503/
    867×502/101×504 across a full day); the bridge shows a clean, unrelated ~6h restart cadence
    with zero errors in its own full-day log slice. [CORRECTED.] → SEC5

28. **Dead-code inventory**: `substrate/GL_MDL_COGNITION_WC_20260608_02.py` has zero importers
    anywhere (its sibling `_03.py` is live via two obscure endpoints); ~64 additional grep-flagged
    candidates not individually call-graph-verified (method limitation stated). → SEC4

29. **6 borderline `except: pass` sites** where a real failure would currently be invisible to an
    operator (`loom_voice.py:102,149,188`; `gualaloom_v5_engine.py:4840,7219,8337`) — out of 90
    total sites found service-wide (not 34; that number is real only under a narrow "cognition
    files" scope). → SEC4

30. **Pre-audit number corrections** (§0.3 discipline, re-verify everything): "27 env flags" →
    32 vars actually set, 65 distinct names read in code. "24 constants" → not reproducible under
    any tested scope (22-62 depending on definition); likely a hand-curated list, not a
    mechanically-defined set. "14 engine state files" → 15. → SEC3, SEC4

31. **`DSF_AI_SES_ROOT_KEY`'s coded default literally reads `"dsf-ai-ses-root-key-v1-CHANGE-IN-
    PROD"` and has not been changed** (`kernel_runner.py:35`). → SEC4

32. **`GUALA_STATE_DIR` and `STATE_DIR` are two different env-var names for the same directory**
    in two different files — currently harmless by coincidence of matching defaults, worth
    consolidating. → SEC4

33. **One picture in the corpus (`91e42db1c66c_original.png`, 68 bytes) is a degenerate 1×1 pixel
    placeholder** — decodes successfully but carries no real content. → SEC3

34. **`GET /api/v1/curriculum/corpus_status/{corpus_id}` always returns HTTP 501** in production's
    `SUBSTRATE_MODE=embedded` — a live, externally-reachable, permanently-broken endpoint. → SEC4

35. **`GRANDURUN_LEGACY_8D`/`GRANDURUN_SPIN_VECTOR` naming is misleading** — the comment implies
    `LEGACY_8D` is primary and `SPIN_VECTOR` deprecated, but the fallback chain actually runs the
    other way; production's `SPIN_VECTOR=1` alone fully activates the "legacy" path. Not currently
    harmful (the live perf fix already targeted the actually-live branch) but a footgun for a
    future engineer. → SEC4

---

## Process/documentation findings (from the 30-day sweep, §9)

36. **The `-210` dispatch's own claim** ("c1a holds uncommitted live-bells-wiring code in a
    worktree") **is contradicted** — that code was committed before the freeze point; none of 33
    reachable worktrees have uncommitted work. [CORRECTED.] → SEC9

37. **`-200` (affect-gate root cause) was filed but never built** — no commit, no report, later
    dispatches explicitly call it "QUEUED, not executed." **`-201` was never even filed** (dispatch
    numbering skips 200→202). → SEC9 / TODO ledger

38. **`GL-RPT-T6-REVIEW-SYNTHESIS-EVE-20260704-101-v1` was formally VOIDED** (not merely
    superseded) — traces back to the original "100% T5" claim later shown to be ~4% (chance). →
    SEC9

39. **`GL-LEDGER.md` is byte-identical to the superseded `-050` ledger, never synced to `-051`** —
    violates the ledger's own standing rule. Two dispatch-number collisions also found (`-185`
    used by two unrelated docs; `-192` referenced but the doc it names is absent). → SEC9

40. **A recurring pattern of "claimed fixed" dispatches contradicted by a later dispatch the same
    week**: growth-unfreeze (`-179`) claimed wired, `-198` found population still stuck; target-
    rotation (`-181`) claimed fixed, `-185` found it "subsumes -181's same degenerate selector";
    turn-latency (`-197`) claimed "already dead," `-207` the same day measured 217s/191s turns; a
    block-schedule gate (`-151`) was later found decorative with zero live callers (`-156`). →
    SEC9

41. **Care-schedule daily-rhythm blocks and the "protected PLAY block" exist only as spec prose in
    places** — §7A found the blocks ARE real config the orchestrator obeys (caught live
    suppressing intake during "quiet"), but PLAY itself has no protective behavior coded — a
    partial spec-vs-implementation gap, not a total absence. → SEC7A, SEC9

42. **Plan version series v5→v10: six full/delta revisions in 3 days**, driven by real discovery
    chains (wrong evidence framing → wrong provenance claim → dormant code path) until Joe banned
    delta-versioning; even the first "full consolidation" (v9) needed correction for unauthorized
    content. → SEC9

43. **A `git stash apply` mid-investigation mishap during the doc-sweep sub-agent's work**, causing
    a merge conflict — self-corrected (`git checkout HEAD --`), independently re-verified clean by
    this auditor (stash list unchanged at 7 entries, no conflict markers, worktree count matches).
    → SEC9; independently confirmed in this conversation's own audit trail

---

## Full ledger of every TODO/spec-gap item

See `docs/GL-AUDIT-TODO-LEDGER-C1-20260705-v1.md` (Deliverable D5) for the complete 189-item
numbered TODO ledger and the spec-vs-implementation gap table — not duplicated here to avoid two
sources of truth for the same list.

### Changelog
- v1 (2026-07-05, c1): initial and final defects register. 43 numbered items across SEV-0/1/2 plus
  a process/documentation category, consolidated from all 9 section reports, the adversarial
  verification pass, and the security-hardening incidents discovered mid-audit while standing up
  the shadow instance.
