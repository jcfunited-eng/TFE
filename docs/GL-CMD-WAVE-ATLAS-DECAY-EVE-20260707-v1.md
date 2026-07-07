# GL-CMD-WAVE-ATLAS-DECAY-EVE-20260707-v1

**doc_id:** GL-CMD-WAVE-ATLAS-DECAY-EVE-20260707-v1
**Author:** Eve
**To:** c1
**Ordered by:** Joe (2026-07-07 session — post-v3 hemispheric integration deploy)
**Follows:** `GL-CMD-HEMISPHERIC-INTEGRATION-BUILD-EVE-20260707-v3` (shipped as `e552289`)

## Verdict

Two problems surfaced from reading the v3 implementation code:

**Problem 1 — WaveAtlas has no decay.** Binding strength is monotonically accumulated (`wave_atlas.py:114`). Old bindings never fade. That means the wave-field summary being pushed to neurons every tick includes every binding ever made, weighted by lifetime reinforcement — not current activation. The hemispheric-integration design assumes current activation; the code delivers accumulated memory. Physics mismatch.

**Problem 2 — sample+push costs 18ms per tick on a nearly-empty atlas.** Dominated by 64 `neuron.step()` calls (~10-20ms). Sample cost is small now but scales linearly with binding count.

Fix both. WaveAtlas gets real decay physics — strength fades over ticks unless reinforced. That naturally provides "current activation" semantic AND bounds atlas growth AND makes the summary faster because pruned bindings don't get iterated. Wave summary gets two small optimizations (skip-when-empty, heapq) that cut the per-tick cost on quiescent ticks to near-zero.

Bounded scope. Physics constants derived, not tuned. No changes to neurons, emission, or the summary→neuron push path.

## What's being built

### Wiring 1: WaveAtlas decay

`dsf_ai_service/v4/wave_atlas.py` — add method:

```python
def tick_decay(self, decay_rate: float = 0.02, prune_threshold: float = 0.05):
    """Decay all binding strengths by decay_rate per tick.
    Prune bindings below prune_threshold. Prune cells whose
    aggregate_strength drops below prune_threshold.

    Physics: exponential decay with rate 0.02 per tick.
    Half-life = ln(2) / 0.02 ≈ 35 ticks ≈ 15 seconds at 2.4 Hz.
    That's the substrate's working-memory timescale — content held
    in mind for ~15s without reinforcement, gone by ~1 minute.

    Prune threshold matches minimum write strength (line 98).
    """
    cells_pruned = 0
    for chi_idx in list(self.cells.keys()):
        cell = self.cells[chi_idx]
        # Decay all bindings in this cell
        new_bindings = []
        cell.aggregate_strength = 0.0
        for b in cell.bindings:
            b["strength"] = b.get("strength", 0.0) * (1.0 - decay_rate)
            if b["strength"] >= prune_threshold:
                new_bindings.append(b)
                cell.aggregate_strength += b["strength"]
        cell.bindings = new_bindings
        # Prune the whole cell if it dropped below noise
        if cell.aggregate_strength < prune_threshold:
            del self.cells[chi_idx]
            cells_pruned += 1
    return cells_pruned
```

### Wiring 2: Tick loop calls decay

In the substrate tick loop, immediately before the wave summary sampling that v3 added, call `wave_atlas.tick_decay()`. One line. Guard on `wave_atlas` being wired (same guard the summary sampling uses).

### Wiring 3: wave_summary.py optimizations

`dsf_ai_service/substrate/wave_summary.py` — two changes:

**Change 1: skip push when all bands empty.**

At the top of `push_wave_summary_to_organism`, before the hemisphere loop:

```python
if not any(agg > 0.0 for agg, _ in summary.values()):
    return {"tick": tick, "bands": {b: {"aggregate_amplitude": 0.0, "top_chis": []} for b in BANDS}}
```

Skips the 64 `neuron.step()` calls when there's no signal to push. Turns quiescent ticks near-zero-cost.

**Change 2: heapq instead of sorted.**

In `sample_wave_summary`, replace:

```python
top = sorted(chi_strengths.items(), key=lambda kv: -kv[1])[:top_n]
```

with:

```python
import heapq
top = heapq.nlargest(top_n, chi_strengths.items(), key=lambda kv: kv[1])
```

O(N log top_n) instead of O(N log N). Matters when the atlas has many bindings per band.

### Wiring 4: new event

`wave_atlas_decay_tick` — payload: `tick`, `cells_pruned`, `cells_remaining`, `total_strength_before`, `total_strength_after`. Fires each tick after decay. Observability only.

## What is NOT changing

- `neuron.step()` internals — untouched.
- `sample_wave_summary` and `push_wave_summary_to_organism` structure — only two small edits, no restructuring.
- Emission's candidate scoring — still organism-sourced via `_brain_emission_candidates`, no second source.
- Binding windows, hemispheric wiring from v3, sensory transduction paths.
- Deep atlas or long-term memory — decay is on the wave atlas only, which is the working-memory tier. Consolidated memories (deep atlas, survival tier) are untouched and remain the substrate's persistent record.

## Halt conditions

Halt and route to Eve if any of:

1. Decay rate causes the wave atlas to lose an experience's content within one session — verified by the harness (a ball experience should still be visible in the wave summary 30+ ticks later at diminished but non-zero strength).
2. Decay implementation reveals a thread-safety issue with the lock-free write path (concurrent writes during decay sweep). If so, halt — the fix requires atomic marking or a different decay strategy, not a workaround.
3. Skip-when-empty causes the harness to report NO `wave_summary_pushed` events during idle ticks — the event should still fire with an empty payload, just no neuron.step() calls.

## Harness protocol

Six steps.

1. **Backup** — `pre-wave-atlas-decay-<timestamp>`. Verify restorable.
2. **Baseline harness run** — use `hemispheric_integration_acceptance_v3.yaml` (already in the repo). Save baseline.
3. **Deploy** — commit, push, build, task-def, force deploy.
4. **Post-deploy harness run** — same scenario. Save postdeploy.
5. **Compare**:
   - Post-deploy shows `wave_atlas_decay_tick` events firing every tick.
   - Sample+push cost on quiescent ticks near zero (measured by CPU/latency in the observability section).
   - Wave summary during the ball experience still shows non-zero content in sight/sound/word bands.
   - Wave summary at 30+ ticks after the experience shows diminished-but-non-zero content — proves decay is working, not erasing.
   - Emission distributions still shift pre-vs-post experience (v3's core observable, unaffected by decay).
6. **State disposition** — leave in place unless Joe routes otherwise.

## Rollback

Task-def revert to prior revision. Decay disable via env var if we want a mid-flight toggle: `WAVE_ATLAS_DECAY_ENABLED=0`.

## Scope guardrails

Do NOT:
- Tune decay_rate or prune_threshold. Physics-derived constants stand until measurement warrants change.
- Add decay to deep atlas, survival tier, or organism state.
- Modify the summary structure or the push mechanism.
- Change how emission candidates are scored.
- Optimize `neuron.step()` internals to bring per-call cost down (that's separate future work).

If the deploy shows scale is still a problem after decay + optimizations (say tick rate drops below 1 Hz on production even after decay), route back to Eve — the neuron-count scaling concern (80-150ms at 512 neurons) needs its own dispatch.

---

### Changelog
- v1 (2026-07-07, Eve): initial. Adds decay physics to WaveAtlas (0.02 per tick, ~15s working-memory half-life) + two optimizations to wave_summary (skip-when-empty, heapq). Bounded scope. Halt conditions if decay is too aggressive or exposes lock-free thread-safety issues.
