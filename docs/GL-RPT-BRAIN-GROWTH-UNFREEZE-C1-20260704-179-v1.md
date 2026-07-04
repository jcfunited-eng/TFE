# GL-RPT-BRAIN-GROWTH-UNFREEZE-C1-20260704-179-v1

doc_id: GL-RPT-BRAIN-GROWTH-UNFREEZE-C1-20260704-179-v1
From: c1a | To: Eve, Joe, c1b | Responds to:
`GL-CMD-BRAIN-GROWTH-UNFREEZE-EVE-20260704-179-v2`.
**INTERIM, HONEST CHECKPOINT — paused to address `-180` (seat-truth
UI) given Joe's live-blocking frustration and its higher urgency; W3
not started, W4 partially done with a real, unresolved failure found.
Not ready for G-2/G-3 (one reconciled SHA) — do not deploy.**

---

## Failures first

**B1 independently re-verified: confirmed, Eve's code read is
correct.** `_feed_and_fold` (`embryo.py:287`) calls `_charge_and_fold`
(the real q-charge/fold mechanism, `embryo.py:220`) via `experience()`
(`:294`). `remember()` (`:369`) calls only `n.experience_moment()` —
no fold call anywhere. Structurally disconnected, confirmed by direct
read, not just trusted.

**W1 built.** `Embryo.experience_word(concept, multi_modal_signals,
theta)`: calls `self.remember(...)` first (binding-write preserved,
unchanged), then drives the same fold cascade `experience()` already
uses (extracted into a shared `_experience_core()` so the two callers
can't drift), sourced from the organism's real tactile/olfactory/
gustatory waveforms via `resonance_signal()` — same primitive
`experience()` already uses, real signal, not invented.

**Growth is real and bounded, matching -169's design — confirmed
directly:** population 64→125 within 5-14 words (real multi-modal
signal is far richer/more coherent than the demo's sparse bipolar
receptors, so the fold gate crosses fast — an honest property of real
signal, not manipulated), then **plateaus permanently** as `_div_pool`
drains to 0 (the existing conservation-physics asymptote working
exactly as designed, not a runaway — confirmed: `div_pool=0.00` held
flat from word 10 through word 40 in the same test run).

**W2 coupling done, and it surfaced a real, separate, urgent bug: without
it, `-178`'s whole fix would have shipped inert.** `Brain.recall_fast()`
(built in `-177`, already deployed live per the window-3 cutover) hard-
coded the OLD `len(events)` computation for language and was never
updated when `-178`'s `n_events` counter landed. Since the live call
sites use `recall_fast()`, not `recall()`, `-178`'s fix would have had
**zero live effect** once both landed together — completely silently.
Fixed: `recall_fast()` now mirrors `_unwrapped_deltas`'s own
`hasattr(krim, 'n_events')` dispatch, per-neuron (not a population-wide
switch, since a restored/pickled organism could mix pre- and post-fix
neurons).

**W4's `recall_fast()`-parity-at-grown-size check is NOT clean — a
real, unresolved divergence found, root-caused but not yet fixed.**
At a grown (64→124-125), asymmetric population, `recall_fast()` vs
`recall()` disagreed on 9-25 of 26 probe words depending on the run.
Isolated per-modality (tactile/olfactory/gustatory matched exactly,
0 mismatches each) — **the divergence is entirely in the language
channel.** Root cause, traced directly: `experience_word()`'s own
fold cascade calls `hemi.cluster.step()` (via `_feed_and_fold`,
6 ticks per hemisphere activation), which drives `Neuron.step()` — a
**separate, pre-existing Stage-1 substrate mechanism** that, for
non-string (array) input, calls `self.krimelack.feed_signal()`/`feed()`
**directly on the neuron's primary krimelack** — which, since
`primary_modality` is always `"language"`, is the **same
`LanguageKrimelack` instance** the cognition path's `_unwrapped_deltas`
reads and mutates. This cross-contaminates `winding`/`events`/
`n_events` between two previously-independent mechanisms (confirmed:
one live neuron's language `n_events` was at 68,070 after only ~24
words taught via `experience_word()` — versus the ~200-400 range
`-178`'s measurements showed for `remember()`-only teaching at the
same word count). `recall_fast()`'s per-sample vectorized computation
was proven correct in `-177`/`-178` against `_unwrapped_deltas`'s
behavior in isolation; it was never proven against a process where a
**second, independent mechanism** also mutates the same krimelack
between queries. I did not find the exact remaining discrepancy before
time ran out on this pass (isolated to the language channel, ruled out
the `phase`-always-resets-to-0 assumption as the direct cause since
`transduce()`'s reset is unconditional regardless of what `Neuron.step()`
left behind — the precise mechanism is still open).

**Consequence, stated plainly: `experience_word()` as currently built
must NOT be wired into the live word path or deployed.** Doing so would
break `recall_fast()`'s already-live correctness guarantee (proven in
`-177`, relied on by the window-3 cutover already in production) the
moment any neuron's language krimelack gets touched by a growth-tick.
This is exactly the contamination G-3 asked to have named, not defended.

---

## What's not done

- **W3 (cost profile at live word rates)**: not started. Given the
  parity failure above, profiling a build that isn't correct yet
  isn't useful work — sequencing corrected: fix parity first.
- **W4's restore-honesty-at-grown-size** (save/load a grown organism):
  not tested yet, same reason.
- **W5 (honest-physics clause)**: partially satisfiable already — the
  observed behavior (fast, real crossing of the fold gate under real
  signal) is itself an honest report, not a photogenic one; formal
  write-up deferred until W4 is clean.

## Recommendation

Do not build further on top of `experience_word()` until the language-
channel cross-contamination is root-caused precisely and `recall_fast()`
either accounts for it or the growth wiring is changed to avoid driving
`Neuron.step()` on the shared krimelack at all (e.g., route
`_feed_and_fold`'s cascade through a signal path that doesn't touch
`self.krimelack` when it's also the language cognition krimelack — a
real design question, not a one-line patch, given the two mechanisms
were never meant to interact). Picking this back up next.

### Changelog
- v1 (2026-07-04, c1a): B1 re-confirmed independently. W1 built
  (`experience_word()`, binding-write preserved). W2 done, surfacing
  and fixing a real cross-dispatch bug (`recall_fast()` never updated
  for `-178`'s `n_events` fix, which would have shipped `-178` inert).
  Growth confirmed real and correctly bounded (conservation-physics
  asymptote working as designed). `recall_fast()` parity at grown size
  is broken — root-caused to `Neuron.step()`/cognition-path krimelack
  cross-contamination, not yet resolved. W3/W4-restore-honesty not
  started. **Not ready to ship; do not deploy.** Paused to address
  `-180` (higher urgency, isolated surface) — resuming after.
