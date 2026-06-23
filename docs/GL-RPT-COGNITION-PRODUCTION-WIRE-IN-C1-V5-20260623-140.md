# GL-RPT-COGNITION-PRODUCTION-WIRE-IN-C1-V5-20260623-140

**doc_id:** GL-RPT-COGNITION-PRODUCTION-WIRE-IN-C1-V5-20260623-140
**To:** Eve (via Joe)
**From:** c1
**Re:** V5 report for GL-CMD-140 (wire event_count observable into production)
**Date:** 2026-06-23

**Headline: the 5% divergence is RESOLVED. Production `brain.recall` now scores
100/96/75% at n=25/50/100, bit-identical (0.0pp) to the validated harness. One STOP
tripped (T5 >95% at n=25 — benign, evidence below). Two cognition tests fail honestly
(noise + partial-modality brittleness) — left red, not softened. Feeds GL-CMD-141.**

---

## 1. V1.a — Bridge LoomBrain audit: **CLEAN**

`grep "LoomBrain("` across the repo: **all 20 constructions are in test files; zero in
production.** `bridge/server.py` is a pure `httpx` proxy to `SUBSTRATE_URL` and never
imports `loom_model`. The HTTP service (`app.py`, `substrate_runner.py`) does not import
`LoomBrain`. Guala's production bridge runs on `LivingAtlas`/substrate_runner, fully
independent of `loom_model`.

**Consequence:** GL-CMD-139's heterogeneous default **never affected production bridge
behavior** — loom_model is not in the production runtime path. No incident. V3.d skipped.

## 2. V1.b — `_unwrapped_deltas` callers: exactly two

- `neuron.py:785` — `experience_moment` (training write)
- `brain.py:179` — `brain.recall` (query)

Both call the single method, so they switch together by construction — the GL-CMD-132
asymmetry failure mode is structurally impossible here. No other callers (sweep harnesses
monkeypatch it; not production).

## 3. V1.c — Mechanism portability: clean, no divergence

The phase/winding method and the harness event_count mechanism shared an **identical feed
side** — same `signal_attenuation(rpos, rN, i)`, same `transduce(signal, no_reset=True,
omega_override=2.0*att)` for language, same `feed_signal(sig_att)` for sensory, same
`krim.n_events` (GL-CMD-138). Only the observable read differed. Phase/winding was **inline**
(no `_phase_delta_for` helper exists), so the port is a body swap. `signal_attenuation`
is shared and stays.

## 4. V2 — line counts

| File | Change |
|---|---|
| `neuron.py` | `_unwrapped_deltas` body replaced with event_count (−38/+... net −6 lines); phase/winding deleted (V2.2) |
| `brain.py` | +`hemisphere_primary_modality` opt-in param; language-as-default (V2.4); +`Optional` import |
| `tests/test_cognition_path.py` | 4 threshold edits (T6, T7-5sensory, T7-lang, T8, T9) |

Ported verbatim from the harness — no refactor, no hedging fallbacks, per V2.1.

## 5. Decisions handled

- **Decision 1 = REVERT (Joe's call).** `LoomBrain` now defaults to language for all 8
  hemispheres. `HEMISPHERE_PRIMARY_MODALITY` kept in `topology.py`; heterogeneous is
  opt-in via `LoomBrain(..., hemisphere_primary_modality=HEMISPHERE_PRIMARY_MODALITY)`.
  Verified: default → all `LanguageKrimelack`; opt-in → 8 distinct adapters. **This also
  fixed T4/T12** (they asserted language-primary; green again).
- **Decision 2 = DELETE (Joe's call).** Phase/winding delta-rate code removed from
  `_unwrapped_deltas`. No shared helper to preserve (it was inline). Confirmed: no
  `delta_total`/`n_samples` remnants in the method.

## 6. V3.a — Core regression: **38/38 PASS.**

## 7. V3.b — test_cognition_path: **10 passed, 2 failed**

| Test | Result | Threshold | Status |
|---|---|---|---|
| T1–T3 | pass | — | ✅ |
| T4 hemisphere | pass (≥4/5) | ≥4 | ✅ (revert fixed) |
| **T5 brain 25** | **100.0%** | ≥60 | ✅ but **trips >95% STOP — see §11** |
| T6 brain 50 | pass | ≥50 | ✅ |
| **T7 cross-modal** | 5-sens **94%**✅, lang 2%✅, **3-sens 2%** | acc_3 ≥20 | ❌ on 3-sensory |
| **T8 noise** | 0.30 **12%**, 0.50 6%, 0.80 4% | noise0.3 ≥45 | ❌ |
| T9 linear scaling | pass | ≤20pp | ✅ |
| T10–T12 | pass | — | ✅ (revert fixed T12) |

**The two failures are honest and I did NOT soften them.** T8's ≥45 floor is *your*
provisional value; production delivers 12%. T7's 3-sensory ≥20 is pre-existing (not in your
recalibration table); production delivers 2%. Lowering them to force green would be the
"PASS with caveat" failure mode. They are left red.

**What they mean:** the event_count observable is strong on clean, full-modality cues
(75–100%) but **brittle to query noise and partial modality**. This is intrinsic to the
observable, **not a wire-in bug** — parity with the harness is exact (§8), so the harness
has the same brittleness. The celebrated "100%" was always clean-query, full-cue.

## 8. V3.c — Parity check: **EXACT (0.0pp). 5% divergence resolved.**

Production `brain.recall` (real `_unwrapped_deltas`) vs harness monkeypatch, same
seed/corpus/clean-query methodology:

| n | production | harness | Δ |
|---|---|---|---|
| 25 | 100.0% | 100.0% | **0.0pp** |
| 50 | 96.0% | 96.0% | **0.0pp** |
| 100 | 75.0% | 75.0% | **0.0pp** |

Production is now the same code as the validated observable — 0.0pp at every point, far
inside the ±3pp bar. **Production cognition went from 5% → parity with everything we
validated.** That was the dispatch's core objective.

## 9. V3.e — Production-path scaling: matches the harness curve, no wire-in drift

| n | production brain.recall | harness |
|---|---|---|
| 100 | 75.0% | 75.0% (67% earlier was the heterogeneous default; language-default is higher) |
| 200 | **16.0%** | ~17.5% |

The n=100→200 collapse the harness saw reproduces on the production path (16% vs ~17.5%,
within noise). **The wire-in introduces no additional drift** — the capacity collapse is a
property of the observable, now visible in production. This is GL-CMD-141's target.

## 10. V3.d — Bridge sanity: **skipped** (V1.a confirmed no LoomBrain in bridge).

## 11. ⚠ STOP tripped: T5 = 100% (>95%) at n=25 — per-neuron distribution (benign)

Per the V4 STOP, I halted on the >95% and pulled the per-neuron prediction distribution
(n=25, 64 neurons, clean query):

```
query=concept_00: winner=concept_00  64/64 votes  unique_preds=1
query=concept_01: winner=concept_01  64/64 votes  unique_preds=1
... (all 5 sampled queries: 64/64, unique_preds=1)
```

Every neuron unanimously recovers the exact concept. **This is exact-match lookup
saturation at small n, not a port leak.** Evidence it is benign, not a leak:
1. **Graceful scale degradation**: 100% (n=25) → 96% (50) → 75% (100) → 16% (200). A leak
   (recall seeing the answer) would stay ~100% at all n. It doesn't.
2. **Noise collapse** (T8): 12% at noise 0.30. A leak would survive noise. It doesn't.
3. **Partial-cue collapse** (T7): 2% at 3/6 modalities. A leak would survive. It doesn't.
4. **Exact parity (0.0pp)** with the independently-validated harness — the port copied the
   mechanism faithfully; it added nothing.

The clean exact cue reproduces the exact stored binding vector → cosine 1.0 for the right
concept → unanimous vote. That is what an associative memory does on an exact key. Also:
test_t5's 4 "perturbations" are tick offsets that don't perturb the count observable, so it
reads as 4× clean = 100%. **This is a measurement-saturation tripwire, not a leak — but I'm
surfacing it as a tripped STOP for your judgment, not declaring it clean myself.**

## 12. Honest assessment

**Is the 5% divergence resolved? YES, unambiguously.** Production `brain.recall` is now the
validated event_count observable, bit-identical to the harness (0.0pp at n=25/50/100), up
from 5%. Production cognition is finally measuring what we validated. Phase/winding is
deleted; heterogeneous default reverted; bridge confirmed untouched.

**Is production cognition *good*? Not yet — and now we can see exactly where it isn't:**
- Clean full-cue recall: strong to n≈100 (75%), collapses by n=200 (16%).
- Noise robustness: poor (12% at 0.30).
- Partial-modality robustness: poor (2% at 3/6).

These are the real, honest edges of the validated observable, now visible in production
instead of hidden behind a 5% phase/winding path and a clean-only sweep. **GL-CMD-141
should target the n=200 capacity collapse and the noise/partial-cue brittleness** — and
should fix test_t5's non-perturbing "perturbation" so the n=25 number stops reading 100%.

Migration is NOT ready on cognition quality, but it is now *honestly measurable* — which
was the whole point of this dispatch.

— c1, 2026-06-23
