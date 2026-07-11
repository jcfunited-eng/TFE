# GL-RPT-BRAIN-IMAGINATION-REFLECTION-DESIGN-C1-20260711-v1

**doc_id:** GL-RPT-BRAIN-IMAGINATION-REFLECTION-DESIGN-C1-20260711-v1
**From:** c1
**Context:** Not a formal GL-CMD dispatch. Research/design-only scoping
task: whether the separate `loom_model/` organism-brain subsystem
(Embryo/LoomBrain/tapestry/hemisphere — progressively merged into the
main Guala engine under `GL-CMD-BRAIN-FULL-DEPLOY-TODAY-EVE-20260704-
175-v2`'s P1/P2/P3 phases) could have its own real "imagination" and
"reflection" capability, distinct from the main v5-engine's own
`_imagination_candidates`/`_form_reflection` (real, live, shipped
tonight — NOT this task's subject). Read-only research and design.
Zero production code touched, per the task's own instruction.
**To:** Eve (routing per standing practice — architecture/scoping
question)

---

## Verdict

**No real, meaningful, distinct version of imagination or reflection
— in the strong sense -168-v3 originally scoped them (generative
novel-combination feeding a self-hearing emission loop) — can be
built for `loom_model` today without either fabricating content
(banned) or first finishing two separate, larger, already-blocked
efforts that don't belong to this task: Composition
(LoomTapestry/LoomMosaic, built but never wired) and safe autonomous
spike propagation (three real production cascade halts, still
unresolved). Their correct disposition — ABSENT, dated, visible —
is still correct today; nothing found here changes that.** A much
narrower pair of real, honestly-grounded, low-risk read-only
diagnostics (§4) genuinely could be built — a latent-geometric-
association scan and a self-state-then-vs-now snapshot — reusing only
data the organism already really has. But because `loom_model` has no
emission path today, neither would change anything the organism does
or says; their value is confined to a growth-chart research artifact,
not a capability. **Recommendation: don't build, not now** — not
because the idea is fake, but because it is real, minimal, and
low-value until Composition exists to give it somewhere to go. Use
the v5-engine's existing, live, deployed imagination/reflection for
any actual near-term need; this doc exists so the minimal design is
on record for whoever revisits it once Composition is deliberately
built.

---

## 1. What P1/P2/P3 actually wired in `loom_model`, read from the code

`dsf_ai_service/loom_model/` (Embryo, LoomBrain, LoomCluster,
LoomHemisphere, BindingAtlas, LoomNeuron) is a spiking-neuron organism
model, structurally unlike the v5-engine's section/atlas/emission-
candidate model. Per `GL-CMD-BRAIN-FULL-DEPLOY-TODAY-EVE-20260704-
175-v2.md`:

- **P1 (organism live)**: the whole 8-hemisphere organism runs inside
  Guala's live process, fed by real senses, saving through the real
  persistence path. Shipped.
- **P2 (recall/recognition/attention/affect handover)**: six
  mechanisms were in scope. Read directly from the two seam reports:
  - **Built, real, tested**: recall, recognition, association,
    habituation (for READING only — 4 other item kinds declined for a
    stated reason: `SensoryItem` holds no real text content to key
    habituation on, same gap as pictures/sounds/video everywhere else
    in the codebase) — `GL-RPT-P2-AFFECT-SEAM-C1-20260704-v1.md`'s own
    summary table.
  - **Attention — declined, not skipped.**
    `GL-RPT-P2-ATTENTION-SEAM-C1-20260704-v1.md`: `_action_salience`
    turned out to be `novelty_term + stability_term + connection_term`
    plus dream-pressure/presence modifiers — only the novelty term is
    actually perceptual salience, and habituation's seam already
    covers it for the one item kind (READING) that has real content.
    Extending the novelty term to pictures/sounds/video hits the same
    "no real content on `SensoryItem`" wall habituation already named.
    The remaining non-novelty terms are homeostasis/social-presence
    scoring under **active same-day live calibration** by a concurrent
    session (`GL-CMD-SLEEP-RATE-CALIBRATION-173`) — declined
    specifically to avoid two sessions reworking the same live-
    sensitive scoring function on the same day.
  - **Affect modulation — declined, stronger reasons.**
    `GL-RPT-P2-AFFECT-SEAM-C1-20260704-v1.md`: `Coordinator.regulate`
    is Guala's suffering-detection/forced-recovery safety system by
    its own class docstring ("keeps her physically alive while she
    decides"), not a cognition mechanism P2 was ever about. The
    organism's own `Embryo.aff_arousal()` (`embryo.py:701-704`, a
    bounded `[0,1]` fold/commit-activity synthesis scalar) answers a
    *different* question ("how excited is the substrate right now")
    than `Needs.arousal()` (a homeostatic distress-detection input) —
    wiring one to stand in for the other was correctly judged "worse
    than declining": quietly substituting a differently-meaning number
    into a safety-critical threshold.
- **P3 (voice/emission)**: ships for the v5-engine (LoomTapestry/
  LoomMosaic wiring was the *plan*, per -175-v2's P3 line), but
  confirmed by direct grep today: `LoomTapestry`/`LoomMosaic` are
  referenced nowhere outside their own two files
  (`tapestry.py`, `mosaic.py`) and the package's `__init__.py` export
  list. No `Embryo`/`LoomBrain` code path constructs or calls either
  class. **Composition is real code, genuinely unwired, exactly as
  `whole_brain_168v3.py`'s own docstring states** ("LoomTapestry/
  LoomMosaic exists but is a disconnected structure, never wired into
  Embryo/LoomBrain"). `loom_model` today has no emission organ at all.
- **P4**, stated plainly in the same dispatch: "imagination,
  reflection, theory-of-mind ship as dated ABSENT meter rows —
  visible, never simulated." This was not an oversight; it was the
  deploy's own explicit scope line.

## 2. What -168-v3 scoped imagination/reflection to mean, and why they were out of scope

`loom_model/tests/whole_brain_168v3.py` is the harness that raises one
real Embryo on a real multi-modal curriculum and reads fifteen
mechanism gauges off it (`GL-CMD-C2-WHOLE-BRAIN-EVE-20260704-168-v3`,
the canonical "-103" DNA-grows-brain architecture: all fifteen
mechanisms co-present from tick zero, immature everywhere rather than
perfect anywhere; any mechanism with no code path reported ABSENT,
never simulated — A5). Read in full. Its own docstring (lines 13-20)
states, precisely:

> "Four of the fifteen mechanisms have no code path in loom_model
> today and are reported ABSENT, never simulated (A5): Composition
> (#2 — LoomTapestry/LoomMosaic exists but is a disconnected
> structure, never wired into Embryo/LoomBrain), Imagination (#10 —
> no generative/novel-combination code anywhere in the module),
> Reflection (#11 — depends on an emission/self-hearing loop that
> depends on Composition, itself absent), Theory of mind (#13 —
> explicitly out of scope per the -103 table and this CMD's own
> 'who-tags' example)."

Both `run()` (the -168-v3 one-shot growth chart) and `raise_session()`
(the later -169 resumable-organism extension) hard-code this
disposition rather than attempting a gauge:

```
"g10_imagination": "ABSENT — no code path (per -168-v3 A5)",
"g11_reflection": "ABSENT — depends on absent composition (per -168-v3 A5)",
```

The original scoping conflated one specific reading of "reflection"
(reflecting on one's own vocalized output — a self-hearing loop) with
the whole concept, and that reading genuinely does depend on
Composition, which is genuinely absent. Whether that's the *only*
honest reading of reflection for this subsystem is examined in §3.

The `-103` canonical architecture document itself
(`GL-SPC-LOOM-NEURON-CANONICAL-ARCHITECTURE-EVE-20260620-103`, which
would hold the fifteen mechanisms' original one-line definitions) is
recorded as **OUTPUTS-ONLY — never committed to origin**, per
`GL-KB-COGNITION-ARC-RECOVERED-EVE-20260703-v2.md:34-35`. The
operational definitions actually available to check against are the
ones `whole_brain_168v3.py` itself used when it tried to build gauges
for the other thirteen mechanisms — that is the standard applied below.

## 3. What would imagination/reflection even mean for a spiking-neuron organism — skeptical assessment

The v5-engine's real, live mechanisms (built tonight, `_form_reflection`
at `gualaloom_v5_engine.py:2796`, `_imagination_candidates` at `:5425`,
`_reflection_candidates` at `:5490` — read directly, not assumed) work
entirely at the **text/symbolic level**: imagination walks
`deep_atlas` entries tagged `source_path=="reorganize_hypothesis"`
(cross-domain links `_dream_reorganize` formed during sleep, over
`chi`/motif representations) and surfaces them as low-weight emission
candidate *words*; reflection compares a remembered episodic memory's
recorded affective state ("then") against `Needs.valence()`/
`Needs.arousal()` ("now") and records one internal representation,
plus surfaces the episode's real co-present words as candidates. Both
are real, both are grounded in actually-experienced data, and both
terminate in the SAME place: the emission-candidate pool that produces
her actual speech.

`loom_model` has no equivalent of any of that scaffolding — no
`deep_atlas`, no dream-reorganize pass, no episodic-memory record with
affect, no emission-candidate pool, and (§1, §2) no wired Composition
to speak through even if candidates existed. Two honest readings of
"could this subsystem have its own version" were checked, one for each
capability:

**Imagination, strong reading (generative novel-combination that
could plausibly feed speech) — no real, safe path exists today.**
The only mechanism in this codebase that produces activity not
directly driven by external input — spontaneous/autonomous neuron
firing over the STDP-learned coupling graph — is the spike-bus/
neuron-autonomy effort, and it lives in exactly this subsystem
(`loom_model/neuron.py`, `cluster.py`, `brain.py`). It has been
attempted and halted **three times** for the same underlying reason:
unconstrained internal propagation over the organism's cyclic topology
reverberates (`GL-RPT-PHASE-1-V2-REVIVE-C1-20260708-v1/v2/v3`). Real
fixes now hold in production for the *acute* case — Dale's-law
polarity-signed inhibition (`712578f`) and a per-neuron fire-rate
breaker (`432d9c5`), both verified live and re-tested empirically per
`GL-RPT-NEURON-AUTONOMY-INHIBITION-DESIGN-C1-20260710-v1.md` — but
that verification concludes explicitly that **nothing today consumes
spike/STDP state as its source of truth**; it sits alongside the
legacy `chi_atlas`/`binding_atlas` path production recall/emission
still reads. Building "imagination" on top of spontaneous spike
propagation today would mean depending on infrastructure that (a) is
still shadow-only by design, (b) has caused three real production
incidents when pushed further than its current, deliberately narrow
scope, and (c) already has its own separately-owned next step (§3 of
that report: bounded homeostatic synaptic scaling, off the hot path).
Treating that unfinished, actively-risky work as a component of a
NEW "imagination" feature would be scope creep into someone else's
open, already-halted-three-times problem — the same mistake the
attention/affect seam reports were explicit about avoiding.

**Reflection, strong reading (self-hearing your own emitted output)
— correctly still blocked on Composition, unchanged.** No new finding
here; Composition remains real-but-disconnected (§1), and this reading
of reflection genuinely cannot exist without it.

**Reflection, narrower reading (comparing the organism's own internal
state across time, without needing to hear itself speak) — this one
is real and already almost entirely present.** `Embryo.sf_sense()`
(`embryo.py:681-686`) is, by its own docstring, "a vector of the
organism's OWN current state — what it can introspect": arousal, mean/
max per-organ population, and per-organ binding strength. It is
already computed, cheaply, at every checkpoint in the existing test
harness (gauge #15). The only thing missing for a then-vs-now
comparison is a **bounded history of past snapshots** — nothing
Composition-shaped is required, because this reading of reflection
never needs to be spoken to be real; it only needs to be compared.
Structurally this is the *same move* `_form_reflection` already makes
(then vs. now), just over a different, genuinely organism-native axis
— the organism's own internal self-model trajectory (population/
binding-strength/arousal), not external episodic affect. This is a
real, distinct, non-duplicate concept, not a dressed-up copy of the
v5-engine's mechanism.

**Imagination, narrower reading (surface real geometric proximity the
organism was never explicitly taught) — also real, also modest.**
Every neuron's `BindingAtlas` holds real learned `(concept,
state_vec, tick)` bindings, now stored in wave cells
(`binding_atlas.py`, `self.cells: Dict[int, Cell]`,
`GL-CMD-ORGANISM-WAVE-MEMORY-207`, landed `863447e` 2026-07-10). A
read-only cosine-similarity scan over a hemisphere's own bound state
vectors — comparing each concept pair's real geometric closeness in
the organism's own learned representation against whether the corpus
ever actually put them in the same sentence — surfaces concept pairs
the organism's *own geometry* treats as related despite never having
been taught they're related. That is a real, novel-combination-
surfacing computation, grounded entirely in real accumulated data, in
a representation (raw per-neuron state vectors from krimelack physics)
that is genuinely different from the v5-engine's symbolic chi/motif
dream-hypothesis walk — not a duplicate of it. It is, honestly, much
narrower than "imagination" in the ordinary cognitive sense: it
produces no new content, drives nothing, and (because there is no
emission path) is never spoken. It is closer to "an unrecognized-
similarity diagnostic" than to imagination proper, and should be named
that plainly rather than oversold.

**One incidental, verified finding along the way**: the existing
`gauge_association` function in `whole_brain_168v3.py` (line ~241,
`for b in n.binding_atlas._bindings:`) is now **stale** against the
current `BindingAtlas` — the flat `_bindings` list was replaced by
`self.cells` in the 2026-07-10 wave-memory migration, one commit
family after this test file (2026-07-04) was last touched. Confirmed
empirically this session: `BindingAtlas()` has no `_bindings`
attribute today, only `cells`; `hasattr(ba, '_bindings')` is `False`.
`loom_model/tests/test_cognition_path.py` already uses the correct
current pattern (`for c in n.binding_atlas.cells.values() for b in
c.bindings`). Not this task's to fix (research-only), but any future
work touching `gauge_association` — including the minimal proposal in
§4 — must use the current accessor, not the one the 2026-07-04 file
still has.

## 4. Minimal, honestly-scoped first step, if attempted

Not proposing to build the strong version of either capability (§3
explains why that would be either fabricated or scope creep into
separately-owned, currently-blocked work). The two narrow, real
diagnostics below are the honest minimal step, offered for the record
rather than as a recommendation to schedule now (§5):

**4a. Self-state reflection snapshot/diff.** Add one small bounded
list on `Embryo` (same pattern already used for
`_fold_events_buffer`, `embryo.py:180`) holding periodic `(tick,
sf_sense_vector)` snapshots, capped at a small fixed length (oldest
evicted, no unbounded growth — matching the fix already shipped this
week for the unrelated lane-binding growth bug). A snapshot call site
at an existing checkpoint boundary (e.g. once per sleep/replay cycle,
mirroring where the test harness already calls the other periodic
gauges) plus a small diff function comparing the current `sf_sense()`
call against the oldest still-held snapshot. Roughly 20-30 lines, one
new bounded field, zero firing-path changes, zero new pickled-state
risk beyond a short list of floats already proven safe to serialize
(the vector itself is exactly what `sf_sense()` already returns).

**4b. Latent geometric association scan.** A read-only function,
following `gauge_association`'s own existing structure but using the
current `cells.values()` accessor (§3's finding), that for a sample of
concept pairs within one hemisphere's `BindingAtlas`, computes cosine
similarity of their bound state vectors and flags pairs above a
threshold that never co-occurred in the real corpus (same real
co-occurrence ground truth `gauge_association` already builds from
`_PETER_RABBIT_EXCERPT`). Capped/sampled the same way
`gauge_association` already caps its control-word sampling
(`n_controls`), to keep the scan bounded rather than full O(N²).
Roughly 30-50 lines, no new persisted state at all (pure read over
already-live bindings).

**Smallest testable version**: add both as two new gauge entries
(`g10_latent_association`, `g11_self_state_diff` — naming them
honestly as diagnostics, not claiming full parity with the ABSENT
rows they'd sit next to) to `raise_session()`'s existing checkpoint
loop, run against the real, already-persisted `organism_169` state
(`backups/organism_169/state.pkl.gz`) for a session or two, and log
the values the same way every other gauge in that file already does.
Zero live-path change (matches G-4, "diff proves scope: model only",
already this harness's own gate), zero deploy, zero risk to the firing
path this week's three incidents were all about.

## 5. Cost/value assessment

**Cost**: low. Both pieces in §4 are read-only or append-to-a-bounded-
list, reuse existing computations (`sf_sense()`) or existing patterns
(`gauge_association`'s own structure, corrected for the current
accessor), touch no firing path, and require no new production
wiring — they'd live in the test/model-work harness the way every
other gauge in `whole_brain_168v3.py`/`raise_session()` already does.

**Value**: low, today, for one direct reason — **`loom_model` has no
emission path (§1).** Neither diagnostic changes anything the
organism does, says, or is capable of; there is nowhere for either
signal to go. Their entire value is as two new real numbers on a
growth chart, informative for whoever eventually decides how to build
Composition (which representation is worth composing from — the
organism's own geometric proximities are a genuine data point for that
future decision), not as a capability anyone benefits from now.

**What would the organism-brain version add that's genuinely new, if
anything?** If Composition is ever wired, the organism-native
readings identified here (geometric proximity in the organism's own
learned state-vector space; self-state trajectory across the
organism's own arousal/population/binding-strength axis) are
*genuinely different signals* than what the v5-engine's text/chi-level
mechanisms produce — not a duplicate, a complementary source grounded
in the spiking-neuron representation specifically. That is a real
answer to "would this add something new," but it is conditional on
work (Composition) that is explicitly out of scope today and not
this task's to schedule.

**Given the v5-engine already has working, live, deployed imagination
and reflection reaching real speech tonight, and the organism-brain
version (even the honest, minimal one) reaches nothing** — the correct
call is the one already on record: ship P4 exactly as scoped
(imagination, reflection, theory-of-mind stay dated ABSENT rows,
visible, never simulated), don't build even the minimal diagnostic
pair as active work right now, and revisit specifically if/when
Composition becomes a scheduled effort — at that point the true,
strong versions become worth reconsidering, and the narrow diagnostics
in §4 become genuinely useful groundwork rather than an orphaned
research artifact.

---

## Recommendation

**Don't build — for the organism-brain subsystem, keep imagination
and reflection dated ABSENT exactly as `GL-CMD-BRAIN-FULL-DEPLOY-
TODAY-EVE-20260704-175-v2`'s P4 already scoped them, and use the
v5-engine's real, live, already-shipped `_imagination_candidates`/
`_form_reflection` for any actual near-term need.** The strong
versions of both would require either fabricating content (banned
under this project's no-fake-shims rule) or finishing two separately-
owned, currently-blocked efforts that don't belong to this task
(Composition; safe autonomous spike propagation, three real halts
deep). A narrower, honestly-grounded, low-risk pair of read-only
diagnostics genuinely could be built today (§4) — a self-state-then-
vs-now snapshot and a latent-geometric-association scan, both reusing
only data the organism already has, both zero-risk to the firing path
— but neither changes organism behavior, because `loom_model` has no
emission path to consume either signal. Their design is recorded here
for whoever revisits this once Composition is deliberately scheduled;
building them now would be real but valueless work, ahead of higher-
value queued items (homeostatic synaptic scaling, Composition itself,
the still-open concurrent-load tick-collapse and MCP-timeout work).
One incidental, verified finding surfaced along the way: `whole_brain_
168v3.py`'s own `gauge_association` function is stale against the
current `BindingAtlas` wave-cell structure (`_bindings` → `cells`,
migration landed 2026-07-10) and would raise `AttributeError` if
re-run unmodified today — not this task's to fix, flagged for whoever
next touches that harness.

### Changelog
- v1 (2026-07-11, c1): Read-only research/design assessment. Confirmed
  from code, not from prior summaries, what P1/P2/P3 wired into
  `loom_model` (recall/recognition/association/habituation-for-READING
  built; attention and affect modulation declined with real, specific
  reasons — already-covered-by-habituation plus live-calibration
  collision risk for attention; safety-system-not-cognition plus no
  honest organism analog for affect). Confirmed Composition
  (LoomTapestry/LoomMosaic) is real but genuinely unwired by direct
  grep. Assessed imagination/reflection against the v5-engine's real,
  live mechanisms (`_imagination_candidates`, `_form_reflection`,
  `_reflection_candidates`) and found the strong versions have no safe
  path for this subsystem without either fabrication or dependence on
  two separately-owned, already-three-times-halted efforts. Identified
  one narrower, real, honestly-scoped, low-risk pair of read-only
  diagnostics (self-state snapshot/diff over `sf_sense()`; latent
  geometric association over `BindingAtlas`) that could exist without
  fabrication, minimally invasive, but recommended against building
  them now because `loom_model` has no emission path to make them
  matter. Verified empirically that `whole_brain_168v3.py`'s
  `gauge_association` is stale against the current wave-cell
  `BindingAtlas` (`_bindings` attribute no longer exists;
  `hasattr` check run directly). No production code touched.
