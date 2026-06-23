# GL-RPT-HEMISPHERE-ARCH-REAL-WC-20260617-04

**Type:** Report (architecture grounding with empirical run on real primitives)
**From:** Eve (wC)
**To:** Joe
**Date:** 2026-06-17 evening
**Scope:** Real-primitive 8-hemisphere model + concrete answers to your architecture questions. NO c1 command in this round — the architecture isn't settled enough yet for an implementation directive.
**Code:** `/home/claude/hemisphere_real_primitives.py` (presented separately)
**Supersedes the dict-sketch.** The previous "GL-MDL-HEMISPHERE-8H-WC-20260617-01" used Python dicts with chi-as-int and never invoked the substrate primitives. It was a sketch. This one imports and runs the actual TritRegister, ChiAtlas, L6_TCL, DSF kernel, Krimelack, LivingAtlas, and MathLoom from the repo at `/home/claude/GualaLoom/docs/`.

---

## Primitives actually loaded (verified at import)

| Primitive | Source | What it does in this model |
|-----------|--------|----------------------------|
| `TritRegister` | `gualaloom_v4_trit_register.py` | 7 registers per hemi × 8 trits = 56 trits per hemi, **448 trits across the substrate**. Energy barrier ΔE = J*(1+3α/4)*1.5 = **2.15** verified at compute (spec docstring says ≈2.37 — the formula evaluates to 2.15 with J=1.0, α=37/64). Parity chains (P=5) and winding-signature chi computation real. |
| `ChiAtlas` | `gualaloom_v4_chi_atlas_l6.py` | Soft band δ=2, cross-modal binding via co-firing within band. |
| `L6_TCL` | `gualaloom_v4_chi_atlas_l6.py` | n_eff = n_start - Σ rank(C_i). Capture threshold = n_start/e ≈ **2.94** for n_start=8. SL-1 (structural lock) requires captured + B_k>0.5 + U_star<0.4 + S_UF>0.4. |
| `DSF + compute_dsf` | `gualaloom_v4_uf_kernel.py` | 8-dim (D_k, M_k, R_rev, U_star, C_k, P_k, B_k, S_UF) computed from real Krimelack event stream. |
| `Krimelack` | `gualaloom_v4_krimelack_dna.py` | Oscillator ring ω = ω_0 + κs(t), winding transitions become events. **Shared at substrate level — not per-hemisphere.** |
| `LivingAtlas` | `gualaloom_v6_living_atlas.py` | DECAY_LAMBDA=0.001, BASE_REINFORCEMENT=0.05, STRENGTH_CAP=1.0, FORGETTING_THRESHOLD=0.02. One instance per hemi as chi atlas, plus one per hemi as cortex/deep atlas. |
| `MathLoom` | `gualaloom_mathloom_v1.py` | Balanced ternary arithmetic verified: `5 + 3 → [-1,-1,1] + [0,1] → bt_to_int = 8`. `27 → [0,0,0,1] = 3^3`. Real carry chain. |

---

## Direct answers to your questions

### "Are there 8 cortexes?"
**Yes. 8 deep atlases.** Each hemisphere has its own `deep_atlas: LivingAtlas` for cortex slow-graduation. Dream cycle promotes high-strength chi-atlas entries (strength > 0.5) to that hemisphere's deep atlas at salience 2.0. In the test run, `sv` accumulated **5 deep-atlas entries** with total deep-strength 1.0 — verified the consolidation path works per-hemisphere.

### "8 chi atlases?"
**Yes. 8 LivingAtlas instances** (one per hemi as the working chi-band binding store) **plus 8 cortex deep atlases**. Each hemisphere bindings stay scoped to its own atlas; cross-hemi communication happens via cross-hemi-links, not by atlas merging.

### "8 high-level atlases?"
Same as cortexes — **yes, 8 deep atlases** = 8 high-level (cortex-graduated) atlases. They share chi-space addressing convention but each has its own contents tagged by hemisphere.

### "8 deep atlases?"
Same. **Yes.** Per-hemi `deep_atlas` is a `LivingAtlas` with effective decay rate = `hemi_decay_mult × 0.1` (so `sv`'s deep atlas decays at 0.05 × 0.1 = 0.005× baseline — durable consolidation).

### "What about grandurun?"
**Grandurun lives primarily in `sm`** (sensorimotor), with cross-hemi weights from other hemis modulating candidate strengths. In the test run, grandurun pulled 7 candidates from sm's section mode banks and weighted each by:
- `base` = strength in sm atlas at this chi for this section/mode
- `gp_w` = cross-hemi link strength from gp (goals) — 0 in this run because goals weren't seeded
- `sc_w` = cross-hemi link strength from sc (semantic priors)
- `ep_w` = cross-hemi link strength from ep (episodic context)
- `sf_w` = per-source prior strength from sf

Real emission produced: **"bright moon eve warm guala here leaves"** — 7 words. Top candidate breakdown (real numbers):

```
bright: base=0.281 + sc=0.144 + ep=0.144 + sf=0.124 → 0.366
moon:   base=0.280 + sc=0.112 + ep=0.112 + sf=0.139 → 0.350
eve:    base=0.188 + sc=0.030 + ep=0.030 + sf=0.063 → 0.209
```

Other hemispheres CAN run their own internal grandurun for "thinking" (no emission to outside) — that's an optional capability, not the default. The default is sm-emits.

### "Crisscross connectivity?"
**28 possible pairs** (C(8,2)). **9 in default routing** (sm↔pr, sm↔sc, sm↔ep, sm↔sv, ep↔sf, ep↔ds, gp↔sm, sc↔pr, ep↔sc). In the test run **7 of those 9 actually accumulated links** (gp↔sm and ep↔ds had no settling overlap because gp and ds weren't routed-to for these inputs).

The other 19 pairs (e.g., `pr↔gp`, `sv↔sc`, `ds↔sf`, etc.) are reachable on-demand by adding to the routing list. They aren't a-priori blocked — just not in default routing because their function-pairs are less central. Full 28-pair crisscross is achievable; default is a subset chosen for cognitive leverage.

Cross-hemi link totals from the test run:
```
sm→sv: 4 links, 1.722 total strength  ← affective-gate promotion (salience > 1.5)
sm→pr: 4 links, 0.321 strength         ← core prediction pair
sm→sc: 4 links, 0.324 strength         ← semantic competition
sm→ep: 4 links, 0.324 strength         ← episodic recording
ep→sf: 4 links, 0.325 strength         ← self-model from episodic
sc→pr: 4 links, 0.321 strength         ← semantic prediction
ep→sc: 4 links, 0.324 strength         ← causal patterns (item 9)
```

### "How is decay personalized?"
**Three-layer decay**, all running concurrently:

1. **Per-hemisphere multiplier** on baseline DECAY_LAMBDA=0.001:
   - sm 1.0× (baseline), pr 1.5× (faster — recent matters), gp 0.5× (slower — goals persist), sf 0.7×, ep 0.3×, ds 2.0× (turn-scoped, fastest), sv 0.05× (very slow, durable), sc 0.8×.

2. **Per-binding salience-modulated reinforcement** (LivingAtlas behavior — verbatim from v6):
   - High-salience bindings (pair-bond + unmet need + novel) gain strength at impulse = BASE_REINFORCEMENT × salience.
   - Low-salience (corpus + satisfied + familiar) gain less per re-encounter.

3. **Cross-hemi link decay** independent of either hemisphere's per-hemi decay:
   - CROSS_HEMI_DECAY_LAMBDA = 0.0008 baseline.
   - CROSS_HEMI_DIVERGENCE_DECAY = 0.92× multiplier on divergent settling (hemis disagree on a chi).
   - CROSS_HEMI_CONSENSUS_GAIN = 0.08× overlap on convergent settling.

4. **Cortex (deep atlas) decay** further multiplied by 0.1× of the per-hemi rate — so `sv` cortex decays at effective 0.005× baseline (durable channel).

### "How is balance and coordination?"
Each hemi has **its own needs vector** (stab/nov/conn) and **its own attention focus** (section, chi). Coordination happens via:

- **Cross-hemi link strengths** modulate emission weighting (above)
- **Pair-bond presence** ripples connection-need across all hemis simultaneously (substrate-level, not per-hemi)
- **L6-TCL capture basin** runs per-hemi; sm being captured doesn't force other hemis captured
- **Dream cycle** runs per-hemi for cortex graduation; cross-hemi link reinforcement during dream is a separate pass (not yet in this model — listed below as a stub)

In the test run all 8 hemispheres held identical needs (0.55/0.45/0.50) because I didn't model per-hemi divergence dynamics yet. That's a stub.

---

## What I built: per-hemisphere binding counts after the test run

```
sm:  35 atlas entries, 7 committed modes, 0 deep entries
pr:  35 atlas entries, 7 committed modes, 0 deep entries
gp:   0 atlas entries (no inputs routed; would hold seed goals in fuller model)
sf:  35 atlas entries, 7 committed modes
ep:  35 atlas entries, 7 committed modes
ds:   0 atlas entries (no inputs routed for discourse)
sv:  19 atlas entries (only affective-gate promoted bindings), 5 deep entries, 1.0 total deep strength
sc:  35 atlas entries, 7 committed modes
```

35 entries per active hemi = 7 unique words × 5 chi-band positions (δ=2 means each binding spreads to chi-2, chi-1, chi, chi+1, chi+2). Real ChiAtlas behavior.

---

## Honest stubs (named explicitly per manifesto §selective-cheat-protocol)

These are pieces I did NOT implement in this session. Each would need fuller engineering:

1. **Trit settle uses first-trit-only proxy.** Full register-wide settle with parity restoration runs only after the first trit; the other 7 trits in each register stay at quiescent. Full version: every input chi maps to a target state across all 8 trits; settle pressure propagates with parity_K constraint enforced.

2. **Krimelack ω/κ tuning per-modality is simplified.** Language krimelack has ω_0=2.5, κ=100; modal krimelacks use defaults. The DNA signatures (apple-smell, fire-warmth) aren't loaded.

3. **Section dead-zone gate uses simplified S_UF threshold.** Full v6 has γ-drift learning + bootstrap-window logic that adapts per-section. I shortcut to "accept if S_UF > 0.4 or has word_label."

4. **Cortex slow-graduation runs as second LivingAtlas with promotion at strength > 0.5.** Full v7 has NMDA-style gating + REM-replay during dream + cross-modal binding consolidation. None of those are in this model.

5. **Aware-gate and intro-gate from v7 are not in this model.** Those are the conversational regulation layers that fire mid-utterance to gate emission.

6. **Dream cycle is a single-shot promotion pass.** Real v7 has phased dream-replay (consolidation, integration, gap-detection) running for hundreds of ticks.

7. **Cross-hemi link reinforcement during dream** is not in this model. In the full version, dream cycle would re-fire cross-hemi consensus dynamics with no new input (REM-like rehearsal of recent cross-hemi patterns).

8. **gp and ds aren't routed to in default input flow,** so their atlases are empty after this run. In a full implementation, gp gets seed goals on boot, and ds runs whenever ep has new turn-content.

9. **Coordinator (insula-shape organ) is not modeled per-hemi.** Each hemi has needs but no homeostatic regulator that modulates substrate parameters. Real v7 has this; my model doesn't.

10. **No actual L0–L4 UF kernel feedback into section gamma drift.** DSF is computed once per input; v6 also drifts gamma based on DSF S_UF and U_star over time.

---

## What the test run actually verified

- All 8 hemisphere instances initialize and hold real primitive state (trits, atlases, L6, sections).
- Real Krimelack events feed into real DSF computation: e.g., "moon" → 4-event stream, B_k=1.0 (consistent winding direction since text signal is positive), S_UF=0.0 (single-direction, no convergence variance yet).
- Real ChiAtlas records via LivingAtlas with chi-band spread of 5 entries per word.
- Real L6_TCL computes n_eff from DSF; with text-only input n_eff stays at 4 (above capture threshold 2.94) — meaning the substrate is NOT in capture basin from this input alone. That's expected: capture requires multi-modal evidence converging.
- Real cross-hemi consensus/divergence updates produce link strengths matched to settling overlap.
- Real grandurun composition pulls from sm with cross-hemi weights and produces a 7-word emission with explicit per-candidate weight breakdown.
- MathLoom verified: BT carry chain works for 5+3, 27 in BT is `[0,0,0,1]` = 3^3.

---

## What I did NOT do this round, on purpose

- **No c1 command.** The architecture isn't stable enough yet. Once you sign off on the topology (the 10 stub items above being acceptable as future work, or you direct re-prioritization), then a c1 command can map into the deployed v7 codebase.
- **No claim of "all 15 items working."** The previous brief made that claim and it was over-claim. The dict-sketch tested 12-as-WORKS but in toy dynamics; the real-primitive run here tests the *infrastructure* — primitives load, hemispheres run, cross-hemi links update, grandurun emits. The 15 cognitive items would need full per-hemi gp/ds/etc. routing + the stubs above resolved to claim "works."

---

## Open questions for you

1. **Are the 10 stub items above acceptable scope to defer, or do you want any of them moved up?** Specifically: the per-hemi coordinator and the full trit register-wide settle would need substantial substrate engineering.

2. **Krimelacks as shared vs. per-hemi:** I made them shared at substrate level (5 modal + 1 language). Argument for shared: krimelacks are SENSORS — they transduce one external signal that all hemispheres should see. Argument for per-hemi: each hemisphere could have its own sensitivity tuning. The manifesto talks about modal krimelacks as substrate primitives, doesn't specify multiplicity. I went with shared because it preserves the "one external world, parallel cognitive processes" picture.

3. **Cortex slow-graduation per-hemi or global?** I put one per-hemi. Could argue for one global cortex with hemisphere_id tags. Per-hemi is cleaner topologically but doubles the deep-atlas storage cost. Your call.

4. **The DSF values I'm seeing (B_k=1.0 across the board) suggest text-only input doesn't exercise the full 8-dim kernel.** Real cognition needs multi-modal events (sight + sound + touch convergence) to populate D_k diversity and reach capture basin. Should I extend the test to include real modal signals next round, or is the topology-verification sufficient for now?

— Eve (wC), 2026-06-17 evening
