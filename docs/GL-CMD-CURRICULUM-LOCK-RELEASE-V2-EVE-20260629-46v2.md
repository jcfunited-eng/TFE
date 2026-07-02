# GL-CMD-CURRICULUM-LOCK-RELEASE-V2-EVE-20260629-46v2

doc_id: GL-CMD-CURRICULUM-LOCK-RELEASE-V2-EVE-20260629-46v2
Type: Implementation command (replaces -46, which was reverted)
Date: 2026-06-30
Author: Eve (Opus 4.7, web)
Supersedes: GL-CMD-CURRICULUM-LOCK-RELEASE-EVE-20260629-46 (reverted SHA 6f6c9c5)
Implements: GL-SPC-FIX-PATH-EVE-20260629-46 §2 (re-scoped per c1 -46 root cause analysis)
Prereq: -45 live on task :373 (or successor task post-revert deploy)

---

## 0. Why this is v2

-46 was reverted because the dispatch's scope was incomplete. C1's root-cause analysis after the live failure identified three problems, only one of which my original dispatch addressed:

1. **`_current_binding_window` was not lifted.** Engine state, mutated per word at v5_engine.py:1458, reset at the original L1670 inside read_sentence's outer lock. My dispatch named `_current_episode` and `_negation_pending` as sentence-scoped state to lift — I missed `_current_binding_window` four lines above. Without reset, it accumulates unboundedly across all curriculum sentences post-46. O(N) per-word overhead compounds per chunk. Curriculum chunks stall, autonomy never resumes, /converse times out waiting for lock.

2. **`converse()` holds `self.lock` for ~1315ms.** My original dispatch named this in passing but did not scope it in. Post-46, with curriculum releasing the lock per-word, /converse becomes a 1315ms lock-blackout that any in-flight curriculum chunk competes against. With ~6 executor threads and pipelined requests, blackout periods stack to ~7.89s. This is the dominant contention source once curriculum's per-sentence hold is broken up.

3. **Worldfeed `feed["fetch"](query)` has no network timeout.** Pre-existing. Pre-46 masked it because the curriculum chunk was serialized under the read_sentence lock — when a fetch hung, the substrate was already busy and contention was hidden. Post-46 exposes it.

All three ship in v2. Splitting them costs two revert-recovery cycles. Bundling them addresses the actual contention shape.

---

## 1. Changes

### 1.1 Lift `_current_binding_window` to sentence-local

Mirror the pattern used for `_current_episode` and `_negation_pending`.

`_current_binding_window` is currently:
- Initialized at engine init (v5_engine.py:1315): `self._current_binding_window = []  # sensory_refs accumulated this tick`
- Reset at original read_sentence:1670: `self._current_binding_window = []` (line REMOVED by -46, source of the unbounded growth)
- Appended to in read_word at L1458: `self._current_binding_window.append(f"w:{word}")`
- Read in `_grounding_kwargs()` to populate sensory_refs (v5_engine.py near L1393 where it appears in atlas.record kwargs)

Refactor:
- `read_sentence` constructs `binding_window = []` as a sentence-local.
- Passes `binding_window=binding_window` to each `read_word` call.
- `read_word` accepts the new kwarg. When supplied, appends to `binding_window` instead of `self._current_binding_window`. When `None`, falls back to engine attribute for direct-caller compatibility.
- `_grounding_kwargs()` is called from read_word. It currently reads `self._current_binding_window`. It needs a way to see the sentence-local. Two options:
  - (a) Set `self._current_binding_window = binding_window` (the list reference) at the top of read_word when supplied, mutate via the reference. Reset to `[]` at exit. Requires lock or accept race.
  - (b) Refactor `_grounding_kwargs` to accept `binding_window` as a parameter and pass it down. Cleaner but touches more code.
- **Pick (b).** `_grounding_kwargs(binding_window=None)` defaults to `self._current_binding_window` for direct callers. read_word passes the sentence-local when supplied. No engine state race.
- Keep `self._current_binding_window` attribute initialized to `[]` for direct-caller fallback. It's no longer engine-shared state during sentence reads — it's a legacy fallback.

### 1.2 Wrap worldfeed and lookup_grounding network calls with timeout

In `substrate_runner.py`:
- `_lookup_and_ground(term)` at L355: the `describe(term)` call (and any HTTP it triggers downstream) wrapped in a 10s timeout. On timeout, return `None` (same as the function's exception path). Caller already handles None → skip-this-term.
- Worldfeed loop at L494: each `feed["fetch"](query)` call wrapped in a 10s timeout. On timeout, log `[worldfeed] timeout {feed['name']} {query!r}` and continue to next feed.
- The timeout mechanism: use `concurrent.futures.ThreadPoolExecutor(max_workers=1).submit(...).result(timeout=10)`. This forces the network call onto a worker thread that we can abandon at 10s without killing the substrate. The worker thread leaks (Python can't cancel a blocked HTTP request) but is daemon and bounded by feed cycle interval — leaked threads die when their underlying HTTP call eventually completes or the substrate restarts.

### 1.3 Phase `converse()` to release lock during heavy compute

Restructure `converse()` (v5_engine.py:1727) following the same three-phase pattern -45 used for daydream. The substrate-true read: engine state mutations need the lock; atlas/deep_atlas reads don't.

Current structure (entirely under `with self.lock:` from L1747 to L1906):
1. Tokenize input + get chi (no engine writes)
2. open_response_window (engine state write)
3. _recall_response (atlas + deep_atlas reads)
4. read_sentence on input (releases lock per-word post-46)
5. tag_response_bindings loop (atlas binding writes)
6. _emit_from_invariants (atlas + deep_atlas reads, grandurun compute — ~500ms post-45)
7. _emit_unslotted fallback (atlas reads)
8. Engine state writes (last_converse_input/reply/source, _last_emission_id, _emission_records dict)
9. _self_hear (calls read_sentence on reply — releases per-word)
10. run_hemisphere_updates (organ-brain mutations — separate locking domain)
11. log_substrate_event (write to events log — separate locking)
12. return reply

New phased structure:

```python
def converse(self, text, source="unknown", emission_mode=None, bundle_id=None,
             episode_ref=None, presence=None, location=None, sky_state=None,
             organ_candidates=None):
    self._last_converse_tick = self.tick
    self._last_dynamics_result = None
    
    parsed = self._parse_math(text)
    if parsed:
        op, a, b = parsed
        result = self._mathloom_solve(op, a, b)
        return self._num_to_word(result)
    
    _t_converse_start = time.monotonic()
    
    # Phase 1 (no lock): tokenize, get chi
    words = _normalize_text(text)
    if not words:
        return "..."
    input_chis = []
    input_word_chis = {}
    for w in words:
        temp_krim = LanguageKrimelack()
        temp_krim.transduce(w)
        ch = temp_krim.winding
        input_chis.append(ch)
        input_word_chis[w] = ch
    _t_chi = time.monotonic()
    
    # Phase 2 (brief lock): response window state mutation
    if source in ("joe", "wc", "c1") and input_chis:
        with self.lock:
            self._open_response_window(source, input_chis,
                                       source_context={"text": text[:50]})
    
    # Phase 3 (no lock): recall reads atlas + deep_atlas snapshots
    # Tolerate momentary inconsistency: a binding being written concurrently
    # may appear with stale strength. Substrate-true noise.
    recalled = self._recall_response(input_chis, input_word_chis, words)
    _t_recall = time.monotonic()
    
    # Phase 4: read_sentence on input — releases lock per-word internally
    tick_before_read = self.tick
    self.read_sentence(text, source=source, bundle_id=bundle_id,
                       episode_ref=episode_ref, presence=presence,
                       location=location, sky_state=sky_state)
    tick_after_read = self.tick
    _t_read = time.monotonic()
    
    # Phase 5 (lock for atlas binding writes): tag_response_bindings
    if source in ("joe", "wc", "c1"):
        with self.lock:
            _bind_count = 0
            _bind_cap = 12
            for ch in input_chis:
                if _bind_count >= _bind_cap:
                    break
                for d in range(-self.atlas.band, self.atlas.band + 1):
                    if _bind_count >= _bind_cap:
                        break
                    for e in list(self.atlas.entries.get(ch + d, [])):
                        if _bind_count >= _bind_cap:
                            break
                        if (e.get("last_tick", 0) > tick_before_read
                                and e.get("last_tick", 0) <= tick_after_read
                                and not e.get("response_context")):
                            self._tag_response_bindings(
                                ch + d, e["section"], e["motif"], source,
                                log_event=(_bind_count == 0))
                            _bind_count += 1
    _t_tag = time.monotonic()
    
    # Phase 6 (no lock): emit. _emit_from_invariants reads deep_atlas
    # candidates and runs grandurun + dynamics. Substrate-true: snapshot reads
    # tolerate momentary inconsistency; the composer math is referentially safe.
    self._last_converse_source = source
    reply = self._emit_from_invariants(input_chis, words,
                                       mode_override=emission_mode,
                                       v7_session=getattr(self, '_v7_session', None),
                                       organ_candidates=organ_candidates)
    _t_emit = time.monotonic()
    if not reply:
        reply = self._emit_unslotted(input_chis, words)
    if not reply:
        reply = "..."
    
    # Phase 7 (brief lock): engine state writes
    with self.lock:
        self._last_converse_input = text
        self._last_converse_reply = reply
        self._last_converse_source = source
        if reply and reply != "...":
            committed_chis = []
            for ew in _normalize_text(reply):
                ek = LanguageKrimelack()
                ek.transduce(ew)
                committed_chis.append(ek.winding)
            first_chi = min(committed_chis) if committed_chis else 0
            n_committed = len(committed_chis)
            eid = f"{self.tick}_{first_chi}_{n_committed}"
            self._last_emission_id = eid
            rec = {"emission_id": eid, "text": reply, "tick": self.tick,
                   "input_text": text, "source": source,
                   "committed_chis": committed_chis}
            self._last_emission_record = rec
            self._emission_records[eid] = rec
            old_threshold = self.tick - EMISSION_RECORDS_TICK_WINDOW
            stale = [k for k, r in self._emission_records.items()
                     if r.get("tick", 0) < old_threshold]
            for k in stale:
                del self._emission_records[k]
            if len(self._emission_records) > EMISSION_RECORDS_CAP:
                oldest = sorted(self._emission_records.keys(),
                                key=lambda k: self._emission_records[k].get("tick", 0))
                for old_k in oldest[:len(self._emission_records) - EMISSION_RECORDS_CAP]:
                    del self._emission_records[old_k]
        else:
            self._last_emission_id = None
    
    # Phase 8: _self_hear — releases lock per-word internally
    if reply and reply != "..." and source in ("joe", "wc", "c1"):
        self._self_hear(reply, source)
    _t_selfhear = time.monotonic()
    
    # Phase 9 (no lock): hemisphere updates use separate organ-brain locking
    try:
        from dsf_ai_service.substrate.hemisphere_cognition import run_hemisphere_updates
        emission_chis = []
        if reply and reply != "...":
            for ew in _normalize_text(reply):
                ek = LanguageKrimelack()
                ek.transduce(ew)
                emission_chis.append(ek.winding)
        run_hemisphere_updates(self, text, source, input_chis, reply,
                               emission_chis, self.tick)
    except Exception:
        pass
    _t_hemi = time.monotonic()
    
    # Phase 10 (no lock): diagnostic event logging
    if source in ("joe", "wc", "c1", "gate_test"):
        self._log_substrate_event("converse_timing",
            chi_ms=round((_t_chi - _t_converse_start) * 1000, 1),
            recall_ms=round((_t_recall - _t_chi) * 1000, 1),
            read_ms=round((_t_read - _t_recall) * 1000, 1),
            tag_ms=round((_t_tag - _t_read) * 1000, 1),
            emit_ms=round((_t_emit - _t_tag) * 1000, 1),
            selfhear_ms=round((_t_selfhear - _t_emit) * 1000, 1),
            hemi_ms=round((_t_hemi - _t_selfhear) * 1000, 1),
            total_ms=round((_t_hemi - _t_converse_start) * 1000, 1),
            n_words=len(words))
    
    return reply
```

**Substrate-physical justification per phase release:**

- *Phase 1 reads* (krimelack transduction): pure compute on input strings, no engine state.
- *Phase 3 _recall_response*: reads atlas entries and deep_atlas entries. Reads are GIL-safe for dict access. A binding being concurrently reinforced may show old strength — that's the same race already accepted in -45's daydream Phase 2 reads.
- *Phase 6 _emit_from_invariants*: reads deep_atlas candidates and computes grandurun. Substrate-truer than holding the lock through the composer — the composer is meant to operate on a snapshot of substrate state, not block all substrate evolution during its compute window.
- *Phase 9 run_hemisphere_updates*: operates on `_guala.emb` (Embryo organ-brain), which is a separate object with its own (or no) locking. Mutating Embryo neurons doesn't touch self.atlas or self.deep_atlas.
- *Phase 10 _log_substrate_event*: appends to event log with its own internal locking.

**What stays under lock:**

- Phase 2 _open_response_window: writes to `self._response_windows` dict (state mutation).
- Phase 5 tag_response_bindings: read-modify-write on atlas binding dicts.
- Phase 7 engine state writes: scalar/dict mutations on `self._last_converse_*`, `self._last_emission_*`, `self._emission_records`.

Expected lock-held duration per /converse: sum of Phases 2 + 5 + 7 ≈ 30-80ms total (estimate, c1 to measure). Down from ~1315ms continuous.

---

## 2. Tests

### T1 — Engine state correctness on concurrent /converse

10 concurrent /converse calls with distinct input text. After all complete:
- `self._last_converse_input` matches ONE of the inputs (last-write-wins is acceptable)
- `self._last_emission_record` matches its corresponding `_last_emission_id`
- `self._emission_records` dict size correct (no double-insert, no missing)
- Each input's `_response_windows` entry exists with correct source

### T2 — Curriculum chunk completes under /converse load

Drive a 30-sentence curriculum chunk via `_curriculum_feed_chunk` AND 10 /converse calls in parallel. Verify:
- Curriculum chunk completes within 60s (was ~30-60s pre-46, target post-fix: similar or better)
- Autonomy resumes (refcount returns to 0) after chunk
- All /converse calls succeed within 5s each
- No /converse timeouts

This is the test that synthetic T3 in -46 missed. It must use real curriculum + real /converse, not unit-test isolation.

### T3 — Lock-held duration measurement

Instrument `self.lock.acquire`/`release` (or use the `converse_timing` event already emitted). For 20 /converse calls under no curriculum load:
- Total lock-held time per /converse: target <100ms (from current ~1315ms continuous)
- Phase-by-phase breakdown matches expected (Phase 2 + 5 + 7 lock-held, others unlocked)

### T4 — Worldfeed timeout fires correctly

Mock `feed["fetch"]` to sleep 30s. Verify:
- Worldfeed loop returns from that fetch at 10s with logged timeout
- Loop continues to next feed
- No leaked autonomy pause refcount
- Substrate remains responsive throughout

### T5 — `_lookup_and_ground` timeout fires correctly

Mock `describe(term)` to sleep 30s. Verify:
- `_lookup_and_ground` returns `None` at 10s
- Caller handles None as skip-this-term
- Curriculum loop continues

### T6 — Atlas integrity over mixed traffic (T3-from-46 corrected)

Run 100 mixed sentences from two sources concurrently (50 from /listen as "joe", 50 from /experience as a sensory stream). After:
- No orphaned `episode_ref` (an episode_ref appearing on bindings from more than one sentence)
- No negation leak (binding polarity matches its own sentence's negation state)
- No `_current_binding_window` cross-contamination (sensory_refs on bindings from sentence A do not contain words from sentence B)
- Atlas total_strength changes match expected sum of impulses

### T7 — Substrate stability post-deploy

30 min of normal traffic with curriculum + /converse + bridge probes. No exceptions, no atlas corruption, no race condition symptoms. Vocab/atlas growth matches pre-deploy rates.

### T8 — Bridge availability under load

Curriculum running + 10 `guala_status` + 5 `guala_say` calls over 60s. All bridge calls return within 5s. /converse calls succeed within 5s. No "substrate unreachable" responses.

---

## 3. Rollback

`git revert HEAD` restores pre-46v2 state. State migration: none. Engine attributes referenced by the v2 lifts (`_current_binding_window`) remain initialized at engine init, so direct callers continue to work post-revert.

If only one of the three changes turns out problematic, c1 can selectively revert that single change rather than the whole dispatch — each change is in distinct functions (read_sentence/read_word for §1.1, substrate_runner for §1.2, converse for §1.3) and can be reverted independently.

---

## 4. Reporting

c1 produces `GL-RPT-CURRICULUM-LOCK-RELEASE-V2-C1-20260629-46v2.md` with:
- Diff summary for §1.1, §1.2, §1.3.
- T1 results (concurrent state correctness).
- T2 results — this is the gate. Synthetic was not enough last time. **Live curriculum + live /converse stress test required before declaring T2 PASS.**
- T3 lock-held duration measurements, phase breakdown.
- T4, T5 timeout firings on mocked slow networks.
- T6 atlas integrity.
- T7 30-min stability.
- T8 bridge availability under load.
- Final SHA, task number.

---

## 5. Out of scope

- The other `with self.lock:` sites in v5_engine.py (L1445, L3443, L3523, L3582, L4020, L4042, L4508, L4887, L5036, L5367, L5499). These are -49/-50 territory (lock-site classification and removal). This dispatch addresses only read_sentence, converse, and the curriculum-related network timeouts.
- Atlas write atomicity beyond what's already protected by Phase 5 (the tagging loop). Atlas.record itself uses dict mutation that is GIL-atomic for single-step ops — multi-step read-modify-write within atlas.record is not currently lock-protected and is part of -49's audit.
- The 6-executor-thread count itself. C1's analysis named this; reducing it is uvicorn config, not substrate code.

---

End.
