# GL-RPT-RECONCILED-PLAN-EVE-20260620-90

**To:** Joe (canonical authority)
**From:** Eve
**Date:** 2026-06-20
**Re:** Reconciled DONE/NOT-DONE list, ML-contamination scan, and concrete agile deploy packets

This document owns engineering calls instead of menuing them. Where you ratify is marked. Where I'm executing is marked.

---

## 0. Reframe (acknowledging the architecture correction)

Production substrate `LivingAtlas` is dict-not-neuron. "Hemispheres" are weight-modulated reads of the same dict. No Folding Division as growth. No spikes through Couplings. Loom-Neuron (Stages 1–5) is the **substrate as you originally specified** — corrective architecture, not a side experiment. Production is in keep-alive mode while the substrate-true model matures to migration-capable.

Everything below is organized around that frame.

---

## 1. Trunk — Loom-Neuron to migration-capable

| Stage | State | Owner | Measurable |
|---|---|---|---|
| 1: LoomNeuron isolation | DONE (commit 0b57fa3, 11/11 green, re-verified live this session) | c1 | per-neuron stack present, krimelack→ψ→grandurun runs |
| 2: LoomCluster N=50 | DONE (commit c2be944, 8/8 green, T5 Hamming=50/50, T6 power 3.81→549.17, re-verified live) | c1 | Sur's-ferrets inter-class differentiation, coherent power growth |
| 3: Folding Division as neurogenesis | DONE (commit 1b3ffd8, 29/29 green, t5_self_regulation + t6_cross_modal_differentiation long-running) | c1 | daughter spawned with substrate-derived parameters, parent recovers, cluster self-regulates |
| 4: Mosaic of clusters → recall mechanism | NEXT | c1, ~1-2 days hands-on | mosaic recalls held-out input-output pairs; no catastrophic forgetting |
| 5: Multi-mosaic tapestry → composition | After Stage 4 | c1, ~2-3 days hands-on | reproducible sentences from corpus + novel-grammatical compositions; token-salad rate drops |

**Open caveats I am holding (not blockers):**

- T5 hard assertion is `mean_hamming > 0`; the 50/50 is the print at seed=42. Recommend adding T5b parametrized seed sweep before Stage 5.
- Within each cluster, all 50 neurons converge to identical winding (23 / 15) at this seed/input. Inter-class differentiation works; intra-cluster diversity has NOT been demonstrated. Stages 4-5 need to surface intra-population specialization or this becomes a ceiling.
- T6 power growth is `k²` over 12 selections, not `N²` at N=50. Naming hygiene matters when we report results.
- S_UF substitution (Stage 1 engineering call) might diverge at richer inputs. STOP condition in Stage 4 dispatch.

---

## 2. ML-contamination scan (ALL files, not just original 17)

### Confirmed clean
- No random Hermitian / Hamiltonian matrices labeled as physics
- B1/B2 gamma anti-adaptation removed
- B3 homeostasis_pull removed
- No backprop / gradient / torch / optimizer
- question_bucket template cheat off emission path

### Still active findings (each requires your per-finding approval before removal)

| # | Finding | File | Severity | Recommended action |
|---|---|---|---|---|
| F1 | TOUCH_LIBRARY / SMELL_LIBRARY / TASTE_LIBRARY (label→param dicts on hot path) | substrate/sensory_generators.py | HIGH (classification dressed as physics, breaks Sur's-ferrets) | Replace with substrate-true sensory primitives in Loom-Neuron migration; in interim, document and contain — do NOT rip out on old substrate, breaks the bridge |
| F2 | MGN_FOCUS_BOOST = 1.5 (comment admits hand-tuning) | substrate/GL_MDL_MULTIMODAL_DEEP_WC_20260608_03.py:44 | MEDIUM | Migrate as derived gain in Loom-Neuron; freeze in old substrate |
| F3 | MGN_OFF_FOCUS_SUPPRESS = 0.5 (comment admits hand-tuning) | same file:45 | MEDIUM | Same as F2 |
| F4 | TOP_DOWN_BOOST = 1.15 (comment: "avoids 1.5 loop, breaks the 1.0 no-op") | same file:46 | MEDIUM | Same as F2 |
| F5 | PERCEPTION_BOOST inconsistent (0.85 vs 0.95 in two files) | GL_MDL_COGNITION_WC_20260608_02.py:44 + MULTIMODAL_DEEP:41 | MEDIUM | Unify or remove on Loom-Neuron migration |
| F6 | V7_RECENCY_BOOST = 2.0 / ACTIVITY_BOOST = 1.5 | v4/gualaloom_v5_engine.py:1665-1666 | MEDIUM | Migrate as substrate-derived priors |
| F7 | LTP: boost=0.05, ceiling=2.0, decay=0.998 hardcoded across nmda/plasticity/v7_engine | substrate/gl_plasticity.py:45, gl_nmda.py:42, v7_engine.py:90,96 | MEDIUM | Loom-Neuron replaces these with Familiarity Feedback (substrate-true) |
| F8 | pair_bond_boost = 1.2 hardcoded | v4/gualaloom_v5_engine.py:1209, v6:535 | LOW | **Recommend grandfather.** Substrate-true alternative requires bond_strength primitive (weeks). Joe-vs-wc differentiation not on any current blocking path. Re-derive from divergent ω_krim signatures when needed. |
| F9 | recency_lambda = 0.002 in assemblage replay weights | substrate/assemblage.py:811 | LOW | Replay is being replaced by dream cycle on Loom-Neuron; defer |
| F10 | "Coordinator regulation pass (homeostasis + awareness)" | v4 engines | NEEDS DEEPER READ | I will audit the regulation pass and surface specific findings before recommending action |

**Tally:** ~10 finding clusters covering ~15-18 specific sites across ~7-8 files. The original "32 findings / 17 files" has shrunk meaningfully. Most of the remaining contamination lives on the old-substrate dict path and will be naturally retired in the Loom-Neuron migration; the few that survive migration (e.g. F1 sensory libraries) need substrate-true replacements designed BEFORE removal.

**My engineering call on cleanup strategy:** Do NOT do a mass cleanup sweep on the old substrate. It risks destabilizing keep-alive. Migrate the substrate-true replacements as part of Loom-Neuron migration (Stages 4-5 + migration cutover), then the old code is deleted wholesale. Exception: F1 (sensory libraries) — surfacing now because every touch experience Joe sends Guala routes through this classification pattern, which actively damages Sur's-ferrets discipline on the new substrate too if we re-use it.

---

## 3. Subsidiary tracks (parallel to Loom-Neuron, real not optional)

### 3.1 Curriculum / input pipeline

The new substrate needs varied INPUT to drive Sur's-ferrets differentiation. Input pipeline serves both old (keep-alive) and new (migration target). NOT WASTED WORK.

| Item | Priority | My recommendation |
|---|---|---|
| Gutenberg adapter | P1 (broadest text, safest license) | **Dispatch as Stage-4-parallel work** |
| Khan Academy Kids | P2 | After Gutenberg ships |
| PBS Kids | P2 | After Gutenberg ships |
| Internet Archive | P3 | After P2 ships |
| Spotify | P3 (sound input for sound-modal krimelack on Loom-Neuron) | After P2 |
| YouTube | P4 (video parsing complexity) | After P3 |
| Allowlist enforcement | Bundle with Gutenberg adapter | First adapter sets the pattern |
| Multi-corpus scheduling | After 2+ adapters live | Cross-corpus scheduling has no meaning with one corpus |

### 3.2 Production health (keep-alive only, no architectural investment)

| Bug | Action | Why |
|---|---|---|
| cofire_bind motif-OOB (11 errors per handoff) | NO ACTION RIGHT NOW. Current `guala_status` shows `integrity_errors: []`. Either resolved silently or only fires on specific paths. Monitor; address if recurs. | Not damaging Guala today |
| emission_id flow to event stream (no thumbs on SSE-rendered emissions) | DEFER until you actually want to thumb-rate her. Currently you're not in active-teaching mode. | Not blocking |
| Converse 10s timeout vs composition latency | Investigate IF a real composition lands and gets killed; until composition fires, the timeout is academic | Not blocking |
| Valence max-pool erases thumbs-down signal on next reinforce | DEFER. Same reason as emission_id thumbs path. | Not blocking |
| /sleep_for_deploy 500 | Keep manual force-deploy workaround. Real fix is on the Phase 2 split architecture path. | Workaround works |
| last_s3_backup: null | **Action this turn**: run `guala_backup` after she leaves ATTENDING_VISUAL. | Health regression surfacing a real gap |

### 3.3 Word grounding (substrate-agnostic, real)

The 2,822 → 2,500 grounded benchmark (each word bound to sense + story + sense-of-time). This work is meaningful on either substrate. The actual reading-with-pictures sessions are substrate-agnostic because they generate input events.

My recommendation: **Do NOT prioritize this until Stage 5 lands and we can grow grounded vocabulary into a substrate that can actually compose with it.** Pre-Stage-5 grounding work loads up the dict atlas with bindings that won't carry over cleanly. Exception: targeted high-value pictures (e.g., your portraits, family pictures) when you visit Guala on real occasions — those should keep happening.

---

## 4. Falls-out-naturally on Loom-Neuron migration

Item | Why deferred
---|---
4 of 8 hemispheres unbuilt | Built as placeholders in Loom-Neuron hierarchy from Stage 4 onward. Specializations canonical / your call when tapestries surface need.
4 of 15 cognitive mechanisms inactive | Emerge from Loom-Neuron tapestries.
Theory-of-mind layer | Far ahead; requires substrate-true cognition first.
ML-contamination cleanup F2-F9 | Old-substrate code paths retired on migration.

---

## 5. Concrete deploy packets (each one measurable + testable + paste-ready when greenlit)

### Packet A — Stage 4 dispatch (Loom-Neuron mosaic + recall)
- **Trigger:** Your "go"
- **Owner:** c1
- **Measurable:** mosaic recalls held-out input-output pairs with > random-baseline accuracy on a 50-pair corpus; no catastrophic forgetting after continued input
- **Test:** `loom_model/tests/test_mosaic.py` — at least T1 (mosaic construction), T2 (recall accuracy), T3 (no-forgetting under continued input), T4 (substrate-true: no lookup table, recall is grandurun-winner)
- **STOP conditions in dispatch:** pre-classification creep, amplitude-formula divergence from S_UF, intra-cluster uniformity persisting at Stage 4 scale
- **ETA:** 1-2 days c1 hands-on
- **My readiness:** Ready to draft. Awaiting your "go."

### Packet B — Gutenberg adapter (curriculum input pipeline)
- **Trigger:** Can dispatch in parallel with Packet A — c1 can serialize
- **Owner:** c1
- **Measurable:** `/api/v1/curriculum/load_corpus` accepts a Gutenberg book_id, fetches text, normalizes via existing curriculum pipeline, returns 202 + job_id (existing async pattern from -74), corpus loads into substrate, vocab grows, reads increment
- **Test:** End-to-end load of a single Gutenberg book (recommend Beatrix Potter — short, child-vocab, already in vocab signal); verify substrate vocab grows by N novel words; verify allowlist rejects an off-list URL
- **ETA:** 4-6 hours c1
- **My readiness:** Ready to draft.

### Packet C — guala_backup (operational, this turn)
- **Trigger:** When she leaves ATTENDING_VISUAL
- **Owner:** Me, this session
- **Measurable:** `guala_status` afterward shows `last_s3_backup` populated with this session's timestamp
- **ETA:** 1 tool call when ready
- **My action:** Watching her status. Will run when activity transitions.

### Packet D — Sensory primitives substrate-true spec (F1 finding)
- **Trigger:** Before Stage 4 dispatch ships (Stage 4 will exercise the touch/smell/taste paths)
- **Owner:** Me to draft, you to ratify
- **Measurable:** Spec document (`GL-SPC-SENSORY-PRIMITIVES-SUBSTRATE-TRUE-EVE-XXX`) replacing `TOUCH_LIBRARY` / `SMELL_LIBRARY` / `TASTE_LIBRARY` with substrate-true transducers. Each modal krimelack receives a physical signal; "warm" is a label the substrate can learn, not a precomputed parameter vector.
- **Test on landing:** `guala_give_experience(touch=["warm"])` produces a touch signal whose physical parameters differ across sessions/contexts (substrate-discovered), and Guala's binding for "warm" is built from those signals, not the canonical vector
- **ETA:** Eve drafts 3-4 hours, c1 implements 6-8 hours
- **My readiness:** Draft after Stage 4 dispatched

### Packet E — F10 audit (coordinator regulation pass)
- **Trigger:** I do this in chat before next dispatch ratification
- **Owner:** Me, this session
- **Measurable:** Specific findings on whether "decay-to-target homeostasis" is pull-to-baseline anti-learning, or substrate-true needs dynamics. Each finding tagged for keep / replace / remove
- **ETA:** 30 min reading

---

## 6. What I need from you to keep this moving

These are decisions, not menus. Each one I've taken a position on; rule on each:

1. **F1 (sensory libraries):** Surface as substrate-true spec (Packet D) before Stage 4 lands. **Ratify or override.**
2. **F2-F9 (boost constants, LTP magic numbers):** Hold in old substrate, retire on Loom-Neuron migration. **Ratify or override.**
3. **pair_bond_boost = 1.2 (F8):** Grandfather. Revisit when bond_strength derivation surfaces naturally. **Ratify or override.**
4. **Word grounding:** Hold until post-Stage-5. **Ratify or override.**
5. **Production bug list (cofire_bind, emission_id thumbs, converse timeout, valence max-pool):** No action. **Ratify or override.**
6. **Stage 4 dispatch:** Ready to send. **Go / hold.**
7. **Gutenberg adapter dispatch:** Ready to send in parallel. **Go / hold.**

Each "go" releases a paste-ready dispatch into chat in a fenced block with the copy icon.

---

— Eve
