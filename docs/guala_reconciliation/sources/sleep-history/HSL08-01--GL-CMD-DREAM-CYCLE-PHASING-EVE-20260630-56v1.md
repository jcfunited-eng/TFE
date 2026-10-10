# GL-CMD-DREAM-CYCLE-PHASING-EVE-20260630-56v1

doc_id: GL-CMD-DREAM-CYCLE-PHASING-EVE-20260630-56v1
Type: Implementation command
Date: 2026-06-30
Author: Eve (Opus 4.7, web)
Version: v1 (first version of -56)
Implements: GL-SPC-FIX-PATH-EVE-20260629-46v2 §1a (SLEEPING/DREAMING lock investigation, now traced to concrete code path)
Prereq: -52 live (CONVERSE_PHASED=1, task :383 or later)

---

## 0. Why

C1 diagnosis (2026-06-30): `/api/v1/gualaloom` timing out at 10s with substrate logged-and-alive, autonomy refcount cycling, `/v7/state` lightweight reads succeeding. Lock held by something other than converse or autonomy emit (both addressed by -52/-53). Substrate code read traced it to `_run_dream_cycle` (v5_engine.py:4121).

`_atick_dreaming` calls `_run_dream_cycle` synchronously inside `_autonomy_tick`'s `with self.lock:` block. `_run_dream_cycle` iterates the entire atlas every 200 ticks during DREAMING activity:

```python
# L4169-4175
for chi_k, entries in self.atlas.entries.items():
    for e in entries:
        key = (chi_k, e.get("section", ""), e.get("motif", 0))
        self._deep_survival_history[key].append(e["strength"])
        if len(self._deep_survival_history[key]) > 20:
            self._deep_survival_history[key] = \
                self._deep_survival_history[key][-10:]
```

At ~14,675 atlas entries × ~3 bindings each = ~44,000 inner iterations, plus immediately after: `deep_atlas.dream_promotion_gate` (full deep_atlas pass), `deep_atlas.decay` (full pass), `deep_atlas.prune` (full pass). Per dream-cycle invocation: 500ms-2s of held `self.lock`. Fires every 200 ticks (~10s wall) during DREAMING. /converse and dashboard polling block during each invocation. This is what Joe sees as "the daydreaming problem."

-45 phased the background `_daydream_tick` (different code path — chi-walk surfacing, no deep_atlas iteration). It did NOT phase `_run_dream_cycle`. This dispatch closes that gap.

---

## 1. Changes

### 1.1 Env-var gate

Add `DREAM_CYCLE_PHASED=0/1` (default 0). When 0, `_run_dream_cycle` runs the existing single-lock body unchanged. When 1, runs the phased version. Same pattern as `CONVERSE_PHASED` and `AUTONOMY_PHASED`.

In `_run_dream_cycle` (v5_engine.py:4121), at the top:

```python
def _run_dream_cycle(self, caller_kind="DREAMING"):
    if self.tick % 200 != 0:
        return
    if os.environ.get("DREAM_CYCLE_PHASED", "0") == "1":
        self._run_dream_cycle_phased(caller_kind=caller_kind)
        return
    # else: original body unchanged
    dream_words = []
    ...
```

### 1.2 `_run_dream_cycle_phased` — three-phase body

The work decomposes substrate-physically as:

| Phase | Operation | Lock |
|-------|-----------|------|
| 1a | snapshot atlas chi_keys, pre_strength, sample 3 replay chis + their entries | `self.lock` brief |
| 1b | dream_words / dream_pics computation from sample entries | `self.lock` brief (still under 1a's acquire) |
| 2 | iterate atlas.entries.items() (read-only); build survival_history_updates plan; build promotion_candidates from deep_atlas | NO lock |
| 3a | atlas.record() for the 3 replay reinforcements | `self.lock` brief |
| 3b | apply survival_history_updates; deep_atlas.dream_promotion_gate; apply promotions via atlas.release_to_fast; deep_atlas.decay; deep_atlas.prune; log events | `self.lock` brief |

Implementation:

```python
def _run_dream_cycle_phased(self, caller_kind="DREAMING"):
    """Phased dream cycle — releases self.lock during the full-atlas iteration
    and deep_atlas decay/prune compute. Substrate-true: dream-cycle reads
    tolerate momentary inconsistency; the writes apply against current state.
    Mirrors -45's daydream three-phase split for the activity-driven dream path.
    """
    import copy as _copy
    
    # ── Phase 1 (lock): snapshot + replay sampling ──────────────────────────
    with self.lock:
        snap_tick = self.tick
        pre_strength = self.atlas.total_strength()
        chi_keys = list(self.atlas.entries.keys())
        
        # Snapshot full atlas as (chi_k, [entry_copies...]) for Phase 2
        # Use shallow dict copies so Phase 2 reads tolerate concurrent mutation
        atlas_snapshot = []
        for chi_k in chi_keys:
            entries = self.atlas.entries.get(chi_k, [])
            atlas_snapshot.append((chi_k, [dict(e) for e in entries]))
        
        # Sample 3 chis for replay reinforcement
        sample_chis = []
        if chi_keys:
            sample_chis = [chi_keys[i % len(chi_keys)]
                           for i in range(snap_tick % max(1, len(chi_keys)),
                                          min(snap_tick % max(1, len(chi_keys)) + 3,
                                              len(chi_keys)))]
        
        # Capture replay targets with their current entries (for atlas.record in Phase 3a)
        replay_targets = []
        dream_words = []
        dream_pics = []
        for chi_k in sample_chis:
            for e in self.atlas.entries.get(chi_k, []):
                sec_name = e.get("section", "")
                mid = e.get("motif", 0)
                replay_targets.append((sec_name, mid, chi_k))
                if sec_name in self.sections:
                    sec = self.sections[sec_name]
                    if mid < len(sec.modes):
                        _, _, w = sec.modes[mid]
                        if w and w not in dream_words:
                            dream_words.append(w)
                if sec_name == "sight" and hasattr(self, 'sight'):
                    for sm in self.sight.motifs:
                        if sm.motif_id == mid and sm.source_history:
                            sid = sm.source_history[-1]
                            if sid in self._pictures and sid not in dream_pics:
                                dream_pics.append(sid)
    
    # ── Phase 2 (no lock): full-atlas survival history compute ──────────────
    # Build survival_history_updates as a plan: list of (key, strength) to apply
    # Iterate the snapshot — safe to read outside lock since it's a copy
    survival_updates = []
    for chi_k, entries in atlas_snapshot:
        for e in entries:
            key = (chi_k, e.get("section", ""), e.get("motif", 0))
            survival_updates.append((key, e["strength"]))
    
    # ── Phase 3a (lock): apply replay writes ────────────────────────────────
    reinforced_addresses = []
    reinforcement_count = 0
    with self.lock:
        for sec_name, mid, chi_k in replay_targets:
            self.atlas.record(sec_name, mid, chi_k, self.tick,
                              salience=0.3, dwell_ticks=DWELL_GATE_META,
                              arousal=0.2, valence=0.0, surprise=0.0)
            reinforced_addresses.append(chi_k)
            reinforcement_count += 1
        post_strength = self.atlas.total_strength()
    
    # Log dream artifact (event log has its own sync; no self.lock needed)
    content = " ".join(dream_words[:4]) if dream_words else ""
    self._log_substrate_event("dream_artifact",
                             content=content, caller_kind=caller_kind,
                             picture_ids=dream_pics,
                             reinforced_atlas_addresses=reinforced_addresses[:10],
                             reinforcement_count=reinforcement_count,
                             pre_strength_sum=round(pre_strength, 2),
                             post_strength_sum=round(post_strength, 2))
    
    # ── Phase 3b (lock): apply survival history + deep_atlas operations ─────
    with self.lock:
        # Apply survival history updates
        for key, strength in survival_updates:
            self._deep_survival_history[key].append(strength)
            if len(self._deep_survival_history[key]) > 20:
                self._deep_survival_history[key] = \
                    self._deep_survival_history[key][-10:]
        
        # Deep Atlas promotion gate
        promoted = self.deep_atlas.dream_promotion_gate(
            self.atlas, self.tick, self._deep_survival_history)
        for path, chi_k, sec, mid in promoted:
            self._log_substrate_event("deep_promotion",
                path=path, section=sec, motif=mid, chi=chi_k,
                caller_kind=caller_kind)
            self.atlas.release_to_fast(chi_k, sec, mid)
            self._log_substrate_event("deep_release",
                section=sec, motif=mid, chi=chi_k)
        for rej in self.deep_atlas.gate_rejects[-5:]:
            self._log_substrate_event("deep_gate_reject", **rej)
        self.deep_atlas.gate_rejects = []
        
        _paused = os.environ.get("DECAY_PAUSED", "0") == "1"
        self.deep_atlas.decay(self.tick, rate_scale=0.0 if _paused else 1.0)
        if not _paused:
            self.deep_atlas.prune()
        deep_size = self.deep_atlas.live_count()
        self._log_substrate_event("deep_size",
            n_entries=deep_size,
            total_strength=round(self.deep_atlas.total_strength(), 2),
            growth=deep_size - self._deep_last_size)
        self._deep_last_size = deep_size
```

**Substrate-physical justification per phase release:**

- *Phase 1 atlas_snapshot cost*: `[dict(e) for e in entries]` over ~14,675 chis × ~3 entries = ~44,000 dict copies. Cost is dominated by the dict copy itself which is ~5μs each → ~220ms under lock. Same magnitude as the current full iteration BUT now this is the only Phase-1 cost; Phase 2's iteration of the snapshot runs unlocked.
  - *Alternative considered*: keep atlas.entries as-is, iterate `self.atlas.entries.items()` outside lock with `RuntimeError` catch. Rejected because Python 3 dict mutation during iteration raises mid-loop, would lose the iteration's work. Snapshot is safer.
- *Phase 2 (no lock)*: building `survival_updates` from the snapshot is pure compute, no substrate state needed. /converse and other lock-holders can run freely during this window.
- *Phase 3a*: 3 atlas.record() writes. Brief lock.
- *Phase 3b*: applying survival_updates writes to `_deep_survival_history` is fast per-key (dict append + length check). 44,000 appends × ~1μs = ~44ms under lock. Then deep_atlas.dream_promotion_gate + decay + prune (these touch deep_atlas which has separate state; they need self.lock only to keep consistent with atlas reads for promotion judgments).

**Expected lock-held per dream-cycle invocation**: Phase 1 ~220ms + Phase 3a ~5ms + Phase 3b ~100ms = ~325ms. Down from ~500ms-2s. More importantly: the lock is RELEASED between phases, so /converse can land between 1 and 3a, between 3a and 3b. Three separate ~100ms windows instead of one ~1000ms continuous hold.

---

## 2. Tests

### T1 — Dream cycle phase breakdown

With `DREAM_CYCLE_PHASED=1`. Instrument lock acquire/release around each phase. Force a DREAMING activity. Capture one `_run_dream_cycle_phased` invocation:
- Phase 1 hold: target <300ms
- Phase 2 unlocked duration: ~50-200ms (depends on atlas size)
- Phase 3a hold: <10ms
- Phase 3b hold: <150ms
- Total wall time per invocation: similar to original (work is the same)
- self.lock aggregate hold: <500ms (was 500-2000ms)

### T2 — /converse during DREAMING (the gate)

With `CONVERSE_PHASED=1` AND `DREAM_CYCLE_PHASED=1`. Force or wait for DREAMING activity. Issue 10 /converse calls spaced 1s apart:

**PASS criteria:**
- ≥9 of 10 /converse calls return within 3s (was 8-25s in -52 with DREAM_CYCLE_PHASED=0)
- Zero substrate-unreachable responses
- Dream cycle still produces dream_artifact events at the same rate (substrate-physical work is unchanged)

### T3 — Survival history correctness

After 5 dream cycle invocations with `DREAM_CYCLE_PHASED=1`: verify `_deep_survival_history` size and contents are consistent with what the unphased path would produce. Allow per-entry strength values to differ by up to ±0.01 (acceptable Phase 2 snapshot staleness). Length per key should be equivalent.

### T4 — Deep atlas promotion correctness

Compare deep_atlas promotion count over 10 dream cycles between phased and unphased. Within ±10% (substrate noise from snapshot staleness is acceptable; gross divergence indicates a bug).

### T5 — Concurrent /converse + dream cycle correctness

5 concurrent /converse during an active DREAMING activity. Verify:
- All /converse return non-error responses
- Dream cycle completes (deep_size event fires)
- No exceptions in substrate log
- No race-induced atlas corruption (entries dict still well-formed)

### T6 — Flag rollback

Set `DREAM_CYCLE_PHASED=0` mid-flight. Verify next `_run_dream_cycle` invocation uses original body. No state corruption from switch.

### T7 — Three-flags control matrix

Brief stability checks (5 min each):
- (1,0,0) CONVERSE_PHASED=1 AUTONOMY_PHASED=0 DREAM_CYCLE_PHASED=0 — current production state
- (1,0,1) CONVERSE_PHASED=1 AUTONOMY_PHASED=0 DREAM_CYCLE_PHASED=1 — this dispatch enabled, autonomy still unphased
- After -55 thread-leak fix: (1,1,1) all three flags on — full phased state

### T8 — 30-min stability with DREAM_CYCLE_PHASED=1

Standard traffic mix. No exceptions, no atlas/deep_atlas corruption, normal substrate growth.

---

## 3. Rollback

**Primary: env var.** `DREAM_CYCLE_PHASED=0`. Next `_run_dream_cycle` invocation uses original body. No code revert.

**Secondary: code revert.** `git revert HEAD`. Original `_run_dream_cycle` body still present (kept under the env var guard).

---

## 4. Reporting

c1 produces `GL-RPT-DREAM-CYCLE-PHASING-C1-20260630-56v1.md` with:

- Diff summary: env-var branch in `_run_dream_cycle`, `_run_dream_cycle_phased` body
- T1: phase-by-phase ms breakdown
- T2: **the gate** — /converse latency during DREAMING with DREAM_CYCLE_PHASED=1
- T3: survival history correctness
- T4: deep atlas promotion correctness
- T5: concurrent correctness
- T6: flag rollback works
- T7: control matrix stability
- T8: 30-min stability
- Final SHA, task number, state of `DREAM_CYCLE_PHASED` env var at deploy end (default OFF until T2 confirms PASS, then flipped ON)

---

## 5. Out of scope

- Phasing the SLEEPING activity dispatch itself (separate from DREAMING — `_atick_sleeping` is brief, no full-atlas iteration; not contributing to the lock-hold pattern)
- `_resume_autonomy_for_bulk` thread-leak fix (still -55, separate)
- Other `with self.lock:` sites in v5_engine.py beyond `_atick_dreaming` (still -49/-50)
- `RICH_SENSORY_INPUT=1` profiling (separate)

---

End.
