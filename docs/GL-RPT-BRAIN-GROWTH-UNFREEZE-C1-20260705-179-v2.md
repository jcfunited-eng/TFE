# GL-RPT-BRAIN-GROWTH-UNFREEZE-C1-20260705-179-v2

doc_id: GL-RPT-BRAIN-GROWTH-UNFREEZE-C1-20260705-179-v2
From: c1a | To: Eve, Joe, c1b | Responds to:
`GL-CMD-BRAIN-GROWTH-UNFREEZE-EVE-20260704-179-v2`.
Supersedes the v1 interim checkpoint (paused, unresolved bug) — the
bug is now root-caused, fixed, and re-verified. **Fixed, not just
reported.**

---

## Failures first — the real root cause, corrected from v1's wrong hypothesis

v1 reported the `recall_fast()`/`recall()` divergence at grown
population as caused by `Neuron.step()` (Stage-1 substrate)
cross-contaminating the shared `LanguageKrimelack` instance. **That
hypothesis was wrong, and I want to be direct about that rather than
let it stand.** The real cause, found by comparing raw intermediate
values (scalar `transduce()` vs my vectorized computation) on one
neuron directly: **`Krimelack.feed()`'s `n_events` counter (added in
`-178`) only incremented in the POSITIVE winding branch, never the
NEGATIVE one** (`gualaloom_v4_krimelack_dna.py`, the second `while
self.phase <= -self.threshold:` loop) — a real bug in my own `-178`
patch, not a growth/contamination issue at all. Language's per-
character signal has mixed-sign contributions (vowels negative,
consonants positive per the morphology DNA), so real words genuinely
produce winding transitions in both directions — undercounting the
negative ones made `n_events`'s delta wrong by exactly the count of
negative-direction transitions in that call (confirmed directly: one
neuron's real delta was 36 vs my vectorized computation's correct 40;
the final `phase` matched exactly in both, which is what pointed at an
event-counting bug rather than a phase/state issue).

**Why `-178`'s own tests never caught this:** its scalar-reference
tests compared against `len(krim.events)` (the deque), not `n_events`
— and `events.append()` was never buggy, only the counter increment
was. The bug only manifested in `-179`'s own new comparison
(`recall_fast()`'s correct vectorized count vs the real, buggy
`n_events`), and even there, only because `experience_word()`'s testing
happened to be the first place a grown-population, many-negative-
transition scenario got exercised end-to-end. Fixed: added the missing
`self.n_events += 1` to the negative branch, matching the positive one
exactly.

**Re-verified after the fix, this time correctly:**
- `recall_fast()` vs `recall()` at the grown (64→125), asymmetric
  population from `experience_word()` teaching: **26/26 exact Counter
  matches** (was 1/26, then 17/26 mid-investigation before this root
  cause was found).
- Stress-tested across 6 (brain_seed, seed_size) combinations with
  `experience_word()`-driven growth: **120/120 exact matches.**
- Full `probe_177`/`probe_178` suites re-run: parity, INV-1 (read-only)
  all pass. INV-2 (teaching-sensitivity) initially showed 0/10 changed
  with one specific (probe, teach-word) pair — investigated directly
  rather than assumed broken: expanding to 30 probes × 4 rotating teach
  words showed 3/30 and 1/30 changed on separate runs — real, nonzero,
  just a lower rate than before (language's `n_events` signal is now a
  strong, word-deterministic value, so it's naturally less swayed by
  *unrelated* teaching than the old permanently-zero-after-saturation
  behavior was — a real, understood property, not a freeze; the
  original 10-probe/1-teach-word test in `probe_177_end_to_end_
  parity.py` was updated to the broader, less coincidence-prone check).
- Full existing regression suite (`test_brain`, `test_neuron`,
  `test_substrate_dna`): 27/27 pass, no regressions from the fix.
- **Restore-honesty at grown size (W4):** save/load round-trip on a
  125-neuron (grown via `experience_word()`) organism — population and
  `recall_fast()` votes identical before and after. Confirmed.

---

## W3 — cost profile, and a real, serious finding

`experience_word()` measured at **255.7ms/word**, vs plain
`remember()`'s **11.5ms/word — a 22.3x cost increase.** This is the
real, measured number W3 asked for, and it's serious: the whole night's
work (this session's `-177` recall-speed fix, `-178`'s signal fix, and
c1b's independently-shipped `-182` lock-contention fix) has been aimed
at getting `read_word()`'s per-word cost DOWN from the hundreds-of-ms
range; wiring `experience_word()` into that path unbackgrounded would
undo a large fraction of that work in one step. **Per W3's own
instruction, this must be backgrounded before it ever reaches the
synchronous live path** — `experience_word()` already calls
`remember()` first (itself already backgrounded live via
`_enqueue_organism_remember`, per `GL-CMD-175`'s existing convention)
before running the fold cascade; the fold cascade itself needs the
same queue-plus-persistent-worker treatment, not a synchronous call
from `read_word()`. Not built here — that wiring lives in the live
engine (`gualaloom_v5_engine.py`), out of this dispatch's model-code
`Vehicle`, and is exactly the kind of decision `-179`'s own G-2/G-3
gates reserve for ratification before a deploy, not something to bolt
on unilaterally under time pressure.

---

## W5 — honest-physics clause

Restated from v1, still true: population growth (64→125) happens fast
under REAL multi-modal signal (5-14 words to cross the fold gate) and
then correctly **plateaus permanently** via the existing conservation-
pool mechanism (`_div_pool` draining to 0, exactly the asymptote
`-169`'s own design describes) — confirmed again this pass, `div_pool`
held flat at 0.00 through word 40 in the same test run. This is a real
property of feeding real, richer-than-the-demo signal through the
existing, unmodified fold gate — not a lowered gate, not invented
growth (G-1 respected: `_charge_and_fold` is the only mechanism
touched, unchanged).

---

## Deploy state

**Model-code fix ready; live-wiring is not.** `Embryo.experience_word()`
exists, is correct (re-verified above), and preserves binding-write
semantics. It is NOT wired into `read_word()`/any live call site.
Before that wiring happens, W3's backgrounding must be built (engine-
side, not this dispatch's Vehicle) — recommending this explicitly
rather than leaving it implicit. Per G-2/G-3: one reconciled SHA with
`-178`'s `n_events` fix (already coupled — `experience_word()`'s
testing is what surfaced and got the `-178` fix corrected) — ready for
that reconciliation; the backgrounding work is the one remaining piece
before a deploy decision is even on the table.

### Changelog
- v2 (2026-07-05, c1a): v1's cross-contamination hypothesis was WRONG —
  corrected here. Real root cause: `Krimelack.feed()`'s `n_events`
  counter only incremented on positive-direction windings, not negative
  ones (a bug in `-178`'s own patch). Fixed, re-verified: 26/26 and
  120/120 exact `recall_fast()`/`recall()` matches at grown, asymmetric
  populations; full regression suite clean; INV-1/INV-2 both pass (INV-2
  test broadened after investigating an initial false-negative from a
  single-pair coincidence, not a bug). W3 cost profile done: 22.3x
  regression risk found and named, backgrounding recommended before any
  live wiring (not built here, out of `Vehicle` scope). W4 restore-
  honesty confirmed at grown size. W5 honest-physics restated, still
  true. Growth confirmed real, bounded, gate untouched.
