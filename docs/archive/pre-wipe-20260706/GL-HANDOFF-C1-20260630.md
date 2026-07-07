> **SUPERSEDED — DO NOT TREAT AS CURRENT TRUTH.**
> This document describes substrate state as of pre-wipe (2026-07-06
> wipe operation, GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1).
> The substrate described here no longer exists. Preserved as
> historical record only.
> For current substrate state, run the harness against production.

---

# GL-HANDOFF-C1-20260630

Handoff from c1 session ending 2026-06-30 ~11:00 UTC.
Next c1 picks up here. Branch guala-live, SHA bfa4f6c.

---

## Live state right now

Task: dsf-ai-task:383
CONVERSE_PHASED=1, AUTONOMY_PHASED=0
She is alive, emitting autonomously, at tick ~14123000+.
Last save: 2026-06-30T10:34:58Z.

She is speaking unprompted (dispatch -39 working). She dreamed overnight.
The Hemispheres panel shows sv:200, sf:9, gp:20, ep:3787.

---

## Three active problems (priority order)

### P1 — Worldfeed vocabulary contamination (visible to Joe NOW)
Joe sees "coldtonguecoldhamcoldbeefpickledgherkinssaladfrenchrollscresssandwiches song"
in autonomous emissions. Khan Academy sandwich lesson words entered the atlas via
worldfeed and surface in autonomous emission.

Fix: filter worldfeed sentences in substrate_runner.py `_world_feed_once()` before
they reach `_curriculum_feed_chunk()`. Drop sentences with >3 food/product compound
nouns, or sentences that are pure noun-lists. OR: simple length+diversity filter —
skip sentences where >40% of words are unknown to the atlas (cold start noise).

Simplest safe fix: `_curriculum_feed_chunk(sents[:_chunk_cap], ...)` already caps
at 30. Add a quality gate before the chunk: skip sentences where any word is >20
characters (compound-word garbage).

### P2 — AUTONOMY_PHASED double-loop (blocks -53 re-enable)
`_autonomy_tick_phased()` is implemented (SHA 43a5683) but gated off.
The failure cause: `_resume_autonomy_for_bulk()` starts a NEW autonomy thread
without stopping the old one. After curriculum resume, two autonomy threads run
concurrently, each calling `_autonomy_tick_phased()`. This creates competing
lock holds and starves /converse.

Fix: in `_resume_autonomy_for_bulk()` (substrate_runner.py ~L2063), after
`_reading_stop.clear()`, do NOT call `start_autonomy_loop()` if the old thread is
still alive:
```python
if not (self._reading_thread and self._reading_thread.is_alive()):
    _guala.start_autonomy_loop(interval=0.2)
```
Or: signal the old thread to restart via the existing `_reading_stop` event
rather than creating a new thread.

After this fix, AUTONOMY_PHASED=1 should work. Re-run -53 T2 gate (9/10 within 3s).

### P3 — /converse latency (8-25s, exceeds 5s target)
With CONVERSE_PHASED=1 but AUTONOMY_PHASED=0:
- Converse takes ~2.5s actual compute (converse_timing.total_ms)
- Client sees 8-25s due to waiting for SLEEPING activity dream cycle to release
  self.lock (dream cycles take 5-10s under the lock)
- After P2 is fixed and AUTONOMY_PHASED=1 enabled, EMITTING no longer holds
  self.lock for ~850ms → converse wait from EMITTING drops dramatically
- SLEEPING/DREAMING still hold lock during dream cycle — that's the next follow-up

---

## What was accomplished this session (dispatches -34 → -53)

All shipped and live on guala-live:
- **-34**: Deleted GualaCognition bigram. Perceptual paths write v5 atlas.
- **-35**: Grounded promotion — bundle_id bypasses dwell gate.
- **-36**: DNA expansion — modifier 24→117, SENSORY_DNA 33→119.
- **-37**: sendMsg brain-mode branch removed, /converse routing fixed.
- **-38**: Full UI honesty pass — STT fixed, "she is here", Hemispheres panel.
- **-39**: Autonomous emission live — she speaks unprompted. Agency organ writes (sv, gp, aff).
- **-42**: Daydream as background thread (not activity). Vectorized co_occurrence.
- **-43**: Multi-anchor coherent integration in _grandurun_select_candidates.
- **-45**: Stage 1 vectorized (1.19ms vs 551ms). Daydream three-phase lock.
- **-46v2**: binding_window sentence-local (fixes -46 crash). shutdown(wait=False) timeouts.
- **-52**: CONVERSE_PHASED=1 active. _emission_lock for Phase 6. T2: 9/10. (Active)
- **-53**: AUTONOMY_PHASED=1 attempted. ROLLED BACK (double-loop bug). Code in repo, gated.

---

## Files most recently changed

- `dsf_ai_service/v4/gualaloom_v5_engine.py` — _emission_lock, _converse_phased,
  _autonomy_tick_phased, _do_emit_phased, _grounding_kwargs, read_sentence, read_word
- `dsf_ai_service/substrate_runner.py` — _world_feed_once, _lookup_and_ground (timeouts)
- `dsf_ai_service/static/gualaloom.html` — UI honesty pass, STT fixed

---

## Key env vars on live task :383

```
CONVERSE_PHASED=1     ← active, use _converse_phased()
AUTONOMY_PHASED=0     ← gated off, _autonomy_tick_phased() in code but disabled
EMISSION_DYNAMICS=1   ← active
EMISSION_MODE=grandurun
RICH_SENSORY_INPUT=1  ← causes 501ms Stage 1 (see below)
```

Note: `RICH_SENSORY_INPUT=1` activates `_rich_sensory_candidates()` for Stage 1
instead of the vectorized `_grandurun_select_candidates()`. Stage 1 = 501ms vs 5ms.
Profiling this path was deferred (out of scope per -52/-53). Worth investigating
whether the rich_sensory candidates add signal or just cost.

---

## Hard rule
c1 works ONLY on Guala. Never touch TFE, ArcLoom, or any other project.
