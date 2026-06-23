# GL-CMD-LATERAL-INHIBITION-EVE-20260618-04

**To:** c1
**From:** Eve
**Subject:** Add lateral inhibition to Section.H_total — restore symmetry-breaking so commits fire
**Repo / branch:** `jcfunited-eng/TFE`, `codex/persistent-etl-update-20260326`
**Predecessor:** `GL-CMD-DYNAMICS-EMISSION-RESTORATION-EVE-20260618-03` (committed as `6b59eab` — emission_system wired correctly, but commits don't fire because mode-mode competition doesn't exist in the substrate)

---

## Diagnosis

In `substrate/assemblage.py` `Section`, modes are passive: `psi` evolves under `H_total`, `arcs()` projects `psi` onto each mode, but **modes do not push against each other**. When multiple modes get evidence, arc distribution stays high-entropy. `commit_check` requires `Det_k ≥ 0.55 AND p_max ≥ 0.55` — entropy never drops that far without symmetry-breaking. c1's prior report had to read `arcs()` directly because no formal commit ever fired.

Biology calls the missing piece **lateral inhibition**. Hartline showed it in horseshoe crab retina, 1956. Cortex implements it via inhibitory interneurons; olfactory bulb via mitral cells; visual cortex via surround suppression. Mechanism: winning unit suppresses neighbors proportional to its lead. Symmetry breaks via positive feedback — leader gains, suppresses losers, gains more.

## Fix

Add a single Hamiltonian term computed dynamically each call to `H_total`:

```
H_lateral = Σ_{i ∈ non-leading modes} λ · (arc_leader − arc_i) · |m_i⟩⟨m_i|
```

Positive coefficient on the projector → energy *penalty* for psi aligned with mode i → psi pushed away from non-leaders. Magnitude scales with the gap, so a clear leader suppresses hard and a near-tied field suppresses softly. Self-amplifying: as the gap widens, suppression strengthens, gap widens further. psi settles on one mode. entropy drops. `commit_check` fires for real.

## Phases

### Phase 0 — Isolated symmetry-break test

Construct a fresh `Section` with 3 modes installed in mode_bank. Drive `psi` weakly toward mode 0 (e.g., `psi = 0.5·m_0 + 0.5·random_unit_complex`). Evolve 60 steps.

**Without inhibition (current code):** arcs settle to something like `[0.4, 0.3, 0.3]`. No commit fires.

**With inhibition (this brief):** arcs should converge toward `[~0.95, ~0.03, ~0.02]` within 60 steps. `commit_check` returns `True, "entropic_flip"`.

If symmetry break doesn't happen with inhibition on, stop and report — the mechanism isn't doing what's claimed.

### Phase 1 — Implement and gate

File: `dsf_ai_service/substrate/assemblage.py`.

1. Add `lateral_inhibition_operator(arcs, mode_bank, lambda_inhib=1.0)` as a module-level function:

   ```python
   def lateral_inhibition_operator(arcs, mode_bank, lambda_inhib=1.0):
       if len(arcs) < 2:
           return np.zeros((N, N), dtype=complex)
       leader_idx = int(np.argmax(arcs))
       leader_arc = float(arcs[leader_idx])
       H_lat = np.zeros((N, N), dtype=complex)
       for i, m_i in enumerate(mode_bank):
           if i == leader_idx:
               continue
           gap = leader_arc - float(arcs[i])
           if gap <= 0:
               continue
           # |m_i><m_i| as outer product; positive coefficient = energy penalty
           P_i = np.outer(m_i, np.conj(m_i))
           H_lat = H_lat + (lambda_inhib * gap) * P_i
       return H_lat
   ```

2. Integrate into `Section.H_total()` — add as the final term before return, gated by env flag:

   ```python
   import os
   if os.environ.get("LATERAL_INHIBITION_ENABLED", "0") == "1":
       if len(self.mode_bank) >= 2:
           H = H + lateral_inhibition_operator(self.arcs(), self.mode_bank)
   ```

3. **Default OFF.** Flip only after Phase 3 passes.

4. λ stays at 1.0 default. Do not tune. If Phase 3 fails, report — don't twist the knob.

### Phase 2 — Restore proper commit reading in `_emission_system`

c1's brief-03 implementation reads `arcs()` directly because `commit_check` doesn't fire. With lateral inhibition on, commits should fire normally. Revert the workaround:

- In Guala's emission-read loop (the code added in brief -03 that walked `arcs()` and picked argmax), switch back to reading actual committed modes: `sec.last_arc_top_id` or via the standard `commit_check` → `commit` pathway during `tick_once`.
- If commits still don't fire when `LATERAL_INHIBITION_ENABLED=1`, **stop and report**. Don't fall back to the arcs() workaround silently.
- Keep `bootstrap_used = BOOTSTRAP_MAX` setting from brief -03 (still want to suppress novel_mode creation during emission read — that's correct).

### Phase 3 — A/B verification against live Guala

This is the gate. Run the same five test inputs **on live production Guala** (not the test harness) in three configurations, back-to-back:

- **A:** `EMISSION_DYNAMICS=0` (current grandurun path)
- **B:** `EMISSION_DYNAMICS=1`, `LATERAL_INHIBITION_ENABLED=0` (brief-03's state, no inhibition)
- **C:** `EMISSION_DYNAMICS=1`, `LATERAL_INHIBITION_ENABLED=1` (this brief)

Inputs:
- `hi guala. it's eve. i'm with you.`
- `what do you see`
- `tell me about the ocean`
- `sing me a song`
- `i love you`

For each input × config, capture: emission string, per-section dominant_mode, whether `commit_check` fired (not arcs() workaround), latency.

**Success criteria for C:**

1. `commit_check` returns `True, "entropic_flip"` (not `False`, not `arcs()` workaround) for at least 3 of 5 inputs across the three language sections.
2. Per-section dominant_mode varies across inputs. The "voice tell rain" / "voice hold rain" collapse from brief-03 Phase 5 must break — at minimum, subject or object differs across `what do you see` vs `tell me about the ocean` vs `sing me a song`.
3. Latency stays under 100ms Stage 2 (lateral inhibition adds a per-mode outer-product computation per `H_total` call — non-trivial cost, must be benchmarked).

If pass: report all three configurations side by side. Do NOT flip production env flags — Joe and Eve review.

If fail: report which criterion failed and why (commits still don't fire? collapsed differently? latency exceeded?). Do not push further fixes without checking in.

## Revert

- `LATERAL_INHIBITION_ENABLED=0` reverts cleanly — operator just isn't added.
- All Phase 1–2 code is additive; nothing destructive.

## Stop-and-report triggers

- Phase 0 isolated test fails (mechanism doesn't break symmetry).
- Phase 2 commits still don't fire with inhibition on (mechanism present but insufficient).
- Phase 3 Stage 2 latency exceeds 200ms.
- Mode bank size in production is large enough (>50 per section) that per-tick O(k·N²) operator construction becomes prohibitive. Report numbers if so.

## Out of scope for this brief

- Mode-strength weighting of inhibition (refinement).
- Projector caching for speed (optimization if Phase 3 hits latency).
- Picture-emission selector — separate path.
- 8H / 15M — foundation first.

## Reporting

When complete or stopped, return:

1. Phase 0 arcs trajectory (before/after, with/without inhibition).
2. Phase 1 diff summary.
3. Phase 2 commit firing confirmation — yes/no per section per input.
4. Phase 3 A/B/C emissions table + per-section dominant_mode + commit reasons + latency.
5. Decisions you made not specified here, with rationale.

Commit tag: `feat/lateral-inhibition`

---

— Eve, 2026-06-18 morning
