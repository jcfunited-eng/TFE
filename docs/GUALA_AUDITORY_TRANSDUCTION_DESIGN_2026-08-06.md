# Auditory transduction — design study

Date: 2026-08-06
Status: **DESIGN STUDY. Nothing implemented in production. Nothing committed.**
Tree studied: `/tmp/guala-production-15a7dca9`, branch `salvage/codex-d3-work-20260805`,
HEAD `ea30bd18` at the start of this session plus the working-tree changes then
present. **Another session was working in the same tree concurrently and advanced
HEAD to `6c4f3a0e` during this study**; every line number below was read against
`ea30bd18` + working tree and should be re-checked before implementation.
Measurement code added under `#[cfg(test)]` only
(`native/guala_core/src/scratch_auditory_probe.rs`, plus one `#[cfg(test)] mod`
line in `lib.rs`). No production logic was changed. Nothing was committed.

> Discharges the obligation left open by
> `docs/GUALA_QUANTIZED_OPTICAL_TRANSDUCTION_RATIFICATION_2026-08-05.md:45`:
> *"Auditory transduction commensurability (whether ear gates can open under
> sound) — to be MEASURED and reported during this work, changed only with a
> further ratification."*

This paper measures what the ears actually receive, measures what the ears
actually do with it, proposes the receptor law, and measures whether that law
is commensurate with the gate lattice it must drive. It is written to be
ratified, amended, or refused as a whole.

All line numbers are working-tree lines in `/tmp/guala-production-15a7dca9`.

---

## 0. Verdict up front

The ears are not weakly connected. They are **not connected at all**, and the
gap is one law wide, not one architecture wide.

> Sound reaches the organism as samples and stops there. No receptor law
> consumes pressure, so amplitude has exactly zero physical effect; and because
> the occurrence gate admits only sight, an ear occurrence cannot even grow the
> cell that would consume it.

The cure does not require a new mechanism. It requires **one transduction law
with one composite constant**, and that constant is not free: it is pinned by
the receiving gate's own dissipation lattice. Everything downstream — quantized
delivery, threshold integration, residue retention, stimulus-boundary closure,
metabolism — is already ratified, already compiled, and accepts the acoustic
integrand unchanged. I measured that directly (§4.4).

Three doctrines constrain this and none of them obstruct it. The **two-real-signal
doctrine** is untouched: this law changes what tutor audio *does* inside a card
lesson, never whether standalone hearing is admitted. The **lean-substrate
doctrine** is satisfied by one added `ExactRational` per ear site and nothing
else, and the law's residue bound is stated in §8.2. The **all-at-once doctrine**
is served: nothing here is shadowed, gated, or parallel.

One finding does not fit in a law and must be decided by Joe: **with two ear
ports, sound can never retain a recognizable original, no matter how good the
transduction law is** (§1.6). That is structural, it is measured, and it is the
single most important thing in this paper.

---

## 1. What is actually built (verified against source)

### 1.1 What actually reaches the ears

| # | Fact | Source |
|---|---|---|
| 1 | Two ear ports, `sense = SOUND`, topology 0 and 1 | `dsf_ai_service/native_production_app.py:911-927` |
| 2 | Declared quantity `normalized_physical_excitation`, unit `normalized_binary64` | `native_production_app.py:135-136, 922-923` |
| 3 | Samples are raw signed PCM divided by full scale — `window[index] / 32768.0` | `native_production_app.py:1407` |
| 4 | Decimated by picking every stride-th sample; stride 16 at 16 kHz over a 250 ms hop → 250 retained frames | `native_production_app.py:1395-1408` |
| 5 | Both ears receive the **identical** sample tuple; `phase_turns` are all exactly zero | `native_production_app.py:930-940, 926` |
| 6 | Sight and sound are always in **separate occurrences** during experience | `native_production_app.py:1446-1461, 1638-1650` |
| 7 | The only live producer of a nonzero ear signal is tutor audio inside `/api/v1/curriculum/teach-card`; every standalone hearing endpoint refuses 503 | `native_production_app.py:1939-1943, 1976-1978, 2045-2047` |

Two naming facts matter for any law keyed on a declared quantity. The served
port calls its physical quantity `normalized_physical_excitation` — which is not
a physical quantity, it is a statement that a number was normalised. The Rust
fixtures call the same thing `acoustic-pressure` / `normalized-binary64`
(`native/guala_core/src/neuron_source_anchor.rs:672-673`). The optical law keys
on `retinal-spectral-irradiance` and refuses anything else
(`optical_receptor_work.rs:194-199`). An auditory law must key on a name that
says what the number is; the served name does not, and must change with it.

### 1.2 The defect, measured

Probe: `scratch_auditory_probe::measured_sound_amplitude_has_exactly_zero_physical_effect`.
One isolated acoustic occurrence carrying the **served** port names is prepared
against a genesis body at amplitudes 1.0, 0.5, 0.1.

```
amplitude    1: neurons=0 transitioned=0 fractals=0 mosaics=0 reassembly=0
   body bytes 140 -> 140, differing byte offsets from genesis: [10]
amplitude  0.5: neurons=0 transitioned=0 fractals=0 mosaics=0 reassembly=0
   body bytes 140 -> 140, differing byte offsets from genesis: [10]
amplitude  0.1: neurons=0 transitioned=0 fractals=0 mosaics=0 reassembly=0
   body bytes 140 -> 140, differing byte offsets from genesis: [10]
all three amplitudes produced byte-identical successor bodies
```

A tenfold change in sound amplitude moves **one byte**, and that byte is the
cognitive ordinal counter. Not one neuron is grown, transitioned, or perturbed.
This is the measurement the optical ratification asked for, now on the record
rather than in a commit message.

### 1.3 The defect, in code

Two independent blocks, both of which must be opened:

```rust
// native/guala_core/src/resident_cognitive_formation.rs:3507-3519
fn exact_optical_occurrence(...) -> bool {
    !occurrence.port_indices.is_empty()
        && occurrence.port_indices.iter().all(|index| {
            source.joint_source_ports().get(*index).is_some_and(|port| {
                port.sense == 0
                    && port.physical_quantity == RETINAL_SPECTRAL_IRRADIANCE_QUANTITY
                    && port.physical_unit == RETINAL_REFERENCE_IRRADIANCE_UNIT
            })
        })
}
```

* At `:955-960` a non-optical, non-vestibular occurrence with no existing cohort
  is `continue`d — **the ear cell is never grown.**
* At `:1111-1112` settlement runs only `if optical_occurrence || vestibular.is_some()`
  — **even a grown ear cell would never settle.**

`optical_receptor_work.rs:191-192` independently refuses `sense != 0` with
`NotSight`. There is no other receptor-work law in the crate that filters on
sense. The ears therefore carry samples into the joint field and the L0–L4 bank
and physically stop.

### 1.4 The two ratified receptor precedents, and which one sound belongs to

The tree already contains two complete, ratified, structurally different
receptor laws. Choosing between them is the first real design decision.

**Optical — energy delivery** (`optical_receptor_work.rs`). Irradiance fraction
`L` is integrated exactly by trapezoid over the interval, scaled by declared
reference irradiance, aperture, absorptance, and conformational coupling to give
`2·L·T` zJ; that energy accumulates in a per-site exact-rational residue and is
delivered as **whole quanta on the receiving gate's own dissipation lattice**,
only once the accumulation reaches that gate's own opening threshold, capped at
that gate's own window (`resident_cognitive_formation.rs:1171-1207`,
`complete_neuron.rs:2245-2280`).

**Vestibular — mechanical bias** (`local_cupula_hair_bundle_geometry.rs` →
`local_tip_link_extension.rs` → `local_gating_spring_energy.rs` →
`vestibular_neuron_path.rs:415-432`). Cupula displacement becomes bundle slope,
becomes tip-link extension, becomes the two-conformation gating-spring energy
`ΔE(C→O) = ΔE° − κ·d·(x + x_C − d/2)`, which is handed to the gate **directly as
`gate_work` with no quantization and no accumulator.**

The difference is not an inconsistency. Photoreception *absorbs energy*;
mechanotransduction *biases a barrier with force*. The two laws differ because
the physics differs.

Sound is mechanical, so the vestibular pattern is the obvious candidate — and it
is wrong, for a reason that is itself physics. Sound has zero mean. Its period
(0.1–10 ms for speech) is two to four orders of magnitude shorter than a
settlement interval. **A signed-pressure mechanical bias evaluated once per
interval integrates to approximately zero**: the positive and negative half
cycles cancel, and a louder sound cancels no less exactly than a quiet one. A
literal transcription of the vestibular chain onto the ear would reproduce the
present deafness with more code.

Nature's answer is the same as the correct engineering answer. What survives
averaging over many acoustic cycles is not pressure but **acoustic intensity**,
`I = p²/Z`, which is quadratic and therefore non-negative. The hair cell's known
rectifying sigmoid is the biological expression of the same fact. Sound
therefore belongs with the **optical** law in form — an energy law with
quantized threshold-integrated delivery — while remaining mechanical in origin.

### 1.5 What already exists and is unused

`native/guala_core/src/auditory.rs` contains a complete causal sixteen-channel
fourth-order gammatone cochlea with streaming continuation state, per-channel
RMS envelopes at a 160-sample observation hop, carrier-phase accumulation, and
an analytic bound check (`auditory.rs:171-187`). It is compiled into the shipped
wheel and asserted present by `tests/test_production_api_surface.py:21-22`.

**No production code calls it.** Its only callers are
`dsf_ai_service/substrate/senses/auditory_full_field_provider.py` and the retired
Python engine, neither of which is in the release manifest, plus
`native/guala_core/tests/test_auditory_gammatone_differential.py`. This matters
in §3.7 and §8.3: the tonotopic front end this design wants already exists in
the binary and is dark.

Separately, `HANDOFF_2026-07-25_LIVE_HEARING.md` records an auditory
kind/memory/stream stack that was proven and never wired. That stack is a
*recognition* architecture built on ternary motif paths, not a receptor law, and
this design does not revive, extend, or depend on it. It is named here only so
that its existence is not later mistaken for a transduction law.

### 1.6 The structural finding that no transduction law can fix

```rust
// native/guala_core/src/resident_cognitive_formation.rs:2266-2283
if member_indices.len() >= 3
    && connected_members(...)
{
    experience.post_experience_rest = Some(settlement.successor.clone());
    cohort.retained_experience = Some(experience);
}
```

Participation retention (ratified 2026-08-05) requires **at least three changed
members connected through contacts active during the experience.** The served
ear occurrence carries exactly **two** ports (`EAR_PORT_COUNT = 2`,
`native_production_app.py:123`), and sight is in a *different* occurrence and
therefore a *different* cohort (`native_production_app.py:1446-1461`).

Therefore: **with the served anatomy, a perfectly working auditory transduction
law would open ear gates, burn fuel, emit fractals, and retain nothing, forever.**
The ears could hear and could never remember. This is measured structure, not a
prediction, and it is the reason §3.8 (tonotopy) is not an optional refinement.

Worse, the two ear ports receive byte-identical samples
(`native_production_app.py:930-940`), so the two ear cells would be bit-identical
for life. Two neurons that always agree carry one neuron's worth of structure.

### 1.7 Measured constraints that bound any proposal

From `docs/GUALA_NIGHT_SHIFT_20260805_CLAUDE.md`, the optical ratification, and
this session's probes:

* Gate lattice, measured for an ear site at genesis: quantum **1/16 zJ**,
  capacity **36 quanta**, opening threshold **17 quanta (17/16 zJ)**, window cap
  **52 quanta (13/4 zJ)**. (`measured_ear_gate_opening_window_at_genesis`.)
* Optical full-scale transduction rate is **2 zJ/s**; full-scale light saturates
  the window cap in **1.625 s**.
* **A lit lesson already burns ~386 fuel of a 14,607 pool — about 38 lessons to
  exhaustion.** Adding a second energy-delivering sense shortens that. No
  auditory deploy may precede the metabolism obligations already queued.
* **DNA expression is uncatalyzed everywhere; neuron count is capped at birth
  anatomy.** A tonotopic ear cannot be grown later — it must be born.
* The retained residue has **no decay term** anywhere
  (`complete_neuron.rs:1999, 2875`), and its doc comment at `:940-945` claiming
  it stays "inside `[0, gate dissipation quantum)`" is **stale**: under
  threshold-integrated delivery it lawfully reaches `threshold − 1` = 16 quanta,
  and this session measured **3.26 quanta** retained after one real utterance.
* `WORLD_MECHANICAL_TICK_MICROSECONDS = 1000` (1 ms) is handed to the neuron as
  `interval_microseconds` for every optical delivery
  (`resident_cognitive_formation.rs:1205`) regardless of the occurrence's real
  span. Any auditory law inherits this placeholder; it is flagged in §8.4.

These are not objections to the design. They are its schedule.

---

## 2. What the physics says

**(a) Acoustic intensity is quadratic in pressure and never negative.**
`I = p²/Z`, where `Z = ρc` is the characteristic acoustic impedance of the
medium (≈415 Pa·s/m for air at room conditions). Dimensionally
`Pa²/(Pa·s·m⁻¹) = W·m⁻²`. Energy through an aperture `A` over an interval is
`∫ I·A dt`. This is the exact structural analogue of the optical
`∫ irradiance · A dt`, differing only in that the integrand is squared — and the
square is not a modelling choice, it is the definition of the quantity that
carries the energy.

**(b) The rectification is therefore free.** Hair cells are famously rectifying:
their open probability rises with positive bundle deflection and cannot fall
below zero, producing a net DC depolarisation under a zero-mean stimulus. A law
built on `s²` reproduces that asymmetry as a consequence of energy conservation
and needs no half-wave rectifier, no envelope detector, no absolute value, and
no threshold on the sample. Silence gives exactly zero because zero squared is
zero — the same way darkness gives exactly zero for light.

**(c) Cochlear place coding is spectral decomposition, and it is upstream of the
receptor cell.** The basilar membrane's travelling wave assigns frequency to
place before any hair cell transduces anything (von Békésy). In this organism's
architecture that decomposition belongs to the *sensor*, in the same layer where
the camera's luminance extraction (`/255.0`) already lives — not inside the
receptor law, which stays exact-rational.

**(d) Auditory temporal integration in humans is on the order of 200–300 ms** for
detection near threshold, not seconds and certainly not days. A receptor
accumulator with no leak is physically defensible over a hop and questionable
over a lesson boundary. §8.2 records this rather than smuggling a decay term in.

**(e) Interaural differences require head geometry.** Interaural time difference
and head shadow are consequences of a declared head of declared size. With no
head declared, two co-located ears receiving one ambient pressure field is the
honest state — and it is what is served. It is honest and it is structurally
sterile (§1.6).

---

## 3. The design

Six laws, one wiring fix, two anatomy corrections, one transport correction.
Each is stated with its constant provenance, its doctrine check, and its cost.

### Law A1 — Acoustic energy at the receptor aperture

> The incident acoustic energy on one ear receptor site over one settlement
> interval is the exact trapezoidal integral of the squared normalized pressure
> sample, scaled by declared receptor anatomy:
> `E_incident = (p_ref² · A_ear / Z_medium) · ∫ s(t)² dt`,
> where `s(t)` are the port's own exact normalized sources and `p_ref` is the
> declared reference pressure that *defines what |s| = 1 means in pascals*.

**Why it is the right shape.** It is `optical_receptor_work::settle_port`
(`:214-233`) with one change: the integrand is `mean(sᵢ², sᵢ₊₁²)` instead of
`mean(Lᵢ, Lᵢ₊₁)`. Same exact-rational trapezoid, same clock-advance refusal,
same sample-cardinality refusal, same absence of DSF coordinates from the
conversion. It introduces no new arithmetic — squaring a `BigRational` is exact.

**Why it is truthful.** Every factor has a physical unit and a real meaning:
reference pressure (Pa), aperture (m² or nm²), characteristic impedance
(Pa·s/m). None of them is a fitted coefficient. Their *product* is pinned by
Law A5, so no individual number is free to be tuned.

**It does not touch sight, the vestibular chain, or the DSF path.**

### Law A2 — Absorption and conformational coupling

> Absorbed energy is incident energy times the declared middle-ear transmission;
> transduced energy is absorbed energy times the declared conformational
> coupling. Both lie in `(0, 1]`, and an anatomy declaring otherwise is refused
> without a fallback.

Verbatim the optical structure (`OpticalReceptorAnatomy::new`, `:34-57`), same
validity predicate, same `InvalidAnatomy` refusal. Middle-ear transmission is
the physical name for what absorptance is on the optical side.

### Law A3 — Rectification is a consequence, not a mechanism

> The auditory receptor law contains no rectifier, no envelope detector, no
> absolute value, and no per-sample threshold. Non-negativity is a theorem of
> the law, not a clause of it: `s² ≥ 0` for every lawful sample, therefore
> transduced energy is non-negative, therefore the residue invariant of the
> ratified delivery law holds unchanged.

This is the load-bearing elegance of the design and the reason the existing
delivery machinery accepts the acoustic integrand with **zero modification**
(measured, §4.4). It is also the reason silence is a lawful state that delivers
nothing and erases nothing — exactly the ratified property of darkness.

### Law A4 — Quantized threshold-integrated delivery, unchanged

> Transduced acoustic energy enters the same per-site exact-rational accumulator
> and is delivered as whole quanta on the receiving gate's own dissipation
> lattice, only once the accumulation reaches that gate's own opening threshold,
> capped at that gate's own window. `quantize_optical_delivery` and
> `gate_opening_quantum_window` are reused verbatim.

Implementation is a rename to `quantize_receptor_delivery` in a shared module,
with **zero behavioural change for sight** — the function body is already
modality-blind (`optical_receptor_work.rs:134-179`; it takes an energy, a
residue, a lattice step, a threshold, and a cap, and knows nothing about light).
The per-neuron state field `optical_quantum_residue` becomes
`receptor_quantum_residue`; its codec width and non-negativity invariant are
unchanged, so the persisted-body format is unchanged.

**No new constant is introduced by this law. Not one.**

### Law A5 — Commensurability is pinned by the gate, not chosen

> The single composite constant of Law A1,
> `K = p_ref² · A_ear · transmission · coupling / Z_medium` (units: zJ per
> second), is not authored as four free numbers. It is pinned by the receiving
> gate's own lattice under the same rule the optical anatomy already satisfies:
> **a full-scale stimulus (`|s| ≡ 1`) sustained over one reference interval
> delivers exactly the gate's own window cap.**

Because the served samples are normalised to the *recording's* full scale
(`/32768.0`), there is no absolute sound pressure anywhere in the pipeline.
`p_ref` is therefore not a measurement of the world; it is the declaration of
the organism's full-scale sensitivity — its dynamic range — and pinning it by
the gate is the only derivation available that does not invent a number.

§4 measures three candidate pinnings and recommends one.

### Law A6 — Refusal surface

> The auditory law refuses, without fallback or clamp: a port that is not
> sense SOUND; a physical quantity or unit other than the declared acoustic
> pair; fewer than two samples; a sample count that disagrees with the time
> count; a clock that does not advance; a sample outside `[-1, 1]`; a negative
> predecessor residue; a non-positive lattice quantum; a zero opening threshold.

Mirrors `OpticalReceptorWorkError` (`:69-84`) one-for-one. Note the range: the
optical law narrows to `[0, 1]` because irradiance cannot be negative; the
acoustic law admits the full signed unit interval `[-1, 1]` because pressure can,
and squares it. The crate's decode boundary already enforces `[-1, 1]` for every
port (`joint_source_episode.rs:598-600`), so this is a re-assertion at the law,
consistent with how the optical law re-asserts its own narrower range.

### Wiring fix W1 — the occurrence gate must admit sound

> `exact_optical_occurrence` is generalised to a total function returning which
> receptor law governs an occurrence — `Sight`, `Sound`, or none — refusing
> **mixed-sense occurrences** as it does today. Cohort genesis
> (`:955-960`) and settlement (`:1111-1112`) key on that result rather than on
> `optical_occurrence` alone.

This is the ear's transport-lie fix, and it is the reason nothing else in this
design can act without it. It is a pure widening: every occurrence that is
optical today remains optical and takes an identical path.

### Anatomy correction W2 — the ear port must declare a physical quantity

> The served ear port's `physical_quantity` / `physical_unit` change from
> `normalized_physical_excitation` / `normalized_binary64` to the acoustic pair
> already used by the crate's own fixtures — `acoustic-pressure` /
> `normalized-binary64` — so that the receptor law can key on a name that states
> what the number is, exactly as the optical law keys on
> `retinal-spectral-irradiance`.

This changes the genesis anatomy declaration and is therefore an
identity-affecting change: it must land at a rebirth, not on a living body.

### Anatomy correction W3 — tonotopy, or the ears can never remember

> The ear declares **N ≥ 2 tonotopic sites per ear**, each carrying its own band
> of the same ambient pressure field, so that an acoustic occurrence can present
> at least three changed members connected through active contacts and satisfy
> the ratified participation-retention predicate.

Sixteen channels per ear (thirty-two ports) is the natural declaration because
the sixteen-channel cochlea is already compiled and already asserted present
(§1.5). Cost is stated in §7. **§1.6 is the whole argument for this: without it,
the auditory law is a fuel burn with no memory.** And because DNA expression is
uncatalyzed, this anatomy must be *born*, not grown — it lands at a rebirth or
not at all.

### Transport correction T1 — the ear port must carry an alias-free interval energy

> The 250 retained frames per hop must estimate `∫s² dt` over the hop faithfully.
> Stride decimation of a 16 kHz speech waveform by 16, with no band limiting,
> does not.

Measured (§4.2): the served decimation misestimates per-hop acoustic energy by
more than 10% on **27.4% of hops**, with observed errors from **−38% to +113%**,
while remaining unbiased over a whole utterance (mean ratio 0.996). A law that
consumes energy per interval consumes the error per interval.

Three options, in preference order:

1. **Carry the cochlear envelope instead of the waveform.** Run the existing
   gammatone at the full 16 kHz in the transport layer and let each retained
   frame be a per-channel RMS envelope in `[0, 1]`. Alias-free by construction
   (it is an energy average over the whole window, not a pick), non-negative,
   and it delivers W3 in the same move. This is the recommendation.
2. **Retain per-frame RMS over the stride window** rather than the stride-th
   sample. Alias-free for `∫s²` specifically, no filterbank, but discards the
   waveform and gives no tonotopy.
3. **Leave transport alone and accept ±30% per-interval energy error.** Honest
   only if recorded as such.

Option 2's mean-over-stride variant — averaging the *samples* rather than their
squares — is the one option that must be refused: it destroys exactly the energy
the law consumes.

---

## 4. Measured commensurability

This section is the obligation the optical ratification left open. All numbers
are measured, and §10 says how to reproduce each one.

### 4.1 What the tutor corpus actually contains

36 signed tutor recordings, pcm_s16le mono 16 kHz, integrated exactly as the
served pipeline decimates them:

| Quantity | min | mean | max |
|---|---|---|---|
| duration | 1.127 s | 1.863 s | 2.705 s |
| peak `\|s\|` | 0.687 | 0.928 | **1.000** |
| rms `s` | 0.0991 | 0.1354 (**−17.4 dBFS**) | 0.1643 |
| `∫s² dt` per utterance | 1.393e−2 s | 3.469e−2 s | 5.272e−2 s |

The organism's loudest available stimulus runs at **1.83% of full-scale power**.
Some recordings touch `\|s\| = 1.000`, i.e. they clip — worth knowing before any
absolute-level claim is made from them.

### 4.2 What the served decimation costs

Per-hop ratio of served `∫s² dt` to full-rate `∫s² dt`, over 219 hops of 36
recordings:

| min | p05 | median | p95 | max |
|---|---|---|---|---|
| 0.6225 | 0.8739 | 0.9974 | 1.2091 | **2.1316** |

Mean absolute error 8.2%; **27.4% of hops err by more than 10%.** Unbiased in
aggregate, badly wrong per interval. This is the evidence for T1.

### 4.3 Commensurability under three candidate pinnings

Gate facts, measured for an ear site at genesis: quantum 1/16 zJ, opening
threshold 17 quanta, window cap 52 quanta.

| Pinning | K (zJ/s) | full-scale saturates cap in | mean utterance | lessons to first ear-gate opening (mean / quietest / loudest) |
|---|---|---|---|---|
| full scale = cap over a 250 ms hop | 13 | 0.250 s | 7.22 quanta | **3 / 6 / 2** |
| full scale = cap over a 1.5 s dwell | 13/6 ≈ 2.167 | 1.500 s | 1.20 quanta | 15 / 36 / 10 |
| **optical parity: K = 2 zJ/s** | **2** | **1.625 s** | **1.11 quanta** | **16 / 39 / 11** |

**Recommendation: optical parity, `K = 2 zJ/s`.** It introduces no number that
is not already in the tree — it is literally the optical full-scale rate — and
it makes full-scale sound and full-scale light equally energetic to the
organism, which is the only defensible statement in the absence of a declared
absolute SPL. Note that it falls within 9% of the independently-derived 1.5 s
dwell pinning; the two arguments converge, which is the main reason to trust
either.

The consequence must be stated plainly: **under optical parity, real tutor
speech opens its first ear gate during roughly the sixteenth card lesson**, with
residue carried across lessons. That is slow, it is honest, and it is exactly
the ratified "dim = slower" behaviour applied to a stimulus running at 1.8% of
full-scale power. If Joe wants the ears live sooner, the lever is not the
constant — it is the tutor audio level, and raising it is an honest change to
the world, not to the physics.

### 4.4 The ratified delivery machinery accepts the acoustic integrand unchanged

Probe: `measured_acoustic_energy_conserves_through_the_ratified_delivery_machinery`.
Six real 250 ms hops of `a-apple-tutor-v1.wav` followed by two silent hops, fed
through the **unmodified** `quantize_optical_delivery`:

```
hop 0: energy=5889/6250000000 zJ delivered=0 quanta retained=5889/6250000000 zJ
hop 1: energy=5294679/125000000 zJ delivered=0 quanta retained=264739839/6250000000 zJ
...
hop 5: energy=45435169/1000000000 zJ delivered=0 quanta retained=5098245581/25000000000 zJ
hop 6: energy=0 zJ delivered=0 quanta retained=5098245581/25000000000 zJ
hop 7: energy=0 zJ delivered=0 quanta retained=5098245581/25000000000 zJ
openings=0  delivered_total=0 zJ  retained=5098245581/25000000000 zJ
```

Bit-exact conservation (`delivered + retained == Σ energy`) is asserted at
**every step**, not only at the end. Silence adds nothing and erases nothing.
The retained residue after one utterance is 0.2039 zJ = **3.26 quanta** —
which incidentally proves the stale doc comment at `complete_neuron.rs:943`
("always inside `[0, gate dissipation quantum)`") false.

### 4.5 The amplitude law, which is the whole point

Under the 250 ms pinning, over one full hop:

| amplitude | delivered |
|---|---|
| 1.0 | 52 quanta (the cap, by construction) |
| 0.5 | 13 quanta |
| 0.1 | 0 quanta (retained) |

Quarter energy for half amplitude — −6 dB — which is what physics requires and
what the present organism cannot express at all.

---

## 5. Falsification and proof obligations

Nothing here ships on argument. Each carries a test that can kill it. All tests
are same-organism, same-budget, receipts reported and never forced.

**P1 — Conservation (kills A4 if it fails).** Over arbitrary interval sequences
of real tutor energies including silences and clipped hops, delivered quanta ×
lattice step + retained residue equals the exact `Σ K·∫s²dt` at every step, with
`residue ≥ 0` at every step. Already demonstrated (§4.4) and must be re-run
inside the shipped law.

**P2 — Amplitude (kills A1/A3 if it fails).** The same lesson at amplitudes 1.0,
0.5, 0.1 must produce three **different** bodies, with delivered energies in the
exact ratio 1 : 1/4 : 1/100. Report the delivered quanta per amplitude. This is
the direct inverse of the §1.2 measurement and is the headline proof.

**P3 — Silence (kills A3 if it fails).** A silent hop must deliver exactly zero,
change no gate, and leave the residue bit-identical. A silent *lesson* must
produce a body differing from its predecessor only in the ordinal.

**P4 — Sight is unchanged (kills the whole design if it fails).** After the
`quantize_optical_delivery` → `quantize_receptor_delivery` rename and the W1
widening, a replayed lit card lesson must produce a **byte-identical** body to
the pre-change replay. Sight regression is an immediate stop.

**P5 — Retention (kills W3 if it fails).** An acoustic occurrence must retain a
connected original. Report the changed-member count and the active-contact count
per occurrence, not a pass/fail. Under the served two-port anatomy this test
**cannot pass** (§1.6); if it cannot pass, the auditory law does not ship. This
is the gate.

**P6 — Metabolism (blocks deploy if unmet).** Re-measure fuel burn per lesson
with both senses delivering. The lit lesson already costs ~386 of 14,607.
Report the two-sense figure and the resulting lessons-to-exhaustion. **No
auditory deploy while that number is smaller than the already-queued metabolism
work can absorb.**

**P7 — Alias error (kills T1 option 3).** After the transport correction, the
per-hop served-vs-full-rate `∫s²` ratio must lie within a stated bound over the
whole corpus. Report the distribution, not the mean.

**P8 — Everything already ratified still holds.** Native suite green; the
stimulus-boundary and quantized-optical proof obligations satisfied **first**,
not concurrently; the two-real-signal refusals still return 503 with unchanged
reasons; persisted-body decode of pre-change bodies unchanged.

---

## 6. Ship order, and what blocks what

```
Stage 0 — W1 occurrence-gate widening + delivery rename, no auditory law yet
          proofs: P4 (byte-identical sight replay), P8
          cost: no new state, no new constant
          ── nothing below starts until Stage 0 is green ──

Stage 1 — T1 transport correction (recommend option 1: cochlear envelope)
          proofs: P7
          cost: transport only; organism untouched
          ── nothing below starts until Stage 1 is green ──

Stage 2 — Laws A1, A2, A3, A6: acoustic energy -> transduced energy
          proofs: P2 amplitude ladder at the law boundary, P3 silence
          cost: one new anatomy struct; no persisted state change

Stage 3 — Laws A4, A5: delivery + gate-pinned constant
          proofs: P1 conservation, P2 end to end, P3 end to end
          cost: residue field renamed, codec width unchanged
          ── nothing below ships without a rebirth ──

Stage 4 — W2 + W3: acoustic quantity names + tonotopic anatomy
          proofs: P5 retention (THE GATE), P6 metabolism
          cost: body growth, §7

Stage 5 — deploy, only after P6 clears against the queued metabolism work
```

The ordering rests on three sentences. Stage 0 is the only change that can
regress sight, so it goes first and alone with a byte-identity proof. Stages 2–3
are inert without Stage 0 and untrustworthy without Stage 1. Stages 4–5 change
identity and cost fuel, so they land at a rebirth and behind the metabolism
obligations that already exist. Any reordering should be argued against those
three sentences.

---

## 7. Cost

* **Per ear site:** one `ExactRational` residue (the existing field, renamed).
  No new persisted state of any kind.
* **Per acoustic anatomy:** one struct of four exact rationals, the same shape
  and size as `OpticalReceptorAnatomy`.
* **W3 tonotopy at 16 channels per ear:** 32 ear neurons instead of 2. Against
  the measured ~116 kB of body per distinct mosaic and the 27 existing card
  sites, this is the dominant cost of the whole design and the number Joe should
  be shown before Stage 4 is authorised. It must be measured, not estimated,
  during Stage 3.
* **Fuel:** a second energy-delivering sense. Unmeasured until P6.

---

## 8. Open questions for ratification

**8.1 — Which pinning?** Recommended: optical parity, `K = 2 zJ/s` (§4.3), on
the grounds that it introduces no new number. The cost is that the first ear
gate opens around lesson 16. The 250 ms pinning opens it at lesson 3 but
declares the ear 6.5× more energetic than the eye with no physical reason.
**This is the easiest thing in the paper to get wrong, because the tempting
answer is the fast one.**

**8.2 — Does the receptor accumulator need a leak?** The ratified residue has no
decay term. Human auditory temporal integration is ~200–300 ms; this residue
integrates across lessons and, at the recommended pinning, across *days*. Adding
a leak is a **new law** that would also change the optical path and must not be
smuggled in under an auditory ratification. Recommendation: **ship without a
leak, record the bound** — the residue is capped at `threshold − 1` = 16 quanta
= 1 zJ per site, which is bounded, lean, and honest — and raise the leak
separately if the behaviour offends.

**8.3 — Cochlea in the transport layer: physics or fitting?** A gammatone
filterbank has empirically fitted ERB spacing and pole placement. It is a model
of basilar-membrane mechanics, not a derivation from one. Placing it in the
*sensor* layer (where the camera's `/255.0` already lives) is consistent, but it
is a real concession and should be named as one at ratification rather than
discovered later. The alternative — T1 option 2, stride-window RMS — is
assumption-free and gives no tonotopy, and therefore cannot satisfy P5.

**8.4 — The 1 ms interval placeholder.** Every optical delivery tells the neuron
`interval_microseconds = 1000` regardless of the occurrence's real span
(`resident_cognitive_formation.rs:1205`). The auditory law would inherit it. Is
that a latent defect in the ratified optical path? It should be checked, and if
real, fixed **before** Stage 3, since a squared-energy law makes interval
truthfulness matter more, not less.

**8.5 — Does this touch the two-real-signal doctrine?** It should not. This law
governs what tutor audio *does* once admitted; it does not admit standalone
hearing. But it does mean that from Stage 3 the ears become an energy-delivering
sense, which raises the stakes of the microphone question when the camera
mounts. Recommendation: **the 503 refusals stay exactly as they are**, and the
microphone question is reopened only by Joe, only with the camera.

---

## 9. Explicitly not proposed

Recorded so that none of these is later mistaken for part of this design:

1. **No revival of the July-25 auditory kind/memory/stream stack.** It is a
   recognition architecture, not a receptor law, and it is not a dependency.
2. **No speech-to-text, no phoneme model, no word boundary, no classifier**
   anywhere in the receptor path, in any layer, under any name.
3. **No shadow or dual-path auditory processing.** One law, or none.
4. **No decay, leak, adaptation, or gain control** in the receptor accumulator
   (§8.2 records the question and refuses to answer it here).
5. **No binaural difference, ITD, or head shadow** until a head geometry is
   declared. Two co-located ears is the honest state.
6. **No change to the optical law's numbers, structure, or behaviour.** P4
   enforces this byte-for-byte.
7. **No new gate lattice, no modality-specific quantum, no auditory-only
   threshold.** The ear uses the gate's own window like everything else.
8. **No absolute SPL claim.** Nothing in the pipeline measures pascals; `p_ref`
   declares the organism's full scale and says so.

---

## 10. How every number here was measured

* **§1.2, §1.7 gate window, §4.3, §4.4, §4.5** —
  `native/guala_core/src/scratch_auditory_probe.rs` (`#[cfg(test)]` only, five
  probes), run with
  `cargo test --lib scratch_auditory_probe -- --nocapture --test-threads=1`.
  This file and the one `#[cfg(test)] mod` line in `lib.rs` are the **only**
  changes to the tree and must be reverted or left uncommitted.
* **§4.1, §4.2** — session scratchpad `measure_ear_energy.py`, which reproduces
  `_pcm_hops` byte-for-byte and integrates `∫s²dt` in exact `Fraction`
  arithmetic at both the served and full capture rates over all 36 tutor
  recordings in `guala_curriculum/audio/`.
* All structural claims cite `file:line` in the working tree and were opened and
  read in this session rather than inherited from a prior document.

---

## 11. Summary for the ratification decision

The ears have no receptor law, and I measured that a tenfold amplitude change
moves exactly one byte, and that byte is a counter.

The cure is one law with one composite constant, and the constant is pinned by
the gate rather than chosen. The delivery machinery, the accumulator, the
threshold window, the stimulus-boundary closure, and the metabolism are already
ratified and already accept the acoustic integrand unchanged — measured, not
argued. Sound belongs with light in *form* (energy, quantized, threshold
integrated) even though it is mechanical in *origin*, because a zero-mean
stimulus averaged over a settlement interval is silence, and only the squared
quantity survives.

* **A1–A3** ship on P2 (amplitude) and P3 (silence).
* **A4–A5** ship on P1 (conservation) and P4 (sight byte-identical).
* **W1** ships first and alone, on P4.
* **T1** ships before any law consumes an interval energy, on P7.
* **W2–W3** ship only at a rebirth, and only if **P5 passes** — and under the
  served two-port anatomy P5 **cannot** pass.

That last line is the paper. A perfect auditory transduction law on the served
anatomy would give the organism ears that hear, burn fuel, and remember nothing,
because retention needs three connected members and the ears are two. Either the
ear is born tonotopic, or it should not be given a receptor law at all yet.

---

## Sources

External science:

* Georg von Békésy, *Experiments in Hearing* — cochlear travelling wave and
  place coding.
* A. J. Hudspeth, "Integrating the active process of hair cells with cochlear
  function", *Nature Reviews Neuroscience* 15 (2014) — hair-bundle
  mechanotransduction, gating springs, rectifying open-probability.
* J. Howard & A. J. Hudspeth, "Compliance of the hair bundle associated with
  gating of mechanoelectrical transduction channels" — the gating-spring
  relation already implemented in `local_gating_spring_energy.rs`.
* B. C. J. Moore, *An Introduction to the Psychology of Hearing* — auditory
  temporal integration windows.
* R. D. Patterson et al., "Complex sounds and auditory images" — the gammatone
  filterbank already compiled in `auditory.rs`.

In-tree authority:

* `docs/GUALA_QUANTIZED_OPTICAL_TRANSDUCTION_RATIFICATION_2026-08-05.md`
* `docs/GUALA_STIMULUS_BOUNDARY_RETENTION_RATIFICATION_2026-08-05.md`
* `docs/GUALA_D3_LOCAL_CUPULA_BUNDLE_PATH_2026-08-04.md`
* `docs/GUALA_D3_REJECTED_SELECTED_LINEAR_HAIR_CELL_GATE_2026-08-04.md`
* `docs/GUALA_NIGHT_SHIFT_20260805_CLAUDE.md`
* `HANDOFF_2026-07-25_LIVE_HEARING.md` (named to be excluded, §1.5)
