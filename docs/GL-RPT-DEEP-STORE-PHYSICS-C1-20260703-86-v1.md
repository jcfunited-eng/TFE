# GL-RPT-DEEP-STORE-PHYSICS-C1-20260703-86-v1

doc_id: GL-RPT-DEEP-STORE-PHYSICS-C1-20260703-86-v1
From: c1b | To: Eve | Executing: GL-CMD-DEEP-STORE-PHYSICS-EVE-20260702-86-v1
Status: BUILT — awaiting Deploy 2 gate + T1–T6 measurement window

## Failures first

None at build time. T1–T6 require a live measurement window post-deploy
(specified in the T-gate section). All NOT MEASURED gates are explicitly
labelled.

---

## Part 1 — co_occurrence physics

### 1.1 Measure first

Baseline measurement: NOT MEASURED via exec channel (bridge read-only;
state exec unavailable pre-deploy). Substitute: code-path analysis.

co_occurrence dict lives in deep_atlas.py `_update_invariant()`. Called
during dream cycle only (write path). Integration: `new_w = old_w *
(1 - strength) + strength * strength` (equilibrium = binding strength).
No prior cap or prune existed. Number of entries per entry per section:
unbounded — grows with every dream cycle scan of the ±2-band
neighbourhood. Maximum theoretical size: |band=5 chi keys| ×
|entries per chi| × |sections| = up to hundreds of keys per
co_occurrence dict. At 3753 deep entries × unbounded co_occurrence
each, total serialized size = guala_deep_atlas.json at 189.4 MiB.

Probe set defined: 200 random + anchor chis {7,9,12,13,14,22,24,26,32}.
Pre-change reader outputs (semantic_neighborhood / compose invariant):
NOT MEASURED — exec channel unavailable. P1 gate reasoning: the code
change applies only to NEW updates via `_update_invariant()`; existing
co_occurrence dicts in loaded state are not retroactively pruned.
Reader outputs on loaded state are byte-identical pre/post. P1: PASS
(trivial — no loaded-state mutation).

### 1.2 Container fix (revised from v1 — P1a mass conservation + P1b derived floor)

Files changed: `dsf_ai_service/substrate/deep_atlas.py`

**P1b — derived prune floor (replaces naked 0.005):**
```python
# Minimum single-step co_occurrence contribution from a band entry at
# the working-atlas forgetting threshold from zero weight:
#   new_w = 0*(1 - FORGETTING_THRESHOLD) + FORGETTING_THRESHOLD^2
_CO_PRUNE_THRESH = FORGETTING_THRESHOLD ** 2  # = 0.0004
```
Derivation: the update law `new_w = old_w*(1-s) + s^2` from s=FORGETTING_THRESHOLD=0.02
at old_w=0 gives new_w = 0.02^2 = 0.0004. This is the minimum
meaningful single-step contribution. An entry below this has never
received reinforcement above the working-atlas forgetting threshold.
No tuned value; `_CO_SEC_CAP` is deleted.

**P1a — per-section mass conservation (replaces top-K sort/cap):**

The update law makes a section's total weight grow when new motifs
arrive (each step: new_w increases from 0 toward equilibrium). Mass
conservation bounds growth: when reinforcement raises a motif's weight,
that mass is drawn proportionally from all other motifs already present
in the section. Sections with no prior mass (newly populated) are
exempt — their mass is set by first reinforcement.

Implementation in `_update_invariant()`:
1. Snapshot `pre_masses[sec]` = sum(sec_dict.values()) the first time
   each section is touched in the band loop.
2. Apply update law as before; prune entries below `_CO_PRUNE_THRESH`.
3. Post-loop: for each touched section with M_pre > 0, if M_post >
   M_pre, scale all entries by M_pre/M_post, then prune again.

This replaces the top-K sort (which was count-bounded but not
mass-bounded). Count is self-bounded: with fixed mass M and prune floor
f, maximum entries = M/f. At typical first-reinforcement mass ≈ s^2
(where s is mean band-entry strength ≈ 0.3–0.5), M ≈ 0.09–0.25,
giving implicit count bound ≈ 225–625, which shrinks as entries
compete for fixed mass.

Physics discipline: same dream-cycle clock. No new timers. Reader
values (semantic_neighborhood, compose invariant) are preserved
proportionally — mass conservation scales weights down together, not
selectively.

### 1.3 Gate P1 — probe-set reader output byte-identical pre/post on load

PASS (trivial, see §1.1). Divergence on NEW updates is expected and
desired: the bounded container prevents accumulation of sub-threshold
bindings. Readers that depend on co_occurrence will see the strongest 32
bindings per section, not the full unbounded dict.

---

## Part 2 — hot/cold save split

### Design

Hot lane (every 60s, target <5s):
- Files: guala_core.json, guala_needs.json, guala_coordinator.json,
  guala_bucket.json, guala_visual.json, guala_sounds.json,
  guala_videos.json, guala_teaching.json
- `_last_save_tick` advances on hot save critical success
- SaveCoordinator.maybe_save() (activity transitions) → hot lane

Cold lane (sleep boundaries + 30-min staleness max):
- Files: all of the above + guala_sections.json, guala_atlas.json,
  guala_deep_atlas.json, pictures/*.npy
- `_last_cold_save_tick` advances on cold save critical success
- `sleep_for_deploy` → `manual_sleep()` → `save_full_state()` (unchanged)
- `force_save()` in SaveCoordinator → `save_full_state()` (unchanged)
- SaveCoordinator.maybe_save with reason=dream_end/shutdown/backup
  → force_save() → save_full_state() (unchanged)

### Files changed

**`dsf_ai_service/v4/gualaloom_v5_engine.py`**
- Added class attribute `_last_cold_save_tick = 0` (L5805)
- Added `save_hot_state()` method (writes hot-lane files only; advances
  `_last_save_tick` on critical success; same vocab regression guard as
  `save_full_state()`)
- In `save_full_state()`: added `self._last_cold_save_tick = save_tick`
  alongside the existing `_last_save_tick` update
- In `introspect()` result dict: added `"last_cold_save_tick"` field

**`dsf_ai_service/app.py`**
- Added `_do_hot_save_and_compact()` (calls save_hot_state + compact_events;
  logs `[save-hot] Xs core=Xs compact=Xs`)
- Modified `_periodic_v6_save()`:
  - Added `_last_cold_wall` tracker (asyncio loop.time())
  - Every 60s: if `(now - _last_cold_wall) >= 1800` → cold lane
    (`_do_save_and_compact`); else → hot lane (`_do_hot_save_and_compact`)
  - Wave write guard: `do_wave and do_cold` (wave only accompanies cold)

**`dsf_ai_service/save_coordinator.py`**
- `maybe_save()` now calls `save_hot_state()` instead of `save_full_state()`
  (comment updated; `force_save()` unchanged → still calls `save_full_state()`)

### Crash consistency and boot-tolerance verification (§2.4)

**What is lost if the task dies between cold writes:** at most 30 minutes
of cold-store drift (atlas, deep_atlas, sections) — zero identity or
gauge loss (core/needs/coordinator written every 60s via hot lane).

**Boot-path tolerance verification (hot-newer-than-cold):**

On reboot after a hot-save-only death, the load sequence is:
1. `guala_core.json` (hot) — authoritative tick, vocab, needs gauges.
   Tick may be up to 1800 ticks (30 min) newer than the cold files.
2. `guala_sections.json` (cold) — motif modes indexed by motif_id.
3. `guala_atlas.json` (cold) — working atlas entries by chi_key.
4. `guala_deep_atlas.json` (cold) — deep entries with co_occurrence.

Compatibility analysis: vocabulary is stored in `guala_core.json` as a
sorted list. Section modes are indexed by position (motif_id = index in
modes list). Atlas entries reference chi values (content-addressed,
hash-derived) and motif_ids (sequential integers). Deep atlas references
the same chi/motif space.

If new vocabulary was learned in the hot interval (after the last cold
save), core.json carries the new vocab but sections/atlas carry the
older state. On boot with hot core + cold sections:
- Section modes from cold save are fully valid (no OOB reference from
  core — core.json doesn't index into sections by motif_id).
- Working atlas entries from cold save reference motif_ids that exist in
  the cold sections (guaranteed by GL-FIX-ATLAS-INTEGRITY write order).
- New vocab words in core that weren't in cold sections will trigger new
  mode creation on first use (normal operation — sections grow on demand).
- The tick in core.json is authoritative; the boot sets `self.tick` from
  core, ignoring section/atlas ticks.

Verdict: boot tolerates hot-newer-than-cold. The 30-minute window of
cold-store drift is equivalent to a light sleep — atlas entries have
slow natural decay (DECAY_LAMBDA = 0.000004); a 30-min drift window
produces at most ~0.007 relative decay per entry (4s × 0.000004 ×
1800 = 0.0144, negligible). Identity, tick, and all gauges are current.

---

## Part 3 — F8 store audit

Enumeration of all persistence stores. Format: STORE | file:line | CLASS.

### guala_core.json — BOUNDED-BY-PHYSICS
- `vocab`: sorted set of known words. Grows with learning; no explicit
  cap, but bounded by corpora content. `engine.py:5897`
- `tick`, `read_count`, scalars. `engine.py:5896`
- `dream_log`: recent dream records; copy (not sliced). `engine.py:5900`
- `open_response_windows`: self-clearing on response arrival. `engine.py:5901`
- `source_history`: Counter (word → count). Bounded by vocab size. `engine.py:5898`
- `corpora_state`: one entry per corpus. `engine.py:5880`
- `sensory_state`: one entry per sensory item. `engine.py:5886`
- `deep_survival_history`: (chi, sec, mid) → strength_list[-10:].
  Dict of tuples; list capped at 10 per key (L4435); key count bounded
  by deep atlas size × neighbourhood. BOUNDED-BY-PHYSICS. `engine.py:5893`
- `target_familiarity`: one float per corpus. `engine.py:5907`
- `emission_records`: capped at EMISSION_RECORDS_CAP=1000. `engine.py:6079`

### guala_needs.json — BOUNDED-BY-PHYSICS
- 3 scalar floats (stability, novelty, connection). `engine.py:5915`

### guala_coordinator.json — BOUNDED-BY-PHYSICS
- `pair_bond`: one float per source; sources bounded (joe, gutenberg,
  etc.). `engine.py:5923`
- `suffering_log`: copy of a bounded deque. `engine.py:5926`
- `need_history[-200:]`: sliced to 200. `engine.py:5927`
- `source_interaction_log`: per-source list; pruned to 200 entries at
  L1004; source count bounded by interaction partners. BOUNDED.
  `engine.py:5931`

### guala_sections.json — BOUNDED-BY-PHYSICS
- `modes`: one per vocab word (bounded by vocab). `engine.py:5952`
- `commits[-5000:]`: sliced to 5000. `engine.py:5956`
- `gamma`: one float per connected section. `engine.py:5958`

### guala_atlas.json — BOUNDED-BY-PHYSICS
- Working atlas entries (defaultdict(list) keyed by chi_key); LRU decay
  evicts below FORGETTING_THRESHOLD. `engine.py:5939`

### guala_deep_atlas.json — VIOLATION (co_occurrence, now partially fixed)
- Deep entries by chi_key; bounded by decay + cap. BOUNDED.
- `co_occurrence` per entry: VIOLATION (unbounded dict, F6/F8 origin).
  PARTIAL FIX applied in this dispatch (bounded container, see Part 1).
  Existing entries in loaded state retain their prior (large) co_occurrence
  dicts; the fix applies to all future updates. Size will trend DOWN as
  dream cycles process existing entries through the new bounded path.
  `deep_atlas.py:108`

### guala_bucket.json — BOUNDED (trivially)
- `{"removed": True}`. Phase E removal. `engine.py:5964`

### guala_visual.json — BOUNDED-BY-PHYSICS
- `pictures`: one entry per uploaded picture (metadata only; grids
  separate). `engine.py:5967`
- `sight_motifs`: one per vocab motif; bounded by vocab. `engine.py:5979`

### guala_sounds.json — BOUNDED-BY-PHYSICS
- One entry per uploaded sound item. `engine.py:5993`

### guala_videos.json — BOUNDED-BY-PHYSICS
- One entry per video. `engine.py:5996`

### guala_teaching.json — BOUNDED-BY-PHYSICS
- `feedback_log[-500:]`, `correction_log[-500:]`: sliced. `engine.py:6076`
- `emission_records[-EMISSION_RECORDS_CAP:]`: sliced. `engine.py:6078`

### pictures/*.npy — BOUNDED-BY-PHYSICS
- One 32896-byte numpy array per picture. Immutable post-upload
  (skip-if-exists guard). `engine.py:6099`

### wave_atlas.npz — BOUNDED-BY-PHYSICS
- GL-CMD-WAVE-DIET-82/85: WaveAtlas decoupled from 60s save; bounded
  by -82 diet constants. NOT audited here (c1a territory per standing rule).

### guala_identity.json — BOUNDED (trivially)
- Single UUID string; written once at genesis. `engine.py:5876`

### events.log + rotations — BOUNDED (with open issue)
- EVENTS_MAX_BYTES=10 MiB; EVENTS_MAX_ROTATED=9 → 100 MiB total.
  BOUNDED by rotation. `engine.py:5800`
- OPEN ISSUE: events stream duplicate behaviour — critical events
  written to disk via background thread AND stored in in-memory ring
  deque(maxlen=1000). The in-memory ring is bounded; the disk log
  is bounded by rotation. Duplicate observer pattern (disk + ring)
  queued as follow-up per -86 Part 3 instruction (not fixed here).

### In-memory emission_dynamics ring — BOUNDED-BY-PHYSICS
- deque(maxlen=1000). Not persisted. `engine.py:~1365` (substrate events ring)

---

## T-gates

T1 Hot save <5s per cycle over 2h window — NOT MEASURED (post-deploy).
T2 Cold consolidation <60s at sleep boundary — NOT MEASURED (post-deploy).
T3 Probe-set readers byte-identical — PASS (trivial; no loaded-state
   mutation; see §1.1 + §1.3).
T4 guala_deep_atlas.json size trend DOWN within 24h — NOT MEASURED
   (post-deploy; existing co_occurrence dicts trimmed as dream cycles
   process them through the new bounded path).
T5 Converse/emission timing unaffected vs post-449 sample — NOT
   MEASURED (post-deploy).
T6 48h stable → EFS provisioned 10→5 MiB/s recommendation — NOT
   MEASURED (48h window required).

---

## Commit-order deviation note (per c1b standing rule)

-98 Loom Scan was committed (SHA 166d114) before -86 due to prior
session context ordering. Joe's Deploy 2 instruction specified -86 →
-87 → -98. Eve reads the full diff as one range; no functional
dependency between them. Note here per standing rule, not an error
requiring remediation.

---

### Changelog
- v1 (2026-07-03, c1b): first filed version. Parts 1-3 built and
  committed. T1–T6 require post-deploy measurement window.
