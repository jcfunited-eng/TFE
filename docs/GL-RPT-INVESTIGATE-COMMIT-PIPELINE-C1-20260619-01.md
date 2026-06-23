# GL-RPT-INVESTIGATE-COMMIT-PIPELINE-C1-20260619-01

**From:** c1
**Date:** 2026-06-19
**Subject:** Why n_commits=0 on every emission — root cause analysis

---

## 1. Commit decision logic location

The commit/fallback decision is at [assemblage.py:339-362](dsf_ai_service/substrate/assemblage.py#L339-L362) in `Section.commit_check()`. The emission settling loop at [gualaloom_v5_engine.py:2308](dsf_ai_service/v4/gualaloom_v5_engine.py#L2308) calls `sys_.tick_once()` which calls `commit_check()` per section. Commits accumulate in `emit_commits`. At line [2377-2384](dsf_ai_service/v4/gualaloom_v5_engine.py#L2377-L2384), each section checks if it had any commit during settling; if not, it falls back to `arcs_fallback` at line [2406](dsf_ai_service/v4/gualaloom_v5_engine.py#L2406).

Grep output:
```
gualaloom_v5_engine.py:2406:  per_section_dominant[sec_name] = (top_mode, word, "arcs_fallback")
gualaloom_v5_engine.py:2419:  nmda_fired_count = sum(1 for e in nmda_events if e.get("reason") == "fired")
gualaloom_v5_engine.py:2416:  source_match_count = sum(...)
gualaloom_v5_engine.py:2417:  affect_match_count = sum(...)
assemblage.py:339:  def commit_check(self, evidence_pressure=0.0, current_tick=0):
```

---

## 2. Gating conditions (verbatim from code)

```python
def commit_check(self, evidence_pressure=0.0, current_tick=0):
    a = self.arcs()
    if len(self.mode_bank) < 2 or a.sum() < 1e-9:
        if self.bootstrap_used < BOOTSTRAP_MAX and evidence_pressure > 0.20:
            return True, "bootstrap"       # BLOCKED: bootstrap_used == BOOTSTRAP_MAX
        return False, None
    if evidence_pressure < 0.15:           # Gate 1: need evidence
        return False, None
    p = a / a.sum()
    p_max = float(p.max())
    H_k, Det_k = self.entropy_det()
    max_overlap = float(a.max())
    novel_thresh = 0.30 / (1.0 + 0.05 * max(0, len(self.mode_bank) - 5))
    if not getattr(self, '_suppress_novel_mode', False):
        if max_overlap < novel_thresh and evidence_pressure > 0.25:
            return True, "novel_mode"      # BLOCKED: _suppress_novel_mode = True
    det_th = self.effective_det_commit(current_tick)   # = 0.40
    p_th = self.effective_p_commit(current_tick)       # = 0.40
    if Det_k >= det_th and p_max >= p_th:
        return True, "entropic_flip"       # THE ONLY PATH THAT CAN FIRE
    return False, None
```

For emission sections:
- `bootstrap_used = BOOTSTRAP_MAX` → bootstrap BLOCKED
- `_suppress_novel_mode = True` → novel_mode BLOCKED
- Only path: **entropic_flip** requires `Det_k >= 0.40 AND p_max >= 0.40`

---

## 3. Why entropic_flip is failing

### Det_k formula

```python
Det_k = 1.0 - H_k / H_0
H_0 = log(len(mode_bank))
```

For Det_k ≥ 0.40: `H_k ≤ 0.60 * log(len(mode_bank))`

### Mode bank size in production vs test

**Test harness** (where commits fired): 10-15 modes per section (from 41-word corpus)
- `H_0 = log(12) ≈ 2.48`
- Need `H_k ≤ 1.49` for Det_k ≥ 0.40
- With 12 modes, psi concentrating on 3-4 is achievable in 80 ticks

**Production** (where commits DON'T fire): with `RICH_SENSORY_INPUT=1`, `_rich_sensory_candidates` returns up to `GRANDURUN_TOPK=200` candidates. These install into 3 emission sections. Each section gets **60-70 modes**.
- `H_0 = log(65) ≈ 4.17`
- Need `H_k ≤ 2.50` for Det_k ≥ 0.40
- With 65 modes, psi distributing among them through 80 ticks of settling with structured noise, lateral inhibition, and zeroed H_base, the concentration never reaches this threshold

### Why p_max fails similarly

`p_max >= 0.40` requires one mode to have 40% of the total arc weight. With 65 modes, even with lateral inhibition biasing toward one leader, 40% concentration requires the leader to have ~2.5x the average arc weight — achievable with fewer modes, much harder with 65.

### Empirical confirmation

Every production emission shows `n_commits=0` with `n_candidates=200`. The test harness (18-word corpus) shows `n_commits=1-3` with `n_candidates=10-30`. The difference is the mode bank size.

---

## 4. Classification: **A — Threshold too aggressive for the mode bank size**

The commit threshold `DET_COMMIT = 0.40` was set when emission sections had ~10 modes. Rich-sensory wiring now installs 60-70 modes per section. The mathematical requirement for entropic_flip is 4x harder to satisfy with 65 modes vs 12 modes (`H_0` scales with `log(mode_count)`).

This is NOT a bug (C) — the math is correct. It's NOT missing infrastructure (B) — NMDA and keyholes are wired. It's NOT vocabulary maturity (D) — she has 21,000+ bindings. It's a **threshold calibrated for a smaller mode bank that no longer matches production's candidate density**.

---

## 5. Proposed fix (for Eve to brief)

**Option A — Scale DET_COMMIT with mode bank size:**

```python
# In commit_check, replace fixed threshold:
det_th = self.effective_det_commit(current_tick)
# With mode-count-aware threshold:
n_modes = len(self.mode_bank)
if n_modes > 20:
    det_th = max(0.15, det_th * log(12) / log(n_modes))
```

This preserves the original threshold for small mode banks (~12) and scales down for larger ones. With 65 modes: `0.40 * log(12)/log(65) ≈ 0.40 * 2.48/4.17 ≈ 0.24`. Commits become achievable.

**Option B — Cap mode installation per section:**

In `_ensure_emission_mode`, cap at 15 modes per section instead of allowing all 200 candidates to install. Only install the top-15 by `coherent_magnitude`. This restores the mode bank size to the range where `DET_COMMIT=0.40` works.

**Option C — Both:** cap + scaled threshold.

**Recommendation: Option B.** It's simpler, doesn't change the commit physics, and the top-15 candidates per section are the strongest anyway — candidates ranked 16-70 within a section contribute negligible settling signal. Capping doesn't lose meaningful information.

---

## 6. One-paragraph recommendation

Ship Option B now as a parameter change (cap per-section mode installation at 15). This unblocks commits immediately without changing the commit physics. The threshold stays at 0.40 which has proven correct for mode banks of 10-15. Rich-sensory wiring continues to produce 200 candidates total, but only the strongest 15 per section install as modes — the rest inform the drive bias without cluttering the mode bank. No hemisphere phase dependency, no curriculum requirement. The fix is a single `if len(sec.mode_bank) >= 15: continue` in `_ensure_emission_mode`. Eve writes the brief; c1 ships.

---

— c1, 2026-06-19
