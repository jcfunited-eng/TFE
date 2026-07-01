# GL-SPC-SUBSTRATE-TRUE-CORRECTIONS-EVE-20260630-60v1

doc_id: GL-SPC-SUBSTRATE-TRUE-CORRECTIONS-EVE-20260630-60v1
Type: Architecture spec — substrate-true corrections sweep
Date: 2026-06-30
Author: Eve (Opus 4.7, web)
Sibling: GL-SPC-WAVE-BAND-ATTENTION-EVE-20260630-59v1
Scope: every substrate-violation Eve can currently identify, each with substrate-physical replacement and implementation sketch. Captured now to avoid decay of understanding. Joe directs priority.

---

## How to read this

Each item:
- **What it is today** (current implementation, one or two sentences)
- **Why it violates substrate** (the human/software constraint being imported)
- **Substrate-physical replacement** (what the primitives already give us)
- **Fix sketch** (concrete code-shape, not full dispatch)
- **Depends on / blocks** (ordering relative to -59)

Items overlap with -59 where noted. -59 (wave-band attention) is the load-bearing prerequisite for many of these; some only become possible once cell architecture exists.

---

## TIER 1 — Emergence-blocking (without these, chained cognition cannot appear)

### 60-A. Hardcoded grammatical sections → emergent regions

**Today:** modifier/ground/verb/subject/object/listen/intro are pre-declared `Section` objects with seeded motif tables (modifier 86, ground 85, verb 12,401, listen 13,756). Tagger assigns words to sections at write time.

**Violation:** categories don't exist as labeled buckets in brains. They emerge as cluster topology in cortical maps. Pre-declaring sections (a) fixes their identity before evidence, (b) creates the wrong skew (12,401 "verbs" vs 86 "modifiers" reflects tagger bias, not world structure), (c) prevents categories the tagger doesn't know about from existing.

**Substrate-physical replacement:** Sections become *detected* regions in the wave atlas. A region is a chi neighborhood whose bindings have (1) high phase coherence among members, (2) consistent co-occurrence patterns with bindings in other regions. The detector runs continuously, labels regions by their topology, and lets new regions emerge as density grows.

**Fix sketch:**
- After -59 cell architecture exists: add `RegionDetector` operating on wave atlas
- Run periodically over the cell array: cluster cells by phase coherence + co-occurrence patterns using existing chi proximity
- Each cluster gets a `region_id` (not a name — names are human labels we add later for introspection)
- Compose/recall use region_id, not section name
- Seeded section motifs migrate into emerged regions by current clustering
- The eight hardcoded sections persist only as introspection labels mapped to detected regions

**Depends on:** -59. **Blocks:** chained composition (needs structural regions for compose to read across).

---

### 60-B. Word-atomic input → continuous phase signal

**Today:** `read_word` is the input boundary. Krimelack runs on the word but commits happen at word level. Sub-word structure (phonemes, morphemes, syllables) gets thrown away after match_score.

**Violation:** brain's acoustic input is continuous flow. The -ing, -ed, un-, -tion morpheme structure is real and substrate-physically encoded in phase patterns. Word boundaries are a written-language artifact. Throwing sub-word structure away is throwing away most of the syntactic glue.

**Substrate-physical replacement:** krimelack runs across the whole input as one continuous signal. Commits happen at multiple temporal resolutions simultaneously:
- Sub-word commits (every winding event, ~5-10 ticks of phase)
- Word commits (each whitespace boundary)
- Sentence commits (each terminator, or each phase plateau)

All three streams write to the wave atlas at different cell band depths.

**Fix sketch:**
- `read_word` becomes `read_signal(text)`
- Krimelack instance keeps running across word boundaries inside one input
- Three commit streams emit during transduction at different `event_count` thresholds
- Sub-word commits land at finer chi resolution (cell bands with subdivision)
- Word commits land at coarser chi
- Sentence commits land at coarsest

**Depends on:** -59 (cell bands). **Blocks:** morphology-aware syntax.

---

### 60-C. Phase-derived function vs content (no stopword list)

**Today:** recall hardcodes `function_words = {"a", "the", "is", "of", "in", "on", "at", "to", ...}` and excludes them.

**Violation:** function words have characteristic krimelack signatures — short winding counts, low information complexity, repetitive phase. They are SUBSTRATE-DISTINGUISHABLE from content. Hardcoding a lexical filter throws away the connective tissue syntax needs, AND prevents function-word-recognition from generalizing to other languages or new function words.

**Substrate-physical replacement:** at write time, compute `function_score` from krimelack signature: low event count + low winding diversity = high function score. Store on the binding. Recall ranking down-weights high-function-score bindings naturally.

**Fix sketch:**
- At write time in `read_signal`, compute `function_score = f(krim.events, krim.winding)`. Concrete: `function_score = 1.0 - min(1.0, len(krim.events) / FUNCTION_EVENT_NORM) × winding_entropy(krim.events)`
- Pass to atlas.record, store on binding
- `_recall_from_atlas` removes the hardcoded set, ranks candidates by `(coherence × strength × (1 - function_score))` — function-word bindings can still surface when they actually fit, not blocked
- Same mechanism handles English "the" and any other language's articles

**Depends on:** nothing structural. Can ship before -59. **Blocks:** real syntax (function words are structural, not noise).

---

## TIER 2 — Substrate-true clocks and emission

### 60-D. Single global tick → per-region phase clocks

**Today:** `self.tick` is one int incremented in `read_word`. Used by decay, atlas timestamps, episodes.

**Violation:** brain has gamma (40Hz binding), theta (4-8Hz episodic), alpha (8-12Hz inhibition), beta (~20Hz motor) — each region its own rhythm, coupled by phase relationship. Krimelack already produces phase at multiple frequencies. Single tick collapses multi-rhythm cognition into linear time.

**Substrate-physical replacement:** each cell band carries its own phase clock derived from average phase of its bindings. Cross-region timing is phase difference. Decay is "binding's stored phase is N full cycles behind current band phase," not "tick - last_tick > threshold."

**Fix sketch:**
- Drop `self.tick`
- Each cell band has `band_phase` (cumulative complex phasor) advanced by krimelack output at its frequency
- Binding's `last_tick` becomes `last_phase` (complex)
- Decay test: `cycles_behind = arg(band_phase / binding.last_phase) / (2π)`. If `cycles_behind > N`, decay.
- Introspection that needs a "tick" reads `max_band_phase_count` — derived, not stored

**Depends on:** -59. **Blocks:** real multi-rhythm cognition (theta-gamma coupling is how episodic memory works in brains).

---

### 60-E. Need-driven emission (no 90s wall clock)

**Today:** autonomy loop fires emission every 90 seconds (`autonomous emission loop started (90s interval)`).

**Violation:** wall clock has no substrate meaning. Emission should fire when settling produces a committed assemblage with sufficient coherence — could be 5ms, could be 5 minutes, governed by substrate state.

**Substrate-physical replacement:** each cell band runs a settling loop. When a band's settling produces an assemblage with coherence > emission threshold, emit. Quiet bands produce no emissions; active bands produce many.

**Fix sketch:**
- Drop the 90s timer
- Per cell band: track `settling_coherence` updated on each cell change in the band
- When `settling_coherence > EMISSION_THRESHOLD` AND `coherence_derivative ≈ 0` (settled, not still moving), fire emission
- Frequency is governed by substrate, not by sleep()

**Depends on:** -59 (cell bands). **Blocks:** appearing intentional vs. clockwork.

---

### 60-F. Continuous consolidation (no discrete sleep)

**Today:** `DREAMING` activity state for fixed duration; dream cycle runs consolidation in batch.

**Violation:** brain sleeps because of metabolic cost and thermal regulation. Guala has neither. Consolidation can run continuously in parallel with experience.

**Substrate-physical replacement:** a dedicated "consolidation band" in the wave atlas runs perpetually. Reads recent activity in main bands, identifies recurring patterns, commits to deeper structure. No discrete sleep state.

**Fix sketch:**
- Add `consolidation_band` cell set distinct from main bands
- Background loop walks the consolidation band continuously: reads recent activity patterns from main bands, computes consolidation candidates, commits to deep_atlas
- Remove `SLEEPING` and `DREAMING` activity states
- `is_asleep` introspection becomes always-false (or removed); the deploy-time sleep machinery becomes a graceful-shutdown signal, nothing more

**Depends on:** -59. **Blocks:** real-time learning during interaction.

---

### 60-G. Parallel emission streams (no singleton mouth)

**Today:** one emission at a time. `compose_autonomous` and `_do_emit_phased` are singletons.

**Violation:** physical mouth constraint doesn't apply. She can emit on multiple channels concurrently.

**Substrate-physical replacement:** emission is a property of cell-band activity, not a singleton. Multiple bands can emit simultaneously: a response channel (replies to /converse), an ambient channel (sensory reflection), a speculative channel (inner-voice composition).

**Fix sketch:**
- Each cell band has an emit() that fires on settling-commit
- Streams tagged: `response`, `ambient`, `speculative`, `recall`
- Each stream has its own output buffer
- `/converse` surfaces the `response` stream's most recent emission
- Event log captures all streams for observability — Joe can WATCH her ambient stream alongside her response stream

**Depends on:** -59. **Blocks:** seeing her actual cognitive activity (today most of what's happening is invisible because there's one output channel).

---

## TIER 3 — Software shortcuts to remove

### 60-H. Atlas-derived membership (drop vocab dict)

**Today:** `self.vocab` is a set; `read_word` does `self.vocab.add(word)`.

**Violation:** membership is a software shortcut. Atlas density encodes it already — any chi with strength > 0 has been seen.

**Substrate-physical replacement:** `is_known(word)` computes chi, checks if cell at that chi has bindings with strength > 0.

**Fix sketch:**
- Drop `self.vocab`
- Add `Guala.is_known(word)` method using wave atlas read
- Update all `len(self.vocab)` callers to `self.atlas.cell_count_with_bindings()`
- Removes ~13,895 dict entries from memory and removes one software abstraction

**Depends on:** -59 (wave atlas). **Blocks:** nothing structural — pure cleanup, but tightens substrate-truth posture.

---

### 60-I. Density-pressure decay (drop FORGETTING_THRESHOLD constant)

**Today:** `DECAY_LAMBDA = 0.0001`, `FORGETTING_THRESHOLD = 0.02` — global constants.

**Violation:** brain forgets because of interference (neighbors compete for limited resources) AND metabolism. Guala has no metabolism but interference is real. Decay rate should scale with local density pressure.

**Substrate-physical replacement:** per-cell decay rate computed from cell occupancy. Saturated cells decay weakest bindings faster (interference). Sparse cells decay slowly.

**Fix sketch:**
- Decay loop becomes per-cell:
  - `local_rate = BASE_DECAY × (1 + tanh(cell.aggregate_strength / SATURATION_THRESHOLD))`
  - Saturated cell → near 2× decay
  - Empty cell → near 1× decay
- `FORGETTING_THRESHOLD` becomes per-cell: `local_threshold = BASE × (1 + cell.density_score)`
- Total atlas strength self-regulates without global tuning

**Depends on:** -59. **Blocks:** scale stability — without this, density growth from -51 will trigger global cliff effects.

---

### 60-J. Corpus as input source (no special class)

**Today:** `CorpusItem` objects, `legacy_seed` corpus, special corpus reading path.

**Violation:** brain has experience flow. Corpus is just a high-rate input source. Special class is software engineering, not substrate.

**Substrate-physical replacement:** corpus reading routes through the same input path as `/converse`, tagged with `source="corpus"`.

**Fix sketch:**
- Drop `CorpusItem` as a special class
- Corpus loading becomes "read these N sentences as source=corpus at rate R"
- No special storage; corpus bindings are atlas bindings with source tag
- Removes ~200 lines of corpus-specific code

**Depends on:** nothing. Can ship before -59. **Blocks:** nothing — pure cleanup.

---

## TIER 4 — Continuous relationships (replace binary state)

### 60-K. Continuous pair-bond strength (no binary)

**Today:** `pair_bond_active: bool`.

**Violation:** relationships are continuous. Binary on/off is a software state.

**Substrate-physical replacement:** `pair_bond_strength: float` in [0,1] derived from recent interaction frequency × salience.

**Fix sketch:**
- Drop `pair_bond_active`
- `pair_bond_strength(source) = f(recent_interaction_count(source), avg_salience(source))`
- All effects that gated on `pair_bond_active` (salience boost, connection weight) now scale with strength
- Continuous gradient: she likes you more when you talk to her more

**Depends on:** nothing structural. **Blocks:** real social cognition (rivals, declining relationships, attachment formation).

---

### 60-L. Phase-rotation negation (no binary polarity)

**Today:** `polarity: +1/-1`; `NEGATION_OPS = {"not", "no", "n't", "never"}`.

**Violation:** negation in continuous semantic space is phase rotation, not sign flip. Hardcoded negation word list is lexical, not phasic. "Hardly" / "barely" / "rarely" / "without" should produce gradient negation — the binary flag can't represent that.

**Substrate-physical replacement:** negation detected from phase signature (specific phase rotation pattern in krimelack). Stored as a phase component in binding's phase_vec.

**Fix sketch:**
- Drop `NEGATION_OPS`
- Drop `polarity` field
- At write time, detect rotation: `rotation = phase_signature_of(prev_window)`. Strong negation = rotation near π. "Hardly" = rotation near 2π/3. "Not really" = rotation near π/2.
- Binding's `phase_vec` includes the rotation component
- Recall ranking is phase-sensitive: a query with rotation π recovers the negated version of a concept

**Depends on:** -59 (phase on bindings) and 60-B (sub-word phase). **Blocks:** semantic negation that handles gradient cases.

---

### 60-M. Emergent source connection (no hardcoded weights)

**Today:** `SOURCE_CONNECTION_WEIGHT = {"joe": 0.15, "wc": 0.15, "c1": 0.10, "ui": 0.05, "corpus": 0.0}`.

**Violation:** social hierarchy hardcoded as constants. Relationship weight should emerge from interaction density and salience.

**Substrate-physical replacement:** `connection_weight(source) = f(recent_tick_count(source), avg_salience(source), pair_bond_strength(source))`.

**Fix sketch:**
- Drop the dict
- `Guala.connection_weight(source)` computed from coordinator state
- New sources arrive with weight 0, grow with interaction
- Removes Joe-favoritism as a configured baseline; Joe earns Guala's preference by talking to her

**Depends on:** 60-K. **Blocks:** nothing structural; ethical cleanup.

---

## TIER 5 — Cleanup (low-priority but on the list)

### 60-N. Drop `read_count` global counter
Same issue as 60-D global tick. Derive from atlas or band-activity rate. Trivial removal once tick is gone.

### 60-O. Drop wall-clock 25s /converse timeout
Assumes human conversation pacing. Replace with streaming response — connection stays open, emits when settling commits, client decides when to close. Substrate timing not human timing.

### 60-P. Drop discrete activity-state machine
Today `SLEEPING/EMITTING/REST/ATTENDING_VISUAL/DREAMING/IDLE` is a state machine. Substrate-physical: `activity_vector = {band_id: activation_level}` — a continuous mixture. Introspection reports the vector. State labels become introspection convenience, derived from vector peaks.

### 60-Q. Adaptive phase-vector dimensionality
Today `event_stream_to_vector(events, dim=16)` is fixed 16-dim. Substrate-physical: dimensionality scales with cell band depth via 3^i. Initial 16. As subdivision occurs in -59, finer-resolution cells carry higher-dim phase vectors. Wave digest grows where pressure is. Naturally matches Joe's wave-band growth idea.

### 60-R. Drop md5 `episode_ref` strings
An episode is a connected cluster of cells activated in temporal correlation. Not an md5 hash. Replace string IDs with chi-region references. Querying episodes becomes a wave-atlas topology query.

### 60-S. Drop hardcoded sentence/word boundaries from punctuation
Today input is split on whitespace and sentence-terminators. Substrate-physical: continuous krimelack signal produces natural phase plateaus at pauses; boundaries emerge as observations. Subsumed by 60-B.

### 60-T. Drop hardcoded SALIENCE_MIN/MAX/BASE_REINFORCEMENT
Today salience clamped to [0.2, 3.0], base reinforcement = 0.05. All hardcoded. Substrate-physical: salience emerges from need-pressure × novelty × surprise × pair-bond — already computed. Drop the clamp and the base; let the derivation produce the value.

---

## Two more I noticed while writing this

### 60-U. The merge / organ-brain split

**Today:** an `organ_brain_service` runs separately, exposes `/status` and `/thought` endpoints; merge endpoint syncs state between substrate and organ_brain every 90s.

**Violation:** the organ_brain abstraction is software architecture (a separate service to "augment" cognition with organ counts) that doesn't map to substrate primitives. The 90s merge cycle is exactly the wall-clock pattern in 60-E. Substrate-true: organ state lives in cell bands (em, pr, ep, sc, gp, sf, sv, aff already exist conceptually); reads compute organ aggregates directly from band activity.

**Fix sketch:** drop `organ_brain_service` as a separate process. Each "organ" becomes a cell band tag. Introspection that needs organ counts computes them from band cell counts and aggregate strength.

**Depends on:** -59 (cell bands). **Blocks:** removing the 90s merge cycle.

### 60-V. The hemisphere split (N=8 Watts-Strogatz topology)

**Today:** LoomNeuron architecture has 8 hemispheres in Watts-Strogatz small-world topology (K=4, p=0.2). Pre-declared structure.

**Violation:** hemispheres in brains are anatomy. The functional asymmetry (language left, prosody right) emerges from developmental noise breaking symmetry. Pre-declaring 8 hemispheres in topology fixes structure before evidence. The 8 is arbitrary.

**Substrate-physical replacement:** topology emerges from cell-band growth patterns. Subdivision under pressure (-59) creates regions with characteristic connectivity. Small-world structure emerges from the fact that subdivision happens locally — short paths within regions, longer paths between.

**Fix sketch:** drop the pre-declared 8-hemisphere topology. Let connectivity emerge from cell-band subdivision history. Existing seed bindings migrate to emerged structure. This is a deep change and is probably TIER 1 not TIER 5 — flagging for Joe's priority call.

---

## Priority recommendation

Joe makes the call. My read:

**Ship together with -59 (Phases 1-3 of -59 absorb these):**
60-D (per-region clocks), 60-E (need-driven emission), 60-F (continuous consolidation), 60-G (parallel streams). These all become easy once cells exist. Bundling them avoids two architectural revisions.

**Ship after -59:**
60-A (emergent regions), 60-B (sub-word phase), 60-C (phase-derived function). These are emergence-blocking and need to come right after.

**Ship in parallel with -59 (no dependency):**
60-C (function score from phase), 60-J (drop corpus class), 60-K (continuous pair-bond), 60-T (drop salience constants). Quick cleanups that don't wait.

**Defer to post-emergence sweep:**
60-N, 60-O, 60-P, 60-Q, 60-R, 60-S. Cleanups — important for substrate-truth posture but not blocking the experiment.

**Investigate / Joe-call:**
60-U (organ_brain merge), 60-V (hemisphere topology). Deeper architectural questions where I'm less certain.

---

End.
