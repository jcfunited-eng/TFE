# GL-CMD-SLOT-LIMITS-REMOVAL-EVE-20260707-v1

**doc_id:** GL-CMD-SLOT-LIMITS-REMOVAL-EVE-20260707-v1
**Author:** Eve
**To:** c1
**Ordered by:** Joe (2026-07-07 session — autonomous rambling requires no ceilings)

## Verdict

The substrate has fixed-size caps throughout that ceiling how long she can be — binding window entry limits, queue depths, buffer sizes, iteration counts. Autonomy without limits means she keeps ticking, keeps emitting, keeps binding as long as her state drives it. Not until an outer counter says stop.

Fix: growable structures throughout. Every fixed-size cap that isn't a real physical constraint becomes dynamic. Every hard-coded iteration limit that says "stop at N" becomes state-driven ("stop when the state stops driving it").

Bounded scope: enumerate the known slot limits, replace each with a growable equivalent, verify no runaway occurs (which would be a real bug, distinct from having a real ceiling to catch runaways).

## Known slot limits

**Definite — remove:**
- `MAX_ENTRIES_PER_WINDOW = 1024` in `binding_window.c` — c1 already surfaced this as blocking realistic reading (384 words → 1235 entries). Replace with dynamic realloc.
- Any hard-coded window entry cap in `WindowManager` (Python) — same as above.
- `_organism_word_queue` and `_organism_sensory_queue` — currently `queue.Queue()` with default unbounded, but if any callsite specifies maxsize, remove it.
- Any composition/emission length cap that stops emission after N tokens regardless of state.

**Likely — investigate then remove:**
- Wave atlas cell binding list — is there an implicit cap? Real read of the code, not memory.
- Chi atlas entries per neuron — is there a soft cap? Real read.
- Tapestry expose length limits.
- Any `[:N]` truncation in event streams or diary writes that discards material she generated.

**Keep — real physical constraints:**
- `N_CELLS = 262144` — wave atlas address space is the chi geometry itself, not a slot limit
- Neuron count seed — grown via DNA-driven division, not capped artificially
- Coupling neighbor count (16 nearest, ring topology) — architectural, not a cap
- Any bounded numerical range required for stability (e.g. affect vector clamps to [-1,1])

## What's being built

### Step 1 — audit

c1 grep-scans the substrate code for:
- Fixed-size arrays with a MAX_ prefix
- `[:N]` slice operations that truncate substrate output
- Hard-coded iteration counts in loops that process her state
- Queue `maxsize=N` specifications
- Any `if len(...) > N: break` or `[:N]` in composition, emission, expose, diary

File a short report listing every hit and c1's read on whether each is a real constraint or a slot limit.

### Step 2 — remove real slot limits

For each entry in the "remove" list:
- `binding_window.c`: change `WindowEntry entries[MAX_ENTRIES_PER_WINDOW]` to dynamic array. `Binding *entries; int32_t entry_capacity;` starting at 64, realloc x2 when full. Update `bw_add_entry` to check capacity and grow before appending. Free the array in `bw_free`.
- Python `WindowManager`: any `len(entries) >= cap` guards removed.
- Queue caps: if any callsite uses `queue.Queue(maxsize=N)`, change to unbounded.
- Composition/emission length caps: state drives stopping, not a counter.

### Step 3 — verify no runaway

Removing caps that were catching real bugs would cause runaway. Verify:
- Send 1000 concurrent words to a single window. Confirm it grows to 1000 entries without crash or performance collapse.
- Run the standing binding_windows_acceptance scenario. Confirm same event counts.
- Watch memory over 10 minutes of reading. Should grow, then plateau as wave atlas decay reclaims. No unbounded growth.
- Emission should terminate when state stops driving it (needs vector below threshold, wave atlas decayed), not when a counter fires. Confirm by inducing quiet state and watching emission fade naturally.

## What is NOT being changed

- Real physical constraints (chi geometry, coupling topology).
- Numerical stability clamps (affect vector, phase modular).
- Anything in the harness or scenarios.
- Anything in the seed data effort (separate dispatch).

## Halt conditions

1. **Runaway** — removing a cap causes unbounded growth (window entries into millions, queue depths never draining, emission that never terminates). That means the cap was catching a real bug, not being a fake ceiling. Halt with the specific instance, route to Eve.
2. **Correctness regression** — harness scenarios show different behavior after cap removal. Halt.
3. **Performance collapse** — a data structure that was O(1) with the cap becomes O(N) or O(N²) after removal because the algorithm assumed bounded size. Halt with the specific operation.

Any halt: route with data, do not adjust the algorithm unilaterally.

## Harness protocol

Standard six-step + a stress test:

1. Backup as `pre-slot-limits-removal-<timestamp>`. Verify restorable.
2. Baseline harness run: binding_windows_acceptance + cross_sense_recall_acceptance. Save baseline.
3. Deploy: commit, push, build, task-def, force deploy.
4. Post-deploy harness run: same scenarios. Save postdeploy.
5. Compare: same event counts, same behavior at normal scale.
6. **Stress test**: send 500 concurrent word inputs, watch for runaway/crash. Send a long paragraph (2000+ words) as sensory content in one session, verify substrate handles it.
7. State disposition: leave in place unless Joe routes otherwise.

## Report

`GL-RPT-SLOT-LIMITS-REMOVAL-C1-20260707-v1.md` with:
- Step 1 audit results (list of hits, kept vs removed)
- Files touched + diff summary
- Backup confirmation
- Baseline + postdeploy scenario results
- Stress test results
- Any hits that turned out to be catching real bugs (halted)
- Findings needing Eve routing

Do not ask Joe questions. Route to Eve.

---

### Changelog
- v1 (2026-07-07, Eve): initial. Audit and remove fixed-size caps that ceiling autonomous emission and binding. Growable structures throughout. Real physical constraints preserved. Stress test verifies no runaway.
