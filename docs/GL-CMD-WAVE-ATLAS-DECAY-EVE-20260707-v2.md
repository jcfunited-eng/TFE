# GL-CMD-WAVE-ATLAS-DECAY-EVE-20260707-v2

**doc_id:** GL-CMD-WAVE-ATLAS-DECAY-EVE-20260707-v2
**Author:** Eve
**To:** c1
**Ordered by:** Joe (2026-07-07 session)
**Supersedes:** `GL-CMD-WAVE-ATLAS-DECAY-EVE-20260707-v1`. Do not execute v1.
**Cites:** `GL-RPT-WAVE-ATLAS-DECAY-BUILD-C1-20260707-v1` (halt report).

## Verdict

v1's `tick_decay` reassigned `cell.bindings = new_bindings`. Concurrent `spill_write.append` on the pre-reassignment reference dropped writes silently. c1 reproduced with a concurrency stress test — 2 lost writes under heavy contention. Real race.

Fix: eliminate the reassignment. Mutate the existing list in place using `list.pop()` from the tail — atomic under GIL, race-free with concurrent `list.append()`. Skip cell deletion entirely in tick_decay — cells with empty bindings stay as small-cost placeholders. A dedicated sweeper for orphaned empty cells can be added later if memory footprint warrants; not this dispatch.

Everything else in v1 stands. Constants stand. Optimizations stand.

## What's being changed relative to v1

### `dsf_ai_service/v4/wave_atlas.py` — replace `tick_decay` body

```python
def tick_decay(self, decay_rate: float = 0.02, prune_threshold: float = 0.05):
    """Decay all binding strengths by decay_rate per tick.
    Prune bindings below prune_threshold via IN-PLACE pop from tail
    (atomic under GIL, race-free with concurrent spill_write.append).

    Physics: exponential decay with rate 0.02 per tick.
    Half-life = ln(2) / 0.02 ≈ 35 ticks ≈ 15 seconds at 2.4 Hz.

    Concurrency contract:
    - list.pop(i), list.append(x), and dict item assignment are all
      atomic under GIL. Iterating from the tail means pops don't
      shift indices of items being examined earlier in the same pass.
    - Never reassigns cell.bindings. Never deletes cells from
      self.cells here. Empty cells persist as placeholders; a
      separate sweeper can reclaim them if needed.
    """
    total_bindings_pruned = 0
    for cell in self.cells.values():
        # Decay strengths in place — no new list, no reference swap
        for b in cell.bindings:
            b["strength"] = b.get("strength", 0.0) * (1.0 - decay_rate)

        # Prune from the tail. Concurrent appends land at the tail after
        # our current index, so they're never at risk of being popped.
        # Iterate tail-to-head so pops don't shift indices we haven't
        # visited yet.
        i = len(cell.bindings) - 1
        while i >= 0:
            if cell.bindings[i].get("strength", 0.0) < prune_threshold:
                cell.bindings.pop(i)
                total_bindings_pruned += 1
            i -= 1

        # Recompute aggregate from what's left. Concurrent appends between
        # the prune loop and this sum will be included (correctly) or
        # counted next tick — either is fine, no write is lost.
        cell.aggregate_strength = sum(
            b.get("strength", 0.0) for b in cell.bindings
        )

    return total_bindings_pruned
```

### Change semantics: what tick_decay reports

The return value in v1 was `cells_pruned`. In v2 it's `total_bindings_pruned` — the number of bindings dropped across all cells. Cells themselves are not deleted here. The event payload changes accordingly:

`wave_atlas_decay_tick` payload:
- `tick`
- `bindings_pruned` (was `cells_pruned` in v1)
- `cells_total` (all cells, including empty placeholders)
- `total_strength_before`, `total_strength_after` (unchanged from v1)

### Everything else from v1 stands unchanged

- Tick loop wiring: call `wave_atlas.tick_decay()` immediately before wave summary sampling.
- `wave_summary.py` skip-when-empty change.
- `wave_summary.py` heapq change.
- Constants: `decay_rate=0.02`, `prune_threshold=0.05`.
- Env-var disable: `WAVE_ATLAS_DECAY_ENABLED=0`.
- Rollback path: task-def revert or env-var flip.

## Concurrency correctness argument

The remaining race points in v1 that this fix closes:

1. **`cell.bindings = new_bindings` reassignment** → gone. `bindings` is the same list object throughout tick_decay.

2. **List comprehension pattern (`bindings[:] = [b for b in bindings if ...]`)** → not used. That pattern has its own subtle window where a concurrent append between the comprehension's read and the slice-assignment's write could be dropped.

3. **`del self.cells[chi_idx]` racing spill_write** → not present. Cells are never deleted in tick_decay.

Remaining atomic operations relied on:
- `list.pop(i)` — atomic under GIL.
- `list.append(x)` (called from spill_write) — atomic under GIL.
- `dict[key] = value` and `dict[key]` (self.cells access) — atomic.

Pop-from-tail direction matters: if spill_write appends at index N while we're popping at index M<N, our pop doesn't touch index N, and its item remains after our pass finishes. If we popped from head-to-tail instead, indices would shift under us mid-loop.

## What is NOT changing

Every non-`tick_decay` piece from v1 stands. This dispatch is scoped narrowly to the race fix.

## Halt conditions

Same three as v1 plus a new one for the specific race being fixed:

1. Decay causes a ball experience to disappear entirely within one session.
2. A different thread-safety issue surfaces beyond the reassignment race — some other reference-swap or shared-mutable-state pattern that the in-place fix doesn't cover.
3. Skip-when-empty accidentally suppresses `wave_summary_pushed` events.
4. Concurrency stress test (the same one c1 built for v1) shows any lost writes under load. Zero tolerance — if any write is lost, halt.

## Harness protocol

Same six steps as v1, plus one prerequisite:

**Step 0 (new) — run c1's concurrency stress test against the v2 code before deploying.** Same test that reproduced the race under v1. Expect zero lost writes. If any write is lost, halt and route to Eve — the fix didn't cover the race, and a different approach is needed (either option 2 or option 3 from Eve's earlier notes).

**Steps 1-6 as v1**, using `hemispheric_integration_acceptance_v3.yaml`.

## Rollback

Same as v1. Task-def revert or `WAVE_ATLAS_DECAY_ENABLED=0`.

## Scope guardrails

Do NOT:
- Reassign `cell.bindings` anywhere.
- Delete entries from `self.cells` in `tick_decay`.
- Add locks. The lock-free contract stands.
- Tune constants.
- Address orphaned empty cells in this dispatch. That's a future sweeper if it becomes measurable.

If the stress test in Step 0 shows any lost writes, HALT — do not deploy, do not attempt fix v3 without Eve.

---

### Changelog
- v2 (2026-07-07, Eve): rewrite of `tick_decay` to eliminate the reference-reassignment race c1 reproduced. In-place mutation via pop-from-tail. Cells with empty bindings persist as placeholders. Prerequisite step 0 added: run stress test against v2 code and confirm zero lost writes before deploying.
- v1 (2026-07-07, Eve): superseded. Contained the reassignment race.
