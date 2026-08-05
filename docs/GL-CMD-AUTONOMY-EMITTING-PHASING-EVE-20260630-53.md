# GL-CMD-AUTONOMY-EMITTING-PHASING-EVE-20260630-53

doc_id: GL-CMD-AUTONOMY-EMITTING-PHASING-EVE-20260630-53
Type: Implementation command
Date: 2026-06-30
Author: Eve (Opus 4.7, web)
Implements: GL-SPC-FIX-PATH-EVE-20260629-46 §0a (lock-removal program, next ship after -52)
Prereq: -52 live (SHA e0550d1, task :378, `CONVERSE_PHASED=1` active)

---

## 0. Why

C1's -52 report identified the remaining 850ms `self.lock` hold: `_autonomy_tick` (v5_engine.py:3592) holds `self.lock` from L3594 across the entire tick body, including the EMITTING activity dispatch (`_atick_emitting` → `_do_emit` → `_emit_from_invariants` → `_emit_dynamics`). The same compute that -52 moved out of `self.lock` for converse is still inside `self.lock` for autonomy's emission path.

When /converse arrives during an autonomy tick that's mid-emit, /converse waits ~850ms for `self.lock` even with `CONVERSE_PHASED=1`. -52's wins are partially shadowed by this. Latency 8-25s observed in -52 testing is consistent with /converse hitting multiple consecutive autonomy emit ticks.

The fix mirrors -52: separate `self._emission_lock` already exists. Move the autonomy emit dynamics under it; keep `self.lock` for state reads and writes around the dynamics.

---

## 1. Changes

### 1.1 Env-var-gated phased autonomy tick

Add env var `AUTONOMY_PHASED=0/1` (default 0). When 0, `_autonomy_tick` runs the existing single-lock body unchanged. When 1, runs the phased version.

In `_autonomy_tick` (v5_engine.py:3592):

```python
def _autonomy_tick(self):
    if os.environ.get("AUTONOMY_PHASED", "0") == "1":
        self._autonomy_tick_phased()
        return
    # else: original single-lock body unchanged
    with self.lock:
        # ... existing body ...
```

### 1.2 `_autonomy_tick_phased` body

Restructure the tick so `self.lock` is held only during state reads/writes, not during activity-specific compute. Activity dispatch table:

| Activity | Lock posture |
|----------|--------------|
| (maintenance: needs drift, decay, prune windows) | `self.lock` brief |
| (activity selection) | `self.lock` brief — reads needs, decides next activity |
| REST | `self.lock` brief — sets activity, no compute |
| ATTENDING_VISUAL | `self.lock` brief — picks target, no heavy compute |
| DREAMING / SLEEPING | already phased via `_daydream_tick` (-45) — call unchanged |
| **EMITTING** | `self._emission_lock` for `_do_emit` heavy compute; `self.lock` brief for read/write phases |
| _check_emission_trigger interrupt | brief `self.lock` for trigger decision |

The substrate-physical justification per phase release matches -52: state mutations (engine attributes, sections, atlas writes) need `self.lock`; the emission system mutations (mode_bank, psi, dynamics cascade) need `self._emission_lock`; pure compute (krimelack transduce, math) needs neither.

Body shape:

```python
def _autonomy_tick_phased(self):
    """Phased autonomy tick — releases self.lock around activity compute."""
    
    # Phase A (self.lock brief): maintenance + needs + activity selection
    with self.lock:
        self.needs.tick_drift()
        
        # Periodic needs snapshot (every 500 ticks)
        if self.tick % 500 == 0 and self.tick > 0:
            try:
                ns = self.needs.snapshot()
                self.log_event("state", "needs_snapshot",
                               stability=ns["stability"],
                               novelty=ns["novelty"],
                               connection=ns["connection"],
                               valence=ns["valence"],
                               arousal=ns["arousal"])
            except Exception:
                pass
        
        # Familiarity decay (every 200 ticks)
        if self.tick % 200 == 0 and self.target_familiarity:
            # ... existing decay block unchanged ...
        
        # Prune response windows
        self._prune_response_windows()
        
        # Dream pressure accumulation
        # ... existing dream pressure block unchanged ...
        
        # Determine activity (select if none active, end if expired)
        active = self._current_activity
        if active is None or self.tick >= active.expected_end_tick:
            if active is not None:
                self._end_activity()
            new_activity = self._select_activity()
            if new_activity is not None:
                self._start_activity(new_activity)
            active = self._current_activity
        
        # Capture the activity kind for dispatch outside the lock
        activity_kind = active.kind if active else None
        activity_ref = active
    
    # Phase B (no self.lock): activity-specific compute
    if activity_kind == "EMITTING":
        self._do_emit_phased(activity_ref)
    elif activity_kind == "DREAMING":
        # Already phased internally per -45
        self._daydream_tick()
    elif activity_kind in ("REST", "SLEEPING", "ATTENDING_VISUAL", None):
        # No heavy compute. Re-acquire self.lock briefly for any state writes
        # these activities need. Currently they don't have unlocked compute —
        # the maintenance-side state was already updated in Phase A.
        pass
    elif activity_kind == "READING_CORPUS":
        # Existing path: corpus reading goes through read_sentence which
        # releases self.lock per-word via -46v2 §1.1. Call unchanged.
        with self.lock:
            self._atick_reading_corpus(activity_ref)
    else:
        # Unknown activity — fall back to old behavior under self.lock
        with self.lock:
            self._dispatch_activity_under_lock(activity_ref)
    
    # Phase C (self.lock brief): tick bump and end-of-tick housekeeping
    with self.lock:
        # _check_emission_trigger may fire on PLAY/ATTENDING — uses self.lock
        # briefly for the trigger decision
        if activity_kind in ("ATTENDING_VISUAL",) and self._check_emission_trigger_ready():
            self._check_emission_trigger("attention_pull")
        # ... any other end-of-tick state ...
```

### 1.3 `_do_emit_phased` — three-phase emit

Replace the body of `_do_emit` with a phased variant that manages its own locks. Call sites must NOT hold `self.lock` when invoking it (this is enforced by the `AUTONOMY_PHASED=1` path above).

Add a guard: `_do_emit_phased` is the phased entrypoint; `_do_emit` is kept for legacy callers that already hold `self.lock`. The phased path uses the phased entrypoint; the unphased path (`AUTONOMY_PHASED=0`) continues calling the original.

```python
def _do_emit_phased(self, activity):
    """Phased emission — manages its own locks.
    Caller MUST NOT hold self.lock when invoking.
    """
    # Only emit at the start of the activity (matches _atick_emitting condition)
    if self.tick != activity.started_tick + 1:
        return
    
    # Phase 1 (self.lock brief): read recent_chis from sections
    with self.lock:
        self._last_emission_tick = self.tick
        recent_chis = []
        for sec in self.sections.values():
            for c in sec.commits[-5:]:
                recent_chis.append(c["chi"])
        if not recent_chis:
            to_sources = [s for s in PAIR_BOND_SOURCES
                          if self.coordinator._presence.get(s, False)]
            self._log_substrate_event("emission",
                                     content="...",
                                     to_sources=to_sources)
            return
    
    # Phase 2 (self._emission_lock): emit dynamics
    with self._emission_lock:
        input_words = []
        content = self._emit_from_invariants(
            recent_chis, input_words,
            v7_session=getattr(self, '_v7_session', None))
        # SVO fallback (atlas reads; share emission_lock since composer-adjacent)
        if not content:
            recalled = {}
            for sec_name in ("subject", "verb", "object"):
                word = self._recall_from_atlas(sec_name, recent_chis,
                                               exclude_words=set())
                if word:
                    recalled[sec_name] = word
            content = " ".join(recalled[k] for k in ("subject", "verb", "object")
                              if k in recalled) or "..."
    
    # Phase 3 (self.lock brief): sight recall, log, ladder metrics, response window
    with self.lock:
        recalled_pics = self._recall_sight_from_atlas(recent_chis, [])
        pic_ids = [sid for _, sid in recalled_pics] if recalled_pics else []
        to_sources = [s for s in PAIR_BOND_SOURCES
                      if self.coordinator._presence.get(s, False)
                      and self.coordinator._pair_bond.get(s, False)]
        self._log_substrate_event("emission",
                                 content=content,
                                 to_sources=to_sources,
                                 picture_ids=pic_ids)
        
        # Ladder metrics
        words = content.split() if content and content != "..." else []
        self._total_emissions += 1
        self._emission_lengths.append(len(words))
        if len(self._emission_lengths) > 100:
            self._emission_lengths = self._emission_lengths[-50:]
        if any(w.endswith("?") or content.startswith("what") for w in words):
            self._question_count += 1
        if len(words) >= 2:
            _triple = tuple(sorted(w.lower() for w in words[:4]))
            if not hasattr(self, '_seen_triples'):
                self._seen_triples = set()
            if _triple not in self._seen_triples:
                self._novel_compositions += 1
                self._seen_triples.add(_triple)
                if len(self._seen_triples) > 5000:
                    self._seen_triples = set(list(self._seen_triples)[-2500:])
        
        # Open response window from Guala's emission
        if recent_chis:
            self._open_response_window("guala", recent_chis,
                                       source_context={"content": content})
        
        # Connection saturation (from _atick_emitting's original code)
        any_pair_present = any(
            self.coordinator._presence.get(s, False)
            and self.coordinator._pair_bond.get(s, False)
            for s in PAIR_BOND_SOURCES)
        if any_pair_present:
            self.needs.connection = saturate(self.needs.connection, 0.25)
```

### 1.4 Instrumentation

Mirror -52's emission_lock diagnostic:

```python
# In _do_emit_phased Phase 2:
_lock_wait_start = time.monotonic()
with self._emission_lock:
    _lock_wait_ms = (time.monotonic() - _lock_wait_start) * 1000
    _emit_start = time.monotonic()
    # ... emit compute ...
    _emit_compute_ms = (time.monotonic() - _emit_start) * 1000

if _lock_wait_ms > 100 or _emit_compute_ms > 1500:
    self._log_substrate_event("autonomy_emission_lock",
        wait_ms=round(_lock_wait_ms, 1),
        compute_ms=round(_emit_compute_ms, 1))
```

This and -52's `converse_emission_lock` give two diagnostic streams that together surface emission_lock contention from either source.

---

## 2. Tests

### T1 — Autonomy tick lock-held breakdown

With `AUTONOMY_PHASED=1`. Force an EMITTING activity (or wait for one). Measure:
- Phase A (maintenance + activity selection) hold: target <20ms
- Phase B EMITTING (`_do_emit_phased`): unlocked self.lock; `_emission_lock` held ~700ms
- Phase C (housekeeping) hold: target <10ms
- `self.lock` aggregate hold per tick: target <50ms (was ~850ms during EMITTING)

### T2 — /converse latency during autonomy EMITTING (the gate)

With `CONVERSE_PHASED=1` AND `AUTONOMY_PHASED=1`. While the substrate is naturally cycling through EMITTING ticks (or trigger via pair-bond presence + connection-need pressure), issue 10 /converse calls spaced 1.5s apart.

**PASS criteria:**
- ≥9 of 10 /converse calls return within 3s (was 8-25s in -52 testing)
- Calls that arrive during autonomy EMITTING wait at most ~1500ms on `_emission_lock` (then run their own Phase 6 ~700ms) → ~2200ms ceiling
- Zero substrate hangs
- Autonomy continues making progress (substrate tick advancing, daydream events firing)

### T3 — Concurrent /converse + autonomy correctness

5 concurrent /converse during active autonomy. Verify:
- All /converse return non-error responses
- Autonomy EMITTING also produces a non-error emission in the same window
- `_emission_records` contains entries from both converse-emits and autonomy-emits, no cross-contamination
- No exceptions in substrate log

### T4 — Curriculum + autonomy + /converse triple stress

With both flags on:
- 30-sentence curriculum chunk via `_curriculum_feed_chunk`
- Autonomy ticks running (substrate normal operation)
- 10 /converse calls spaced 2s

Verify chunk completes in <90s, /converse 9/10 within 5s, autonomy resumes after chunk, no hangs.

### T5 — Flag rollback

Set `AUTONOMY_PHASED=0` mid-flight. Verify next autonomy tick uses original single-lock body. No state corruption.

### T6 — Both flags off (control)

Deploy with `CONVERSE_PHASED=1 AUTONOMY_PHASED=0` first. Run 5 min stability. Confirms the new code paths don't break the existing -52 behavior when not enabled.

### T7 — Stability with both flags on

30 min with `CONVERSE_PHASED=1 AUTONOMY_PHASED=1` and steady traffic. Vocab growth, atlas growth, emission rate. Compare to -52-only baseline. Acceptable: similar or better growth rates, no exceptions, no atlas corruption.

### T8 — _emission_lock fairness

Under load (curriculum + 5 concurrent /converse + active autonomy), capture `converse_emission_lock` AND `autonomy_emission_lock` events for 5 min. Verify:
- No single source is starved (both event streams have entries)
- Wait times are bounded (no entry shows wait_ms > 5000)

---

## 3. Rollback

**Primary: env var.** `AUTONOMY_PHASED=0`. Next tick uses original code path. No code revert.

**Secondary: code revert.** `git revert HEAD`. Original `_autonomy_tick` and `_do_emit` bodies still exist; phased versions added alongside.

---

## 4. Reporting

c1 produces `GL-RPT-AUTONOMY-EMITTING-PHASING-C1-20260630-53.md` with:

- Diff summary: env-var branch in `_autonomy_tick`, `_autonomy_tick_phased`, `_do_emit_phased`, instrumentation
- T1: phase-by-phase ms breakdown from `autonomy_emission_lock` event
- T2: **the gate** — /converse latency during autonomy EMITTING with both flags on
- T3: concurrent correctness
- T4: triple stress (curriculum + autonomy + converse)
- T5: flag rollback works
- T6: control deploy with AUTONOMY_PHASED=0
- T7: 30 min stability with both flags on
- T8: emission_lock fairness — no starvation
- Final SHA, task number, state of `AUTONOMY_PHASED` env var at end of deploy (default OFF until T2 confirms PASS, then flipped ON)

---

## 5. Out of scope

- `RICH_SENSORY_INPUT=1` profiling. Note: confirmed substrate-functional (provides cross-modal candidates not selected by the vectorized path). 501ms cost is real but the candidates are different — turning it off is a substrate regression, not a free optimization. Profile and optimize the rich path as a separate dispatch. Tracked as a follow-up; not -53.
- Other `with self.lock:` sites in v5_engine.py (L3535, L4054, L4508, L4887, L5036, L5367, L5499). Still -49/-50 territory.
- Refactoring `_emission_system` to per-call working storage. Still -49/-50 endgame.
- Activity scheduler behavior (which activity gets selected and when). This dispatch preserves the existing scheduler; only the lock granularity around dispatch changes.

---

End.
