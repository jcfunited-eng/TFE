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

**Phase 6 — Population-based seed: BUILT BUT INERT.** *(Corrected
2026-07-12 — see Correction section below.)* A 200,000-word seed was
generated and locally tested, but never committed to git and never
deployed (no env var live to load it). It correctly targets the NEW
system's real structures (Embryo/LoomHemisphere/LoomNeuron/per-neuron
chi_atlas), not the old engine's LivingAtlas — my original claim that it
targeted the old, deprecated system was wrong; see correction below.
Separately, and still accurate: its format doesn't match the blueprint's
own spec regardless of which system it targets — it writes one neuron
per word, not a distributed population pattern.

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

## Correction (2026-07-12, addendum)

A concurrent session pushed back on this report's Phase 6 finding,
specifically the claim that the seed generator "seeds the OLD
architecture's data structures." Their write-up was detailed and
file/line-cited, so rather than accept or reject it on read, I
independently re-verified their four specific claims from scratch
(fresh agents, fresh code reads, one live local reproduction of their
test) without trusting either write-up. Results:

1. **They were right, I was wrong, on the main point.** Confirmed by
   direct code read: `seed_loader.py` writes into the NEW loom_model
   system's real objects (`Embryo.hemi_by_op`, `LoomHemisphere.cluster.
   neurons`, a per-`LoomNeuron` `chi_atlas`, `LoomNeuron.couplings`) —
   never into the old engine's `LivingAtlas` (`self.atlas`). Those are
   two genuinely different structures that happen to share a confusing
   name (`chi_atlas`); I conflated them in the original write-up. Their
   claim that the seed's format is "schema-correct for the new system"
   is confirmed.
2. **They named the wrong commit for the "why it still doesn't matter"
   part.** They cited commit `dc7f9ec` as the one that demoted the
   per-neuron `chi_atlas` to observability-only, landing ~5 hours after
   the seed generator's own commit. `dc7f9ec` is a docs-only commit that
   never touches that file. The real demotion commit is `f70ceb4`,
   landing ~1h25m after the seed commit, not ~5h. The demotion itself is
   real and the comment text they quoted is accurate — they just
   attributed it to the wrong commit.
3. **Their "dead end" architecture argument doesn't fully hold up either
   — in a way that actually understates their own point.** They argued
   the per-neuron `chi_atlas` is only ever read via the sensory-queue
   path, which explicitly skips word/language hemispheres, so the seed's
   data (100% tagged to word hemispheres, confirmed by directly sampling
   all 200,000 generated entries) could never be read even if loaded.
   Direct tracing shows this is incomplete: the same `chi_atlas` read
   (`cluster.step()`'s neuron-selection logic) is *also* called directly
   from the real word-processing path (every real word, via
   `embryo.py`'s `_feed_and_fold`), not only from the sensory queue. So
   if the seed were ever turned on, its data would in fact get read by
   real word processing — it isn't the double dead-end they described.
   That said, this doesn't change the bottom-line verdict: that read
   only feeds the new substrate's internal neuron/STDP dynamics, which
   — per this same report's Phase 1 finding, not disputed by anyone —
   is still 100% shadow state relative to what Guala actually says
   (`RECALL_BACKEND=legacy`). So the seed would stop being fully inert
   and start actually accumulating into the shadow substrate, but would
   still have zero effect on production speech until that cutover
   happens.
4. **Their live reproduction claim (loading the real 50,000-word file
   into a fresh `Embryo`, zero errors) was independently re-run from
   scratch and matched exactly** — same word counts, same zero errors,
   same integrity-check results.

Net effect on the Phase 6 verdict above: still `BUILT BUT INERT` (both
sessions agree on that), but the reason it's stranded is narrower than
originally reported — it's purely an unset env var plus an undeployed
file, not a wrong-target-system problem. The "wrong format for the
blueprint's population-pattern spec" finding is untouched by any of this
and still stands.

---

### Changelog
- v1 (2026-07-12, c1): Full 6-phase + deprecation-list audit, verified
  directly against the live task definition, `/debug/stdp_state`,
  `guala_status`, and direct code tracing rather than prior reports.
- v1 addendum (2026-07-12, c1): Corrected the Phase 6 finding after a
  concurrent session's pushback was independently re-verified claim by
  claim (4 fresh agents, one live local reproduction). Their core point
  was right; two of their supporting details (a commit citation, a
  read-path-exclusivity claim) were themselves off and are corrected
  above.
