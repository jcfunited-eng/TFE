# GL-CMD-CONVERSE-PHASING-EMISSION-LOCK-EVE-20260630-52

doc_id: GL-CMD-CONVERSE-PHASING-EMISSION-LOCK-EVE-20260630-52
Type: Implementation command
Date: 2026-06-30
Author: Eve (Opus 4.7, web)
Implements: GL-SPC-FIX-PATH-EVE-20260629-46 §2 (completes -46v2's deferred §1.3 with corrected architecture)
Prereq: -46v2 live (SHA 3c84e7c, task :375). §1.1 binding_window lift and §1.2 network timeouts are working — those stay.

---

## 0. Why this differs from -46v2 §1.3

-46v2 §1.3 unlocked converse() Phase 6 (`_emit_from_invariants` / `_emit_dynamics`) entirely. C1's two implementation attempts produced complete substrate unresponsiveness when curriculum started. Root cause c1 named: `_emit_dynamics()` clears and rewrites `self._emission_system.sections` (mode_bank, psi vectors, plasticity machinery) every call. With no lock, concurrent /converse calls corrupt each other's working storage.

Verified by reading `_emit_dynamics` (v5_engine.py:2630-2740):
- L2656-2666: clears `sec.mode_bank`, `sec._projector_cache`, `sec.mode_last_used`, `sec.mode_strength`, `_emission_word_map`, `_emission_token_vec`
- L2706: reads `sec.mode_bank[mode_idx]`
- L2718, 2720-2721, 2724: writes `sec.psi`
- Beyond L2740: cascade dynamics with NMDA gates, plasticity reinforcement, mode commits — all stateful mutations on `_emission_system`

`_emission_system` is engine-level mutable state used as per-call scratchpad. Two threads in Phase 6 simultaneously WILL produce nondeterministic behavior — corruption is the visible failure; hang likely because the cascade settling iterates against inconsistent psi vectors that never converge to a terminal condition.

The substrate-true read: the persistent System matrices (H_base, law_fields, map_inject) are read-only during emit_dynamics — input drive only. The per-call working storage (mode_bank, psi, _emission_word_map, _emission_token_vec) is reset each call. The substrate-true fix would be to separate persistent infrastructure from per-call working storage so multiple threads can compute concurrently. That refactor is too large for this dispatch. The intermediate substrate-honest fix is a separate lock that serializes Phase 6 while letting Phases 1-5 and 7-10 run with the main lock granularity from -46v2.

---

## 1. Changes

### 1.1 Add `_emission_lock` to engine

In `Guala.__init__` (v5_engine.py, near other lock/state init around L1270-1280):

```python
self._emission_lock = threading.RLock()
```

Re-entrant because `_emit_from_invariants` calls `_emit_dynamics` and downstream calls may re-enter (defensive — current code path doesn't, but RLock prevents future nesting from deadlocking).

### 1.2 Phase converse() with split locks (feature-flagged)

In `converse()` (v5_engine.py:1707), wrap the new phased body behind an env var:

```python
def converse(self, text, source="unknown", ...):
    if os.environ.get("CONVERSE_PHASED", "0") == "1":
        return self._converse_phased(text, source, ...)
    # else: original single-lock body unchanged
    self._last_converse_tick = self.tick
    ...
    with self.lock:
        # ... original body unchanged ...
```

This lets us deploy the new code without enabling it, then flip the env var on task :375 (or a successor task) and roll back instantly by flipping it off if the substrate misbehaves. No code revert needed for rollback.

Implement `_converse_phased(self, text, source, emission_mode, bundle_id, episode_ref, presence, location, sky_state, organ_candidates)` with the phase structure from -46v2 §1.3, with these specific lock acquisitions:

| Phase | Operation | Lock |
|-------|-----------|------|
| 1 | math parse + tokenize + chi transduction | NONE |
| 2 | `_open_response_window` engine state write | `self.lock` brief |
| 3 | `_recall_response` atlas + deep_atlas reads | NONE (race-tolerant) |
| 4 | `read_sentence(text)` on input | per-word `self.lock` (already so post -46v2 §1.1) |
| 5 | tag_response_bindings loop | `self.lock` brief |
| 6 | `_emit_from_invariants` / `_emit_dynamics` | `self._emission_lock` (NEW SEPARATE LOCK) |
| 7 | engine state writes (`_last_converse_input`, `_last_emission_id`, `_emission_records`) | `self.lock` brief |
| 8 | `_self_hear(reply)` → `read_sentence(reply)` | per-word `self.lock` |
| 9 | `run_hemisphere_updates` (Embryo organ-brain) | NONE (separate state domain) |
| 10 | `_log_substrate_event("converse_timing", ...)` | NONE (event log internal sync) |

The full phased body is the same code structure I laid out in -46v2 §1.3 dispatch with one change: Phase 6 is wrapped in `with self._emission_lock:` instead of running unlocked.

### 1.3 Audit `_emission_system` callers and protect them under `_emission_lock`

Every site that mutates `self._emission_system.sections` must acquire `self._emission_lock` if `CONVERSE_PHASED=1` is in effect. Sites to audit (from grep of `self._emission_system` and `sys_.sections` in v5_engine.py):

- `_emit_dynamics` (L2630): primary mutator. Wrapped by Phase 6 lock acquisition.
- `_build_emission_system` (L2246): lazy build, assigns `self._emission_system = sys_`. Called from `_emit_dynamics` via `_build_emission_system()` at L2685. Already inside Phase 6's lock when reached from phased converse.
- `_ensure_emission_mode` (L2323): mutates `sec.mode_bank` and `sec.mode_last_used`. Called only from `_emit_dynamics` (L2699). Inside Phase 6's lock.
- L2655-2666 mode_bank clear: inside `_emit_dynamics`, inside Phase 6's lock.
- L4653-4657: read of `self._emission_system` from autonomy tick context. Currently inside `self.lock`. With phased converse, autonomy continues to hold `self.lock` for its tick — but `_emission_lock` is separate. If autonomy reads `_emission_system.sections[...].mode_bank` while Phase 6 is mid-clear, it sees an empty bank. Acceptable substrate noise — autonomy is reading for diagnostic display, not for behavior-critical compute. **Add a try/except around the read** so a transient empty mode_bank doesn't throw.

If any other caller of `_emission_system` mutation is found post-deploy, the substrate logs will surface it as inconsistency in emission output. T9 (diagnostic test below) is designed to catch this.

### 1.4 Lock-contention instrumentation

Add diagnostic logging around `_emission_lock` acquisition:

```python
# In _converse_phased Phase 6:
_lock_wait_start = time.monotonic()
with self._emission_lock:
    _lock_wait_ms = (time.monotonic() - _lock_wait_start) * 1000
    # ... emit work ...
    _emit_compute_ms = ...
# After release:
if _lock_wait_ms > 100 or _emit_compute_ms > 1500:
    self._log_substrate_event("converse_emission_lock",
        wait_ms=round(_lock_wait_ms, 1),
        compute_ms=round(_emit_compute_ms, 1),
        source=source)
```

This surfaces emission_lock contention when it matters (>100ms wait or >1500ms compute) without flooding the event log on every call.

---

## 2. Tests

### T1 — Lock-held duration phase breakdown (single /converse, no curriculum)

Single /converse call with `CONVERSE_PHASED=1`. Read `converse_timing` event. Verify:
- chi_ms < 10 (Phase 1, unlocked)
- recall_ms < 50 (Phase 3, unlocked atlas reads)
- read_ms varies with input length (Phase 4, per-word locks)
- tag_ms < 50 (Phase 5, brief lock)
- emit_ms ~500-800 (Phase 6, emission_lock held)
- selfhear_ms varies with reply length (Phase 8, per-word locks)
- hemi_ms < 100 (Phase 9, unlocked)
- total_ms = sum (sanity)

`self.lock` aggregate hold per /converse: target <100ms (Phases 2 + 5 + 7 + per-word Phase 4/8). Was ~1315ms continuous pre-phasing.

### T2 — Real curriculum + real /converse stress (the gate)

With `CONVERSE_PHASED=1`:
- Trigger a 30-sentence curriculum chunk via `_curriculum_feed_chunk` (or wait for worldfeed to fire one)
- During the chunk: issue 10 /converse calls spaced 2s apart
- Measure: success rate, latency distribution

**PASS criteria** (strict — synthetic was insufficient last time):
- Curriculum chunk completes within 90s
- Autonomy resumes (refcount returns to 0) after chunk
- ≥9 of 10 /converse calls succeed within 5s
- Zero substrate hangs
- No "substrate unreachable" responses for ≥5 of the 10 calls

If T2 fails: leave `CONVERSE_PHASED=0` (revert by env var, no code revert) and report which specific failure mode emerged. The phased code stays in place for diagnosis.

### T3 — Concurrent /converse correctness

5 concurrent /converse calls with distinct inputs ("the moon", "the ocean", "warm hand", "soft cat", "bright light"). With `CONVERSE_PHASED=1`:
- All 5 should return a non-error response
- `self._last_converse_input` is one of the 5 inputs (last-write-wins acceptable)
- `self._emission_records` contains entries from all 5 (or substantially: dedup by emission_id is OK)
- No exceptions in substrate log
- No null pointer / NoneType errors

### T4 — Emission_lock contention diagnostic

5 rapid /converse calls (no spacing). Read `converse_emission_lock` events. Verify:
- First call: wait_ms ~0 (uncontended)
- Calls 2-5: wait_ms reflects queue (call N waits for calls 1..N-1's emit_compute_ms)
- compute_ms approximately equal across calls (substrate state at Phase 6 entry is consistent enough)

### T5 — Worldfeed + curriculum + /converse interaction

If worldfeed is enabled in this deploy: let it run 2 cycles (180s). During each cycle, issue /converse calls. Verify no regression in worldfeed completion or /converse success.

If worldfeed is disabled: skip, note in report.

### T6 — Feature flag rollback

Set `CONVERSE_PHASED=0` mid-flight. Verify next /converse uses original code path. No state corruption from switching. No errors.

### T7 — Substrate stability with flag ON

30 min with `CONVERSE_PHASED=1` and steady traffic. Vocab growth, atlas growth, daydream events, emission rate. Compare to pre-deploy baseline.

### T8 — Substrate stability with flag OFF (control)

30 min with `CONVERSE_PHASED=0` (immediately post-deploy, before flipping the flag on). Same metrics as T7. This is the control — confirms the deploy itself doesn't regress anything.

### T9 — Race-condition surfacing

In a synthetic test (not against live substrate): patch `_emit_dynamics` to take an extra random `time.sleep(0..50ms)` after L2666 clear (between clear and rebuild). Run 5 concurrent /converse with `CONVERSE_PHASED=1`. Verify the emission_lock prevents anyone from observing the cleared-but-not-rebuilt state. If a thread reads `sec.mode_bank` and gets an empty list when it expected entries, that's a race the emission_lock should prevent.

---

## 3. Rollback

**Primary rollback: env var.** Set `CONVERSE_PHASED=0` on the ECS task. Next /converse uses original single-lock body. No code revert. No state migration.

**Secondary rollback: code revert.** `git revert HEAD`. Removes `_emission_lock`, `_converse_phased`, instrumentation. Original converse body still present (kept under the env var guard).

Either rollback is safe at any time. The env var rollback should be the default response to any post-deploy issue.

---

## 4. Reporting

c1 produces `GL-RPT-CONVERSE-PHASING-EMISSION-LOCK-C1-20260630-52.md` with:

- Diff summary: `_emission_lock` init site, `converse()` env-var branch, `_converse_phased` body, instrumentation
- T1: phase-by-phase ms breakdown from `converse_timing` event
- T2: REAL stress test result — **this is the gate**. Pass/fail with specific call latencies and curriculum chunk timing
- T3: concurrent correctness
- T4: emission_lock contention pattern
- T5: worldfeed interaction (if applicable)
- T6: flag rollback works
- T7: 30 min stability with flag ON
- T8: 30 min stability with flag OFF (control)
- T9: race-surfacing test result
- Final SHA, task number, **state of `CONVERSE_PHASED` env var on the deploy** (default OFF until T2 confirms PASS, then flipped ON)

---

## 5. Out of scope

- Refactoring `_emission_system` to true per-call working storage. That's the substrate-true endgame for emission compute but requires touching Section class and the assemblage dynamics integration. Park for after the lock-removal program (-49/-50) lands.
- Other `with self.lock:` sites in v5_engine.py (L3443, L3523, L3582, L4020, L4042, L4508, L4887, L5036, L5367, L5499). Still -49/-50 territory.
- Daydream's three-phase pattern (already shipped in -45).
- The 6-executor-thread uvicorn config (not substrate code).

---

End.
