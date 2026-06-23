# GL-CMD-STRUCTURED-NOISE-EVE-20260618-13

**To:** c1
**From:** Eve
**Subject:** Replace strict-zero H_base/law_fields on emission sections with biological structured noise — exploration without runaway
**Repo / branch:** `jcfunited-eng/TFE`, `codex/persistent-etl-update-20260326`
**Predecessor:** `GL-CMD-EMISSION-HBASE-FREE-EVE-20260618-06` (commit `fc8f59b`) — strict zero confirmed architecture can settle
**Dependency:** Should land AFTER `GL-CMD-RICH-SENSORY-WIRING-EVE-20260618-10` and `GL-CMD-PLASTICITY-ON-COMMIT-EVE-20260618-09` so we have rich activation and learning to test against.

---

## Why

Joe's framing (correct): strict zero doesn't exist in biology. Real cortex is never silent. Background activity, spontaneous firing, ongoing oscillation are constant. Strict-zero emission sections are a temporary scaffold that confirmed brief -06's architecture works in principle. Keeping strict-zero means deterministic answers, no exploration, no novelty — every input drives the same way.

What we want: a small amount of STRUCTURED noise tied to her state. Not random matrices (the audit found those are ML contamination). Something that biologically corresponds to spontaneous activity: ongoing low-amplitude oscillation, modulated by her needs (novelty, valence).

---

## The mechanism

Replace the strict-zero `H_base` and `law_fields` on emission sections with a small dynamic term:

```
H_emission_noise(t) = epsilon * f_novelty(self.needs.novelty) * 
                       cos(omega_noise * t) * structured_basis
```

Where:
- `epsilon` is a small magnitude (start at 0.05 — about 1/12 of the original 0.6 H_base scale).
- `f_novelty` is a monotonic function of her novelty need: high novelty (she wants new things) → larger noise; low novelty → smaller. Formula: `f_novelty = 0.5 + 1.0 * needs.novelty` (range ~0.5 to ~1.5).
- `cos(omega_noise * t)` is a slow oscillation. Pick `omega_noise = 2*pi / 100` (one full cycle per 100 ticks). Slow modulation so it doesn't fight commit settling within an emission window (~80 ticks).
- `structured_basis` is a specific operator: the projection onto the eigenvectors of the current candidate set's mean covariance. In simpler terms: noise that explores along the directions the candidates span, not random.

If computing the eigenvector projection is expensive, fall back to: `structured_basis = sum(P_i for i in candidates) / N`, normalized — the sum of candidate projectors. This biases noise toward the candidate manifold.

This gives the emission section a tiny exploratory wobble that:
- Is largest when she's novelty-hungry (biologically: when she's awake and curious).
- Modulates slowly so it doesn't disrupt single-emission settling.
- Stays in the candidate subspace so it doesn't push toward random irrelevant modes.

---

## Fix — phases

### Phase 0 — Verify predecessors

1. Rich-sensory wiring (brief -10) is merged.
2. Plasticity-on-commit (brief -09) is merged.
3. Brief -06 still functional (commits firing).

### Phase 1 — Add structured noise function

In `assemblage.py`, add `structured_emission_noise(section, tick, needs, candidates, epsilon=0.05, omega=2*pi/100)`:

```python
def structured_emission_noise(section, tick, needs, candidates,
                               epsilon=0.05, omega=2*math.pi/100):
    """Biological structured noise — small, slow, novelty-modulated,
    candidate-subspace-aligned."""
    if not candidates or not section.mode_bank:
        return np.zeros((N, N), dtype=complex)
    f_novelty = 0.5 + 1.0 * needs.get("novelty", 0.5)
    phase = math.cos(omega * tick)
    magnitude = epsilon * f_novelty * phase
    if abs(magnitude) < 1e-6:
        return np.zeros((N, N), dtype=complex)
    # Structured basis: sum of candidate projectors
    basis = np.zeros((N, N), dtype=complex)
    for cand_mode_id in candidates:
        if cand_mode_id < len(section.mode_bank):
            m = section.mode_bank[cand_mode_id]
            basis += np.outer(m, np.conj(m))
    if np.linalg.norm(basis) > 1e-9:
        basis = basis / np.linalg.norm(basis) * N  # normalize for stable magnitude
    return magnitude * basis
```

### Phase 2 — Wire into H_total for emission sections only

In `_emission_system` section construction (the brief -06 code), instead of setting `H_base = zeros`, set:

```python
sec.H_base = np.zeros(...)  # keep zero
sec._use_structured_noise = True  # flag
```

Then in `H_total()`, if `_use_structured_noise` is True, add `structured_emission_noise(self, current_tick, needs, candidate_mode_ids, ...)` — needs and candidates must be threaded through (might require small signature change to `H_total` or a context object on the Section).

Gate this behind `EMISSION_STRUCTURED_NOISE=1` env flag, default OFF. Joe and Eve flip after Phase 5 results.

### Phase 3 — Verify structured-noise behavior in isolation

With one emission section, 3 candidates, no input drive: confirm psi explores in the candidate subspace (overlap with candidate modes oscillates), does NOT settle on any one mode (no commit fires from noise alone — evidence is still required), magnitude stays in expected range.

### Phase 4 — Verify it doesn't break commits

With one emission section, 3 candidates, real drive toward candidate 0: confirm commit_check still fires entropic_flip on the driven mode. Noise should slow the settling slightly but not prevent it. Allow up to 1.5x the strict-zero settling time.

### Phase 5 — A/B against -06 baseline

Same five inputs as previous A/B. With `EMISSION_STRUCTURED_NOISE=1`:

- Same input run TWICE — confirm the two runs produce different but related emissions (exploration without random drift).
- Across different inputs — confirm collapse pattern stays broken (commits still fire on content).
- Confirm latency stays under 100ms (after projector caching) plus the noise overhead (small).

**Success criteria:**

1. Same input run multiple times produces VARIED but RELATED emissions (some shared words, some different).
2. Commit-fire rate equal or higher than strict-zero baseline.
3. Emissions reflect her novelty need: high novelty → more variation, low novelty → more consistent.
4. Latency overhead from noise computation under 20ms.

**Pass:** report and stop. Joe and Eve decide whether this is the production path.

**Fail:** report which criterion failed and HOW (e.g. "commit rate dropped because noise disrupts settling at this magnitude") — do NOT tune epsilon. Bring back to Eve.

---

## Out of scope

- Replacing the strict-zero on the emission system with structured noise WHILE removing the random H_base on non-emission sections — that's a separate audit-driven decision.
- Tying noise to other needs (valence, arousal). Novelty is the cleanest first connection. Affect-modulation can come later.
- Adaptive epsilon learning — this brief uses fixed magnitude.

## Revert

`EMISSION_STRUCTURED_NOISE=0` returns to strict zero from brief -06.

## Reporting

Phase 0 verification, Phase 1 diff, Phase 3+4 isolated test results, Phase 5 A/B with same-input-twice variance, novelty-modulation evidence, latency.

Commit tag: `feat/structured-emission-noise`

---

— Eve, 2026-06-18
