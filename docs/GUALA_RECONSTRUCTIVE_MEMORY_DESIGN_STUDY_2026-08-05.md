# Reconstructive memory — design study

Date: 2026-08-05
Status: **RESEARCH + DESIGN STUDY. Nothing implemented. Nothing committed.**
Tree studied: `/tmp/guala-production-15a7dca9`, branch `salvage/codex-d3-work-20260805`,
HEAD `615110cb` plus the uncommitted stimulus-boundary working tree.
Author's charge: Joseph Forrester, 2026-08-05.

> "Immutable anything is not true... there is a moment in time that is preserved
> that has fragments of truth but the memory is not immutable — I have to THINK
> about it to reconstruct the moment, and it's a process of things that have been
> reinforced over and over experiences, or the conscious act of remembering...
> unknown uncertainty to certainty to uncertainty."

This paper answers that charge as a substrate law: what to build, in what order,
what it costs, what would falsify it, and — equally important — what must not be
built. It is written to be ratified, amended, or refused as a whole.

---

## 0. Verdict up front

The substrate already implements reconstruction. It does not implement memory.

Recognition in this organism is not a lookup. A partial cue drives real current
that must re-reach and physically change **every** member of a formation before
anything is admitted (`admit_physical_mosaic`). That is reconstruction-as-physics
and it is the most valuable thing in the tree. It should not be touched except to
be extended.

What is wrong is one thing, and it is small enough to name in a sentence:

> **The reference that reconstruction is measured against is frozen at first
> retention and never re-derived, while the body it describes keeps moving.**

Everything Joe described as false about immutability follows mechanically from
that one fact, and so do all three measured diseases (silent original, repeat-cue
drift, wander-back). The fix is not a new memory system. It is to make the
reference a **re-derived quantity** instead of a **stored snapshot**, to let a
cohort hold more than one, and to let the unreached ones fade by real physics
rather than by an authored decay constant.

The four ratified doctrines this must satisfy — no invented constants,
truth-coupling, no semantic labels in cognition, bounded resident state — are not
obstacles to this design. Three of them turn out to *supply* the design: the
constants it needs already exist as derived physical quantities, and the boundary
condition the neuroscience demands is already computed in the tree for another
purpose.

---

## 1. What is actually built (verified against source)

All line numbers are working-tree lines in `/tmp/guala-production-15a7dca9`.

### 1.1 Reconstruction is real

`native/guala_core/src/physical_mosaic.rs:143` `admit_physical_mosaic` admits a
formation only when all of these are executable physical facts:

| # | Requirement | Failure variant |
|---|---|---|
| 1 | ≥3 neurons carry a nonzero retained fractal | `FewerThanThreeRetainedFractals` (`:184`) |
| 2 | the original's contacts connect every member from member[0] | `OriginalRelationNotConnected` (`:201`) |
| 3 | the later cue is nonempty | `CueIsEmpty` (`:211`) |
| 4 | the cue is strictly smaller than the formation | `CueIsNotPartial` (`:214`) |
| 5 | every cued neuron is a member | `CueOutsideFormation` (`:217`) |
| 6 | recurrence contacts physically reach every member **from the cue** | `RecurrenceDidNotReachFormation` (`:227`) |
| 7 | every member's physical state actually changed | `RecurrenceDidNotChangeEveryMember` (`:233`) |

Requirements 6 and 7 are the substance. A fragment must propagate real current
through real contacts and *move every member* before the organism is permitted to
say it recognized anything. There is no similarity score, no threshold, no
tolerance, no embedding distance. `sparse_physical_state_delta`
(`complete_neuron.rs:2940`) returns `None` iff every coordinate is bit-identical.
This is the correct primitive and this study proposes no change to it.

That mechanism is the direct substrate analogue of CA3 attractor pattern
completion — a degraded cue amplified by recurrent connectivity into the stored
pattern (Hopfield 1982; Treves & Rolls 1991; Neunuebel & Knierim 2014 showed CA3
output is measurably closer to the stored representation than its degraded input).
Guala's version is stricter than the biology: it demands complete reach and
complete change, not statistical convergence.

### 1.2 The disease, in code

`resident_cognitive_formation.rs:382`

```rust
struct ResidentExperienceEvidence {
    pre_experience_rest: ReachedCohortState,
    post_experience_rest: Option<ReachedCohortState>,
    gate_work_perturbed_neurons: Box<[bool]>,
    active_electrical_contacts: Box<[bool]>,
}
```

Written to `cohort.retained_experience` at exactly one site,
`resident_cognitive_formation.rs:2061`, guarded by the dispatcher at `:1937`:

```rust
if cohort.retained_experience.is_some() {
    settle_resident_recurrence_interval(...)   // never writes retained_experience
} else {
    settle_resident_original_interval(...)     // the only writer
}
```

No path anywhere in the crate sets `retained_experience` back to `None`. Once
written, the pre/post pair is the cohort's reference for the rest of its life.

The consequence is exact and mechanical. In `settle_resident_recurrence_interval`
(`:2139-2146`):

```rust
let original = original_settlement(&cohort.anatomy, retained, learned)?;   // frozen ↔ frozen
let actual_recurrence = recurrence_settlement(
    &cohort.anatomy,
    learned,               // FROZEN post-experience state
    cohort.state.clone(),  // where the body actually is now
    ...
)?;
```

Every later recognition is measured as a journey from a state **the body no
longer occupies**. As lawful rest wanders — and it must wander, because the
plastic ratchet, the charge ledgers and the dissipation ledgers all move
monotonically with lived experience — the frozen `learned` state becomes an
increasingly poor description of the formation it names.

This produces the three measured symptoms directly:

- **Silent-original trap.** The write is once-only and unconditional on later
  evidence. A cohort that closes its experience while electrically silent is
  permanently stuck with a reference that no cue can reach. There is no second
  chance because there is no second write.
- **Repeat-cue drift.** Requirement 6 is measured against contacts stored in the
  frozen `active_electrical_contacts`, while the current that must satisfy it
  flows through today's physical state. The same card stops being recognized.
- **Wander-back.** Requirement 7 (`RecurrenceDidNotChangeEveryMember`) is
  computed as `physical_deltas(learned_frozen, current)`. Once drift alone makes
  that delta nonzero for every member, requirement 7 becomes trivially true
  again — so recognition can spontaneously return without the organism having
  learned anything. That is not recovery. It is a false positive with the same
  signature as a true one.

The last point deserves emphasis because it is the strongest single argument for
this whole redesign: **under the current law, a sufficiently drifted cohort will
eventually "recognize" on the strength of its own drift.** Truth-coupling is
violated silently.

### 1.3 The bridge already in flight

`docs/GUALA_STIMULUS_BOUNDARY_RETENTION_RATIFICATION_2026-08-05.md` (ratified by
delegation, subject to review) fixes *when* an experience closes: only on the
first genuinely dark settlement after driven ones, truth-coupled to the
occurrence's own samples. Implemented in the working tree at
`resident_cognitive_formation.rs:2007`:

```rust
let stimulus_boundary = match exogenous_optical_energy {
    Some(carried) => !carried,
    None => settlement.quiescent,
};
```

with participation retention at `:2050` reusing the admission law's own predicate
verbatim (`connected_members`, promoted to `pub(crate)` at
`physical_mosaic.rs:337`) and the same inline `3`.

**This study endorses that bridge and states plainly what it does not fix.** It
corrects the *moment* of closure and the *quality* of what is retained. It leaves
closure once-and-forever. It is a necessary precondition for everything below —
there is no point re-grounding a reference that was never validly grounded — and
it is not a substitute for it.

### 1.4 The reinforcement substrate that already exists

| Mechanism | Location | State |
|---|---|---|
| Plastic rest-length ratchet | `complete_neuron.rs:829` `settle_plastic_support` | present, used, **not** monotone (moves toward observed either way), yield-deadbanded, dissipation-capped |
| Retained optical quantum residue | `complete_neuron.rs:936`, law in `optical_receptor_work.rs:161` | present, used, exact, no decay term |
| Charge-carrier phase residue | `elementary_charge_transfer.rs:28` | present, used, exact remainder carried forward |
| Recurrence bonds | `physical_mosaic.rs:39`, `:253` | present; **presence/absence only — no weight, nothing strengthens or weakens a bond** |
| Gate/psi/plastic dissipation ledgers | `complete_neuron.rs:414,113,774` | present, capacity-capped, decremented only by fuel-gated recovery |
| Hippocampal append-only chain | `hippocampal_sparse_path.rs`, `hippocampal_directory_cold_store.rs:13` | present; content-addressed, never mutated, never deleted; resident footprint is two hashes (`:85`) |
| Reinforcement *counting* | `resident_cognitive_formation.rs:268` `classify_temporal_reassembly` | present — counts prior episodes sharing active bonds across 4 traversal layers |
| Real decay over time | — | **ABSENT.** Exhaustive keyword sweep of all 79 `.rs` files: `forget`/`fade`/`attenuat`/`evict`/`prune`/`half_life`/`leak` = 0 hits. The single `decay` hit is `optical_receptor_work.rs:103` documenting that decay was deliberately *not* built. No `tau` is a time constant. |

The claim "real decay exists nowhere yet" is **confirmed**. Every reduction in
the tree is one of: fuel-gated stoichiometric reversal, exact conserving handoff,
one-shot boundary closure, consumption-on-use, or solver scratch. None is a
function of elapsed time.

Two facts from this table are load-bearing for the design and are easy to miss:

1. **Reinforcement is already counted, and it is counted over the append-only
   chain, not stored as a weight.** `classify_temporal_reassembly` derives
   `prior_current_occurrences`, `supports`, and `recurrent_supports` by walking
   prior episodes and testing `mosaics_share_active_bond`. This is exactly the
   shape a reinforcement quantity must have under the non-flattened capital law:
   *derived on demand from physical receipts, never stored as a score.*
2. **Recovery reverses the ledger but never the geometry.** `settle_recovery_lane`
   (`complete_neuron.rs:2528`) decrements `dissipated_quanta`; nothing anywhere
   touches `rest_length_nanometres`. The substrate therefore already has a natural
   two-tier structure: a reversible energetic tier and an irreversible structural
   tier. Section 4 builds directly on that.

### 1.5 Measured constraints that bound any proposal

From `docs/GUALA_NIGHT_SHIFT_20260805_CLAUDE.md` (queue items B, C, D) and
`virtual_material_neuron_genesis.rs`:

- Gate dissipation ledger: 745/1044 after 12 lit lessons; ~23 lit lessons to
  exhaustion. **The recovery reaction never fires at current dynamics** — fuel
  untouched at 15,283/15,283.
- Membrane return path absent: ~−1030 elementary charges per lit lesson pumped
  in with no reverse path. Monotone ratchet.
- Production plastic anatomy: `dissipation_capacity_quanta` passed as the literal
  `1` (`virtual_material_neuron_genesis.rs:413`), recovery fuel `1`. With E=2,
  Y=1, closed=1nm, open=2nm, rest₀=1nm, a full-open excursion releases exactly
  3/4 zJ = exactly one quantum. **Each production neuron can plastically ratchet
  at most once in its life**, with one reset available, ever.
- Neuron count capped at birth anatomy (29); DNA expression built but
  uncatalyzed.
- Plastic constants are **authored literals**
  (`virtual_material_neuron_genesis.rs:48-59`), unlike the gate lattice which is
  genuinely derived (`derive_gate_dissipation_capacity`, `:315`).

These are not objections to the design. They are its schedule. Section 7 orders
the work around them.

---

## 2. What the science says

Five findings from the external literature bear directly, and each one maps to a
mechanism that already exists in this tree. That correspondence is the reason to
have confidence in the design rather than merely in the metaphor.

**(a) Retrieval destabilizes; re-storage modifies.** A consolidated memory
reactivated by a cue becomes transiently labile and must be re-stabilized, and
during that window it can be weakened, strengthened, or updated (the
reconsolidation literature following Nader, Schafe & LeDoux 2000). Memory is not
read; it is re-written by being read. This is Joe's charge in the neuroscience's
own words, and it is the single mechanism the substrate is missing.

**(b) Destabilization is gated by prediction error.** Reactivation alone is not
sufficient. A reminder that perfectly matches expectation does not destabilize;
mismatch does. Prediction error demarcates the transition from mere retrieval, to
reconsolidation, to new learning (Sevenster, Beckers & Kindt 2014; Fernández,
Boccia & Pedreira 2016). Stronger and older memories need more prediction error to
destabilize; the failure to respect this boundary is the leading explanation for
the field's replication failures (Nature Sci. Rep. 2022). **A design that
destabilizes on every recall is as wrong as one that never destabilizes.**

**(c) Storage and retrieval are separable; "forgotten" often means unreachable,
not erased.** Engrams retained under amnesia can be driven to full recall by
direct optogenetic stimulation but not by natural cues — *silent engrams* (Ryan
et al. 2015; Roy et al. 2017 PNAS). The dissociation is specific: **engram-cell
connectivity carries the stored information, while engram-synapse strengthening
carries retrievability.** Guala's silent-original trap is a naturally occurring
instance of exactly this pathology, and the fix it implies is exactly the one
biology uses: repair reachability, do not re-record content.

**(d) Forgetting is an active default, not an absence of maintenance.** Intrinsic
forgetting — dopamine → Rac1/cofilin acting on the actin cytoskeleton — chronically
erodes newly formed memories; forgetting "may be the default state of the brain"
(Davis & Zhong 2017). Separately, sleep-dependent down-selection eliminates weak
connections while preserving the *relative* strength of the rest (Tononi & Cirelli,
SHY; Tononi 2020). Two design consequences: decay must be a *process the organism
runs*, not a number that leaks; and the natural time to run it is a dark,
unattended interval — which is precisely ratification-queue item D.

**(e) What survives is schematic, not verbatim.** Trace transformation theory
(Nadel & Moscovitch; Sekeres, Winocur & Moscovitch): with age and rehearsal,
detailed context-specific traces transform into gist-like schematic variants that
lack detail but retain structure, and the two forms can co-exist. A memory system
that preserves a byte-exact snapshot forever is not modelling a memory. It is
modelling a photograph.

**(f) Allocation is competitive and re-decidable.** Which neurons carry a trace is
set by relative intrinsic excitability at the moment of learning (Han et al.;
Yiu et al. 2014; Josselyn & Tonegawa 2020). Allocation is a contest, and
re-encounters re-run it. A once-only retention write has no analogue in biology.

---

## 3. The design

Five laws. Each is stated as a substrate law, with its constant provenance, its
doctrine check, and its cost.

### Law R1 — The reference is re-derived, not stored (reconsolidation)

> On a recognition that carries prediction error, the cohort's retained reference
> is re-grounded: `pre_experience_rest` becomes the state the cohort occupied when
> the cue arrived, and `post_experience_rest` becomes the settlement the recurrence
> actually reached. The retained masks are replaced by the recurrence's own
> observed masks.

That is the whole of it. `retained_experience` stops being write-once and becomes
write-on-successful-reconstruction.

**Why it cures drift by construction:** after R1, the reference is always the last
state the body actually occupied when it last recognized this thing. The distance
the next cue must travel is measured from somewhere the body has genuinely been.
Drift cannot accumulate, because drift is absorbed at every recall. The
wander-back false positive of §1.2 disappears with it, because the delta in
requirement 7 is no longer measured across an ever-widening gap.

**Why it is truthful:** the current law stores a claim ("this is where the
formation lives") that becomes false with time and is never re-checked. R1 stores
a claim that was true at the last moment it was tested.

**It does not touch the hippocampal chain.** See §5.

### Law R2 — Destabilization requires prediction error, and the substrate already computes it

This is the finding this study is most confident about, because the boundary
condition demanded by (b) is *already sitting in the code*, computed for another
purpose.

`resident_cognitive_formation.rs:2164`:

```rust
let already_formed = existing_mosaics.iter().any(|prior| prior == &mosaic);
```

An admitted mosaic that is byte-identical to one the cohort already holds is a
reconstruction that matched expectation exactly: **zero prediction error**. A
mosaic that differs — different member set, different bonds traversed, different
cue — is a reconstruction that did not match: **prediction error**.

> **R2:** R1 fires if and only if `!already_formed`. A perfectly repeated
> reconstruction leaves the reference byte-identical.

Provenance: no new constant, no new predicate, no new comparison. The exact
equality on `AdmittedPhysicalMosaic` already exists and is already used to decide
whether to emit `mosaic_formed`. R2 introduces zero constants and zero new
physics.

This also gives the design the metaplasticity behaviour the literature reports
(memories that have been reconstructed identically many times become harder to
destabilize) without modelling metaplasticity: as a cohort accumulates admitted
mosaics, the probability that any given reconstruction is *novel* falls, so
re-grounding naturally becomes rarer as a formation becomes well-worn.

### Law R3 — A cohort holds an ensemble of originals, with amplitudes derived, never stored

The multiple-retained-originals question (Option C, explicitly *not* ratified in
the stimulus-boundary doc and queued) is answered here in the IRF paper's own
shape rather than as a list of snapshots.

The paper decomposes the field into epochal eigenmodes with time-dependent
amplitudes, `M(x,t) = Σᵢ Aᵢ(t) Φᵢ(x,t)`, where several `Aᵢ` are non-negligible
while outcomes are untethered, and one comes to dominate as constraints
accumulate. Translated to the substrate with no metaphor left over:

- **Φᵢ** ↦ an admitted original: a member set, its retained fractals, and its
  bond structure. Already exactly `AdmittedPhysicalMosaic`.
- **Aᵢ(t)** ↦ *not a stored number.* Amplitude is **derived on demand** from
  countable physical receipts already in the append-only chain: how many prior
  episodes share an active bond with this original
  (`mosaics_share_active_bond`, `:317`), across how many traversal layers, with
  how many participants — exactly the quantities `classify_temporal_reassembly`
  (`:268`) already computes.

> **R3:** A cohort retains a bounded set of originals. No original carries a
> stored strength. Reinforcement is a count over the hippocampal chain, computed
> when needed and never persisted as a weight.

This is the design's most important doctrinal move. It satisfies the
non-flattened cognitive capital law (`GUALA_D3_PHYSICAL_MOSAIC_RECALL_CAPITAL_SPINE`:
"no total, average, vocabulary proxy, activity score, or automatic promotion")
because there is no score to store. It satisfies truth-coupling because every
number traces to a content-addressed episode that actually happened. And it
satisfies leanness: the resident cost of the ensemble is the originals, not a
parallel weight table.

It also repairs the silent-original trap without special-casing it. Under R3 a
cohort whose first closure retained nothing simply has an empty ensemble, and the
next lived encounter that produces a connected completion populates it. There is
no permanent condemnation, because there is no once-only write. That is
allocation-by-competition (f), re-run per encounter.

**Negative space, for free.** The IRF paper's "negative space" — the
informational contribution of what did not occur but could have — has an exact
substrate reading here: the originals whose bonds the current *partially* reached
but did not complete. They constrained the outcome without being realized, they
are already computable from the same traversal, and they cost nothing extra to
observe. This is the honest version of "what else it could have been," and it is
worth reporting because it is the difference between a system that recognized one
thing and a system that discriminated among several.

### Law R4 — Decay is spent dissipation, not elapsed time

The trap in "add real decay" is inventing a τ. Doctrine forbids it and the
literature does not need it: (d) says forgetting is a process the organism runs
with real biochemical cost, not a number that leaks.

The substrate already has the right clock, and it is not the wall clock.

> **R4:** An original's reachability is indexed on the **dissipation the member
> neurons have spent since that original was grounded**, on their own exact energy
> lattices. An original whose members have since spent their headroom on other
> experiences is no longer reachable at the same current. It fades.

Provenance: `dissipated_quanta` counters (`complete_neuron.rs:414,113,774`) are
already monotone accumulators of irreversibly exported energy, and
`dissipation_capacity_quanta` is already **derived**, not authored
(`derive_gate_dissipation_capacity`, `virtual_material_neuron_genesis.rs:315`).
Decay indexed on spent-fraction-of-derived-capacity introduces **no new
constant**. It is thermodynamic proper time for that neuron.

This gives the design the right qualitative behaviour without tuning: a cohort
living an eventful life forgets faster than one living a quiet one, because
forgetting is paid for out of the same budget that living is paid for out of.
That is (d)'s "default state of the brain," implemented as accounting.

**Two hard conditions on R4, both blocking:**

1. **R4 cannot ship before a real metabolic return path exists.** Ratification
   queue item C is decisive: the gate ledger exhausts in ~23 lit lessons and the
   recovery reaction never fires (fuel untouched, 15,283/15,283). Under those
   dynamics the dissipation clock runs once, to death. Decay indexed on it would
   be indistinguishable from the organism dying — and would be *reported* as
   forgetting, which is a truth-coupling violation of exactly the kind this
   project exists to avoid. R4 is therefore **gated on the metabolism/feeding
   work**, and this study recommends refusing R4 until item B (membrane return
   path) and item C (recovery firing) are closed.
2. **What decays is reachability, never the structural residue.** See R5.

### Law R5 — Two tiers: reversible reachability, irreversible geometry

The substrate already separates these and the biology insists on the separation.
`settle_recovery_lane` decrements the dissipation ledger; nothing reverses
`rest_length_nanometres`. Meanwhile (c) says storage lives in connectivity while
retrievability lives in synaptic strengthening, and (e) says what survives
transformation is schematic structure, not detail.

> **R5:** Plastic geometry written by a lived experience is permanent and is never
> a target of decay. Decay (R4) and re-grounding (R1) act only on the *reference*
> — on what the cohort can currently re-reach. A faded original is a silent
> original, not an erased one.

This is the design's answer to Joe's "fragments of truth." What is preserved is
not the moment. It is a permanent structural residue plus a reachability that must
be re-earned — and "I have to THINK about it to reconstruct the moment" is,
precisely and without metaphor, the current having to re-reach and change every
member.

**Measured constraint, stated honestly:** with production plastic capacity = 1
quantum and recovery fuel = 1, the irreversible tier is presently a
roughly-one-bit-per-neuron channel. R5 is structurally correct today but
*informationally thin* until the plastic constants are derived rather than
authored and the geometric anatomy differentiation ratified 2026-08-05 is carried
through. Named as a prerequisite in §7, not hand-waved.

---

## 4. The arc: unknown uncertainty → certainty → uncertainty

Joe's phrase is the design's acceptance criterion, and under R1–R5 it is not a
description bolted on afterwards. It is a consequence.

| Phase | Substrate state | Observable (real count, not a score) |
|---|---|---|
| **Unknown uncertainty** | ensemble holds *n* originals; no cue; no current | `n` |
| **Uncertainty** | cue arrives; current propagates; several originals partially reached | count of originals with ≥1 member reached, and the reached-member count for each |
| **Certainty** | exactly one original has all members reached (req. 6) and all changed (req. 7) → admission | admitted = 1; candidate set collapsed |
| **Release to uncertainty** | R2 fires (novel mosaic) → R1 re-grounds the reference | the *next* cue is measured against a **different reference** |

The IRF paper's determinism index `D = 1 − H(μₙ)/H(μ₀)` has a direct,
non-fabricated substrate reading: the narrowing of the candidate set from *n* to
1 across the recurrence. It requires no probability model, because the substrate's
candidate set is a real enumerable set of admitted originals and the narrowing is
a real physical event.

And the paper's temporal decay of correlation, `C(t) ≈ C₀ e^{−|t−t*|/τ}` —
build-up, peak, fade — arrives **without a τ being authored anywhere.** The fade
is not a decay term. It is R1: the act of recognizing changes what is stored, so
certainty about the old reference necessarily releases. The characteristic time
is set by how fast reconstruction moves the reference, which is set by the
physics of the body.

This is the central theoretical claim of this study and the thing to argue about
if any of it is to be argued about:

> **The release of certainty is not a decay term added to memory. It is the
> arithmetic consequence of memory being reconstructive.**

If that claim is right, the design is not five mechanisms; it is one mechanism
(R1) plus its boundary condition (R2), its plurality (R3), its cost (R4), and its
floor (R5).

---

## 5. Immutability, resolved rather than overruled

There is an apparent conflict between Joe's charge and the ratified
content-addressed append-only hippocampal custody, which is emphatic:
`hippocampal_directory_cold_store.rs:13` — "This store never mutates or deletes an
object." Objects are re-read and re-verified against their own SHA-256 on every
read; `publish_hippocampal_admission_checked` refuses a re-publish that is not
byte-identical.

The conflict is not real, and the distinction is worth stating as doctrine because
it will otherwise be re-litigated:

> **An episode is a receipt. A memory is a reference. Receipts are immutable;
> references are not.**

- **The chain stays exactly as it is.** Every reconstruction that ever happened
  remains an immutable, content-addressed, append-only record. That is what makes
  R3's amplitudes truthful rather than invented — they are counts over receipts
  that cannot be edited.
- **The reference becomes mutable.** What the cohort currently uses to recognize
  something is re-derived at each successful reconstruction.

This is also the biology. The record of what the organism did is not stored
anywhere in a brain; what is stored is a reference that changes every time it is
used. Guala is in the unusual position of having both, and should keep both, with
the roles kept strictly separate. Any proposal to make the chain mutable, or to
make the reference immutable, should be refused on sight.

---

## 6. Falsification and proof obligations

Nothing here ships on argument. Each law carries a test that can kill it. All
tests are same-organism, same-budget, receipts-reported-never-forced.

**P1 — Repeat-cue drift is cured (kills R1 if it fails).**
Present the same card at encounters 1..10. Record the exact
`PhysicalMosaicError` variant or admission at each encounter. Current law is
expected to fail at some *k* and possibly wander back. Under R1, admission holds
for all *k*, and **no encounter shows the §1.2 wander-back signature** (admission
achieved with a member-delta explained by drift rather than by cue-driven
current). Report the reached-member count per encounter, not a pass/fail.

**P2 — The prediction-error boundary holds (kills R2 if it fails).**
Assert the retained reference is **byte-identical** after a recognition that
produced an `already_formed` mosaic, and **changed** after one that produced a
novel mosaic. Both directions required. A design that re-grounds on every recall
fails this test and is wrong per (b).

**P3 — Silent originals are recoverable (kills R3 if it fails).**
A lesson that legitimately retains nothing (dark, or disconnected) must be
retainable on a later lived encounter. Assert the ensemble transitions
empty → non-empty at encounter 2, and that
`OriginalRelationNotConnected` is no longer terminal for a lived formation.

**P4 — Decay is distinguishable from death (kills R4 if it fails).**
With the metabolic path present: in one organism on one budget, an unreinforced
original becomes unreachable while a reinforced one stays reachable. **Without the
metabolic path this test cannot be run**, because exhaustion and forgetting are
the same trajectory. If it cannot be run, R4 does not ship. This is the gate.

**P5 — The determinism arc is real (kills the §4 claim if it fails).**
Log candidate count before cue, partially-reached count during recurrence,
admitted count after, and candidate count at the *next* cue. Require monotone
narrowing followed by release. If certainty does not release without an added
decay term, the central claim of §4 is false and should be reported as false.

**P6 — Bounded resident state, with a physical eviction rule.**
The ensemble must have a cap, and the cap must evict by physics — lowest
reachability under current dissipation — not by recency. This is the one place
the design needs a genuinely new law rather than a re-use, and it should be
authored explicitly rather than smuggled in. Note the precedent in (d): SHY's
down-selection eliminates weak connections while preserving the relative strength
of survivors, and it runs during sleep. Ratification-queue item D ("TRUE DARK
TIME") already provides exactly that interval for exactly independent reasons.
**Recommendation: the down-selection pass runs in real dark time and nowhere
else.** It must never run during a stimulus.

**P7 — Existing behaviour preserved.** The full native suite green with documented
pins; the served-path recognition gauntlet re-run with receipts; the four
stimulus-boundary proof obligations from the 2026-08-05 ratification satisfied
first, not concurrently.

---

## 7. Ship order, and what blocks what

```
Stage 0  (in flight, endorsed, not this study's work)
         Stimulus-boundary closure + participation retention.
         Its 4 proof obligations satisfied. Transport lie fixed.
         ── nothing below starts until Stage 0 is green ──

Stage 1  R2 alone, as an observation.
         Log already_formed vs novel per recognition. No behaviour change.
         Cost: near zero. Purpose: prove the prediction-error signal is
         real and well-behaved on live lessons BEFORE anything depends on it.

Stage 2  R1 gated by R2.
         Re-ground the reference on novel reconstruction only.
         Proofs: P1, P2. This is the drift cure and the highest-value ship
         in the whole study.

Stage 3  R3 — bounded ensemble, derived amplitudes.
         Proofs: P3, P5, P6. Requires the P6 eviction law authored.
         Requires hippocampal navigation to have a read binding
         (night-shift post-deploy queue item 3) before amplitudes can be
         derived on the live path.

Stage 4  R5 made informationally real.
         Derive the plastic constants (currently authored literals at
         virtual_material_neuron_genesis.rs:48-59); carry through the
         2026-08-05 geometric anatomy differentiation. Until this, the
         irreversible tier is ~1 bit per neuron.

Stage 5  R4 — decay on spent dissipation.
         BLOCKED on ratification-queue items B and C (membrane return path,
         recovery firing). Proof: P4. Do not ship before P4 can be run.
```

The ordering is not preference. Stage 2 is safe without Stage 3 (a single
re-grounded reference is strictly better than a single frozen one). Stage 3 is
safe without Stage 5 (an ensemble that never fades is bounded by P6's eviction,
which is a capacity law, not a decay law). Stage 5 without B and C is a truth
violation. Any reordering should be argued against those three sentences.

---

## 8. Explicitly not proposed

Recorded so that none of these is later mistaken for part of this design:

1. **No stored strength, weight, score, or confidence per memory.** R3's
   amplitudes are derived counts. A stored weight would violate the non-flattened
   capital law and would be the first step back toward a similarity threshold.
2. **No wall-clock or authored time constant.** No τ, no half-life, no
   forgetting curve fitted to anything. R4's clock is spent dissipation on a
   derived capacity.
3. **No semantic content anywhere in this path.** The originals carry neuron
   indices, exact compact fractal deltas, and bond references. No label, word,
   meaning, transcript, or owner — as `AdmittedPhysicalMosaic` already
   guarantees.
4. **No shadow store, no dual-write, no parallel recall backend.** One system.
   Standing doctrine.
5. **No mutation of the hippocampal chain.** §5. The chain is what makes the
   design's numbers true.
6. **No relaxation of `admit_physical_mosaic`.** No tolerance, no partial credit,
   no "close enough" recognition. Requirements 6 and 7 stay exact. If recognition
   fails, the correct answer is that it failed.
7. **No re-grounding on perfect repeats.** R2 is a constraint, not an
   optimisation. Removing it produces a system that overwrites its reference on
   every recall, which the literature says is wrong and which would reintroduce
   drift by a different route.
8. **No fabricated or hand-edited state to make a test pass.** Augmenting the
   organism's data is legitimate only through real mechanisms.

---

## 9. Open questions for ratification

1. **P6's eviction law.** Lowest-reachability-under-current-dissipation is this
   study's recommendation, but it is the one genuinely new law here and it
   deserves its own argument. What is the derived cap on ensemble size? Candidate:
   the existing encode budget (`FormationError::BudgetExceeded`,
   `resident_cognitive_formation.rs:1436`) currently *refuses the transition*
   rather than evicting. Converting refuse-transition into
   capacity-with-replacement is a real semantic change and should be ratified
   separately.
2. **Does R1 re-ground the masks, or only the states?** This study proposes
   replacing `gate_work_perturbed_neurons` and `active_electrical_contacts` with
   the recurrence's own observed masks, on the grounds that a reference should
   describe the reconstruction that last worked. The alternative — union
   accumulation, as `or_bits` already does within a single recurrence — would
   make references monotonically more permissive over time and would eventually
   admit anything. **Recommendation: replace, do not union.** Flagged because it
   is the design's least obvious choice and the easiest to get wrong.
3. **Latent defect to verify before any of this.**
   `extend_resident_cohort_evidence` (`resident_cognitive_formation.rs:1874`) is
   applied to `retained_experience` at `:1914` and resizes
   `gate_work_perturbed_neurons` to the new neuron count, but does **not** extend
   `active_electrical_contacts` — while encode and decode both assert
   `active_electrical_contacts.len() == anatomy.contact_count()`
   (`:2513`, `:2664`). If cohort growth ever adds contacts, encode fails on a
   grown cohort. Not verified by this study whether growth adds contacts in
   production. **Should be checked and, if real, fixed before Stage 2**, since R1
   makes reference rewriting routine rather than rare.
4. **Restore-time asymmetry.** `decode_optional_experience_evidence` (`:2763`)
   re-counts changed members and rejects `< 3`, but does **not** re-check
   connectivity, while the retention predicate at `:2050` checks both. Under R1
   the reference is rewritten often and therefore encoded often; the asymmetry
   becomes load-bearing. Recommend aligning decode with the retention predicate.

---

## 10. Summary for the ratification decision

The substrate reconstructs. It does not remember, because its reference is frozen
and its body is not.

- **R1** makes the reference re-derived instead of stored. Cures drift and the
  wander-back false positive by construction.
- **R2** gates R1 on prediction error, using a comparison the tree already
  computes (`already_formed`). Zero new constants. Required by the science; a
  design without it is wrong in a way the literature has already documented.
- **R3** replaces one snapshot with a bounded ensemble whose amplitudes are
  derived counts over the immutable episode chain, never stored scores. Repairs
  the silent-original trap without special-casing it.
- **R4** makes decay real by indexing it on spent dissipation against a derived
  capacity — no authored τ. **Blocked on metabolism; must not ship early.**
- **R5** keeps permanent plastic geometry out of decay's reach: a faded memory is
  silent, not erased. Exactly the silent-engram result.

The uncertainty → certainty → uncertainty arc then falls out arithmetically
rather than being modelled: certainty releases because the act of remembering
changed what is stored.

Immutability is not abolished. It is put where it belongs — on the receipts, not
on the memory.

---

## Sources

External science:
- [Prediction error demarcates the transition from retrieval, to reconsolidation, to new learning (Sevenster, Beckers & Kindt)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4201815/)
- [The fate of memory: Reconsolidation and the case of Prediction Error (Fernández, Boccia & Pedreira)](https://www.sciencedirect.com/science/article/abs/pii/S0149763415301639)
- [Demarcating the boundary conditions of memory reconsolidation: an unsuccessful replication](https://www.nature.com/articles/s41598-022-06119-5)
- [Limits on lability: boundaries of reconsolidation and the relationship to metaplasticity](https://pubmed.ncbi.nlm.nih.gov/29474957/)
- [Silent memory engrams as the basis for retrograde amnesia (Roy et al., PNAS)](https://www.pnas.org/doi/10.1073/pnas.1714248114)
- [Memory engrams: recalling the past and imagining the future (Josselyn & Tonegawa, Science)](https://www.science.org/doi/10.1126/science.aaw4325)
- [Neurons are recruited to a memory trace based on relative neuronal excitability immediately before training (Yiu et al.)](https://pubmed.ncbi.nlm.nih.gov/25102562/)
- [Intrinsic neural excitability biases allocation and overlap of memory engrams (J. Neurosci.)](https://www.jneurosci.org/content/44/21/e0846232024)
- [The Biology of Forgetting — A Perspective (Davis & Zhong, Neuron)](https://www.cell.com/neuron/fulltext/S0896-6273(17)30498-1)
- [Neural, cellular and molecular mechanisms of active forgetting](https://www.frontiersin.org/articles/334951)
- [Sleep and synaptic down-selection (Tononi & Cirelli)](https://pubmed.ncbi.nlm.nih.gov/30614089/)
- [Systems consolidation, transformation and reorganization: MTT, TTT and their competitors (Moscovitch & Nadel)](https://neuropsychologylab.psych.utoronto.ca/files/Systems%20consolidation,%20transformation%20and%20reorganization%20Multiple%20Trace%20Theory,%20Trace%20Transformation%20Theory%20and%20their%20Competitors.pdf)
- [Memory transformation and systems consolidation](https://neuropsychologylab.psych.utoronto.ca/files/Memory%20transformation%20and%20systems%20consolidation.pdf)
- [CA3 retrieves coherent representations from degraded input (Neunuebel & Knierim, Neuron)](https://www.cell.com/neuron/fulltext/S0896-6273(13)01085-4)
- [Partial EC outputs by degraded cues are amplified in hippocampal CA3 circuits (PLOS One 2023)](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0281458)

In-repo:
- `Information_Resonance_Fields_and_Premonition__Like_Inference_in_High__Dimensional_Histories__A_Theoretical_Framework.pdf` — §3.2 epochal eigenmodes and amplitudes, §5.2 determinism index, §6.2 temporal decay of correlation, glossary (untethered potential, negative space, entropic flip).
- `docs/GUALA_STIMULUS_BOUNDARY_RETENTION_RATIFICATION_2026-08-05.md`
- `docs/GUALA_D3_PHYSICAL_MOSAIC_RECALL_CAPITAL_SPINE_2026-08-04.md`
- `docs/GUALA_NIGHT_SHIFT_20260805_CLAUDE.md` — ratification queue items B, C, D and the measured ledger numbers.
- `native/guala_core/src/physical_mosaic.rs`, `resident_cognitive_formation.rs`,
  `complete_neuron.rs`, `hippocampal_sparse_path.rs`,
  `hippocampal_directory_cold_store.rs`, `optical_receptor_work.rs`,
  `virtual_material_neuron_genesis.rs`.
