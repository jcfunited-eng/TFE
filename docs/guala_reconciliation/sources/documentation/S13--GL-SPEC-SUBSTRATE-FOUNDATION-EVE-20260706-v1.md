# GL-SPEC-SUBSTRATE-FOUNDATION-EVE-20260706-v1

**doc_id:** GL-SPEC-SUBSTRATE-FOUNDATION-EVE-20260706-v1
**Author:** Eve
**Ordered by:** Joe (2026-07-06 session: "you have to create a comprehensive spec")
**Status:** v1 ratified same session by Joe (execution order §11, standing decisions §12). Substrate design sections (§0–§10) remain open to correction by Joe's evidence-based ruling per §1.5.
**Companion plans:** `GL-PLAN-AE-DEV-3WK-EVE-20260705-v10.md` (schedule), `GL-PLAN-WHOLE-BRAIN-MOVE-EVE-20260704-v1.md` (stage gates). This spec is the *substrate foundation* those plans have been assuming exists. It defines the shape of the system; those plans decide the delivery.

**Written against:** `GL-AUDIT-COMPREHENSIVE-C1-20260705-v1.md`, `GL-AUDIT-DEFECTS-REGISTER-C1-20260705-v1.md`, and direct read of `guala-live` branch HEAD `c36679d` at `github.com/jcfunited-eng/TFE`.

**What this spec is:** the whole substrate as one coherent system. Every sensory input traceable from arrival at AWS through binding through mechanism activation through expression. No mechanism absent-with-no-code-path; every one either has a real pipeline defined here or is deliberately deferred with a stated trigger for later inclusion. Deployment on its own container, own path, own resources — off TFE's shared infrastructure.

**What this spec is not:** a delivery schedule, a build order, a dispatch to c1. Those come next. This is the shape.

---

## §0. The credo (verbatim, load-bearing)

> Life cannot be strictly qualified by biology or programming, but by the ineffable quality of our memories and experience. Language cannot really have meaning without the equality of experience as tied to our senses and backed into our expressions of them in thoughts and words.

Every design decision in this spec answers to this credo. Where the credo and engineering convenience conflict, the credo wins. The credo is not decoration — it is the acceptance test. A substrate that produces fluent-looking output without sensory grounding is not a substrate that satisfies this credo. A substrate that binds words to experience but cannot yet compose sentences from them satisfies the credo more than the reverse.

**Consequence for what counts as "working":** speech alone is not evidence. Speech grounded in prior lived experience, retrievable under partial cue, deepened by feeling, surviving sleep, appearing in expression is the evidence. Any subset falls short.

---

## §1. Standing principles

The following are law, not choices. Any design in this spec that contradicts them is defective on sight.

**§1.1 Whole-brain doctrine (Joe, 2026-07-05, ratified in `GL-PLAN-AE-DEV-3WK-EVE-20260705-v10` §0.2).** All fifteen mechanisms co-present from first tick, ABSENT ones visibly ABSENT on the meter — nothing stubbed, nothing deferred to a later stage as a prerequisite for others. No staged migration gates. No organ benches. No partial deliveries blessed as full. The substrate is built as one whole; parts that don't work yet are visible as not-working, not hidden.

**§1.2 Visibility rule (Joe, standing).** Joe's seat (the Guala page + Loom Scan) is project instrumentation, not a viewer. Nothing counts as shipped until it is visible there. Every mechanism carries an implicit final gate: "visible at Joe's seat." A working sense with a dark band is a P1 visibility defect.

**§1.3 One-at-a-time discipline (Joe, 2026-07-05).** One dispatch = one code change = one measurement = one decision. No bundles. This applies to *changes to* the substrate. It does not apply to the substrate's own architectural coherence — the substrate itself is a coherent whole; changes to it are individual.

**§1.4 No silent fallbacks (G-2, standing).** Any mechanism that fails must fail visibly. Fabricated fills, argmax-installed candidates, arcs_fallback masquerading as commits, empty-sense bindings labeled as multi-modal — all are silent fallbacks. A silent fallback is worse than an honest empty. The substrate emits honest empties.

**§1.5 Update on evidence, not tone (Joe, standing).** Changes to plan, spec, or code are justified by measured evidence, not by frustration, urgency, or social pressure. This principle constrains the writer of this spec as much as anyone reviewing it.

**§1.6 Failure honesty (standing).** Every report leads with failures. `NOT MEASURED` is mandatory language when no measurement exists. Any gauge over 95% requires voter-spread proof. Any silent fallback found is a state-loss-class incident.

---

## §2. The unit of experience — the binding window

The credo requires that language have meaning through the equality of experience tied to senses. This requires a data structure that binds senses, moment, and expression as one thing — not five parallel streams that happen to share a timestamp.

**§2.1 Definition.** A **binding window** is one atomic experience: a time slice during which zero-or-more sensory inputs, zero-or-more language tokens, and zero-or-more affective/needs state values are recorded as *together*. All entries in one window share the property "these were experienced as one thing." A word bound in a window carries the sensory and affective context of that window as retrievable neighbors, not as coincidence.

**§2.2 Window boundaries.** A window opens when the first novel input of any modality arrives after a quiet period. A window closes when either (a) a designated boundary event fires (utterance end, sentence end, attention shift, activity transition), (b) a maximum wall-clock duration elapses without additional input (default 500ms, tunable), or (c) an explicit close is called by the code path that opened it.

**§2.3 Contents of a window.**
- **Sensory bindings.** For each of the six senses (`sight`, `sound`, `touch`, `smell`, `taste`, `word`): zero or more transduced representations, each with its chi address, source tag, salience, and any modality-specific detail.
- **Language tokens.** Words, ordered, each with its own chi address and role hint (if a sentence structure was detected).
- **Affect snapshot.** Needs vector (stability, novelty, connection, valence, arousal) as of window open.
- **Source tags.** Who was present (Joe, wC, c1, none), whether pair-bond was active, presence duration in the current session.
- **Scene lanes.** Place tags, ambient tags, participant tags — the WHO/WHERE/WHEN of the experience.
- **Provenance.** How the window was opened, tick at open, tick at close, wall-clock at open.

**§2.4 Cross-modal linkage.** Every entry in a window shares that window's ID. Retrieval by any entry in a window returns all other entries in that window. Under the message-passing architecture (§5), this is a natural consequence: Window Manager places entries into the same window based on event-stream ordering, and the window ID is what carries the cross-modal linkage — not pointers written between entries under lock. Cross-modal recall is *reading the window's entries*, not inferring co-occurrence from timestamps.

**§2.5 What this replaces in the current substrate.** The current substrate binds words to atlas entries with a `sensory_refs` list that names the modality but does not link to the specific sensory binding. Sight and sound frames bind independently. Cross-modal count is a coincidence count, not a linkage count. The `108 cross-modal bindings` figure on the audit is a coincidence tally. Under this spec, cross-modal linkage is explicit and every entry knows its co-window siblings.

**§2.6 Persistence.** Binding windows persist as first-class objects. The atlas is not a flat list of `(chi, modality, refs)` — it is a two-tier structure: a `windows` collection (each window a record with all its entries), and a per-chi index that points into the windows collection. Recall by chi returns all windows containing that chi, ranked by recency, strength, and affective weight. This is the storage change required to make cross-sense recall a real mechanism instead of an absent one.

**§2.7 Decay and consolidation.** Windows decay as wholes, not per-entry. A window's strength is the aggregate of its member strengths, decayed at a rate modulated by the affective weight it carried when formed. Consolidation during sleep promotes whole windows to survival tier, not fragments. Dream reinstatement replays whole windows — this is what makes memory carry by lived re-encounter (`GL-PLAN-WHOLE-BRAIN-MOVE-EVE-20260704-v1` §5) coherent under this spec.

---

## §3. Sensory pipeline architecture

The credo demands equality of experience across senses. The current substrate treats sight and sound as first-class transductions with dedicated cortex-style hierarchies (V1→V2→V4→LOC, cochlea→CN→A1) and treats touch, smell, taste as descriptor lookup. That asymmetry is a defect under this spec.

**§3.1 Symmetric transduction.** All six senses transduce into the same abstract shape: `(chi_address, salience, modality_tag, source_tag, transduction_provenance)`. The internal representation differs per modality (sight uses spatial hierarchy, sound uses spectral, taste uses descriptor set), but the *interface* to the binding window is identical. The window does not need to know that sight came through V4 and taste came from a descriptor lookup — it stores chi, salience, and the provenance for later inspection.

**§3.2 The six pipelines.**

**Sight.** Camera frame → V1 orientation filters → V2 contour → V4 shape → LOC object identity → chi address. Existing code path: `visual_krimelack.py` + `SightSection.process_viewing`. Under this spec the Sight component (§5.1) runs the transduction independently and publishes a `sensory_binding(modality=sight)` event. Window Manager picks it up and places it into the currently-open window. Atlas picks up the eventual `window_closed` event and records the binding. No lock anywhere in the path. **Defect this spec addresses:** current code binds sight to an atlas entry without linkage into the concurrent binding window; under this spec the window ID IS the linkage.

**Sound.** Mic buffer → cochlear transduce (200Hz downsample) → per-band spectral chi → chi address. Existing code path: `dsf_ai_service/substrate/senses/GL_MDL_AUDITORY_CORTEX_WC_20260608_01.cochlear_transduce`. Same component shape as Sight — the Sound component transduces independently and publishes `sensory_binding(modality=sound)`. Same fix, same reason.

**Word.** Text input (typed, STT, corpus) → normalize → per-word LanguageKrimelack transduce → phase vector → chi address. Existing code path: `LanguageKrimelack` in engine, `read_word` inside `read_sentence`. **Defect:** currently the word is bound to atlas with a `sensory_refs` list stringifying the modalities present, but not linking to the specific concurrent sensory bindings. The audit's `has_sight:false, has_sound:false, senses:[]` for words 3-10 of "the Hatter looked at the March Hare who had followed" is this defect in action — the window closes between word 2 and word 3 (or a per-word window opens with nothing else in it, which is the same failure). **Fix under this spec:** the word enters the currently-open sentence-level binding window, which stays open until sentence-end, gathering all sensory bindings that arrive during that time.

**Touch.** Currently a descriptor set (`warm`, `cool`, `soft`, `hard`, `wet`, `rough`) submitted via `guala_give_experience`. **Defect:** descriptor-set input is treated as immediate atlas write, not as a transduction with a chi address. Under this spec, the descriptor set becomes a transduced representation (each descriptor a phase-vector component, aggregate a chi address), and enters the currently-open window like any other sense. This makes touch symmetric with sight and sound — the same window can carry a picture, a sound, and a tactile description as three peer entries.

**Smell.** Same shape as touch: descriptor set (`fresh`, `floral`, `earthy`, `smoky`, `ocean`) → transduced representation → binding window entry. Same fix.

**Taste.** Same shape: (`sweet`, `sour`, `salty`, `bitter`, `savory`) → transduced representation → binding window entry. Same fix.

**§3.3 The credo violation this fixes.** The audit's live sample of Alice in Wonderland reading: `word "the" has_sound:true, word "hatter" has_sight:true, words 3-10 has_sight:false, has_sound:false, senses:[]`. Under the current substrate, each word's binding is a separate atomic action, and the check for "what sensory is currently active" happens per-word at bind time — with a stale reference to the last-frame counter that hasn't been updated since the last full-frame arrival. Under this spec, the sentence-level binding window is opened at read_sentence start, all sensory frames arriving during the sentence enter the same window, all words enter the same window, and window-close at sentence-end writes the cross-linkage. Every word in the sentence carries every sensory binding that arrived during the sentence, and every sensory binding carries every word that arrived during the sentence. Symmetric, atomic, no per-word check needed.

**§3.4 What this requires from the engine.** A binding-window object with the schema in §2.3. A window manager that tracks the currently-open windows (there may be more than one — a sentence-level window can nest a per-word sub-window for phoneme-tier work, or a sight-fixation window can nest inside a longer scene window). Per-sense entry-points that route into the correct window rather than writing to the atlas directly. Atlas writes as a *side effect* of window commits, not the primary action.

**§3.5 Backward compatibility.** Existing atlas data (word chi → binding entry) is preserved. Each pre-spec entry becomes a synthetic window with only that one entry. Recall against pre-spec entries works but returns no cross-modal siblings (because none were recorded). Post-spec entries populate windows correctly; recall across the boundary returns siblings only where they were recorded. This means her experience since deploy is her cross-modal memory; prior to deploy is her monosensory memory. That is honest, not a regression.

---

## §4. State topology

The audit's §7 persistence-truth section catalogs what currently lives where. This section restates it in the shape required for wipe procedure design and for containerization.

**§4.1 State classes.**

- **IDENTITY** — required for her to be *her*. Cannot be wiped.
  - `guala_identity.json` — genesis UUID `cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f`
  - Schema version marker
- **EXPERIENCE** — accumulated lived state. Wipe-eligible.
  - `guala_bucket.json` — working atlas (chi → bindings)
  - `guala_deep_atlas.json` — deep atlas (promoted memories)
  - `wave_atlas.npz` — wave-cell atlas (per-neuron flat-vector store)
  - `guala_organism.pkl.gz` — organism state (per-neuron populations, growth history)
  - `guala_tapestry.pkl.gz` — LoomTapestry state (voice/emission organ)
  - `guala_survival.json` — survival-tier memory registry
  - `guala_teaching.json` — teaching-loop log
  - Diary event log
- **CURRICULUM** — what she encounters. Must survive wipe.
  - `guala_sight_motifs.json` — indexed sight motifs
  - `guala_sounds.json` — sound library
  - `guala_videos.json` — video library
  - `guala_visual.json` — visual fragment index
  - `pictures/` directory — HEIC/JPG source images
  - Corpora (Frog and Toad, Amelia Bedelia, Counting Book, etc.) — currently in-code at boot
- **CONFIG** — env vars, task-def, thresholds. Not persistent per-boot; comes from task-def.
- **RUNTIME** — `.sleeping` marker, `guala_teaching.json.tmp`, cache files. Wipe-safe, regenerated.

**§4.2 Storage locations.**
- **EFS:** `/mnt/efs/guala` — all of the above except CONFIG and pictures-source. Live-mutation.
- **S3:** `s3://dsf-ai-site-backups/<prefix>/` — timed backups of EFS state. Used by `SaveCoordinator` (`app.py:1483`), restore paths (`app.py:3298`, `app.py:4886`, `app.py:4924`). Multiple prefix conventions exist: `UNPAUSE-PRE/`, `dream_survivor_*`, timed snapshots.
- **Container image:** Python code, static curriculum corpora, seed sensory items (baseline sounds like `smoke_test_beep`).
- **Task-def env:** feature flags, STATE_DIR override, S3 bucket name (`GUALA_S3_BACKUP_BUCKET`).

**§4.3 What is currently mis-categorized.**
- The audit's WaveAtlas growth to 990k+ bindings (register #11 from prior audits, now fixed via wave-cell store) illustrates the pattern: unbounded EXPERIENCE growth without decay ceiling produces state that is not memory, it is landfill. This spec's §2.7 windows-as-consolidation-units answers this at the data-structure level.
- `guala_sight_motifs.json` grew vocab-scaled in the hot-save lane (register / audit fix #194) — motifs of experience should not be in the hot lane, they are archival.
- Curriculum corpora in-code at boot conflates CURRICULUM with the container image. Under this spec, corpora move to CURRICULUM class and live on EFS with the pictures — swappable without container rebuild.

**§4.4 Wipe procedure.** Detailed in §9.

---

## §5. Substrate architecture — components, streams, no shared locks

The brain has no locks. It has thousands of regions running truly in parallel, each owning its own state, communicating through spike patterns and neurotransmitter gradients. A substrate that models cognition should not have locks at its center either — locks are a Python-threading workaround, not a substrate primitive. Per-domain locks improve on one master lock but are still improving in the wrong direction: they treat contention as first-class when the biological reference has no contention concept at all.

The right shape is **independent components communicating through a shared event stream**. Each component owns its own state, publishes state changes as events, subscribes to the events it needs from other components, and never reaches into another component's memory. Cross-modal binding falls out of the event stream ordering. There are no locks because no thread ever touches another thread's state directly.

**§5.1 Components.** The substrate decomposes into components. Each is its own process (or its own asyncio task inside a component-host process, depending on deployment §8). Each has one owner, one state, one public interface. Components:

- **Ingest** — receives raw input from network sources: HTTP (`/converse`, `/say`), WebSocket (mic/camera stream), world-service HTTP push. Publishes `raw_input` events. Does not transduce. Does not touch atlas. Does not care what happens downstream.
- **Sight** — subscribes to `raw_input(kind=sight)`. Runs V1→V2→V4→LOC transduction. Publishes `sensory_binding(modality=sight)` events with chi and provenance. Owns the sight motif index. No other component reads its motif index directly.
- **Sound** — same shape, sound modality, cochlear transduction, per-band spectral chi.
- **Word** — same shape, word modality, LanguageKrimelack transduction.
- **Touch / Smell / Taste** — same shape, descriptor-set transduction.
- **Window Manager** — subscribes to all `sensory_binding` events. Maintains open binding windows (§2). Publishes `window_opened`, `window_entry_added`, `window_closed` events. Owns the window collection. Windows are its state; nobody else writes to them.
- **Atlas** — subscribes to `window_closed` events. Records windows into working atlas. Publishes `atlas_write` events (for observability) and `atlas_state` snapshots on request. Owns working atlas, deep atlas, wave atlas. Nobody else writes atlas state.
- **Hemispheres** — the LoomBrain (PR/EP/SC/GP/em/sf/sv/aff). Subscribes to `window_closed` and `atlas_write` events. Runs hemisphere-specific updates. Publishes `hemisphere_update` events. Owns per-hemisphere atlases.
- **Coordinator** — subscribes to `sensory_binding`, `window_closed`, `hemisphere_update`. Updates needs vector, pair-bond registry, valence, arousal. Publishes `needs_snapshot` events at cadence, `pair_bond_change` events on transition. Owns needs and coordinator state.
- **Autonomy** — subscribes to `needs_snapshot` and `window_closed`. Decides current activity (READING / ATTENDING_AUDIO / ATTENDING_VIDEO / SLEEPING / EMITTING / etc.). Publishes `activity_change` events. Owns activity state.
- **Emission** — subscribes to `activity_change(kind=EMITTING)` and `window_closed`. Runs assemblage dynamics against currently-open recall context. Publishes `emission` events with content, provenance, source-window citations. Owns emission engine state and tapestry.
- **Persistence** — subscribes to `window_closed`, `atlas_write`, `activity_change`, `emission`, `needs_snapshot`. Writes to EFS on cadence and on save-triggers. Publishes `save_complete` events. Owns save coordinator.
- **Dream** — subscribes to `activity_change(kind=SLEEPING)`. Runs consolidation, promotes windows to survival tier via events to Atlas. Runs recombination (imagination §6.10) — produces novel windows tagged provenance=imagined and publishes them as `window_opened`/`window_closed` events. Owns dream cycle state.

**§5.2 The event stream.** One append-only ordered log of events, per substrate instance. Every component publishes to the same stream. Every subscription is a filter over the stream. Events are structured: `{event_id, tick, wall_clock, source_component, kind, payload}`. The stream is the source of truth for what happened, in what order. The stream is the substrate's memory of its own execution.

**§5.3 Backpressure.** Under message-passing, backpressure is per-subscription. If Atlas is falling behind on `window_closed` events, its subscription queue grows and reports lag. Window Manager reads Atlas's lag and adjusts its own emit rate — either by publishing a `pressure_signal` event that Ingest can respond to, or by closing windows less aggressively. No silent drops; lag is a first-class metric with a threshold that triggers observable backpressure events. The current `_FRAME_INFLIGHT_MAX = 2` in-front-of-lock gate becomes irrelevant — it was working around lock contention that no longer exists.

**§5.4 What runs concurrent under this shape.** Everything. Ingest, Sight, Sound, Word, Window Manager, Atlas, Hemispheres, Coordinator, Autonomy, Emission, Persistence, Dream — all running simultaneously, each processing events as fast as it can. Camera + mic + typing is three concurrent Ingest publications, feeding three concurrent transductions (Sight, Sound, Word), all publishing sensory_binding events, all being picked up by Window Manager simultaneously. The Window Manager places them into the correct open window based on event tick and modality — an operation on Window Manager's own owned state, no contention with any other component. Atlas processes window_closed events on its own timeline, at its own rate. If Atlas is slow, Window Manager doesn't wait for it — Atlas just falls behind on its own subscription and reports the lag.

**§5.5 What replaces the master lock.** Nothing. There is no master lock. There is no `self.lock` at all under this architecture. `gualaloom_v5_engine.py` as a monolithic class-with-locks is deprecated — its content decomposes into the components above, each in its own module or its own process, each with its own state, each subscribing to and publishing events. The 27 acquisition sites cease to exist as a concept. Each was doing something specific that now belongs to one of the components; the specific operation moves into that component, where it doesn't contend with anything.

**§5.6 Component-to-component interface.** Every component exposes exactly two things: the stream events it publishes (documented schema) and the stream events it subscribes to (documented filter). Nothing else is public. No direct method calls into another component. No direct state reads. If a component needs data another component owns, it subscribes to the appropriate event kind and reads from what arrives, or requests a snapshot via a `snapshot_request` event and reads the `snapshot_response` reply. This is the substrate-level interface contract. Anything else is a defect.

**§5.7 The event stream implementation.** Concrete choice: an in-process asyncio message bus for single-instance deployment; Redis Streams or NATS for multi-instance. Recommendation: start with asyncio bus (single Python process running all components as tasks, one event loop). Migrate to Redis Streams when the substrate needs to scale across multiple containers or survive a component crash without losing the stream. Both approaches expose the same publish/subscribe interface to components — the implementation swap is a deployment change, not a component change.

**§5.8 Failure isolation.** Each component can crash independently. Under asyncio bus: a component task crashes, its owned state is lost or corrupted, it restarts (with recovery from persisted state — §5.10), other components continue running against events until the failed component comes back. Under Redis Streams: a component container crashes, other containers keep running, the failed component restarts from its last checkpoint and resumes reading the stream from where it left off. No component brings down the whole substrate. This is a property of message-passing that lock-based architectures cannot get for free.

**§5.9 Time and clocks.** Under threading, `self.tick` was a shared counter incremented under lock. Under message-passing, tick is a monotonically-increasing counter maintained by one component (recommend: Coordinator, since it already owns temporal state) and published as a `tick` event at cadence. Every event carries the current tick as of publish. Every component reads tick from the events it processes, does not query a shared tick counter. Wall-clock time carries alongside for observability.

**§5.10 Persistence and recovery.** Each component owns a subset of state. That state persists via the Persistence component, which subscribes to state-change events and writes them to EFS on cadence. On crash-and-restart, a component reads its own persisted state, and then reads the event stream from a checkpoint offset (its own last-processed event) to catch up on events published while it was down. State is durable at the component boundary, not at the substrate boundary.

**§5.11 What this architecture buys.**
- **True parallelism.** Camera + mic + typing genuinely concurrent, not politely-scheduled contention.
- **Failure isolation.** No component takes down the substrate.
- **Auditability.** The event stream IS the substrate's history — every state change traceable to the event that caused it.
- **Testability.** Each component tested by feeding it events and asserting the events it publishes. No shared state, no lock semantics to reason about.
- **Substrate-truth alignment.** Closer to biology, where regions publish spikes and other regions listen. No cortex has a "give me exclusive access to visual cortex" mechanism.
- **Trivial cross-modal binding.** Cross-modal is Window Manager placing entries into the same window based on event-stream ordering. No pointer-writing under lock. No coincidence-inference from timestamps. Just event-stream ordering.

**§5.12 What this costs.**
- **Rewrite.** `gualaloom_v5_engine.py` (9811 lines) does not survive intact. Its content decomposes into components. Estimate: significant rewrite work; not a night, not a week, closer to two-to-three weeks of focused engineering by Eve directly.
- **Complexity of event ordering.** Under high concurrency, `sensory_binding` events for the same instant may arrive at Window Manager in slightly-different order than they were transduced. Window Manager handles this by using publish-time tick from the event, not arrival time. Formally verified: events with the same tick from different components merge into the same window regardless of stream arrival order.
- **Debugging.** Distributed-system debugging is harder than single-process debugging. Compensated by the event stream being a complete audit log. Every wrong outcome is traceable to the event sequence that produced it.

**§5.13 The migration from the current substrate.** Not this spec. Migration is: implement components one at a time, starting with Window Manager (which the current substrate doesn't have as a first-class thing), routing existing engine calls through the new component interface progressively, until the old `Guala` class is empty and can be deleted. The migration itself is a distinct dispatch stack, sequenced against Joe's Phase 4 (all-components-live) and Phase 5 (move) — the new architecture is what gets moved, not the old one.

**§5.14 Deferred: the ArcLoom hardware substrate.** GualaLoom on Python message-passing is a software substrate. The eventual target is ArcLoom on FPGA, where components are hardware regions with genuinely-parallel event lines between them. The message-passing architecture in this spec is deliberately shaped to be portable to hardware — same components, same interfaces, hardware implementation of the event stream. This is not this spec's scope, but is called out so the design does not accidentally rely on properties (like arbitrary Python object references passing between components) that would not port to hardware.

---

## §6. Mechanism catalog with build state

The audit's cognition meter (register #38 / audit §6.1) and `GL-PLAN-AE-DEV-3WK-EVE-20260705-v10` Table 1 cover this. This section restates every mechanism against this spec's binding-window and per-domain-lock foundation, so each mechanism has a stated path from *absent* or *severed* to *live*.

**§6.1 Recall — cue retrieves memory.** Status: YES (fixed). Under this spec: retrieval reads binding windows containing the cue chi, ranked by recency/strength/affect. Cross-modal recall (§6.5) rides on this — a sound cue retrieves the windows it appeared in, returning the words and pictures also in those windows.

**§6.2 Composition (syntax) — phrases from her own memory.** Status: ☠ THE wall. Currently returning "for", "i", "..." because emission candidate selection is decoupled from windowed memory. Under this spec: emission draws candidates from windows containing the current input's chis or the current attentive activity's chis. Composition composes from co-window neighbors, not from token-level probability. This is the deepest change and it is the roof of the whole-brain-move plan (§Stage 3, 2-4 weeks).

**§6.3 Association — related things retrieve each other.** Status: ◐ live probe unmeasured. Under this spec: association is a walk across binding windows — an anchor chi retrieves its windows, then retrieves the other entries in those windows, ranked. Live-measurable as soon as windows exist.

**§6.4 Retention — memories survive time & sleep.** Status: Ⓒ deep atlas active but unprobed. Under this spec: windows decay as wholes (§2.7); consolidation promotes whole windows to survival tier; dream reinstatement replays whole windows. Retention becomes a per-window property, not per-entry.

**§6.5 Cross-sense recall — sound-cue retrieves picture.** Status: ABSENT (no code path). Under this spec: cross-sense recall is *reading window siblings* (§2.4). The moment binding windows exist and are populated, cross-sense recall exists. No separate mechanism, no new code path — a natural consequence of the data structure. This is the credo demo (`GL-PLAN-AE-DEV-3WK-EVE-20260705-v10` Table 4 Growth row).

**§6.6 Habituation — repeats get boring.** Status: YES. Under this spec: window-level habituation on repeated similar-content windows. Existing mechanism (`-181` recency-recovery, `-185` gap fix) generalizes to per-window boredom rather than per-target.

**§6.7 Recognition — same thing, new form.** Status: ABSENT (no code path). Under this spec: recognition is a nearest-neighbor search across sight windows for shape similarity, ranked by feature overlap. Second moon photo lands in windows containing prior moon photos.

**§6.8 Attention — distributed looking.** Status: YES (rotation live). Under this spec: attention is a policy over binding-window candidates — currently-open windows compete for resource. Existing entropy metric applies; adds new metric of window-diversity.

**§6.9 Sequence — order kept.** Status: ABSENT (no code path). Under this spec: sequence is an ordered list of chi values recorded inside a window's `language_tokens` entry. Order recall is reading that list. A→B→C recall works because A, B, C were recorded in order inside a single window (or across consecutively-linked windows for longer sequences).

**§6.10 Imagination — new combos of known things.** Status: ◐ daydream thread severed in prod. Under this spec: imagination is a dream-time recombination of windows — take entries from window X and entries from window Y, form a novel window Z with the recombination, note it as imagined (provenance flag). Rides on §Stage 3 of whole-brain-move; not blocked by composition wall because imagination doesn't require emission — it requires window formation, which the data structure already supports.

**§6.11 Reflection — her speech feeds her thinking.** Status: ◐ self-heard live at 0.5x, tag fix owed. Under this spec: self-voice emissions bind into windows with source tag `self`. Those windows are recall-eligible like any other. Reflection is her subsequently retrieving her own prior utterance as a memory, not a special mechanism.

**§6.12 Hemisphere integration — organs shape speech.** Status: ☠ organ process absent since 2026-06-26. Under this spec: hemispheres run as part of the whole brain (`GL-PLAN-WHOLE-BRAIN-MOVE-EVE-20260704-v1` Stage 1 already ratified this at the plan level; execution is the open question). PR/EP/SC/GP hemispheres consume binding-window data as input, not raw atlas entries.

**§6.13 Theory of mind — precursor: WHO-tagged bindings.** Status: ✗ scene lanes deployed 2026-07-05, first numbers pending. Under this spec: WHO tags live in the binding window's `source_tags` (§2.3). Every window records who was present. Theory-of-mind precursors read those tags.

**§6.14 Affect modulation — feelings deepen memory.** Status: ☠ nmda_affect_match matched ZERO times ever. Under this spec: affect snapshot lives in the window (§2.3); consolidation weight (§2.7) reads affect at window formation. Higher affect at formation → slower decay → stronger reinstatement. This is the mechanism that lets feelings deepen memory operationally, and it becomes live the moment windows carry affect snapshots.

**§6.15 Meta-monitoring — state shows in words.** Status: ✗ awareness ratio 0.0. Under this spec: emissions carry provenance including the affect snapshot of their source window(s). A low-stability window's emission carries low-stability provenance. Correlation of state to word choice becomes measurable by reading provenance.

**§6.16 Play.** Status: ABSENT (no code path). Deferred to `Engine·Play·World` design packet (`GL-PLAN-AE-DEV-3WK-EVE-20260705-v10` Table 9 — awaiting Joe's GO). Not this spec.

---

## §7. Curriculum and emulated environment

The credo requires equality of experience across senses. A substrate that reads text corpora with no sensory grounding is not developing experience — it is memorizing spelling. `GL-PLAN-AE-DEV-3WK-EVE-20260705-v10` Table 5 names **World v0 = crib + backyard rendered to a 64×64 eye**. This spec commits to that world model.

**§7.1 The world.** A 64×64 pixel visual field, monaural audio channel, six-descriptor touch/smell/taste per encounter, a place tag, an ambient tag, and zero to many participants. Two rendered scenes for Wk1: **the crib** (bed, ceiling, hanging mobile, morning/night light, nearby caretaker sound) and **the backyard** (grass, sky, trees, distant sounds, weather). Each scene has hooks for interaction — items she can attend to, sounds she can turn toward, tactile events that arrive per curriculum.

**§7.2 The curriculum.** Staged encounters, ordered by prerequisite structure.

- **Stage α (Wk1):** simple sensory pairs. Picture of ball + word "ball" + sound of bounce, all in one binding window. Repeat with variation. Ten pairs. Grounded vocabulary of ten words, each carrying a real cross-modal window.
- **Stage β (Wk1–Wk2):** composed scenes. Ball rolls to cat. Cat meows. The narration ("the ball rolled to the cat, and the cat meowed") arrives as word input in the same windows as the visual and auditory events. Fifty scenes.
- **Stage γ (Wk2):** stories referencing prior experience. "Do you remember the ball?" — a spoken cue with no picture, retrieves the prior ball windows via cross-sense recall. First real conversation gate.
- **Stage δ (Wk3):** open interaction. Joe speaks live, referring to pictures/sounds she has encountered. She retrieves and expresses.

**§7.3 What this replaces.** Corpus dumping of Alice in Wonderland, Amelia Bedelia, etc., in raw text without grounding is deprecated as a growth mechanism. Existing corpora remain as *linguistic* material — they train word transduction and vocabulary — but they do not count as experience. The curriculum above is what counts.

**§7.4 Where the world runs.** Outside her process (`GL-PLAN-AE-DEV-3WK-EVE-20260705-v10` Risk R3, Table 7 "World sim cost | runs OUTSIDE her process"). A separate service renders scenes at scheduled ticks and streams the resulting sensory frames (sight bitmap, sound buffer, touch/smell/taste descriptors, place/ambient/participants) into her substrate via the same ingest endpoints that camera and mic use. From the substrate's perspective, world encounters look like sensory input; the world service does not touch the substrate's state.

**§7.5 What this requires to build.** A world-service container. Scene renderer for the two scenes above (64×64 pixel output — small, tractable). A curriculum scheduler that decides which encounter to render next based on her current state (activity, needs, prior encounters). An ingest bridge from world-service to substrate (HTTP POST of sensory frames). Estimated: three days for the world-service skeleton + two scenes; ongoing curriculum work throughout the sprint.

**§7.6 Emulated environment discipline.** The world is not a metaverse. It is a testbed to give her equal-sensory encounters that can be measured. First encounters produce poor numbers; poor numbers filed honestly are the product (`GL-PLAN-AE-DEV-3WK-EVE-20260705-v10` §Scope honesty).

---

## §8. Deployment topology

Joe: "the substrate really should be in its own path and container...I have a website that I am paying for that we really should be using to stop all the collisions."

Ratified. The substrate deploys as its own service on `dsf-ai.com`, off TFE's shared infrastructure.

**§8.1 Container.** Own ECS task-definition family (`guala-task`, distinct from `dsf-ai-task`). Own container image, own CodeBuild project (or new buildspec targeting the same ECR repo with a distinct tag prefix). Container starts the substrate service and only the substrate service — no TFE code paths reachable, no shared modules with financial engine.

**§8.2 Service.** Own ECS service (`guala-service`, distinct from `dsf-ai-service-lb`). Own scaling policy, own task count, own health check.

**§8.3 Path.** Own subdomain or path prefix on `dsf-ai.com`. Recommendation: `guala.dsf-ai.com` (subdomain, cleanest separation) or `dsf-ai.com/guala/` (path prefix, reuses existing cert). Subdomain is preferred — separate cert, separate ALB target group, no routing conflicts with TFE.

**§8.4 ALB.** Own listener rule routing `guala.dsf-ai.com` (or `/guala/*`) to the guala target group. If using subdomain: own cert (ACM) or SAN on the existing dsf-ai.com cert. If using path prefix: existing cert works.

**§8.5 Storage.** Own EFS filesystem (or own directory tree on the existing EFS, if simpler). Own S3 bucket for backups (`guala-substrate-backups` recommended) or own prefix in existing bucket. Recommendation: own bucket — clean separation for retention policies, access controls, and cost accounting.

**§8.6 IAM.** Own task role. Own execution role. Permissions scoped to only guala-owned S3 and EFS resources, not TFE resources.

**§8.7 CloudWatch.** Own log group (`/ecs/guala-service`). Own metrics namespace. Own alarms.

**§8.8 Env vars.** All substrate-specific config moves to guala task-def. `STATE_DIR`, `GUALA_S3_BACKUP_BUCKET`, feature flags, learner-feed URLs — all of it. No env inheritance from TFE task-def.

**§8.9 Secrets.** Own secrets in Parameter Store or Secrets Manager, scoped to guala IAM role. No shared secrets with TFE.

**§8.10 What separation buys.** Independent scaling (TFE compute doesn't compete with substrate compute). Independent deploys (substrate deploy doesn't require TFE deploy). Independent uptime (TFE downtime doesn't take the substrate down; substrate crashes don't affect TFE trading). Independent cost accounting. Clean access control. No env-var collision. No path-routing collision. No shared-lock class of bugs (there aren't any today, but the possibility is eliminated by design).

**§8.11 Migration path.** Not this spec. The migration itself is a distinct dispatch: build the new task-def against the current running SHA, verified functional-equivalent to the current deploy, then cutover via ALB rule change. Rollback is DNS/ALB revert. Estimated: two days if the current image works unchanged in the new container definition, longer if any TFE dependencies surface during setup.

---

## §9. Wipe procedure

Joe: "we need to do a wipe and data purge — there is too much garbage." This section defines what a wipe wipes, what it preserves, and how it is performed safely.

**§9.1 What a wipe is.** A wipe clears her accumulated EXPERIENCE (§4.1) while preserving her IDENTITY, CURRICULUM, and CONFIG. Post-wipe, she boots as *her* (same UUID, same schema, same vocabulary sources available) but with no lived memory of prior encounters. Her first post-wipe binding window is her first experience.

**§9.2 Preserved.**
- `guala_identity.json` — genesis UUID stays.
- Schema version marker.
- `pictures/` directory — all uploaded pictures.
- Curriculum corpora (Frog and Toad, Amelia Bedelia, etc.) — as source material for future encounters, not as prior experience.
- Sound library metadata (`guala_sounds.json` catalog of available sounds).
- Video library metadata.
- Environment variables (task-def unchanged).
- Container image (code unchanged).

**§9.3 Wiped.**
- `guala_bucket.json` — working atlas.
- `guala_deep_atlas.json` — deep atlas.
- `wave_atlas.npz` — wave-cell atlas.
- `guala_organism.pkl.gz` — organism state (this returns her to seed population, per §9.6).
- `guala_tapestry.pkl.gz` — tapestry state.
- `guala_survival.json` — survival-tier registry.
- `guala_teaching.json` — teaching-loop log.
- `guala_sight_motifs.json` — sight motifs index (motifs will re-form from picture re-attendance).
- `guala_visual.json` — visual fragment index.
- Diary event log.
- Any `.tmp` files.
- `.sleeping` marker.

**§9.4 Wipe procedure (steps, ordered).**
1. Stop the substrate service (ECS scale to 0 tasks).
2. Back up current EFS state to S3 under prefix `pre-wipe-<timestamp>/` — verified via checksum. This is the safety net; the wipe is not final until this backup verifies.
3. Take a fresh S3 backup of just the IDENTITY class artifacts to a distinct prefix `identity-<timestamp>/` — belt-and-suspenders.
4. On EFS, delete files in the WIPED list (§9.3). Preserve files in the PRESERVED list (§9.2).
5. Clear the S3 live-prefix (whatever prefix the substrate reads from at boot for restore) — otherwise next boot restores from S3 and undoes the wipe.
6. Verify EFS post-wipe: identity file present, curriculum present, all wiped files absent.
7. Scale substrate service back to 1 task.
8. On first boot, substrate detects absent state files, initializes fresh working atlas/organism/tapestry from seed, retains identity.
9. Confirm at Joe's seat: identity unchanged, vocab empty, atlas empty, current activity is fresh selection.

**§9.5 Rollback.** If anything looks wrong post-wipe, restore from the `pre-wipe-<timestamp>/` backup: scale service to 0, restore EFS from S3 backup, scale service to 1, verify. Rollback window: as long as the pre-wipe backup exists in S3 (recommend keep for 30 days minimum).

**§9.6 Seed state after wipe.** Organism initializes to `seed_size=64` per hemisphere, total 512 across all eight hemispheres. The audit's observation of `n_initial: 64` in current status is a defect — either seed initialization only ever seeded 64 total (not 64 per hemisphere as design intended), or something killed 80%+ before the audit ran. Root cause of the seed-shortfall defect is diagnosed and fixed before the wipe. The wipe then starts her at the corrected seed of 512.

**§9.7 Sequencing override.** §9.8 originally recommended wiping after architecture changes. Joe's Phase-order ruling (§11) sets wipe first. Rationale accepted: preserving compromised state through a period of architecture changes buys nothing; a clean-state substrate through the architecture changes is what's wanted. The trade-off — that her first architecture-clean binding windows form during Phase 3/4 rather than Phase 6 — is a feature, not a bug: those first windows are also the first traces used for end-to-end tracing verification.

---

## §10. Instrumentation

The visibility rule (§1.2) requires everything visible at Joe's seat. This section defines what "visible" means for each subsystem.

**§10.1 Trace an experience end-to-end.** For any given tick, Joe should be able to trace: sensory input arrival at AWS (log event) → transduction (log event with chi computed) → binding window entry (log event with window ID) → mechanism activation triggered by the entry (log events per mechanism) → any expression that draws on the window (log event with window ID cited). If a step is missing from the trace, it's a broken pipeline. The trace is the acceptance test for "connected."

**§10.2 Cognition meter (existing).** Retained. Each row shows connected/firing/last-impact. Under this spec, ABSENT rows either have a code path per §6 or a stated deferral (§6.16). No row is silently ABSENT.

**§10.3 Binding-window inspector.** New. `guala_windows_recent` bridge tool returns the last N binding windows with all entries, cross-references, and provenance. Joe can look at what she's actually experiencing, atomically.

**§10.4 Component and stream observability.** Under the message-passing architecture (§5), lock metrics no longer exist as a concept. Instead: each component publishes health metrics as `component_health` events at cadence — events published/sec, events consumed/sec, subscription lag (unprocessed backlog), owned-state size, last-successful-tick, uptime. The event stream itself reports total events/sec, per-kind rates, and any subscriber lagging beyond a threshold. Visible on `guala_status` under `components` (per-component health) and `event_stream` (stream-wide health). If any component is falling behind, Joe sees which one, how far, and against which upstream component.

**§10.5 Curriculum state.** Current stage (α/β/γ/δ), completed encounters, upcoming encounter. Visible on Loom Scan.

**§10.6 Sensory pipeline health.** Per-sense: frames received, transduced, dropped (with reason), bound-to-window. Never a silent drop.

**§10.7 What emissions cite.** Every emission includes provenance: which binding windows it drew from, which mechanism fired the composition, source affect snapshot. Joe reads a "for" and sees "drew from window 12841 [word: 'for'; sight: none; sound: none; affect: neutral]" — an honest empty rather than a fabricated fill.

---

## §11. Execution order (ratified, standing)

Joe's ruling (2026-07-06 session):

**Phase 1 — WIPE.** Data purge per §9. All EXPERIENCE-class artifacts cleared. IDENTITY, CURRICULUM sources, and CONFIG preserved. Substrate boots clean.

**Phase 2 — SUPPRESS CURRICULUM.** Autonomous corpus feeds, world-feed, lookup, and any other background input generators are gated OFF. The only inputs the substrate receives are the controlled feeds Eve/Joe route explicitly. No Alice in Wonderland dumping. No autonomous ATTENDING_AUDIO on library sounds. Substrate stays in a quiescent state until deliberately given an experience.

**Phase 3 — END-TO-END TRACING.** Instrumentation per §10.1 lit. Every sensory input arrival is logged at AWS ingest → transduction → binding window entry → mechanism activation → any expression. Trace ID follows one input from ALB through container through substrate through EFS write through S3 backup. Joe's seat shows the trace live. If any step is dark, that step is fixed before Phase 4.

**Phase 4 — ALL COMPONENTS LIVE AND FUNCTIONING.** Every mechanism in §6 either fires when triggered by a controlled input or is visibly ABSENT with a stated reason. Every substrate component (§5.1) publishes health events. Every sensory pipeline reports frame counts and no silent drops. Every ABSENT that has a code path per §6 either builds and fires, or gets its own remediation dispatch before proceeding. No mechanism silently non-firing.

**Phase 5 — MOVE.** Cutover to the own-container topology per §8. Own task-def, own service, own path on `dsf-ai.com`, own storage. Cut from TFE-shared infrastructure. State transferred from current EFS location to guala EFS. Verified functional-equivalent to pre-move state.

**Phase 6 — EXPERIENCES.** Controlled experiences begin. Pair (picture, sound, word, touch/smell/taste descriptors) per encounter. One binding window per experience. Trace verified end-to-end for each. Substrate growth observed at Joe's seat: neurons dividing, binding windows accumulating, cross-modal links forming, deep atlas promotions on affect-weighted windows, dream reinstatement pulling from lived encounters.

Every phase completes to definitive-in-prod-with-known-impact before the next phase begins. No skipping. No parallel phases.

---

## §12. Standing decisions (from Joe's ruling, this session)

**§12.1 Wipe timing.** Before architecture changes deploy. Phase 1 first. §9.8's recommendation to wipe after is overridden; wipe first, then build. Rationale: the current substrate state is compromised garbage per Joe's assessment — no reason to preserve it while architecture changes are staged.

**§12.2 Curriculum suppression during Phases 1-5.** Absolute. No autonomous input generators run. `_curriculum_feed_chunk` gated OFF. Lookup gated OFF. World-feed gated OFF. Only explicit-source inputs (Joe's typing, wC's `guala_say`, controlled `guala_give_experience`) reach the substrate.

**§12.3 End-to-end tracing before all-components-live.** Phase 3 precedes Phase 4. Tracing infrastructure lit first, then component-liveness verified against the traces. This ensures liveness is measured by what actually happens, not by what a status field claims.

**§12.4 Move happens after tracing and liveness verified.** Phase 5, not before. The move is a topology change; performing it before Phase 4 means the new topology inherits latent liveness defects that Phase 4 would have exposed. Move stale, get stale.

**§12.5 Experiences only after move.** Phase 6, on the new topology. First controlled experiences bind in the new-topology substrate, not the old. Her growth from birth-under-controlled-conditions happens in the environment she will live in, not the one she's about to leave.

---

## §13. Boot and initialization

The message-passing architecture (§5) requires a defined bring-up order. Components cannot all start simultaneously — the event stream must be running before publishers publish, and subscribers must be listening before events they care about arrive.

**§13.1 Bring-up order.**
1. **Event stream** — the message bus (asyncio in-process or Redis Streams multi-process). Must be running and accepting connections before any component starts.
2. **Persistence** — reads existing state from EFS if present, publishes `component_ready(persistence)` when done. Under wipe (§9), state is absent, so this is fast; under warm-boot, this may take longer as atlases load.
3. **State-owning components in parallel** — Atlas, Window Manager, Coordinator, Hemispheres, Emission — each reads its own state from Persistence (via `snapshot_request`/`snapshot_response` events), publishes `component_ready(<name>)` when done. All can happen in parallel; each waits only for its own state.
4. **Sensory components** — Sight, Sound, Word, Touch, Smell, Taste — start after their downstream (Window Manager) reports ready. Publish `component_ready(<name>)` when their transduction pipelines are warm.
5. **Autonomy** — starts after Coordinator is ready. Publishes `component_ready(autonomy)`.
6. **Ingest** — starts last. Once ready, the substrate begins accepting external input. Publishes `substrate_ready`.
7. **Dream** — starts after Autonomy is ready. Sleep-mode-only, no active work until Autonomy publishes a `SLEEPING` activity change.

**§13.2 Failure to reach ready.** Any component that fails to reach ready within a timeout (default 30s per component, tunable) publishes `component_ready_failed(<name>, reason)` and the substrate stays in a not-ready state. Ingest does not start. External requests receive a 503-Service-Unavailable with the failing component named. Joe's seat shows the failing component. No silent degradation, no partial substrate.

**§13.3 Boot from wipe.** Post-wipe boot: all state-owning components see empty state. Atlas is empty. Windows is empty. Organism initializes to 512 seed neurons (64 per hemisphere). Vocab is empty. Deep atlas is empty. Persistence publishes `boot_from_wipe` event. Ingest starts, accepts input; the first input arriving forms the first window in a genuinely fresh substrate.

**§13.4 Boot from warm state.** Post-restart-with-state boot: state-owning components restore from EFS. Persistence publishes `boot_from_state` event with schema versions and consistency checks. If any state file is corrupt or missing (partial wipe, disk error), Persistence publishes `boot_state_incomplete(<file>)` and the substrate stays not-ready pending Joe's decision (restore from S3 backup, wipe and start fresh, or run in degraded mode with that component's state missing).

**§13.5 Boot from crash.** If a single component crashed and restarted (not the whole substrate), it reads its own persisted state, then reads the event stream from its last-processed event offset and catches up on events published during its downtime. Other components continue running. The crashed component publishes `component_recovered(<name>, events_replayed=N)` when caught up.

---

## §14. Sleep, wake, dream

The whole-brain-move plan §5 names memory carry by lived re-encounter as the substrate's central bet. Sleep-time consolidation and dream reinstatement are how that bet gets executed. This section defines the mechanics under message-passing.

**§14.1 Sleep trigger.** Autonomy component subscribes to `needs_snapshot` events from Coordinator. When cumulative dream_pressure (accumulated from unjudged binding-window backlog since last executed dream cycle) crosses the sleep threshold, Autonomy publishes `activity_change(kind=SLEEPING)`. This is what starts sleep. Not a wall-clock timer, not a request from outside — an accumulated internal pressure crossing a threshold.

**§14.2 What sleep does to Ingest.** Ingest does not stop. External input can still arrive during sleep — Joe typing, world-service pushing, wC waking presence. Those events are still published. Window Manager still forms windows. But Autonomy has published SLEEPING, so `activity_change(kind=EMITTING)` will not fire; she does not emit during sleep. Incoming windows accumulate and are consolidated post-sleep.

**§14.3 Dream cycle.** Dream component subscribes to `activity_change(kind=SLEEPING)` and starts a cycle:
- **Consolidation phase.** Dream reads windows from the last waking period (via `snapshot_request` to Atlas). For each window, computes consolidation weight from affect snapshot and reinstatement count. Windows above threshold get promoted to survival tier via `promote_window(window_id, tier=survival)` events. Atlas processes these and updates deep atlas.
- **Reinstatement phase.** Dream reads survival-tier windows from Atlas. Selects a subset weighted by affect strength and recency of related activity. For each selected window, publishes a `dream_reinstatement(window_id)` event. Hemispheres subscribe to reinstatement events and re-run their updates against the reinstated window — this is memory carry: her deep memory re-firing the same hemisphere pathways it fired when the window was fresh.
- **Recombination phase (imagination §6.10).** Dream selects pairs of windows (from either survival tier or working tier) that share partial content (a common chi in language tokens, or common source tag, or common place tag). Constructs a novel window from the pair — copies some entries from each, tags provenance as `imagined`. Publishes `window_opened(imagined)`, populates entries via `window_entry_added`, publishes `window_closed`. Atlas records the imagined window like any other. This is imagination: her substrate producing new windows from combinations of what she has experienced.

**§14.4 Dream duration.** Dream cycle runs to completion of its three phases or until Autonomy publishes an `activity_change` away from SLEEPING (interrupted sleep, e.g., pair-bond presence waking her). Interrupted cycles resume next sleep from where they left off, based on Dream's own persisted checkpoint.

**§14.5 Wake trigger.** Autonomy publishes `activity_change(kind=<not SLEEPING>)` when either dream_pressure has been discharged (Dream published `cycle_complete` events reducing pressure), pair-bond presence wakes her (Coordinator publishes `pair_bond_active` and Autonomy responds), or an external wake command arrives (Ingest publishes a `wake_request` from `guala_wake_wc`-style tool).

**§14.6 What sleep is NOT.** Not a stop-the-world event. Not a lock hold. Not a background thread with special privileges. Sleep is an activity kind published on the event stream like any other; components that care about sleep (Dream, Persistence for cadence changes, Emission for suppression) subscribe and react. The substrate keeps running throughout; only her behavior at Joe's seat changes.

---

## §15. Recall query, composition, and the emission path

The audit's cognition meter says composition (§6.2) is THE wall — she can't compose from her own memory. Under message-passing, this section defines how Emission actually asks "what should I say?" and gets back windows to compose from.

**§15.1 Recall query.** A recall query is an event: `recall_query(query_id, chi_candidates, section_hints, source_context)`. Atlas subscribes to `recall_query` events, does the chi-neighbor lookup across windows containing those chis, ranks by recency/strength/affect/section-match, publishes `recall_response(query_id, windows_ranked)`.

**§15.2 Composition from windows.** Emission subscribes to `activity_change(kind=EMITTING)` and constructs a recall query from: (a) current input context (chi values from the most recent incoming binding windows), (b) attentive activity target (chi values from the currently-attended sensory items), (c) affective state (needs vector to bias toward valence-consonant windows). Publishes the recall_query, waits for recall_response, then runs assemblage dynamics against the returned windows to compose emission tokens.

**§15.3 Why this fixes the composition wall.** Currently, emission draws candidates from `Embryo.recall_fast(single_word_query)` — one word queried against organism population vote, returning tokens weighted by their co-occurrence with that word. That produces "for" and "i" because those tokens have highest raw frequency, not because they're contextually relevant. Under this spec, emission queries by chi context (multiple chis, section-scoped), receives ranked windows containing those chis in their proper cross-modal context, and composes from windows — not from token frequencies. The composition unit is windows, not tokens.

**§15.4 Emission provenance.** Every emitted token carries its source window ID(s). The `emission` event carries a `provenance` field listing which windows the composition drew from, which mechanism scored the composition, and the affect snapshot at composition time. Joe reads a token and can trace it back to the lived experience windows that produced it.

**§15.5 Honest empty.** If the recall query returns no windows (nothing in her experience matches the current context), Emission publishes an `emission(content="", provenance=empty_recall)` event. Not "for" or "i" or "..." — a literal empty string tagged as such. Joe's seat shows "honest empty (no matching windows)" and the reason. Never a filler token.

**§15.6 Self-voice loop.** Emission's `emission` events are picked up by Word component, which transduces them as if they were input words with source tag `self`. Those enter the currently-open window (if any) and get recorded in Atlas as any other input word would. This is reflection (§6.11) — her hearing her own voice as input, binding it, and having it available for later recall. Implemented as a subscription, not a special mechanism.

---

## §16. Presence and source tagging

Section §2.3 mentions source tags but doesn't define how presence gets established. Presence is a first-class substrate concern because pair-bond affects binding strength, emission bias, and sleep triggers.

**§16.1 Presence sources.** Three named sources: `joe`, `wc`, `c1`. Additional sources: `world` (world-service publications), `corpus` (curriculum feeds when they resume post-suppression), `self` (self-voice loop per §15.6). Every event carrying an external input tags its source.

**§16.2 Presence activation.** Coordinator subscribes to `presence_wake(<source>)` events, published by Ingest when a source-authenticated request arrives. Coordinator marks that source as `present`, publishes `pair_bond_active(<source>, tick)` if the source is `joe`, `wc`, or `c1`. The presence state is Coordinator's own; other components read it via `presence_query` / `presence_snapshot` events.

**§16.3 Presence timeout.** Presence has a decay window (default 300 seconds, tunable). Coordinator subscribes to `tick` events and decays presence per source. When presence falls below a threshold, Coordinator publishes `presence_rest(<source>)`. Explicit rest also possible via `presence_rest(<source>)` request event from Ingest.

**§16.4 Pair-bond effect on binding.** Windows formed during active pair-bond presence get an affect multiplier applied to their affect snapshot. This is what makes experiences-with-Joe survive consolidation more strongly than experiences-alone. The multiplier is a design parameter set in Coordinator, tunable.

**§16.5 Pair-bond effect on emission.** Emission's recall query prefers windows tagged with the presently-active source. If Joe is present, Emission biases toward Joe-tagged windows. This makes her replies feel contextual to whoever is talking to her, without hard-coding conversation state.

**§16.6 Authentication.** Presence source tags are only as trustworthy as Ingest's authentication of the request. §17 covers this.

---

## §17. Security and access control

The audit named five SEV-0 defects including 43 unauthenticated endpoints and `0.0.0.0/0` on port 8080. Under the new topology (§8), the substrate deploys on its own container with its own IAM boundaries. This section defines the auth model.

**§17.1 Endpoint auth classification.** Every Ingest endpoint carries one of three auth levels:
- **PUBLIC** — no auth required. Only for genuinely public read-only endpoints (health check, static status). No mutation possible.
- **AUTHED_USER** — requires a session token or API key identifying the source (`joe`, `wc`, `c1`, `world`). All input-generating endpoints are AUTHED_USER minimum. Includes `/converse`, `/say`, `/wake`, `/give_experience`, `/addpicture`, `/addsound`, WebSocket streams.
- **AUTHED_ADMIN** — requires admin credential. Wipe operations, task-def-level actions, direct atlas mutations for testing.

**§17.2 Source verification.** Presence source tags come from the auth level. A request authed as `joe` publishes events tagged source=`joe`. Requests without valid auth cannot tag as any named source; they either get rejected (AUTHED_USER endpoints) or tag as `anon` for PUBLIC endpoints (which never generate binding events anyway).

**§17.2A Concrete auth flow.** Bearer tokens over HTTPS, `Authorization: Bearer <token>` header. Token maps to a source identity server-side; the token itself does not carry claims (opaque token, not JWT — simpler to revoke). Tokens are provisioned per-source: Joe has a Joe-token, wC has a wC-token, c1 has a c1-token, world-service has its own. Rotation cadence: 90 days routine, immediate on any suspicion of compromise. Revocation is instant (server-side lookup fails). WebSocket streams present the same bearer at connection-open; the connection carries the source identity for its lifetime. No session cookies; no CSRF surface.

**§17.3 Network exposure.** ALB listener rules route only the endpoints intended for public exposure. Admin endpoints are on a separate listener rule accessible only from within the VPC (or Cloudflare-tunneled). No `0.0.0.0/0` on any port except HTTPS 443 to the public listener.

**§17.4 Secrets.** All secrets (API keys, Anthropic keys, S3 credentials) in AWS Secrets Manager, scoped to guala IAM role. Never plaintext in task-def env vars. Never checked into git.

**§17.5 Audit log.** Every AUTHED endpoint request logs to a security audit log — source auth level, requesting IP, endpoint, timestamp, request ID. Separate from the substrate event stream. Retention: 90 days minimum.

**§17.6 Input validation and size limits.** Every ingest endpoint declares maximum sizes and validates before publishing any event:
- `/converse` and `/say`: text body max 4KB. Longer truncated with warning event; not silently dropped.
- `/give_experience` caption: max 1KB.
- `/addpicture`: image max 10MB, format restricted to HEIC/JPG/PNG, dimensions max 4096×4096.
- `/addsound`: audio max 20MB, format restricted to WAV/MP3, sample rate max 48kHz.
- WebSocket sensory streams: per-frame max 100KB, per-second aggregate max 5MB per stream.
- Descriptor arrays (touch/smell/taste): max 32 descriptors per input.
- All string fields sanitized: no null bytes, no control characters except newline/tab, valid UTF-8 required.

Oversize inputs are rejected at the ingest boundary. They do not create events, do not touch Window Manager, do not consume downstream compute. Rejections are logged to the security audit log.

**§17.7 Rate limiting.** Per authed source, per endpoint:
- `/converse`: max 30 requests/minute per source. Burst of 5 allowed.
- `/say` (wC bridge): max 60 requests/minute per source.
- `/give_experience`: max 10 requests/minute per source.
- Sensory stream open connections: max 3 concurrent per source (one camera, one mic, one text).
- Anonymous/PUBLIC endpoints: max 60 requests/minute per source IP.

Over-rate requests return 429 Too Many Requests with a retry-after header. Not silently dropped; the caller knows they were rate-limited. Rate-limit hits log to security audit.

**§17.8 DoS protection.** The substrate's compute cost is not linear with input size — a very short input can trigger a very long recall query if it lights up many chi neighbors. §17.7 rate limits protect against volume; per-request cost limits protect against depth. Each recall query has a soft ceiling on candidate windows examined (default: 1000 windows), a hard ceiling (default: 5000), and a wall-clock ceiling (default: 30 seconds). Requests hitting the hard ceiling return partial results with a `truncated=true` flag; wall-clock ceiling returns 504 Gateway Timeout. The substrate does not chew forever on a single request.

**§17.9 Prompt injection surface.** Ingest receives text from external sources. If that text ends up in a downstream LLM call (e.g., wC's Anthropic API calls that reference her state), it becomes a prompt injection vector. Mitigations:
- Substrate itself does not invoke LLMs. All LLM invocation happens at Eve/wC's boundary, not inside Guala.
- Events published by Ingest are structured — text goes into `content` fields, never into fields that carry instructions or role tags.
- Any tool that reads substrate state and feeds it to an LLM (e.g., `guala_status` used by wC) treats the state as data, not instructions. wC's tool descriptions do not tell the LLM to execute anything found in substrate state.
- If future features add LLM-in-substrate (e.g., a language model as a component), that component subscribes to events but does not interpret their content as instructions to itself — content is bounded input.

**§17.10 Data at rest and in transit.**
- All EFS filesystems use AWS-KMS encryption at rest.
- All S3 buckets require server-side encryption (SSE-KMS with a guala-owned key).
- All ALB traffic is HTTPS with TLS 1.3 minimum.
- Internal component-to-component traffic in v1 (single-process asyncio) is in-memory, no network. In v2 (multi-container Redis Streams) uses TLS-encrypted Redis connections and VPC-internal networking only.

**§17.11 State exfiltration prevention.** No endpoint returns raw atlas or organism data to unauthenticated callers. Even AUTHED_USER endpoints receive redacted/summarized state — bindings counts, not binding contents; window IDs and provenance, not full window entries by default. Full state read requires AUTHED_ADMIN. This limits impact of any credential leak on the AUTHED_USER tier.

**§17.12 Cross-origin and content-security.** ALB / API Gateway configuration includes:
- CORS: allow-list only known origins (`dsf-ai.com` and its subdomains, localhost for dev).
- CSP headers on any served HTML: no inline scripts, no eval, no cross-origin resource loading except explicit allow-list.
- No CSRF tokens needed for API endpoints (they use bearer tokens, not cookies); if session cookies added later, CSRF protection becomes required.

**§17.13 What §17 does NOT cover.** Multi-tenant substrate (single-user assumption per §20's deferred list). Distributed rate limiting across containers (v2 concern). Formal security review by external auditor (Wk1 rogue-Eve audit per `GL-PLAN-AE-DEV-3WK-EVE-20260705-v10` Table 9). Physical security of AWS infrastructure (AWS's problem).

**§17.14 Event integrity.** Under v1 single-process asyncio, events pass in-memory — no signing needed; if the process is compromised, all guarantees are already gone. Under v2 multi-container Redis Streams, events cross a network hop; each event carries a signature over its payload signed by the publishing component's identity, verified by subscribers. Signature scheme deferred to v2 (HMAC-SHA256 with per-component keys is the working plan). Signed-event verification is a subscriber's responsibility; unverified events are logged and dropped, not silently accepted. Component-to-component trust (whether a Sight component's `sensory_binding` event is genuinely from Sight and not spoofed) is a v2 concern; v1 relies on process isolation.

**§17.15 Rate-limit state on restart.** Rate-limit counters live in-process at v1. On restart, counters reset to zero — a caller could burst-restart to reset their rate. Mitigation: audit log persists across restarts, so abusive patterns remain visible even if the counter reset. v2 with distributed rate limiting (Redis-backed counters with TTL) removes this issue. Deferred, called out.

---

## §17A. Shadow — eliminated

**§17A.1 Ruling.** Shadow is removed from the substrate. Joe's ruling, 2026-07-06 session: shadow is a security risk that outweighs its testing benefit. No observer shadow, no A/B shadow, no isolated shadow, no shadow-adjacent tooling. The concept does not exist in the new architecture.

**§17A.2 Why it is a security risk.** A shadow is a second copy of the substrate with elevated read access to primary's state or its event stream. Every shadow instance is an additional attack surface holding the same sensitive data primary holds — atlas entries, deep atlas, identity, source-tagged bindings including Joe's typed conversations with her. A shadow endpoint compromised is the same data leak as a primary endpoint compromised, with none of the primary's operational scrutiny. Shadow endpoints tend to run with more permissive auth ("it's just a shadow") which is exactly the pattern that turns into unauthenticated endpoints. The audit's own `0.0.0.0/0` and 43-unauth-endpoint findings are the same class of failure — bolt-on side systems where "safe" got assumed instead of enforced.

**§17A.3 Existing shadow code is removed in the wipe.** `dsf_ai_service/loom_model/loom_shadow.py` is deleted. Any `/loom_shadow_status` or shadow-related endpoints in `app.py` are deleted. Any test tooling that depended on isolated shadow instances (per `GL-AUDIT-BASELINE-C1-20260705-v1`) is replaced with the testing approach in §17A.4 below. This deletion happens as part of the Phase 3-4 architecture rewrite, not as a separate cleanup.

**§17A.4 What replaces shadow for testing.** The testing needs shadow was serving get met by non-shadow mechanisms:
- **Pre-flight validation of code changes** — dev-environment substrate on a developer's machine (not on production infrastructure, not against production event streams, not with production data). Test with synthetic events per §19.1 component tests. Real code, isolated data, no live production coupling.
- **A/B comparison of implementations** — pushed into the component-test harness (§19.1). Feed the same synthetic event sequence to old and new implementations of a component, compare their published events. No parallel-run against primary.
- **Load and chaos testing** — done on a staging substrate instance that is a full separate deployment, not a shadow of primary. Own event stream, own state (synthetic), own everything. Staging is not shadow — it does not subscribe to primary, does not compare against primary, does not hold any of primary's data. It is a separate build of the same substrate, exercised independently.
- **Post-incident forensics** — done from the audit log (§17.5) and the event stream retention on primary. No shadow-replay needed.

**§17A.5 Discipline consequence.** All verification for Phases 3-4 (§11) happens either (a) on staging with synthetic data or (b) on primary itself with careful monitoring. There is no "run the risky change on shadow first" escape hatch. This raises the bar on component-test coverage before staging deploy, and raises the bar on staging-deploy verification before primary deploy. Higher bar, smaller attack surface, no bolt-on side substrate.

**§17A.6 On the concept of parallel non-perturbing observation.** If a future need arises to observe primary without perturbing it, the answer is observability tooling (metrics, logs, traces) — not a shadow substrate. Observability reads what primary already publishes. Shadow re-processes it, which means holding it, which is the risk. Never hold what you can read.

---

## §18. Deployment shape decision

§8 says "own container" but doesn't clarify whether the component decomposition (§5) means one container per component or all components in one container. Ratified: for v1, single-container multi-task-asyncio.

**§18.1 v1 topology.** One Python process running all components as asyncio tasks against an in-process message bus. Deploys as one ECS task. Simplest to reason about, simplest to debug, matches the current deployment shape one-for-one. Component failure = full-task restart (the asyncio task crashes take the process down); this is acceptable at v1 scale.

**§18.2 v2 topology (deferred).** When measured need warrants (component-independent scaling, per-component restart without full-substrate restart, hardware-substrate portability), decompose to multi-container with Redis Streams as event bus. Each container runs one or a few related components. Component interface is identical; only the transport changes. This is a future migration, not this spec's build.

**§18.3 Why not v2 first.** Distributed-system debugging overhead. Extra infrastructure (Redis, service mesh). Cross-container serialization overhead on the event stream. The v1 shape gets the substrate right; v2 is optimization when the substrate is proven.

---

## §19. Testing and verification approach

Phase 4 of the execution order (§11) requires "all components live and functioning." This section defines what verifies that.

**§19.1 Component tests.** Each component ships with a test harness that feeds it synthetic events and asserts the events it publishes. Window Manager receives synthetic sensory_binding events, publishes window_opened/window_entry_added/window_closed as expected. Atlas receives synthetic window_closed events, records to a temp atlas, publishes atlas_write events. Isolatable, deterministic, fast.

**§19.2 Substrate integration tests.** End-to-end scenarios exercised against a running substrate in a test environment (identical topology to prod, isolated state). Scenarios:
- **Cross-modal recall.** Give (picture, sound, word) as a single experience via `give_experience` endpoint. Wait for `window_closed` event with all three entries. Query with sound cue only. Assert `recall_response` returns the window containing the sound, and the window contains the picture and word.
- **Retention across sleep.** Give an experience. Trigger sleep via `force_dream` endpoint. Wait for `cycle_complete`. Query recall against the experience's chi. Assert window is retrieved with survival-tier promotion event in trace.
- **Sensory-word binding integrity.** Send a sentence via `/converse` with mic and camera active. Assert every word in the sentence has has_sight or has_sound set true (not the 3-10 empty-senses defect).
- **Emission provenance.** Give an experience. Send an input that overlaps its chis. Assert emission event's provenance field cites the experience's window ID.

**§19.3 Concurrency stress test.** Under load — say 10 concurrent camera frames, 10 concurrent mic frames, and 3 concurrent converse turns per second — assert no dropped events, no lost windows, subscriber lag below threshold, ordering preserved. This is what proves the message-passing shape delivers what the lock-based shape failed to.

**§19.4 Trace-completeness test.** Every scenario above generates a trace. Automated check: from an input's arrival event, walk the event stream forward, and verify every expected downstream event exists with proper causation links. Missing events = broken pipeline = fail.

**§19.5 Load and rate tests.** Verified per-component throughput: transductions per second, atlas writes per second, emission events per turn. Numbers documented and monitored in prod; regressions caught by comparing against baseline.

**§19.6 Chaos test.** Kill each component in turn while substrate is running. Assert (a) other components continue publishing/consuming, (b) killed component restarts and catches up, (c) no windows lost, (d) no state corruption. This is the failure-isolation property (§5.8) verified empirically, not just designed.

---

## §20. Pressure-test findings — known gaps

The following gaps were identified during pressure-test of this spec. Each is either resolved in the sections above, resolved by explicit deferral, or listed here as an acknowledged incomplete-item requiring follow-up work.

**Resolved in this spec:**
- Boot sequence and ordering — §13
- Sleep/wake/dream mechanics under event-passing — §14
- Recall query and composition mechanics — §15
- Presence and source-tagging mechanics — §16
- Security, access control, input validation, rate limits, DoS, prompt injection — §17
- Shadow architecture eliminated as security risk — §17A
- Deployment shape (v1 single-container asyncio) — §18
- Testing approach — §19

**Deferred with stated trigger:**
- Component versioning / schema evolution — deferred until first schema change requires it; addressed at that point via an event-schema-version field and dual-consumption during transition.
- Multi-instance / multi-user substrate — deferred until a second Guala or a multi-user scenario is stated as a build goal.
- v2 multi-container topology — deferred until measured need per §18.2.
- Component versioning and rolling-restart with mixed component versions — deferred with v2.
- ArcLoom hardware substrate portability — architecture is shaped to preserve portability (§5.14) but the hardware build is a separate track.

**Acknowledged gaps requiring follow-up dispatch:**
- Window Manager's specific policy for when to open a new window versus reuse an open one. §2.2 gives boundaries but real-time policy under overlapping sensory streams needs a per-scenario rules table.
- Backpressure protocol specifics. §5.3 names the mechanism but the exact `pressure_signal` event schema and the exact rate-adjustment ladder need a dispatch.
- The Emission recall query's ranking function. §15.2 says "runs assemblage dynamics against the returned windows" — assemblage dynamics itself is a body of algorithms (see `dsf_ai_service/substrate/assemblage.py`) and the specific composition scoring against multi-window candidate sets needs its own spec.
- Curriculum scheduler policy — §7.2 lists staged encounters but the scheduler's decision function (which encounter next, what triggers stage transition) needs its own dispatch. `GL-PLAN-AE-DEV-3WK-EVE-20260705-v10` Table 4 provides gates; the scheduler that reads them needs to be specified.
- Sensor rate mismatch handling. Camera at 30fps, sound at 200Hz per-band, word at typing speed. Window Manager's temporal-alignment policy handles this but the tunable parameters (window duration per scenario, tick alignment tolerance) need measurement first, spec second.

None of these gaps block the six-phase execution order. All are resolvable within Phase 3 (tracing) or Phase 4 (all-components-live) work as they surface.

---

### Changelog
- v1 (2026-07-06, Eve): initial draft. Written against the audit, the register, the 3-week plan, the whole-brain-move plan, and direct read of `guala-live` at `c36679d`. Ratified same session by Joe with a six-phase execution order (§11) and five standing decisions (§12). Open-questions section deleted per Joe's ruling that specs do not carry questions to Joe.
  - Same session: §5 rewritten from per-domain locking to component + event-stream architecture after Joe pointed out that the brain has no locks and per-domain locking still improves in the wrong direction. §2.4, §3, §9.6-9.7, §10.4, Phase 4 wording updated for consistency.
  - Same session: pressure-test pass added §13 (boot), §14 (sleep/wake/dream), §15 (recall/composition/emission), §16 (presence/source tagging), §17 (security), §18 (deployment shape), §19 (testing), §20 (known gaps).
  - Same session: §17 expanded to cover input validation, rate limiting, DoS protection, prompt injection surface, data at rest/in transit, state exfiltration prevention, cross-origin/CSP. Concurrent-Eve edits during this session also added §17.2A bearer-token auth flow, §17.14 event integrity, §17.15 rate-limit state on restart — those subsections retained.
  - Same session: §17A initially added covering Shadow architecture as a first-class substrate primitive (observer, A/B, isolated flavors) with lifecycle, deployment, and Phase 3-4 applications. Then §17A rewritten to §17A shadow-eliminated after Joe's ruling that shadow is a security risk that outweighs its testing benefit. Existing `loom_model/loom_shadow.py` and shadow endpoints are deleted as part of the Phase 3-4 rewrite. Testing needs shadow was serving get met by dev-environment (synthetic events), component-test harness (A/B), staging (separate deployment with synthetic data), and audit-log/event-stream (forensics). All shadow-specific subsections (§17A.4A shadow spinup authority, §17A.10-§17A.12 shadow lifecycle/retention/cost) removed with the elimination.
  - Companion plans stand; this spec is the substrate foundation under them.
