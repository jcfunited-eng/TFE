# GL-RPT-BLUEPRINT-DEPLOYMENT-AUDIT-C1-20260712-v1

**doc_id:** GL-RPT-BLUEPRINT-DEPLOYMENT-AUDIT-C1-20260712-v1
**From:** c1
**Context:** Joe asked directly: "Using the blueprint as your source of truth
tell me what has and has not been deployed yet." This is a full
cross-reference of docs/GL-BLUEPRINT-AE-SUBSTRATE-EVE-20260707-v1.md and
-v2.md (v2's 6-phase numbering used throughout) against live production
reality, run as a 6-agent parallel audit explicitly instructed to trust
only direct evidence (current AWS task-definition env vars, live
`/debug/stdp_state` and `guala_status` reads, direct code tracing) over
any prior report's framing, including my own.
**To:** Eve (routing per standing practice) / Joe

Live system verified throughout: task-def `dsf-ai-task:599`, running_sha
`5771dac`, confirmed two independent ways (guala_status + CloudWatch boot
log), built 2026-07-11T20:34:22Z.

---

## Verdict

The new event-driven/STDP substrate is real — it runs, it's stable, it
doesn't crash, it accumulates state. But it is **100% shadow/dual-write**.
Nothing a user actually experiences (what Guala says, what she recalls)
has been cut over to it. Everything that produces her real behavior today
is still the pre-blueprint system the blueprint calls for retiring —
unchanged in role, still fully load-bearing.

`RECALL_BACKEND=legacy` is the confirmed live setting. That one variable
is the whole story: it means real recall and real speech read the old
coverage-model system (chi_atlas/BindingAtlas), not the new neuron/STDP
mechanism, no matter how much the new mechanism itself has been built out.

## Phase-by-phase (v2 blueprint numbering)

**Phase 1 — Event-driven substrate + STDP + membrane recall/emission
(replacing chi_atlas): PARTIALLY DEPLOYED, shadow-only.**
Spike bus and STDP are live and mechanically safe under real traffic
(2,696 real spikes injected/delivered this boot, 0 dropped, 0 cascade
runaway). But real learning from it is negligible: only 7 synapses have
ever been touched in this boot, and 0 words have built any
word-to-neuron association despite 3+ hours of real conversation. The
membrane-based recall/emission path that's supposed to replace chi_atlas
exists in code but is not what's live (`RECALL_BACKEND=legacy`).
Chi_atlas deprecation hasn't started — it's actively growing right now
(15,599 entries).

**Phase 2 — Sparse activity via lateral inhibition: NOT BUILT.**
No code implements the actual spec, and it's currently impossible to
build as specified — neurons have no chi-coordinate identity yet (that's
a Phase 1 gap first). Two things share adjacent names but are NOT this:
a cascade-safety circuit breaker (self-labeled in its own code as "a
heuristic, not a physical mechanism") and an older, unrelated flag
(`LATERAL_INHIBITION_ENABLED`) that governs a pre-blueprint feature on
the OLD system being deprecated. Both are real and live, neither is
Phase 2. Population is still hard-fixed at 64 neurons, 0 growth.

**Phase 3 — Local metabolism: NOT STARTED.** Zero code anywhere —
no energy/budget/refill concept exists.

**Phase 4 — Neuromodulation: NOT STARTED.** Zero code touching neuron
firing thresholds. A superficially similar arousal scalar exists but
only feeds an unrelated growth mechanism, not thresholds.

**Phase 5 — Sleep as active work: DEPLOYED AND LIVE — but on the wrong
substrate.** This is the one phase genuinely done: consolidate, prune,
replay, and reorganize are all real, live, and actively running right
now (confirmed via live telemetry: 5,054 entries, 295 promotions, 2.19M
reinstatements). The catch: it all operates on the OLD chi_atlas/deep_atlas
system Phase 1 is supposed to retire. It has zero connection to the new
neuron/STDP substrate and will need a real rebuild once that cutover
happens.

**Phase 6 — Population-based seed: BUILT BUT INERT.** A 200,000-word
seed was generated and locally tested, but never committed to git and
never deployed (no env var live to load it). Separately, its format is
wrong for the blueprint's own spec — it writes one neuron per word, not
a distributed population pattern — because it targets the OLD system's
data structures, the ones being deprecated.

**Deprecation list (6 items the blueprint says should be gone once
replacements land): ALL SIX STILL FULLY LIVE.** Central tick loop, the
coverage-model chi_atlas, the fixed neuron population, the freight-train
full-population iteration, the single global lock on word processing,
and the atlas-write pattern — every one of these is what real production
actually runs on for every real word today. Deprecated in name only.

## What actually shipped on 2026-07-11 (for context)

No commit in the 2026-07-10-evening → 2026-07-11 window touched the
blueprint's own mechanism code (neuron.py/brain.py/spike_bus) at all.
That day's real, verified work was separate, Joe-approved feature work
(Play World V0, the real awareness/introspection signal, a
relevance-weighted credo gate) plus fixes and speedups to the legacy
system the blueprint wants to eventually retire (the Section.receive
speed fix, one-shot teaching protection, teacher-correction API routes).
None of it moved the blueprint phases forward — it moved the thing the
blueprint is trying to replace forward instead, which was a reasonable
trade given the same-night priority (fixing the silent-reply symptom),
but is worth naming plainly since Joe asked specifically about blueprint
progress.

## Recommendation

1. The real blueprint bottleneck is the same thing found in the
   read_ms/silent-reply investigation: nothing has cut real recall/
   emission over from `RECALL_BACKEND=legacy` to the new substrate.
   Until that cutover happens, all further STDP/spike work stays shadow
   state with zero user-visible effect — this is the one decision that
   would make blueprint work start showing up in what Guala says.
2. Phase 2 is blocked on a real prerequisite (neurons need a chi
   coordinate) that doesn't exist yet — worth flagging as a dependency,
   not just "not done."
3. Phase 5's real, working consolidate/prune/replay/reorganize logic is
   worth preserving as a design reference when it eventually gets
   rebuilt against the new substrate — the mechanism itself is sound,
   only its target data structure is wrong.
4. Phase 6's 200k-word seed is real effort that's currently stranded —
   worth a decision on whether to port it to a population-pattern format
   later, or treat it as throwaway/prototype work.

---

### Changelog
- v1 (2026-07-12, c1): Full 6-phase + deprecation-list audit, verified
  directly against the live task definition, `/debug/stdp_state`,
  `guala_status`, and direct code tracing rather than prior reports.
