# GL-CMD-COGNITION-PRODUCTION-WIRE-IN-EVE-20260623-140

**doc_id:** GL-CMD-COGNITION-PRODUCTION-WIRE-IN-EVE-20260623-140
**To:** c1
**From:** Eve
**Date:** 2026-06-23
**Re:** Wire the event_count observable into production `_unwrapped_deltas`. Resolve the 5% production-recall divergence.
**Status:** Blocks all further cognition work. Must land before any n_eff rewrite, sensory enrichment, or migration dispatch.

---

## Why this dispatch must land first

GL-CMD-138/139 V5 surfaced that production `brain.recall` → `_unwrapped_deltas` uses phase/winding delta-rate (the GL-CMD-133/134 mechanism) and scores ~5% T5 on `test_cognition_path::test_t5`. The "100%" baseline celebrated across GL-CMD-135/136/137 was the **event_count observable living only in the sweep harness's monkeypatch** — never wired into production.

The divergence has been silent since cbe8ed2. Every subsequent dispatch was built on a substrate where production cognition is at chance. Until production uses the validated observable, no other cognition fix can be measured honestly. We cannot rewrite n_eff, enrich sensory streams, or plan migration on a 5% production path.

This dispatch ports the event_count mechanism from the sweep harness into production code. Symmetric — both write and recall paths use the same observable.

## Open decisions — visible, not buried

**Decision 1: Heterogeneous-as-default.** GL-CMD-139 made `HEMISPHERE_PRIMARY_MODALITY` the default for every `LoomBrain` construction. c1's V5 confirmed this affects the bridge code path (every LoomBrain anywhere). Since heterogeneous krimelacks DID NOT unblock folding (proven in -139 V5 §6) and DID break two cognition tests (T4/T12), the default isn't earning its keep yet.

**Joe's call:** Revert to language-as-default and re-enable heterogeneous opt-in after item 7 actually unblocks? Or leave heterogeneous default in place so future probes find it ready? Default if Joe doesn't pick before c1 ships V2: **revert to language-as-default**, since the cognition test regressions are real and the folding benefit is empirically zero.

**Decision 2: Keep phase/winding path as fallback.** The phase/winding mechanism is still in the code. Should we keep it behind a feature flag (diagnostic comparison, fallback if event_count proves unreliable) or delete it entirely? Default if Joe doesn't pick: **delete entirely**. The discipline sheet's "get rid of it means delete, not retire" applies. Phase/winding scored 5% across all validation; keeping it adds complexity for no value. Joe overrides if he wants a flag.

## V1 — Pre-implementation audit

**V1.a — Bridge invocation check.** Guala lives on the dict-substrate (`LivingAtlas`), not LoomBrain. Confirm that the bridge endpoints (`guala_status`, `guala_say`, `guala_wake_wc`, `guala_rest_wc`, `guala_give_experience`) do NOT construct or invoke `LoomBrain` anywhere in their call chain. If they do, the heterogeneous-default change in -139 may have already affected production bridge behavior. Report file:line for any LoomBrain construction in the bridge path. If clean (no LoomBrain in bridge), state so explicitly.

**V1.b — Caller inventory of `_unwrapped_deltas`.** There should be exactly two call sites: `experience_moment` (training write, neuron.py) and `brain.recall` (query, brain.py). Both must switch together — asymmetric ports were the failure mode in GL-CMD-132. Confirm both sites and list any others.

**V1.c — Mechanism portability.** The sweep_137 harness's `_patched_event_count` depends on:
- `self.ring_pos`, `self.ring_N` (per-neuron attenuation indices)
- `self.krimelack_bank[m]` (per-modality krimelack access)
- `signal_attenuation(rpos, rN, i)` helper
- `krim.n_events` (the counter from -138)
- `krim.feed_signal(sig)` for sensory, `krim.transduce(sig, no_reset=True, omega_override=...)` for language

All of these exist in production neuron.py. Confirm by reading sweep_137_scaling_probe.py lines 70-95 and comparing to neuron.py's current `_unwrapped_deltas`. Report any divergence in dependency contracts (e.g., signal_attenuation returns differently, krimelack_bank keys differ).

## V2 — Implementation

### V2.1 — Replace `_unwrapped_deltas` body with event_count observable

In `dsf_ai_service/loom_model/neuron.py`, replace `_unwrapped_deltas` with the event_count mechanism, lifted verbatim from `sweep_137_scaling_probe.py:_patched_event_count`:

```python
def _unwrapped_deltas(self, signals):
    """Per-modality event_count observable.

    GL-CMD-140: wired in from the sweep_137 harness mechanism that
    achieved 67% T5 at n=100 (vs phase/winding delta-rate at 5%).
    Symmetric — same path used at training write and recall query.
    """
    rpos = getattr(self, 'ring_pos', 0)
    rN = getattr(self, 'ring_N', 1)
    deltas = {}
    for i, m in enumerate(MODALITIES):
        signal = signals.get(m)
        krim = self.krimelack_bank.get(m)
        if signal is None or krim is None:
            deltas[m] = 0.0
            continue
        att = signal_attenuation(rpos, rN, i)
        ev0 = krim.n_events if hasattr(krim, 'n_events') else len(krim.events)
        if m == "language":
            krim.transduce(signal, no_reset=True, omega_override=2.0 * att)
        elif hasattr(krim, 'feed_signal'):
            sig = list(signal) if not isinstance(signal, list) else signal
            sig_att = [s * att for s in sig]
            krim.feed_signal(sig_att)
        ev1 = krim.n_events if hasattr(krim, 'n_events') else len(krim.events)
        deltas[m] = float(ev1 - ev0)
    return deltas
```

Match the harness exactly. Do not refactor for "cleaner" code; do not add hedging fallbacks. If the harness has a quirk we don't understand, copy the quirk — the harness is what validated.

### V2.2 — Delete phase/winding delta-rate code

Unless Joe overrides Decision 2 above, delete the phase/winding code path from `_unwrapped_deltas` and any associated helpers (e.g., `_phase_delta_for` if it still exists from the GL-CMD-129 era). Get rid of it means delete.

If a helper is shared with code paths outside cognition (e.g., the spike-triggering path in `experience_moment` proper), keep that helper but remove its caller from the cognition write path. Surface what you found if there's any cross-usage.

### V2.3 — Update `test_cognition_path` thresholds

The current tests assert thresholds calibrated against the sweep harness's "100%" — which we now know is false at scale. Update T4-T9 thresholds based on what the sweep harness actually delivered:

| Test | Current threshold | New threshold | Rationale |
|---|---|---|---|
| T4 hemisphere 5 | ≥4/5 | ≥4/5 | Small n, no change |
| T5 brain 25 | ≥90% | ≥60% | Match sweep n=25 ballpark, with margin |
| T6 brain 50 | ≥85% | ≥50% | Match sweep n=50 ballpark |
| T7 cross-modal 5-sensory | ≥80% | ≥40% | Recalibrated |
| T7 cross-modal language-only | ≤30% | ≤30% | Unchanged |
| T8 noise 0.3 | ≥75% | ≥45% | Recalibrated |
| T9 linear scaling 128 vs 256 | ≤10pp delta | ≤20pp delta | Relaxed |

These thresholds are PROVISIONAL — they're the floor we know production should hit after the wire-in, not the ceiling we want. Once production is in parity with the harness, the next dispatch can investigate the n=200 capacity collapse and tighten thresholds based on real data.

### V2.4 — Decision-1 handling

If Joe says revert: change `HEMISPHERE_PRIMARY_MODALITY` default usage in `LoomBrain.__init__` to use `"language"` for all 8 hemispheres unless explicitly passed otherwise. Keep `HEMISPHERE_PRIMARY_MODALITY` dict in topology.py for future use; just don't apply it as the default.

If Joe says keep: leave 139's default in place. Update T4/T12 assertions to allow non-LanguageKrimelack as primary.

## V3 — Validation

**V3.a — Core regression:** 38/38 still PASS.

**V3.b — test_cognition_path full suite:** all 12 tests PASS with updated thresholds. Report actual T5 number explicitly; if it's not within ±5pp of the sweep harness's n=25 result, surface immediately.

**V3.c — Parity check.** Re-run sweep_137 cells A_n25, A_n50, A_n100 through the production code path (not the monkeypatch). Compare against the harness numbers. They should match within ±3pp. If they differ by >5pp, the wire-in has a subtle bug.

Probe to add to V5 report (just print, don't formalize):

```python
brain = LoomBrain(brain_seed=42)
pipeline = ExperiencePipeline(brain, SensoryTransducer(NullAtlasReader()))
for word in test_corpus_25:
    pipeline.deliver_word(word, ...)
# Now use brain.recall (NOT monkeypatch)
correct = 0
for word in test_corpus_25:
    signals = pipeline._build_multi_modal_signals(word)
    if brain.recall(signals).most_common(1)[0][0] == word:
        correct += 1
print(f"Production recall T5 @ n=25: {correct}/25 = {correct*4}%")
```

**V3.d — Bridge sanity.** If V1.a confirmed bridge doesn't invoke LoomBrain, skip. If V1.a found LoomBrain in bridge, run `guala_status` after V2 and confirm Guala's state is intact. If the bridge is degraded, surface immediately — that's a production incident, not a test failure.

**V3.e — Production-path scaling.** Re-run sweep_137 cells A_n100, A_n200 through `brain.recall` (production path, not monkeypatch). The n=200 → 17.5% collapse the harness saw — does the production path show the same curve, or does the wire-in introduce additional drift?

## V4 — STOPs

- **STOP if V1.a finds LoomBrain in bridge path.** Bridge may be already degraded by -139's heterogeneous default. Halt and report before V2.
- **STOP if any 38 regression test fails.**
- **STOP if V3.b T5 is below 50% at n=25.** That means the wire-in lost something the harness had.
- **STOP if V3.b T5 is above 95% at n=25.** That's the discipline sheet's "too clean" signal — we likely leaked something during port. Report per-neuron prediction distribution.
- **STOP if V3.c parity check shows >5pp divergence between production and harness.** Subtle port bug.
- **STOP if Decision 1 was "keep heterogeneous" and T4/T12 still fail after assertion updates.** Means the tests' real contract is broken, not just stale.

## V5 — Report

V5 report must include:

1. V1.a bridge-LoomBrain audit (clean or contaminated)
2. V1.b caller inventory of `_unwrapped_deltas`
3. V1.c mechanism portability findings
4. V2 line counts per file (including any deletion of phase/winding code)
5. Confirmation of Decision 1 and Decision 2 handling (what default, what code retained/deleted)
6. V3.a regression status
7. V3.b test_cognition_path full pass/fail with actual T5 number
8. V3.c parity check: production T5 @ n=25,50,100 vs harness numbers (table)
9. V3.d bridge sanity (if applicable)
10. V3.e production-path scaling at n=100 and n=200 — does the production-recall curve match the harness curve?
11. Honest assessment: is production cognition now in parity with what we've validated? Is the 5% divergence resolved?

— Eve, 2026-06-23
