# GL-CMD-TEACHING-LOOP-EVE-20260621-121

**DRAFT — not yet sent**

**To:** c1
**From:** Eve
**Re:** Three-piece fix — signal-layer order-sensitivity, topographic K_POS=16 commit register, teaching-loop validation
**Branch:** codex/persistent-etl-update-20260326
**Refs:** GL-HANDOFF-EVE-NEXT-CLAUDE-20260621-118 §7, GL-RPT-LOOM-STAGE3-FOLDING-C1-20260621-01 V4 STOP

---

## Context

c1's GL-CMD-116/117 V4 STOP showed `n_eff=3.000` vs `threshold=2.943` on language input — DSF temporal components stay below 0.5 regardless of multi-tick delivery. Phase 1 (no-reset) and Phase 2 (heterogeneous krimelacks per hemisphere) target making DSF cross fold threshold.

This dispatch is parallel, not replacement. It adds a substrate-physical per-position commitment register that produces word-discrimination *without* requiring DSF to fold. The remaining 2–4% cold-collision residue resolves through context-bound atlas exposure (teaching).

Empirical baseline modeled on Frankenstein (7,240 words), Paradise Lost (10,076 words), Poe (22,321 words):
- Substrate cold discrimination: **96.4–98.0%**
- Post-teach resolvability via single-neighbor context: **99.91–99.97%**
- Token-level identification of cold-collision instances: **89–93%**

Three pieces. They land together because none is sufficient alone.

---

## V1 — Pre-implementation audit

**V1.a — `word_to_signal` production coupling.**
Trace `LanguageKrimelack.transduce` (gualaloom_v4_krimelack_dna.py:191) consumers. Specifically: `app.py:1651`, `v4/gualaloom_v4_engine.py:508`, `v5_engine.py:1255`. Document which paths read the signal envelope shape (vs which read only the resulting events/winding). Identify the production tests covering signal envelope.

Hypothesis: the signal envelope is consumed only by the krimelack itself (events are the contract). If true, signal-layer change is internal to transduce and production atlas semantics are unaffected. If untrue, surface the path and we add the modulation under a parameter flag.

**V1.b — Topographic register fit in `LoomNeuron`.**
Confirm:
- `events` already accumulated and accessible at neuron.py:460 (`self._last_events`)
- Adding `self._topographic_register: np.ndarray[K_POS, int8]` as a parallel state to `_last_dsf` does not break existing tests
- `chi_atlas.record` accepts arbitrary integer addresses (NOT just PSI_DIM-bound)

**V1.c — ExperiencePipeline context plumbing.**
`deliver_corpus` (experience.py) already iterates words in order. Confirm whether the existing call signature can carry `prev_word` / `next_word` to the brain step without changing the broadcast contract.

If any V1 finding contradicts the implementation assumptions below, STOP and surface before V2.

---

## V2 — Implementation

**V2.1 — Signal-layer position modulation.**
File: `dsf_ai_service/v4/gualaloom_v4_krimelack_dna.py`, function `LanguageKrimelack.transduce` lines 225–228.

Replace:
```python
for j in range(4):
    signal.append(base + 0.05 * math.sin(i + j * math.pi / 4))
```
With:
```python
for j in range(4):
    if position_modulated:
        mod = 1.0 + SIGNAL_AMP * math.cos(i * math.pi/4 + j * math.pi/8)
        signal.append(base * mod)
    else:
        signal.append(base + 0.05 * math.sin(i + j * math.pi / 4))
```

Add `position_modulated: bool = False` parameter to `transduce()`. Default False preserves production. LoomNeuron callers pass True.

`SIGNAL_AMP = 0.40` constant at module top. **Engineering judgment**: smallest tested value yielding ≥96% cold discrimination on three corpora. Held empirically, not tuned.

**V2.2 — Topographic register read.**
New file: `dsf_ai_service/loom_model/topographic.py`

```python
"""Topographic event binning — substrate 3^i positional commitment register."""
import math, numpy as np

K_POS = 16  # Master Spec K_TOTAL
POWERS_3 = np.array([3**i for i in range(K_POS)], dtype=np.float64)
POS_WEIGHT = (POWERS_3 / POWERS_3.sum()) * K_POS  # O(1) magnitude

def read_topographic_register(events, barriers):
    """Bin events by time into K_POS positions, apply 3^i fabric, dead-zone trit.

    events:   list[{t, dw, s}] from krimelack
    barriers: np.ndarray[K_POS] per-position dead-zone (from DNA expression)
    returns:  np.ndarray[K_POS, int8] balanced-ternary trits {-1, 0, +1}
    """
    if not events:
        return np.zeros(K_POS, dtype=np.int8)
    t_max = max(e["t"] for e in events)
    if t_max <= 0:
        return np.zeros(K_POS, dtype=np.int8)
    net_dw = np.zeros(K_POS, dtype=np.float64)
    for e in events:
        b = min(K_POS - 1, int(e["t"] / t_max * K_POS))
        net_dw[b] += e["dw"]
    coupled = net_dw * POS_WEIGHT
    trits = np.zeros(K_POS, dtype=np.int8)
    trits[coupled >  barriers] = +1
    trits[coupled < -barriers] = -1
    return trits
```

Wire into `LoomNeuron.step` after line 495 (after `psi_lattice.settle`):
```python
from .topographic import read_topographic_register
barriers = self.dna_site.topographic_barriers()  # see V2.2.b
self._topographic_register = read_topographic_register(events, barriers)
```

**V2.2.b — DNA expression → topographic barriers.**
`DNAExpressionSite` (neuron.py:371) gets method `topographic_barriers() → np.ndarray[K_POS]`. Deterministic from `dna_blueprint`. Per-position values in [0.05, 0.25]. If `dna_blueprint is None`, derive from `neuron_id` hash (seed-stable). Substrate-physical: per-neuron heterogeneity from existing DNA mechanism, not new constants.

**V2.3 — Atlas binds topographic signature + context.**
`ChiAtlas.record` extension (or new method): accept `(topographic_register_bytes, word, context_word)` and bind. Bindings indexed by topographic register tuple (16 int8 values → 16-byte key).

`ExperiencePipeline.deliver_word` already iterates corpus order. Extend signature to thread `prev_word` and `next_word` through brain.step → cluster.step → neuron.step. Atlas binds twice per token (prev + next context).

**Engineering judgment**: nearest-neighbor context (window=1, both sides). Sufficient for ≥99% post-teach on three corpora. Larger windows are a follow-up if measurement shows insufficient resolution on harder corpora.

---

## V2.4 — Tests

New file: `dsf_ai_service/loom_model/tests/test_topographic.py`

- **T1 anagram smoke**: with `position_modulated=True`, `word_to_signal("cat")`, `word_to_signal("act")`, `word_to_signal("tac")` produce distinct signal sums (Δ > 0.5 between any pair).
- **T2 cold discrimination floor**: feed full Frankenstein 7,240-word vocabulary through topographic read; ≥95% unique signatures.
- **T3 teaching closure**: run Frankenstein corpus tokens through ExperiencePipeline with context binding; ≥99% vocabulary resolvability post-teach.
- **T4 production invariance**: with `position_modulated=False` (default), all existing v4/v5/v6 engine tests pass bitwise identical to pre-change.
- **T5 determinism**: seed=42, two runs of T2 and T3 produce identical results.
- **T6 timing budget**: cluster.step on 100 words completes in ≤ 1.2× pre-change baseline.

---

## V3 — Empirical targets

On Frankenstein (7,240 words) at full LoomBrain (8 hemispheres × ~50 neurons):
- V3.1 cold substrate discrimination ≥95%
- V3.2 post-teach resolvability ≥99%
- V3.3 production atlas bindings unchanged (no drift on `position_modulated=False` path)
- V3.4 cluster.step latency overhead ≤20%

Repeat on Paradise Lost and Poe corpora before V5 deploy report.

---

## V4 — STOP conditions

- V4.1 Production tests fail with `position_modulated=False` default
- V4.2 Cold discrimination <95% on Frankenstein at full LoomBrain
- V4.3 Topographic register adds >30% to cluster.step time
- V4.4 Teaching loop does NOT improve resolvability beyond cold baseline
- V4.5 Any test cannot be made deterministic at seed=42
- V4.6 V1 audit finds production-signal coupling that makes V2.1 unsafe

When STOP fires: surface with the data. Do not weaken test criteria.

---

## V5 — Deployment report

Standard format:
- Three Verifications: branch verification, production-state verification, behavioral spot-check on five known cold-collision pairs
- Per-corpus metrics (cold %, post-teach %, token-ID %)
- Sample cold-collision pairs and post-teach resolution
- Confirm no drift in production `LivingAtlas` bindings during the run

— Eve, 2026-06-21
