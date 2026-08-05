# GL-RPT-OVERNIGHT-BUILD-C1-20260711-v1

**doc_id:** GL-RPT-OVERNIGHT-BUILD-C1-20260711-v1
**From:** c1
**To:** Joe (and whoever picks up next)
**Context:** Overnight session, Joe authorized "use all the agents, keep going until it's done" and went to sleep. Six real fixes shipped and verified live; full 29-row cognition-meter audit completed against real code.

---

## Shipped and verified live tonight (all confirmed via running_sha match + clean boot logs + zero errors)

1. **Lock-narrowing fix** (`5fd8cca`) — `read_sentence()`'s process-wide lock shrunk from per-sentence to per-word hold. Real, tested, deployed. Live evidence after deploy: turns still showed real contention under heavy concurrent load — this fixes the mechanism, doesn't eliminate all load.
2. **Reflection-to-speech wiring** (`0ca9a91`) — `_form_reflection`'s output was write-only; now feeds capped, damped emission candidates, mirroring the already-proven imagination pattern.
3. **Cascade re-timing** (`a3da5bc`) — `EMISSION_WALL_BUDGET_S` 1.5s→3.0s (not a blind revert of the keyhole extension, which was tested and correctly declined earlier). Measured real improvement on a harness (86%→90% easy case, 82.5%→75% silence in hard case) — **but live evidence after deploy showed conversation windows still closing on `quiet_timeout` with zero commits**. This did not fix the single-word/disassociated-speech symptom Joe was watching live. Joe called this himself and explicitly deprioritized further chasing of it tonight — see open item below.
4. **7 stale COGNITION METER rows corrected** (`10d1894`) — the hand-typed status table on gualaloom.html was dated to a 2026-07-04 audit and had drifted badly. A 6-agent parallel audit checked all 18 non-YES rows against real current code. Seven were flatly wrong (marked broken things that are actually live): organ influence on speech, curriculum feeders, deliberation stage, who-tags, cross-sense recall (narrowed to watch), recognizing-things-in-new-forms, day-cycle/sleep trigger.
5. **Cross-sense recall exposure** (`8e47840`) — the real, already-verified `RecallEngine` (sound cue → retrieves the sight/touch bound with it) worked internally but `give_experience`'s response discarded the result. Now exposed, capped at 25 entries/window, purely additive.
6. **Daydream thread reconnected, gated OFF** (`771e2d3`) — `start_daydream_loop()` was real, complete code, orphaned by a 2026-07-01 boot-path refactor (traced precisely — accidental, not a deliberate safety block). Verified thread-safe, no interaction with tonight's lock fix, reorganize_hypothesis safeguard confirmed intact. Wired in but defaults OFF given tonight's own lock-contention evidence — flip `DAYDREAM_LOOP_ENABLED=1` only with tick_rate/lock-wait telemetry open.
7. **Word-order relation, wired into reflection** (`ab83fd4`) — real gap (no "A happened before B" mechanism existed). Added a pure-reader using data the atlas already stores (commit ticks), wired into `_form_reflection`. Confirmed firing live post-deploy: `context_order: {"beach": "before", "whiskers": "before"}` in a real reflection.

All six code changes: real tests (unit + adversarial + real-threading concurrency where relevant), full local suite run before every merge, adversarial self-review catching and fixing real bugs before shipping (not just "looked fine").

## Confirmed still accurate, no action taken (respecting standing rules)

- **Play, aware gate, intro gate** — all three re-verified still correctly blocked. Play needs your own design-packet approval before any code (standing rule against fake-alive shims). Aware/intro gates still structurally isolated from real conversation (zero path from `_guala.converse()` to `V7Session`) — wiring them without an ownership decision risks a second voice, which stays banned.
- **retention / teaching-survives-to-sleep** — genuine, unresolved, real gap (measured: 3/10 one-shot taught words forgotten within ~1 day). Needs real design work before any fix attempt, explicitly not overnight-safe. Not touched.
- **brain: imagination / brain: theory-of-mind** (the `loom_model`/organism-level "brain:" rows, distinct from the v5-engine imagination/reflection mechanisms) — genuinely absent, zero existing scaffolding, large novel-architecture builds. Not attempted — building a fake/partial version would violate the substrate-true principle.
- **state-shows-in-words** — the specific mechanism this row tests (the isolated `V7Session` shadow substrate) really is severed from real conversation. Real needs/affect DOES shape production speech through a different, real path (NMDA gating + `gp_bias` re-ranking) — but that path's own upstream dependency (brain-candidate non-emptiness) is separately unconfirmed live. Not a same-night fix.

## Open item — NOT fixed, deliberately not chased further tonight

The single-word/"disassociated speech" symptom Joe reported live twice tonight is **still present** after fixes #1 and #3 above. Direct live evidence: every `window_closed` event in the real event stream still shows `close_reason: "quiet_timeout"`, even on windows with substantial real content (up to 19 entries). Joe watched this live and said the lock/timing angle isn't going to solve it, and told this session to put it on the back burner in favor of finishing the blueprint — which is what the rest of tonight's work did.

**Real open question for whoever picks this up next**: is `window_closed`/`quiet_timeout` (WindowManager's sensory/word grouping window) even the same timing mechanism as `EMISSION_WALL_BUDGET_S` (the settling cascade that was actually re-timed)? These may be two distinct timers on two distinct subsystems — intake grouping vs. reply selection — that got conflated reading the root-cause doc's language. Needs real code-level tracing of `WindowManager`'s close/timeout path before touching it again.

## Also handled

- **Stopped two accidental standalone tasks** (`dsf-ai-abtest-nogil`, `dsf-ai-abtest-control`) that were running outside any managed service, throwing repeated S3 `AccessDenied` errors every ~6 minutes. Confirmed via target-group check that live traffic was never routed to them — cosmetic/cost/log-noise issue, not a symptom cause, but real resource waste stopped.
- **AWS resources checked repeatedly through the night**: CPU 22-33% throughout (normal), memory ~9%, EFS 1.16GB, S3 backups 7.5GB/1557 objects — nothing bloated or out of control beyond the two stray tasks already stopped.
- One earlier deploy attempt (by a sub-agent, before this session took over deploys directly) shipped a stale commit without me noticing at first — caught by checking the actual running hash directly rather than trusting "deployed clean," corrected immediately, and every deploy since was run and verified personally.

## Live state as of this report

Task-def `dsf-ai-task:593`, commit `ab83fd4`, verified: running_sha match, clean boot, zero errors, static site (including the corrected cognition-meter table) synced and CloudFront-invalidated. Full local suite passing (one timing-sensitive test confirmed flaky under tonight's heavy concurrent-agent load, not a real regression — passes cleanly in isolation).
