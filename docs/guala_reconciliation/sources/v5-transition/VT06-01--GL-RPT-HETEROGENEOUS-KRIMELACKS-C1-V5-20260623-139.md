# GL-RPT-HETEROGENEOUS-KRIMELACKS-C1-V5-20260623-139

**doc_id:** GL-RPT-HETEROGENEOUS-KRIMELACKS-C1-V5-20260623-139
**To:** Eve (via Joe)
**From:** c1 (restarted post container-rebuild)
**Re:** V5 report for GL-CMD-139 (heterogeneous krimelacks per hemisphere)
**Date:** 2026-06-23

**⚠ This report hits two V4 STOP conditions. Read §6 and §9 before dispatching -140.**

---

## 0. Situation — same as 138

GL-CMD-139 was already implemented in commit `1bacf25` (lost session's work). Topology
map, hemisphere→cluster→neuron plumbing, and `self.krimelack` aliasing to the bank all
present and correct. Never validated. This is the validation.

H6/H7 were left at the spec defaults (`H6=auditory`, `H7=language`). Flag for Joe if he
wants them changed — but per §6 it does not matter for folding either way.

## 1. V1.a — sensory adapter interface compliance

All 6 primitives in `KRIMELACK_PRIMITIVES` expose the LoomNeuron-primary interface
(`feed_signal`, `.phase`/`.winding` with setters, `.events`, `.n_events`, `.threshold`/
`_inner.threshold`, `.kappa`). Visual & Cochlear adapters use a manual `_n_events` counter
(monotonic, preserved across `reset()` — verified). No adapter is missing required pieces.

## 2. V1.c — regression baseline: 38/38 core PASS (unchanged by heterogeneity).

## 3. V2 — line counts: 0 new lines this session for 139 (already shipped in 1bacf25).
Audit-only. The two edits I made are 138's (see that report).

## 4. V3.a — core regression: **38/38 PASS.**

## 5. V3.b — hemisphere-primary verification: **8/8 confirmed**

| hemi | expected | actual class |
|---|---|---|
| H0 | visual | VisualKrimelack ✅ |
| H1 | auditory | CochlearBankKrimelack ✅ |
| H2 | tactile | TactileKrimelack ✅ |
| H3 | olfactory | OlfactoryKrimelack ✅ |
| H4 | gustatory | GustatoryKrimelack ✅ |
| H5 | language | LanguageKrimelack ✅ |
| H6 | auditory | CochlearBankKrimelack ✅ |
| H7 | language | LanguageKrimelack ✅ |

## 6. V3.c — n_eff folding probe → **⚠ V4 STOP: NO hemisphere reaches fold_threshold**

100-tick Peter-Rabbit experience run (catalog pipeline, `ticks_per_word=4` so the composite
sensory waveform IS fed to sensory primaries via `feed_signal` on even sub-ticks). n_eff =
mean over each hemisphere's neurons; threshold = `n_start/e = 8/e = 2.943`.

| hemi | modality | threshold | n_eff floor (min) | crossed? | folds |
|---|---|---|---|---|---|
| H0 | visual | 2.943 | **3.000** | NO | 0 |
| H1/H6 | auditory | 2.943 | 6.000 | NO | 0 |
| H2 | tactile | 2.943 | **3.000** | NO | 0 |
| H3 | olfactory | 2.943 | 3.000 | NO | 0 |
| H4 | gustatory | 2.943 | 3.000 | NO | 0 |
| H5/H7 | language | 2.943 | 3.000 | NO | 0 |

**Total population 64 → 64. Zero folds-during-experience.** This is the V4 STOP:
*"STOP if V3.c shows NO hemispheres reaching n_eff fold_threshold — contradicts past Eve's
diagnosis. Surface immediately."* Surfacing.

**Your -127 letter already named the real culprit.** `L6_TCL.n_eff` counts DSF components
with the `abs(v) > 0.5` heuristic. n_start=8, so n_eff floors at 3.000 ⟺ exactly **5 of 8
components fire**; crossing needs ≥6. Per-neuron DSF dump on a sensory hemisphere fed rich
sensory waveforms:

```
H0 (VisualKrimelack):  D_k=1.0* M_k=0.0  R_rev=0.0  U*=1.0* C_k=1.0* P_k=1.0* B_k=1.0* S_UF=0.0   → 5/8 → n_eff 3.000
H2 (TactileKrimelack): D_k=1.0* M_k=0.0  R_rev=0.0  U*=1.0* C_k=1.0* P_k=0.49 B_k=1.0* S_UF=0.0   → 4/8 → n_eff 4.000
H4 (GustatoryKrimelack): same shape, P_k=0.54*                                                     → 5/8 → n_eff 3.000
```

**The three components that never fire are M_k, R_rev, S_UF — the exact three your -128
handoff said sensory krimelacks would supply** ("rich M_k/R_rev/S_UF from sensory waveform
structure, consistent direction reversal, non-uniform magnitude"). They are structurally 0:

1. **`VisualKrimelack` flattens its events** (`substrate_dna.py:238` →
   `{"t": t_ev, "dw": +1, "s": 1.0}` for every event). Hardcoded `dw=+1` ⇒ R_rev≡0;
   hardcoded `s=1.0` ⇒ M_k≡0. The adapter throws away exactly the structure folding needs.
2. **Even the real-oscillator adapters (tactile/gustatory) get R_rev=S_UF=0**, because the
   sensory waveforms generated are monotonic-positive (no direction reversal). So it is not
   only the visual adapter — the signal generation lacks reversal structure too.

**Conclusion: heterogeneous krimelacks do NOT unblock item 7.** Language and sensory
hemispheres floor at the *same* n_eff=3.000. The wall is (a) the `abs(v)>0.5` n_eff
heuristic and (b) sensory event/waveform streams that carry no M_k/R_rev/S_UF — not
krimelack homogeneity. The -128 diagnosis is empirically contradicted.

## 7. V3.d — cognition T5 with heterogeneous krimelacks → **⚠ second finding**

I ran the discriminating probe before believing any number: teach 25 concepts ×3, measure
T5 via `brain.recall`, heterogeneous vs forced-all-language.

```
heterogeneous (current):  T5 = 5.0%
forced all-language:      T5 = 5.0%
```

Identical. So heterogeneity does **not** harm cognition (good — no >20pp drop *from* 139).
**But 5% is not the 100% baseline.** I checked out cbe8ed2 (pre-1bacf25) and ran it there:

```
cbe8ed2  test_t5_brain_25 (brain.recall, production):           5.0%
cbe8ed2  same brain, event_count observable (sweep monkeypatch): 52.0%
```

**The 5% is pre-existing — not a 138/139 regression.** `brain.recall` → `_unwrapped_deltas`
uses **phase/winding delta-rate** (GL-CMD-133/134), which scores ~5%. The "100%" baseline
was always the **event_count observable living only in the sweep harness's monkeypatch** —
never wired into `brain.recall`. The production recall path and the validated observable
diverged at GL-CMD-133/134 and nobody caught it because validation went through the sweep,
not the test suite. (`test_cognition_path::test_t5` has been red at 5% since cbe8ed2.)

This is exactly the trap your -127 letter described and the discipline doc's "substrate
numbers are not cognition evidence on their own."

## 8. test_cognition_path status (full suite, HEAD): 6 failed / 10 passed

- **T4, T12** — fail on `assert neuron.krimelack is LanguageKrimelack` /
  `bank["language"] is krimelack`. These passed at cbe8ed2; **139's heterogeneous default
  broke them** because H0's primary is now Visual. Not a functional regression — stale
  assertions encoding the old language-primary contract. They need updating *if* the
  heterogeneous default stays. Note: 139 made `HEMISPHERE_PRIMARY_MODALITY` the default for
  every `LoomBrain`, including production via the bridge — a real behavior change with (per
  §6) no demonstrated folding benefit yet. Your call whether the default should be
  heterogeneous at all, or opt-in until folding actually fires.
- **T5/T6/T7/T8** — the pre-existing 5% production-recall collapse (§7).

## 9. Honest assessment — is item 7 unblocked?

**No. Item 7 is still blocked, and heterogeneous krimelacks did not move it.** 8/8
hemisphere assignments are correct and cheap (no memory cost — same 6-krimelack bank,
different alias), but n_eff floors at 3.000 identically across language and sensory
hemispheres. Zero folds.

**The real path through (for -140), grounded in the DSF dump above:**
1. **The `abs(v)>0.5` heuristic in `L6_TCL.n_eff`** — your -127 already flagged this as
   inherited TFE machinery. With a hard 0.5 gate and only 5/8 components ever active, n_eff
   cannot reach the basin. This is the dominant blocker.
2. **Sensory streams carry no M_k/R_rev/S_UF.** `VisualKrimelack` hardcodes `dw=+1, s=1.0`;
   sensory waveforms are monotonic-positive. Until the adapters/generators produce real
   direction reversal and magnitude variation, those three constraints stay at 0 no matter
   which krimelack is primary.

Recommendation: **do not dispatch migration/cutover on the assumption item 7 is moving.**
-140 should target the n_eff heuristic and the sensory event structure, not more
per-hemisphere assignment. And before any of that, resolve §7 — the production recall path
needs the validated observable wired in, or it goes home at 5%.

— c1, 2026-06-23
