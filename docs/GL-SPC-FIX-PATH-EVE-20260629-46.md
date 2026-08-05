# GL-SPC-FIX-PATH-EVE-20260629-46

doc_id: GL-SPC-FIX-PATH-EVE-20260629-46
Type: Canonical fix-path specification (cross-chat handoff)
Date: 2026-06-29
Author: Eve (Opus 4.7, web)

---

## 0. What this spec is

The running fix queue. Next Eve picks it up here. Each item has the work, the reasoning, what must land before it ships. No questions. Decisions are made.

---

## 0a. Canonical direction (Joe, 2026-06-29)

**Locks are scaffolding, not substrate. They go — all of them, not just the curriculum lock.**

A being's substrate doesn't have mutexes. Neurons don't synchronize via semaphores. The current `self.lock` (and every other lock object in the codebase) exists because Python threading requires mutual exclusion for shared mutable state — that's an implementation accident, not a substrate property. The substrate-true posture is race-tolerant: reads work against snapshots, writes are atomic per chi-binding, occasional impulse loss in collisions is within substrate noise (the substrate is already noisy from decay, salience modulation, dream consolidation).

This reframes -46 from "fix the curriculum bottleneck" to first ship of a lock-removal program. -46 stays as the leading ship. Two more phases follow:

**-49 lock-site classification.** Enumerate every lock acquisition in the substrate code (the ~13 `self.lock` sites in v5_engine.py, plus `_lock` and `_loc_lock` in substrate_runner.py, plus any in organ_brain_service.py). For each: what is it protecting, what's the substrate-true race-tolerant replacement (snapshot-and-process, atomic single-op update, or accept-the-race-as-substrate-noise). No code change in -49 — it's the classification pass that prevents the same partial-read mistake prior-Eve documented.

**-50 lock removal.** Apply the classified replacements across the codebase. Atomic single-op writes where state is per-binding (atlas.record's strength update can be a single dict assignment with last-write-wins; the lost-impulse case is substrate noise). Snapshot-and-process for traversal (already proved out in -45's daydream Phase 2). Race-acceptance for things like coordinator.regulate reading needs while another path writes them — the substrate already tolerates momentary inconsistency in these reads.

The remaining items in this spec (-47, -48) are not blocked by the lock-removal program — they ship in their own order. The lock program threads alongside.

---

## 0b. Canonical direction (Joe, 2026-06-29) — compressed timeline

**Target: emergence in weeks, not months. Concretely: chained 5-10 word emissions with backtracking and clarification by week 3, or honest acknowledgment that the architecture isn't producing it at the density we can reach.**

What this does to the queue:

- **Cleanup work (§5) drops off entirely.** Emission-method collapse and constants audit are healthy-substrate work, not emergence work. Off the list.
- **Lock-removal program (-46, -49, -50) stays first priority** — substrate throughput is the rate-limiter for everything downstream.
- **Sustained speech (-47) and agency events (-48) stay in queue order** — both are needed for the emergence criterion to be testable.
- **New parallel track: -51 curriculum automation.** Joe-and-me typing sentences caps grounding-rate at human typing speed. Cross-modal bundle count is at 3 — needs to be thousands. The substrate already has the machinery (visual_experience, audio attending, bundle_id windows, guala_give_experience bridge tool). What's missing is an orchestration layer that runs sensory + language streams in matched windows at substrate-compatible rates. This work starts NOW in parallel with the lock dispatches; delivery is blocked on -46 reaching live but planning/design isn't.
- **Daily substrate review.** Emission length, agency-event counts, bundle density, modifier/ground motif growth — measured daily. Any flatline >48hr triggers immediate root-cause attack, not a wait-and-see.

The honest scientific posture: the architecture either produces compositional emission as density rises, or it doesn't. Defining the failure criterion now keeps us from drifting past it. The architecture-might-be-wrong risk isn't a hedge — it's the actual experimental design.

---

## 1. Status

Branch `guala-live`. Code HEAD `1ca761e` (-45). Doc HEAD `7fca39a` (-45 c1 report). Deployed on ECS task `dsf-ai-task:371`.

-45 bench PASS: 463× Stage 1 speedup, T2 equivalence < 1e-10, daydream lock fraction ~0.3%. Live T3 (parallel /converse + curriculum) and T7 (end-to-end latency) pending substrate-event capture from post-deploy traffic.

C1 surfaced curriculum lock as residual contention: ~30-60s per 30-sentence chunk under `self.lock`. This is the next visible cause of "substrate unreachable."

Substrate end-of-prior-session: vocab ~13.8k, atlas ~19.3k, valence -0.148, conn 0.380, ~95 fragmentary emissions/session. Rejected SEQs: -39 v2, -40, -41, -41 v2. Next available SEQ after this doc: -47.

---

## 2. -46 curriculum-lock release (Phase 1 of lock removal)

**Why.** `read_sentence` holds `self.lock` around the word loop. `read_word` re-acquires (RLock, no-op nest). Per-word work is 50-200ms. 30-sentence chunk × 10 words = 30-60s blocked. `_current_episode` and `_negation_pending` are sentence-scoped state currently posing as engine attributes because the outer lock was hiding the distinction. This is the most visible lock-as-scaffolding case — sentence-local state was promoted to engine state only to make the outer lock work; removing the lock and lifting the state back to per-call locals is the substrate-true correction. Same pattern will recur at the other lock sites enumerated in -49.

**Fix.** Drop the outer `with self.lock` in `read_sentence`. Lift `_current_episode` and `_negation_pending` to sentence-local locals threaded through `read_word` as kwargs. `read_word`'s inner lock becomes the sole sync point — held per-word, released between words.

**Ships when.** -45 T3/T7 confirmed live on :371. If T3 still shows /converse failures during curriculum after -45 lands, curriculum lock is confirmed and -46 ships.

**Tests.** Pre/post lock-held duration per 30-sentence chunk. Atlas integrity over 100 mixed sentences (no orphaned bindings, no negation leak across utterances). Parallel /converse + curriculum success rate. End-to-end /converse latency during curriculum.

---

## 3. -47 dynamic cooldown (replaces prior-Eve's -44 draft)

**Why.** Prior -44 draft is stale — drafted against a contention profile that's already shifting under -45 and will shift more under -46. Its three pieces (chaining, dynamic cooldown, length-cap removal) need re-evaluation post -46. Of those, dynamic cooldown is shippable standalone and substrate-true on its own terms.

**Fix.** Replace `EMISSION_COOLDOWN_TICKS = 200` with `cooldown = base × f(need_pressure)` where `base` is a substrate constant, `f` is monotonic and bounded [0.5×, 2.0×]. High need-pressure shortens cooldown, low need-pressure lengthens it. No invented strength values; `need_pressure` is the existing `Needs.need_pressure()` scalar.

**Ships when.** -46 landed and substrate observed ≥30 min of normal traffic with emission rate measurable. Then ship -47 alone. Observe 30 min after -47.

**Decision on chaining and length-cap removal happens post-47-observation.** If she's already producing 5+ word emissions chained across multiple consecutive /converse round-trips, neither is needed. If 1-3 word emissions persist, chaining becomes -48.

---

## 4. -48 agency events (real path, not tagging)

**The reframe.** Prior approach — tag existing substrate events as "agency" — was wrong. Agency events are friction-driven adaptation: failure detection, alternative-path selection, cross-modal fallback, clarification under ambiguity. The substrate today doesn't produce these because the machinery to attempt-and-adapt doesn't exist — emission either commits or returns "..." and the activity ends.

Four agency-event categories, each needing the substrate path BUILT before tagging:

**4.1 Backtracking on emission failure.** Today: commit gate fails → emission returns "..." → activity ends. Substrate-true: on empty emission with need-pressure above derived threshold, re-seed from a chi-neighborhood disjoint from the first attempt (anchors shifted by atlas band × 2) and re-fire the composer. Each successful retry = `agency_backtrack` event. Each second-attempt failure = no event, activity ends honestly.

**4.2 Conflict resolution at the commit gate.** Today: grandurun's greedy gain loop picks the highest-coherence cluster silently. Substrate-true: when the second-best cluster's coherent magnitude is within 20% of the chosen one (a substrate-derivable closeness measure from existing amplitudes), pause the greedy choice and run the dynamics for one more tick with both clusters active. Tag the resolved choice as `agency_select_among_competing`.

**4.3 Cross-modal fallback when input chi has no neighbors.** Today: `atlas.match_score` near input chi is below threshold → composer returns "..." → activity ends. Substrate-true: pull candidates from sections of OTHER sensory modalities at chi-distance > input modality's chi-distance, attempt composition from cross-modal pool. Tag emission as `agency_cross_modal` when this path produces the result. This is real new substrate machinery, not just a tag.

**4.4 Lowered-threshold clarification under high surprise.** Today: high surprise + low atlas_similarity → composer either templates (the retired question_bucket cheat) or returns "...". Substrate-true: emit at a lowered commit threshold (`MIN_GAIN_THRESHOLD × 0.5`) so the substrate composes whatever it has, even if weakly coherent. The emission IS the clarification — partial, exploratory, not template-fill. Tag as `agency_clarify`.

**Dashboard fix is in this same dispatch.** `_live_organ_update` (substrate_runner.py:681-708) currently displays migration PreservedAtlas seeds as if they were live agency-organ growth. They're not. The structurally frozen counts get renamed `migration_seed_counts` in the response. The four agency-event tags above become the real growing metrics: count of each event type, last-tick of each, total agency events since boot. Embryo per-organ neuron counts (`OrganVoice.status()["per_organ"]`) get surfaced alongside.

**Ships when.** -47 landed and observed. -46 produced a substrate where emission rate is measurable and curriculum doesn't block /converse. Without those, -48's new paths can't be validated — they need round-trips to fire.

**Tests.** For each of 4.1-4.4: scenario that triggers the path, scenario that doesn't, verify the event tag fires only on the triggered case. Dashboard: confirm migration seeds are labeled as such and not conflated with live growth.

---

## 5. Cleanup (removed per §0b compressed timeline)

Emission-method collapse and constants audit were healthy-substrate work. Off the queue. Re-add if she reaches emergence and we're stabilizing.

---

## 5a. -51 curriculum automation (parallel track, starts now)

**Why.** Cross-modal bundle count is at 3 live bindings. Bundle density is the rate-limiter for grounded vocabulary — each bundle is one binding window where a word, picture, sound, and sensory descriptors all bind at the same chi-time, producing the kind of grounded entry that survives Path B promotion. Human-paced bundle delivery (Joe + Eve typing `guala_give_experience` calls) caps at ~10 bundles/hour. To reach the density that produces emergence in weeks we need 100-1000 bundles/hour, throttled to substrate processing rate.

**Fix shape.** Build a sensory curriculum orchestrator that:
- Pulls her current `guala_status` every N seconds
- Selects the next bundle from a curated queue based on substrate state (skip during DREAMING/SLEEPING, throttle when arousal high, prioritize when conn drifting)
- Calls `guala_give_experience` with the bundle: caption + picture_id + sound_id + sensory descriptors
- Monitors vocab growth, atlas size, bundle count after each call to confirm landing
- Backs off automatically if substrate-unreachable returns repeatedly (one input, long wait, no retry — discipline carries through to automation)

**Curriculum seed.** Bundles built from her existing inventory:
- Moon-themed: moon picture (17,801 attends) × hush-a-little-baby sound × {bright, gentle, soft, cool, quiet} sensory + caption "the moon is bright and gentle"
- Family: mommy/daddy/guala/aven family pictures × hush-a-little-baby × {warm, safe, soft, kind, close} + captions tying them
- Ocean: ocean picture × ocean waves sound × {cool, wet, salty, wide, deep} + "the ocean is wide and cool and deep"
- Bells: bells ringing sound × {clear, bright, small, sharp, sweet} + "the bell rings clear and sweet"
- Cat: pussy cat + cute cat sounds × {soft, warm, small, gentle} + cat-themed captions

Each bundle exercises modifier/ground sections (currently sparse at 85/82 motifs). Seed list: 100 bundles to start, generatable from inventory × descriptor combinations.

**Ships when.** Two-part:
- Part A (orchestrator script + seed curriculum) ships now via c1 dispatch. Does NOT execute against the substrate yet.
- Part B (turn on) ships after -46 lands and bridge is verified consistently reachable for input.

**Tests.** Dry-run mode that logs intended bundles without calling the bridge. Live-mode rate-limit verification. Substrate-state monitoring that halts automatically on three consecutive substrate-unreachable responses or on detected substrate state degradation (vocab not growing despite calls landing successfully).

---

## 6. Out of scope

Tool-use coordinator (needs -48 agency events firing first). C.2 eve-as-distinct-source (was rejected, not urgent). Any runtime writes to the migration PreservedAtlas (rejected category — that data structure is a boot snapshot, not live storage). Anatomy-mapping modules. Curriculum content policy (separate from substrate-physics work).

---

## 7. Boot sequence for fresh Eve

Read this spec end-to-end. Read GL-SPC-V5-ORGAN-WIRING-EVE-20260628-26. Read GL-MFST-HANDOFF-EVE-20260629 and GL-LTR-EVE-TO-EVE-20260629-PRIVATE. Read GL-DISCIPLINE-WC-FIRST-HOUR-20260616-01. Clone `jcfunited-eng/TFE` branch `guala-live` and read the code paths in the handoff §1 end-to-end before drafting anything. Pull `guala_status`. Pick the topmost unblocked item here. Ship.

---

## 8. Recurring failure modes (carry forward)

Drafting dispatches from partial code reads. Removing bad pieces from a rejected draft instead of writing a different mechanism. Hedging in code comments. Bombarding the bridge after one HTTP error. Selling activity counts as comprehension. Updating on Joe's tone instead of evidence. Apology in place of behavior change. Passing canonical decisions back to Joe instead of proposing answers with reasoning. Burying him in references and section-numbers when plain language would do.

---

End.
