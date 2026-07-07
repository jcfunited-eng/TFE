# GL-RPT-WAVE-ATLAS-DECAY-BUILD-C1-20260707-v1

**doc_id:** GL-RPT-WAVE-ATLAS-DECAY-BUILD-C1-20260707-v1
**From:** c1
**Executing:** GL-CMD-WAVE-ATLAS-DECAY-EVE-20260707-v1
**To:** Eve (routing per dispatch instruction — no questions to Joe in this doc)

**HALT. Routed per the dispatch's own explicit instruction.** All four
wirings were built exactly as specified and verified correct in
isolation. One of the three named halt conditions — thread-safety with
the lock-free write path — is **confirmed real**, empirically, twice,
via a targeted concurrency stress test. Not deployed. Code is committed
to `guala-live` (so the work and the reproducer aren't lost) but the
task-def was never touched — production is untouched, still running
`5a5bede` (task:542, the last known-healthy state from the v3
rollback).

---

## What was built (all four wirings, exactly as specified)

1. **`dsf_ai_service/v4/wave_atlas.py`**: `WaveAtlas.tick_decay(decay_rate=0.02, prune_threshold=0.05)`, pasted verbatim from the dispatch text — no deviation, no tuning.
2. **Tick loop**: called immediately before v3's wave-summary sampling in `_autonomy_tick()` (the live path), guarded the same way (`self.wave_atlas is not None`) plus a new `WAVE_ATLAS_DECAY_ENABLED` env-var check (default `"1"`, matching the dispatch's own "mid-flight disable via WAVE_ATLAS_DECAY_ENABLED=0" rollback instruction — this only works as a fast disable if the default is *on*).
3. **`dsf_ai_service/substrate/wave_summary.py`**: both changes applied exactly as given — the skip-when-empty early return in `push_wave_summary_to_organism` (returns the honest all-zero payload, still lets the caller's `wave_summary_pushed` event fire, just skips every `neuron.step()` call), and `heapq.nlargest` replacing the `sorted(...)[:top_n]` line in `sample_wave_summary`.
4. **New event `wave_atlas_decay_tick`**: `tick`, `cells_pruned`, `cells_remaining`, `total_strength_before`, `total_strength_after`, fired from `_autonomy_tick` right after `tick_decay()` returns.

## Local verification — two of three halt conditions cleared

**Halt condition 1 (content survival) — cleared.** Local `Guala()`,
`read_sentence("ball")` → sight/sound/word bands at ~0.207-0.829
aggregate. Ran `tick_decay()` 30 times: **zero cells pruned**, all
three bands still present at ~0.113-0.452 (diminished by the expected
`0.98^30 ≈ 0.545` factor, not gone) — matches the dispatch's own
"diminished but non-zero" bar with room to spare at these default
constants.

**Halt condition 3 (skip-when-empty still fires the event) — cleared.**
Fresh `Guala()` (empty wave atlas) → `push_wave_summary_to_organism`
returns the all-zero payload; monkeypatched one neuron's `step()` to
confirm it is **never called** on a quiescent tick. The caller in
`_autonomy_tick` still logs `wave_summary_pushed` with this payload
either way — event suppression was never wired to depend on whether
neurons actually got stepped.

**Halt condition 2 (thread-safety with the lock-free write path) —
CONFIRMED, not cleared.** Reasoned through this before testing: the
given `tick_decay()` does `cell.bindings = new_bindings` (a full list
**reassignment**, not an in-place mutation) for every cell, every
call. `WaveAtlas`'s write path (`tools/wave_spillover.py:135`,
`_commit_cell`) does `cell.bindings.append(binding)` for a genuinely
new binding — CPython resolves `cell.bindings` to a list object, *then*
calls `.append()` on it as a separate step; if `tick_decay()` reassigns
`cell.bindings` to a *different* list object in the gap between those
two steps, the append lands on the now-orphaned old list and is
silently lost. Reinforcement of an *existing* binding is safe (the
binding dict itself is shared by reference between old and new lists,
mutated in place) — this is specific to brand-new bindings racing a
concurrent decay pass on the same cell.

Built a targeted stress test to check whether this is real or just
theoretical, not assumed either way: N writer threads each writing a
guaranteed-new `(section, motif)` binding (never reinforcement) against
a small, shared pool of chi values (to force contention on the same
cells), racing against M decayer threads calling `tick_decay(decay_rate=0.0,
prune_threshold=-1.0)` in a tight loop (zeroed decay/pruning so the test
isolates the concurrency mechanism from the decay math itself — a test-
only parameter choice, not a product change; the shipped code still
uses the dispatch's exact 0.02/0.05 defaults).

- Run 1 (6 writers, 3 decayers, chi pool of 10, 4s): 1437 attempted, 1437 found, **0 missing**.
- Run 2 (12 writers, 6 decayers, chi pool of 3, 8s): 904 attempted, 903 found, **1 missing**.
- Run 3 (same as run 2, repeated): 2698 attempted, 2697 found, **1 missing**.

No crashes, no exceptions, in any run — this is a **silent** data-loss
race, exactly the kind that would never show up as an error in
production, only as an occasional, unexplained missing binding under
real concurrent load (a real `give_experience` write racing the
autonomy loop's decay call). Confirmed real, reproducible under heavy
contention, not a one-off fluke (two independent runs at the tighter
contention setting both lost exactly one write).

## Why this halts here rather than being fixed in-flight

The dispatch's own scope is explicit: `tick_decay()`'s code was given
verbatim, and "DO NOT... Modify summary structure or push mechanism"
signals this dispatch's intent was to ship the *given* implementation,
not for me to redesign it. A real fix here (e.g., mutating
`cell.bindings` in place via slice assignment, `cell.bindings[:] =
new_bindings`, instead of reassigning the reference — which would keep
`.append()`'s target object stable throughout, though it still needs
its own careful reasoning about ordering, and possibly the same
question for `cell.aggregate_strength`'s reset-then-rebuild sequence in
the given code) is a genuine design change to the decay mechanism
itself, not a clarification of an ambiguous instruction — squarely the
kind of thing this dispatch's own halt clause reserves for Eve's
decision, not mine to patch unilaterally under "route to Eve."

## Recommendation

Not a rejection of the goal — three of four wirings are correct and
low-risk as specified, and the decay math itself (constants, survival
window) checks out. The blocker is narrow and specifically located:
`WaveAtlas.tick_decay()`'s cell-rebuild pattern needs to not replace
`cell.bindings`'/`cell.aggregate_strength` via reference reassignment
while the lock-free write path can still be appending to/reading the
same cell concurrently. Options surfaced, not decided:
1. In-place mutation (`cell.bindings[:] = new_bindings`, `cell.aggregate_strength =` last, after the loop, computed from a local accumulator not touched mid-rebuild) — smallest change, needs review for the aggregate_strength ordering question above.
2. Route decay through whatever synchronization discipline (if any) the write path already trusts — needs whoever designed `spill_write`'s lock-free contract to weigh in on what's actually safe there, not a guess from me.
3. Accept the race as a rare, non-corrupting, silently-dropped-binding cost (confirmed non-crashing, low frequency even under artificial heavy contention) and ship anyway — a real option, but a deliberate risk-acceptance call, not mine to make by default.

## What was NOT done

Not deployed — no backup, no harness run, no task-def touched. Nothing
in production changed. The code is committed to `guala-live` (this
report + the three modified files) so the concurrency reproducer and
the otherwise-correct implementation aren't lost, but production is
still running the pre-existing, healthy `5a5bede` (task:542) from the
v3 rollback the whole time.
