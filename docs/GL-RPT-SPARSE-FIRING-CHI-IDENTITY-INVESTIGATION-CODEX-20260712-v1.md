# GL-RPT-SPARSE-FIRING-CHI-IDENTITY-INVESTIGATION-CODEX-20260712-v1

**doc_id:** GL-RPT-SPARSE-FIRING-CHI-IDENTITY-INVESTIGATION-CODEX-20260712-v1
**From:** Codex (this session)
**Context:** Two-stage investigation requested: (1) build real, stable
per-neuron chi-coordinate identity from the existing `chi_atlas` mechanism,
if the accumulated real data is genuinely meaningful yet; (2) only if (1)
succeeds, investigate a bounded sparsity mechanism for spike-injection entry
selection using it. Directly follows on
`docs/GL-RPT-BLUEPRINT-DEPLOYMENT-AUDIT-C1-20260712-v1.md`'s Phase 2 finding
("neurons have no chi-coordinate identity yet").
**To:** Eve / Joe

---

## Verdict

**Stage 1: not ready. No code built.** The `chi_atlas` mechanism is real and
actively written on real production paths, but at real production scale the
load-bearing (committed) data is both too sparse (most neurons never commit
even once across hundreds of real word-events) and, where present,
collapsed onto a narrow, largely population-shared low-value band — a
structural artifact of the current commit-gating mechanics, not real
per-neuron distinguishing content. This was verified empirically (three
independent runs, methodology below), not assumed. Deriving a "center of
mass" identity from this now would be deriving identity from noise, which
the dispatch instructed against.

**Stage 2: not attempted.** Gated on Stage 1 by the dispatch's own
condition, which failed. Independently, a *different*, already-live,
structural (not experience-derived) per-neuron chi coordinate already
exists and already drives real entry-neuron selection successfully — see
Finding 3. Swapping its input to the currently-noisy experience-derived
signal would be a strict downgrade to a subsystem with real, recent,
documented cascade-incident history, not warranted.

**One real, separate, currently-live bug was found and is reported (not
fixed)** in the `chi_atlas` write path itself — Finding 2. Out of scope to
fix here per the dispatch's explicit conservatism instruction for this
subsystem; routed to Eve/Joe.

No files were modified. No kill-switch is needed because nothing was
shipped. This report is the only change (docs-only), committed locally,
not pushed.

---

## Background: two independent per-neuron "chi" concepts exist

This investigation found it necessary to separate two things that share a
name:

1. **`LoomNeuron.chi_position`** (`dsf_ai_service/loom_model/neuron.py:872`)
   — a *structural* address, set once at birth from
   `(hemisphere_index, ring_position)`, spread evenly across the full chi
   address space. **Already deployed and live** since commit `712578f`
   (2026-07-08), which pre-dates the currently-running task-def SHA
   (`5771dac`, confirmed live per the 2026-07-12 blueprint audit). This is
   what `gualaloom_v5_engine.py`'s `_select_entry_neurons`/`_chi_to_neurons`
   already reads.
2. **`LoomNeuron.chi_atlas`** (`dsf_ai_service/loom_model/neuron.py:872`
   area, `ChiAtlas` instance) — a real, per-neuron, experience-accumulating
   record of committed chi values over time. This is what the dispatch
   asked me to derive identity FROM. It exists and is written, but (per
   Findings 1-2 below) doesn't yet carry meaningful signal.

`neuron.py:865-871`'s own in-code comment ("Chi position for
propagation-delay computation... NOT populated anywhere in Phase 1... no
per-neuron static chi coordinate exists... Flagged in the Phase 1 report as
an open question — where would a real value come from?") is **stale** — it
describes a state that commit `712578f` already changed. See Finding 3.

This means the 2026-07-12 blueprint audit's Phase 2 line ("neurons have no
chi-coordinate identity yet") is more precisely: *no
**experience-derived** chi-coordinate identity yet* — a structural one has
existed and been live for four days. Worth a small correction note on that
audit; not disputing its bottom line (Phase 2/lateral inhibition is still
not built).

---

## Finding 1 — real chi_atlas commit data is sparse AND collapsed, reproducibly, independent of data volume

### Method

Constructed the organism using the *exact* real production call
(`Embryo(brain_seed=42, seed_size=8, observable="event_count")`, matching
`gualaloom_v5_engine.py:2556`'s live construction), then drove it through
the real `experience_word()` production call path (same call
`_organism_worker_loop` makes at `gualaloom_v5_engine.py:4845`), using real
`LanguageKrimelack` transduction on real English words, with a real
(deterministically-generated, non-fabricated) non-language `visual` signal
via `embryo.py`'s own `bipolar_sense()` helper on a fraction of events —
mirroring the real regime where sensory feeds are present some of the time
and absent (language-only) the rest, since production sensory feeds are
largely blocked. Instrumented `LoomNeuron.step()` and `ChiAtlas.record()`
directly (monkey-patched to log args/results, not inferred from static
reads) across three independent runs of increasing size (120, 240, 480
real word-events; different seeds/word sets).

### Results (480-event run, largest; smaller runs matched qualitatively)

- 49,308 real `LoomNeuron.step()` calls; 26,652 with a real, non-None
  `input_chi` (the wide-range, krimelack-winding-derived chi from
  `Embryo._compute_input_chi`).
- Only 1,324 (5.0%) of those ever reached `committed=True`
  (`PsiLattice.committed()`, `neuron.py`).
- **`input_chi` offered to `step()` ranged 0-21 in this run (theoretically
  unbounded / up to the wave-atlas convention's 262,144-address space per
  `gualaloom_v5_engine.py:5315`). But `input_chi` on calls that actually
  committed was confined to {0, 1, 2, 3, 4} — narrower than the smaller
  120-event run's {0..5}, not wider.** Commit rate for `input_chi <= 5`:
  1324/16002 (8.3%). Commit rate for `input_chi > 5`: **0/10650 (exactly
  zero)**. Reproduced across all three runs, different seeds:
  120-event run 0/2166, 240-event run 0/2166 (separate instrumentation
  pass), 480-event run 0/10650.
- Population-wide, of the neurons that ever recorded a real numeric
  committed value, most had 1-2 records total after hundreds of real
  word-events; a small number of "hub" neurons accumulated dozens; most of
  the population (70-75% in the 240-event runs) never committed once.

### Interpretation

If more real production time were the only issue, the value RANGE reached
by real commits should widen as more data accumulates. It didn't — it
stayed pinned to the same narrow near-zero band across a 4x range of
simulated traffic. This points to a structural gate in the current
ψ-lattice commit mechanics (something makes `PsiLattice.committed()` —
`p_max >= P_COMMIT and B_k >= DET_COMMIT`, `neuron.py` — essentially only
reachable when the offered `input_chi` happens to be small) rather than a
"not enough time has passed" problem. Root-causing *why* is out of this
investigation's scope (would mean touching the same live commit/injection
mechanics the dispatch told me to be conservative around); flagged here as
the concrete next question for whoever picks this up.

**Practical consequence for Stage 1:** even setting Finding 2 aside, the
real chi values that make it into `chi_atlas` today are not a meaningful,
neuron-distinguishing sample of "what has this neuron actually been
responsible for" — they're a thin, mostly-empty, near-uniformly-collapsed
set shared across almost the whole population. A "center of mass" computed
from this would not reflect real per-neuron meaning-space specialization;
it would mostly reflect which of the 3-5 structurally-favored low values a
given neuron happened to touch a handful of times.

---

## Finding 2 — a real, live, reproducible argument-order bug in the chi_atlas write path

`ChiAtlas.record` (`dsf_ai_service/v4/gualaloom_v4_chi_atlas_l6.py:46`):

```python
def record(self, section_name, motif_id, chi_value, tick=None):
    ...
    for d in range(-self.band, self.band + 1):
        bucket = self.entries[chi_value + d]   # line 55 -- bucket KEY is chi_value (3rd positional arg)
```

The commit-path call site, `neuron.py:1872`:

```python
self.chi_atlas.record("neuron", _chi_for_atlas, dominant_mode, tick)
```

Positionally: `motif_id = _chi_for_atlas` (the real upstream chi —
`input_chi` when given), `chi_value = dominant_mode` (the ψ-lattice's own
0-15-range `argmax` index). **The bucket key ends up being `dominant_mode`,
not the upstream chi.**

Verified directly with a standalone `ChiAtlas` check (not inferred from
reading):

```python
ca = ChiAtlas()
ca.record('neuron', 42, 7, tick=1)      # motif_id=42 (upstream chi), chi_value=7 (dominant_mode)
ca.match_score(42, 'neuron')   # -> 0.0   (looked up under the wrong key)
ca.match_score(7, 'neuron')    # -> 0.5   (actually filed here)
```

This directly contradicts the surrounding comment (`neuron.py:1858-1862`:
*"chi_atlas now stores the UPSTREAM chi... not dominant_mode — so
match_score(input_chi, ...) ... can actually land in the same numeric range
real callers pass as input_chi"*) and the dispatch that shipped this exact
line, `docs/GL-CMD-CHI-UNIFICATION-EVE-20260707-v3.md:36-38`, whose own
specified snippet has the identical argument order (i.e. the bug was
specified this way, not introduced by a later slip):

```python
self.chi_atlas.record("neuron", input_chi, dominant_mode, tick)
```

**Practical effect:** `LoomCluster._select_by_chi_familiarity`
(`dsf_ai_service/loom_model/cluster.py:224`) calls
`n.chi_atlas.match_score(input_chi, "neuron")` — keyed by the real, wide
`input_chi`. Since real entries are actually filed under `dominant_mode`
instead, this lookup can essentially never hit (except by numeric
coincidence when `input_chi` itself happens to be under ~16), so the
chi-familiarity neuron gate this whole dispatch existed to enable is very
likely non-functional whenever a real, wide-range `input_chi` is involved
— it silently falls through to the "all neurons" / "2-neuron novelty pool"
fallback instead.

**Why the prior verification (`docs/GL-RPT-CHI-UNIFICATION-C1-20260707-v3.md`)
didn't catch this:** its learning-curve test repeated the same word via
`experience_word()`. In that path `input_chi` is commonly `None` (composite
signal all-zero when no real sensory data is present, the common case per
existing memory of blocked sensory feeds) — and when `input_chi is None`,
`_chi_for_atlas` *falls back to* `dominant_mode`, so both `record()`
arguments become the same value and the bug is inert. The 16→12 convergence
curve that report measured is real and was correctly observed; it just
didn't exercise the `input_chi is not None` path the whole dispatch was
written to fix. A real coverage gap, not a fabrication.

**Not fixed here** — this is squarely the subsystem the dispatch told me to
be conservative around, and fixing it would change live neuron-selection
behavior in a mechanism with real, recent cascade-incident history. Routed
for Eve/Joe to decide the fix + a verification pass that specifically
exercises `input_chi is not None`.

---

## Finding 3 — a structural (non-experience-derived) chi_position already exists and already works

`embryo.py:275-280` (`Embryo._seed_dna_diversity`, shipped in `712578f`,
2026-07-08, confirmed pre-dating the current live SHA):

```python
structural_index = hemi_index * ring_N + ring_pos
total_positions = n_hemispheres * ring_N
n.chi_position = int(structural_index * MAX_CHI_DISTANCE / total_positions)
```

Set exactly once, from birth position; the only other write to
`.chi_position` anywhere in production code is the `None` initializer
(`neuron.py:872`, `neuron.py:1026`). It is never updated from real
experience afterward.

This is already read by `gualaloom_v5_engine.py:_chi_to_neurons`/
`_select_entry_neurons` (lines 5317-5389) for the STDP/spike-injection
subsystem's entry-neuron selection, and per that code's own docstring
already produces real single-neuron precision
("`_chi_to_neurons` empirically always returns exactly one candidate...
verified across 163 real words", `gualaloom_v5_engine.py:5415`).

So a form of "Stage 2" (chi-proximity-biased entry selection) is already
built, live, and working — just using a *structural* identity (birth
position) rather than an *experience-derived* one (what a neuron has
actually learned). That distinction is the actual gap Stage 1 was asked to
close, and per Findings 1-2, it isn't closed yet.

---

## Recommendation

1. **Do not build Stage 1/2 yet.** The real prerequisite data doesn't carry
   enough real signal, for structural reasons (Finding 1) that more
   production time alone won't fix.
2. **Route Finding 2 (record() argument-order bug) to Eve/Joe.** It's real,
   reproducible, currently live, and independent of Findings 1/3 — worth a
   deliberate fix + a targeted verification pass (specifically exercising
   `input_chi is not None`, which the original verification didn't).
   Fixing it will not by itself unblock Stage 1 (Finding 1's collapse is a
   separate, deeper issue), but it's the honest state of the write path and
   affects the mechanism `docs/GL-CMD-CHI-UNIFICATION-EVE-20260707-v3.md`
   was written to fix.
3. **Correct `neuron.py:865-871`'s stale comment** (still says
   `chi_position` is "NOT populated anywhere") — low-risk, comment-only,
   not done here since it wasn't the ask, but noted so it doesn't mislead
   the next person who reads it.
4. **The real next question for chi-based sparsity**, if anyone picks this
   up later: root-cause *why* `PsiLattice.committed()` is only reachable at
   low `input_chi`/small-magnitude signal conditions (Finding 1). That's a
   commit/injection-mechanics question, not a chi_atlas-reading question,
   and it's the actual blocker underneath both findings.

## Scope compliance

No production code touched. No deploy, no push. `gualaloom_v5_engine.py`
and `neuron.py` unmodified. This report is the only change, committed
locally per instruction.

---

### Changelog
- v1 (2026-07-12, Codex): Stage 1 investigated and found not ready
  (empirically: real chi_atlas commit data is sparse and collapses onto a
  narrow, population-shared band, independent of data volume across a 4x
  range tested). Stage 2 not attempted (gated on Stage 1; also found a
  working structural alternative already live). One real, separate,
  currently-live write-path bug found and routed, not fixed. No code
  built or changed.
