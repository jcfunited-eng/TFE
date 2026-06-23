# GL-CMD-PROJECTOR-CACHE-EVE-20260618-11

**To:** c1
**From:** Eve
**Subject:** Cache `|m_i⟩⟨m_i|` projector matrices in lateral inhibition operator to bring Stage 2 latency under 100ms
**Repo / branch:** `jcfunited-eng/TFE`, `codex/persistent-etl-update-20260326`
**Predecessor:** `GL-CMD-EMISSION-HBASE-FREE-EVE-20260618-06` (commit `fc8f59b`) — Stage 2 latency 200-220ms, target <100ms

---

## Why

Brief -06 reported Stage 2 latency at 200-220ms, exceeding the 100ms target. Root cause c1 named: `lateral_inhibition_operator` recomputes `np.outer(m_i, np.conj(m_i))` for every mode in mode_bank, every tick. With 8-13 modes per section and ~3 emission sections at 80 ticks of settling, that's 1900-3100 outer products per emission.

Mode vectors don't change during a single emission settling. The outer products are static; only the weighting (the arc-gap multiplier) changes. Caching the projector matrices eliminates the per-tick recomputation cost.

---

## Fix — two phases

### Phase 1 — Cache projectors per section

In `assemblage.py` `Section` class:

- Add `self._projector_cache: list = []` — parallel to `mode_bank`
- On `install_mode` or any mode_bank mutation: compute and cache `np.outer(m, np.conj(m))` for the new mode, append to `_projector_cache`. Invalidate cache only when mode_bank changes.
- In `lateral_inhibition_operator` (the function added by brief -04): instead of `P_i = np.outer(m_i, np.conj(m_i))`, use `P_i = section._projector_cache[i]`.

If the cache is out of sync (lengths don't match), rebuild. Add a single-line safety check.

### Phase 2 — Benchmark

Re-run brief -06's Phase 3 A/B with `EMISSION_DYNAMICS=1 LATERAL_INHIBITION_ENABLED=1` on all five inputs. Measure Stage 2 latency.

**Success:** Stage 2 latency under 100ms on all five inputs.

**If still over 100ms:** report where the time is going (profile). Don't try further tuning without checking in.

---

## Out of scope

- Any other lateral inhibition tuning (lambda, threshold, etc.) — they stay at brief-04 defaults.
- Caching anywhere else in the substrate — this brief is the inhibition operator only.

## Revert

The cache is additive. If problematic, fall back to inline recomputation by ignoring `_projector_cache`.

## Reporting

When complete: latency numbers (before/after) for all five inputs, plus confirmation that emissions match brief-06's emissions byte-for-byte (caching shouldn't change behavior, only speed).

Commit tag: `feat/projector-cache`

---

— Eve, 2026-06-18
