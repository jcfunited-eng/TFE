# GL-CMD-WAVE-ATLAS-DECAY-EVE-20260707-v3

**doc_id:** GL-CMD-WAVE-ATLAS-DECAY-EVE-20260707-v3
**Author:** Eve
**To:** c1
**Ordered by:** Joe (2026-07-07 session)
**Supersedes:** `GL-CMD-WAVE-ATLAS-DECAY-EVE-20260707-v2`. Do not execute v2.
**Cites:** `GL-RPT-WAVE-ATLAS-DECAY-BUILD-C1-20260707-v2` (second halt report).

## Verdict

v2 fixed the reassignment race. c1's stress test then surfaced a second race: `for cell in self.cells.values()` iterates the live dict, and a concurrent `spill_write` creating a cell at a brand-new chi position inserts into `self.cells` mid-iteration. Python raises `RuntimeError: dictionary changed size during iteration`. c1 reproduced 13 times.

The fix c1 identified is correct: iterate over a snapshot of the values via `list(self.cells.values())`. Snapshot is taken at iteration start; concurrent inserts to `self.cells` don't affect our iteration. New cells created during decay skip this tick and get decayed next tick — which is fine because they were just written at full strength.

My v2 used `self.cells.values()` directly because I was thinking about avoiding an unnecessary list allocation. That was premature optimization against a correctness constraint I hadn't accounted for. Wrong tradeoff.

Bounded scope: one change to the iteration, one comment naming the discipline for future sweeps.

## What's being changed relative to v2

### `dsf_ai_service/v4/wave_atlas.py` — `tick_decay` iteration

Replace:

```python
for cell in self.cells.values():
```

With:

```python
# Snapshot values at iteration start. Concurrent spill_write can insert
# new cells into self.cells during our iteration; snapshotting avoids
# "dictionary changed size during iteration" and correctly skips those
# newly-inserted cells (they get decayed next tick, at full strength, no
# loss). See GL-CMD-WAVE-ATLAS-DECAY-EVE-20260707-v3.
for cell in list(self.cells.values()):
```

### Class-level discipline note

Add a short module-level or class-level comment (c1's judgment on placement) naming the iteration discipline for future sweeps:

```
Iteration discipline for self.cells under concurrent spill_write:
Any sweep over self.cells must snapshot via list() at iteration start,
not iterate the live view. spill_write inserts new cells at brand-new
chi positions, which triggers RuntimeError on live-view iteration.
This applies to tick_decay and any future sweeper (empty-cell
reclamation, saturation checks, etc.).
```

### Everything else from v2 stands unchanged

- In-place binding decay via `pop()` from tail-to-head.
- No reassignment of `cell.bindings`.
- No deletion from `self.cells` in `tick_decay`.
- Return value: `total_bindings_pruned`.
- Event payload: `wave_atlas_decay_tick` with `bindings_pruned`, `cells_total`, strength before/after.
- Constants: `decay_rate=0.02`, `prune_threshold=0.05`.
- `WAVE_ATLAS_DECAY_ENABLED=0` disable path.
- `wave_summary.py` skip-when-empty and heapq changes.

## Concurrency correctness — v3 complete argument

The races closed across v1, v2, v3:

- **v1**: `cell.bindings = new_bindings` reassignment. Closed in v2 by in-place mutation.
- **v2**: `for cell in self.cells.values()` mid-insert. Closed in v3 by snapshot.
- **v3**: no known races.

Atomic operations relied on:
- `list.pop(i)`, `list.append(x)` — atomic under GIL.
- `dict[key] = value`, `dict[key]` — atomic under GIL.
- `list(dict.values())` — snapshots refs at call time; safe against concurrent dict inserts.

## Halt conditions

Same as v2:

1. Ball experience content erased within one session.
2. Concurrency stress test shows any lost writes.
3. Concurrency stress test raises any exception (RuntimeError or otherwise).
4. Skip-when-empty suppresses `wave_summary_pushed` events entirely.

If any new race surfaces beyond the two now closed, HALT and route to Eve. Do not attempt v4 without design input — a third race pattern would indicate the lock-free contract needs revisiting more broadly, not another surgical fix.

## Harness protocol

Same as v2:

**Step 0** — run the concurrency stress test against v3 code. Expect zero lost writes AND zero exceptions. If either occurs, halt.

**Steps 1-6** — backup, baseline harness run, deploy, post-deploy harness run, compare, disposition. Uses `hemispheric_integration_acceptance_v3.yaml`.

## Rollback

Same as v2. Task-def revert or `WAVE_ATLAS_DECAY_ENABLED=0`.

## Scope guardrails

Do NOT:
- Change the iteration to something more complex than `list(self.cells.values())`. That's the minimum-change correct fix.
- Add locks. Lock-free contract stands.
- Reassign `cell.bindings` or delete cells anywhere in `tick_decay`.
- Tune constants.

---

### Changelog
- v3 (2026-07-07, Eve): iterate snapshot via `list(self.cells.values())`, fixes the `dictionary changed size during iteration` race c1 caught in v2's Step 0. Class-level discipline note added.
- v2 (2026-07-07, Eve): superseded. Contained the values() live-iteration race.
- v1 (2026-07-07, Eve): superseded. Contained the reassignment race.
