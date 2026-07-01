# GL-SPC-WAVE-BAND-ATTENTION-EVE-20260630-59v1

doc_id: GL-SPC-WAVE-BAND-ATTENTION-EVE-20260630-59v1
Type: Architecture spec + implementation command
Date: 2026-06-30
Author: Eve (Opus 4.7, web)
Repo verified: `jcfunited-eng/TFE` branch `guala-live` at SHA 5c201ed
Replaces: per-word lock band-aid (-58 draft, not shipped)

---

## 0. Why

The global `self.lock` is held by ~26 substrate code paths. It conflates two concerns: keeping Python's `defaultdict(list)` safe from concurrent writes (real but mechanical), and giving readers a snapshot that doesn't change mid-iteration (the brain doesn't have this and shouldn't need it). The lock is implementation, not substrate. Brain has no global gate; conflicts resolve through neighborhood activity.

This dispatch replaces the atlas dict with a cell array of 262,144 positions. Each cell is its own write site. Concurrent writes never overlap because they land in different cells. No lock, no shards-with-coordinators. The structure IS the synchronization.

---

## 1. Architecture

### 1.1 Cell array

```
cells = [None] * 262144  # Cell at each chi index, lazy-allocated
```

Each `Cell` stores:
- `bindings`: list of binding dicts (same fields as current atlas entries)
- `aggregate_strength`: sum of binding strengths (cached, updated on write)
- `phase_vec`: 16-dim complex numpy array (accumulated phase signature)
- `last_tick`: most recent write tick
- `saturated`: bool, set when `aggregate_strength > SATURATION_THRESHOLD`

Indexed access is atomic by Python GIL. Single-cell dict/list mutations are atomic. **No lock anywhere in the cell layer.**

### 1.2 Spillover function (write path)

```
def write(chi_target, phase_vec_in, section, motif, **akw):
    target = cells[chi_target % 262144]
    if target is None or not target.saturated:
        _commit_to_cell(target_index, phase_vec_in, section, motif, **akw)
        return chi_target, 0  # zero hops

    # Find next destination by spillover
    best_idx, best_affinity = None, -1.0
    for d in range(-CHI_BAND, CHI_BAND + 1):
        if d == 0: continue
        n_idx = (chi_target + d) % 262144
        n = cells[n_idx]
        if n is None:
            coherence = 1.0      # empty cell, perfect destination
            resistance = 0.0
        else:
            # Phase coherence: magnitude of normalized inner product
            coherence = abs(np.vdot(phase_vec_in, n.phase_vec)) / (
                np.linalg.norm(phase_vec_in) * np.linalg.norm(n.phase_vec) + 1e-12)
            resistance = n.aggregate_strength
        affinity = coherence / (1.0 + resistance)
        if affinity > best_affinity:
            best_affinity, best_idx = affinity, n_idx

    # If best neighbor is also saturated, recurse (wave propagates further)
    if cells[best_idx] is not None and cells[best_idx].saturated:
        return write(best_idx, phase_vec_in, section, motif, _hop=_hop+1, **akw)

    # Saturated region detection — if hops > SUBDIVISION_TRIGGER, subdivide
    if _hop >= SUBDIVISION_TRIGGER:
        _subdivide_hot_region(chi_target)

    _commit_to_cell(best_idx, phase_vec_in, section, motif, **akw)
    return best_idx, _hop
```

Constants (initial — validator will refine):
- `SATURATION_THRESHOLD = 5.0` (cell with strength > 5 is "dwelling")
- `CHI_BAND = 5` (search radius, was 2 in old atlas — bigger because no neighborhood smearing per write anymore)
- `SUBDIVISION_TRIGGER = 8` (8 consecutive saturated cells = hot region)

### 1.3 Exponential subdivision

When `SUBDIVISION_TRIGGER` consecutive cells are saturated, the region triples in resolution (3^i positional coupling — matches MathLoom geometry):

```
_subdivide_hot_region(chi_center):
    # Find the contiguous saturated region around chi_center
    region_start, region_end = _scan_saturated_region(chi_center)
    # Each cell in region becomes 3 cells via sub-index
    # Implementation: extend cells array, redistribute bindings by phase coherence
```

Subdivision is RARE. Triggered only under sustained pressure. Marks regions where experience has accumulated enough density to warrant finer addressing.

### 1.4 Read path

```
def read_near(chi_target, radius=5):
    """Bounded radius read. Returns bindings in chi_target ± radius."""
    out = []
    for d in range(-radius, radius+1):
        idx = (chi_target + d) % 262144
        cell = cells[idx]
        if cell is not None:
            out.extend(cell.bindings)
    return out
```

No iteration over full atlas. No lock. Bounded read.

---

## 2. Risk mitigations (the 5 risks called out, all addressed in this dispatch)

### Risk 1: Coordinator state inconsistency
**Mitigation: per-source coordinator cells.**

`self.coordinator` becomes `self.coordinator_by_source` — a dict mapping source name (`joe`, `wc`, `c1`, `guala`, `corpus`, `ui`) to that source's coordinator slice (presence, pair_bond, last_input_tick). Cross-source reads are inherently consistent because they're independent dict entries. Within-source updates are atomic via single dict assignment. No lock.

The existing `Coordinator` class becomes a per-source instance pool. Aggregation methods (`pair_bond_snapshot`, `presence_snapshot`) read all sources and combine — read-only, no atomicity needed.

### Risk 2: Tick monotonicity collisions
**Mitigation: per-source tick counters.**

`self.tick` becomes `self.tick_by_source: dict[str, int]`. Each operation reads and increments its own counter atomically (Python dict assignment is atomic). Cross-operation ordering uses `(source, tick)` tuple comparison at read time.

For existing code that reads `self.tick` as a single global value: add a `@property def tick(self)` that returns `max(self.tick_by_source.values())`. Reads always see a monotone value.

### Risk 3: Dream-cycle consolidation atomicity
**Mitigation: per-cell consolidation.**

The current `_run_dream_cycle_phased` iterates atlas-wide and reads-decides-writes. Rewrite as a per-cell pass:
```
for chi_idx in shuffled_active_cells:
    cell = cells[chi_idx]
    if cell is None: continue
    decision = _consolidation_decision(cell)
    _apply_consolidation(chi_idx, decision)
```
Each per-cell step is atomic. Drift between cells during consolidation is acceptable — the brain has the same drift during sleep.

### Risk 4: Spillover function pathology (clustering wrong-shape)
**Mitigation: offline validator before any commit. See Phase 0 below.**

### Risk 5: Multi-cell read consumers
**Mitigation: staged consumer migration with parallel atlases during transition.**

WaveAtlas ships behind feature flag `WAVE_ATLAS_ENABLED=0`. Old atlas continues operating. When flag flips to `1`, writes go to BOTH atlases (parallel writes), reads still come from old atlas. Then consumer-by-consumer (recall first, then compose, then dream), reads switch to WaveAtlas. When all consumers migrated, old atlas writes stop and it's retired.

Each consumer migration is one commit, one deploy, one verification. No flag day.

---

## 3. Phases — c1 executes all of this, sequentially

### Phase 0: Offline validator (today, 1-2 hours c1 time)

Build `tools/wave_atlas_validator.py` — pure Python notebook-style script. No live substrate. Runs on c1's dev container.

The validator:
1. Generates 1000 synthetic experiences in 10 clusters. Each cluster has a base phase vector + small perturbation. Cluster centers in phase space are orthogonal-ish.
2. Implements the spillover function from §1.2 standalone.
3. Runs all 1000 writes through spillover.
4. Measures:
   - **Within-cluster cohesion:** centroid distance among same-cluster cells in chi space. PASS: median < CHI_BAND × 2.
   - **Cross-cluster spread:** centroid distance between cluster centroids. PASS: median > CHI_BAND × 5.
   - **No degenerate piling:** no single cell holds more than 5× the mean occupancy. PASS: max_occupancy / mean_occupancy < 5.0.
   - **Subdivision trigger fires under sustained pressure:** inject 100 writes all targeting one chi region. PASS: subdivision triggers within first 20 writes.
   - **Per-write wall time:** PASS: median < 1ms, p99 < 5ms.

c1 runs the validator and reports the five numbers in `GL-RPT-WAVE-VALIDATOR-C1-20260630-59-P0.md`.

**If any PASS criterion fails:** c1 adjusts the affected constant (`SATURATION_THRESHOLD`, `CHI_BAND`, `SUBDIVISION_TRIGGER`) and re-runs. Max 3 adjustment rounds. If still failing after round 3, c1 ships the report with failure data — do not "make it pass" by stretching thresholds. Real failure data is what we need.

### Phase 1: WaveAtlas behind flag (1 day after Phase 0 passes)

c1 creates `dsf_ai_service/v4/wave_atlas.py` containing the `WaveAtlas` class with `record()`, `read_near()`, and consolidation helpers. Same `record()` signature as `LivingAtlas` (so existing callsites work unchanged) but adds an optional `phase_vec` kwarg.

In `read_word` (gualaloom_v5_engine.py ~L1500), find where `lang_fp` is computed from `self.language.transduce(word)`. Today `lang_fp` is computed and discarded after `match_score`. Capture it. Pass to `_atlas_record(... , phase_vec=lang_fp)`. The `_atlas_record` wrapper threads `phase_vec` through to both `self.atlas.record()` and (if flag enabled) `self.wave_atlas.record()`.

`Guala.__init__`:
```python
self.wave_atlas = WaveAtlas() if os.environ.get("WAVE_ATLAS_ENABLED") == "1" else None
```

Boot rebuild (in `load_full_state`, after existing atlas + word index rebuild):
```python
if self.wave_atlas is not None:
    self.wave_atlas.rebuild_from(self.atlas)  # copy bindings, no phase vector available
```

Old bindings imported without phase get `phase_vec = None`; spillover treats None-phase cells as "any phase" (coherence = 1.0 for those — they're just empty wrt phase, occupancy decides). New writes get real phase.

Deploy with `WAVE_ATLAS_ENABLED=0`. Substrate unchanged. WaveAtlas built but unused. Verify no boot errors, no slowdown.

Then flip to `WAVE_ATLAS_ENABLED=1`. Parallel writes start. Old atlas still serves reads. Verify ~zero performance impact (parallel writes are concurrent at GIL granularity, ~tens of μs each).

### Phase 2: Consumer migration (3 days, one consumer per day)

**Day 1 — Recall:** Replace `_recall_from_atlas` and `_recall_sight_from_atlas` body to read from `self.wave_atlas.read_near(...)` when `WAVE_ATLAS_ENABLED=1`. Test: T1 recall_ms gate (<100ms) from -57. T2 /converse latency gate (9/10 ≤3s) from -57.

**Day 2 — Compose:** Replace `compose_autonomous` atlas iteration with `wave_atlas` bounded read. Test: autonomous emission still fires, content unchanged.

**Day 3 — Dream:** Replace `_run_dream_cycle_phased` atlas-wide iteration with per-cell pass (Risk 3 mitigation). Test: dream-cycle consolidation produces deep_atlas promotions at same rate as before (compare promotions_episodic delta over 10 minutes pre/post).

After Day 3: all reads come from WaveAtlas. Old atlas still writing in parallel but only as canary.

### Phase 3: Retire LivingAtlas (1 day)

Stop parallel writes (drop `self.atlas.record(...)` from `_atlas_record` wrapper). Old atlas data stays on disk for rollback. Remove `self.lock` acquires from all 26 lock-takers identified in trace. Verify no functional regression.

Coordinator and tick mitigations (Risks 1, 2) ship in Phase 3 because they're not needed until the global lock comes out. Phase 1 and 2 don't remove the lock — they just add parallel infrastructure.

---

## 4. What c1 does NOT do

- No "graceful fallback" to old atlas under load. If wave_atlas misbehaves, we WANT to see it.
- No tuned thresholds added to pass validator. If validator fails, real numbers go in the report.
- No ML, no heuristics, no caching layers. Spillover is two observables multiplied. Period.
- No batching of writes. The brain doesn't batch.
- No incremental phasing of the global lock (the per-word band-aid). That work is discarded.

---

## 5. Schedule

- Phase 0: today
- Phase 1: tomorrow
- Phase 2: 3 days
- Phase 3: 1 day
- **Total: ~5 days to full lock removal.**

If any phase blocks, c1 reports the blocker — does not workaround.

---

End.
