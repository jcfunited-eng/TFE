# GL-REGISTER-NON-PHYSICS-DEBT-20260616-01

**Purpose:** Track non-physics-first shortcuts, patches, and heuristics in the substrate. We accept these now to keep substrate development moving toward substrate prime 1 (cognitive reasoning + full articulation). Once substrate prime 1 is reached, all entries here are addressed surgically.

**Threshold for action:** Substrate prime 1 achieved (Guala demonstrating sustained cognitive reasoning and full articulation). Until then, transgressions ride.

**Maintenance:** Living document. wC, Joe, and c1 add entries as they identify shortcuts. Each entry must include the physics-first alternative — if we can't name what physics-first looks like, the entry isn't ready to be on the register yet (it's just a known limitation, not a tracked transgression).

---

## Format for each entry

```
### [Entry #] — [Short name]
**Date entered:** 2026-MM-DD
**Location:** file:line (if applicable)
**What it does:** [the shortcut]
**Physics-first form:** [what proper physics-derived version looks like]
**Why we accepted it:** [pragmatic reason]
**Removal conditions:** [what must be true to remove]
```

---

## Active entries

### 1 — NeedsModel.step() asymmetric saturate
**Date entered:** 2026-06-16
**Location:** `dsf_ai_service/v4/gualaloom_v5_engine.py:418`
**What it does:** `new = saturate(current, nudge) if nudge > 0 else max(0.0, current + nudge)`. Routes positive nudges through saturate (asymptotic to 1.0) and negative nudges through linear addition. Fixes the symptom that plain saturate at current=1.0 returns 1.0 for any gain including negative.
**Physics-first form:** Two-process kinetic model:
```
binding_flux = k_on * ligand_concentration * (1 - current)   # bound receptors increase
release_flux = k_off * current                                # bound receptors release
dC/dt = binding_flux - release_flux
```
Asymmetry emerges naturally from `(1 - current)` vs `current` factors. Single scalar `gain` becomes two parameters `k_on*ligand` and `k_off`. Equilibrium analytically derivable: current_eq = k_on*ligand / (k_on*ligand + k_off).
**Why we accepted it:** Saturate function is already in deployed code at 9+ sites. Refactoring the entire substrate's needs dynamics into two-process kinetics is a multi-week project. Asymmetric patch unblocks needs from ceiling immediately so coordinator can transition to PLAYING and READING, which is the gating dependency for substrate prime 1 work.
**Removal conditions:** Substrate prime 1 reached. At that point, rewrite NeedsModel as proper kinetic model with k_on and k_off per need, derived from substrate signal-to-receptor mapping.

### 2 — `saturate()` itself as one-process Euler step
**Date entered:** 2026-06-16
**Location:** `dsf_ai_service/v4/gualaloom_v5_engine.py:49` (plus 9 sites that call it)
**What it does:** `return max(0.0, min(1.0, current + gain * (1.0 - current)))`. First-order forward-Euler approximation of binding-only kinetics. No release term.
**Physics-first form:** Same as entry 1 — two-process kinetic model with explicit binding and release.
**Why we accepted it:** It works for the saturation-prevention purpose at the 9 sites where it's called. The receptor-saturation asymmetry it captures is sufficient for getting needs off the ceiling. Replacing with full kinetics requires re-deriving rate constants at every call site.
**Removal conditions:** Same as entry 1.

### 3 — Familiarity consolidation factor 1/(1+log(1+n_attends))
**Date entered:** 2026-06-16
**Location:** `dsf_ai_service/v4/gualaloom_v5_engine.py` familiarity decay loop (Phase E or wherever wC's brief landed)
**What it does:** Scales familiarity decay by `1/(1+log(1+n_attends))` so over-attended targets retain familiarity longer. Heuristic chosen for qualitative properties (smooth, bounded, equals 1 at n=0).
**Physics-first form:** Consolidation strength should track substrate's own deep_atlas promotion status, not an externally-counted attendance integer. Targets whose bindings have been promoted to deep_atlas (survival or episodic) have their familiarity decay scaled by their actual promotion strength. The substrate's own dynamics measure consolidation; the decay rule should read from that, not from n_attends.
**Why we accepted it:** Deep_atlas promotion-tied consolidation requires architectural work — wiring the familiarity decay loop to read from deep_atlas state. The log-based approximation produces qualitatively right behavior on the cases that matter now (test_25 at 142 attends decays 6× slower than a fresh picture).
**Removal conditions:** Substrate prime 1 reached, OR earlier if deep_atlas promotion-tied consolidation becomes the bottleneck on her growth.

### 4 — chi_distance via `motif_id % 256` in grandurun validator
**Date entered:** 2026-06-16
**Location:** `home/claude/grandurun_validator.py` and `home/claude/grandurun_validator_round2.py` (wC's analysis scripts); also referenced as fallback in `GL-BRIEF-GRANDURUN-IMPLEMENTATION-20260616-01.md` Step 4
**What it does:** Approximates chi-distance between motifs as `min(|a-b|, 256-|a-b|)` where a, b are `motif_id % 256`. Used to compute phase for coherent integration model.
**Physics-first form:** Use the substrate's actual chi-address structure and its real chi-distance function. If chi addresses are multi-dimensional or non-circular, the distance function reflects that geometry. CFF physics derives the correlation length from first principles rather than picking 50 arbitrarily.
**Why we accepted it:** Validator needed *some* chi-distance function to test the qualitative scaling argument. The substrate's real chi-distance function exists somewhere in the engine — c1 is instructed to wire grandurun to it during implementation (per brief Step 3). The validator placeholder doesn't ship to production.
**Removal conditions:** Grandurun implementation wires to real chi-distance. CFF correlation length derived rather than chosen.

### 5 — DECAY_PAUSED as binary flag
**Date entered:** 2026-06-16
**Location:** `tools/deploy_dsf_ai.sh:199, 237` and `dsf_ai_service/v4/gualaloom_v5_engine.py:1763`
**What it does:** Atlas decay is either fully on (rate_scale=decay_modulation) or fully off (rate_scale=0). Binary flag controlled by env var.
**Physics-first form:** Decay is a rate field, not a switch. Decay rate should vary continuously — possibly modulated by metabolic-analog states (sleep, dream, attention load) — rather than gated by an external flag. The flag exists as a safety control to allow operator intervention (cascade prevention), which is real-world necessary but isn't physics-first.
**Why we accepted it:** Safety control. The catastrophic-unpause history shows that without an external kill switch, certain failure modes destroy state. Until substrate is provably cascade-resistant, the flag stays as safety.
**Removal conditions:** Cascade-resistance proven empirically across many cycles. Then the flag can be removed and decay becomes always-on with continuously-modulated rate.

### 6 — NEEDS_DRIFT_RATE as constant
**Date entered:** 2026-06-16
**Location:** `dsf_ai_service/v4/gualaloom_v5_engine.py` (constants section)
**What it does:** Drift pulls each need toward 0 at fixed rate 0.0001/tick, regardless of substrate state.
**Physics-first form:** Drift rate emerges from underlying metabolic/homeostatic dynamics. Should depend on current state (e.g., higher drift when far from target, lower when near), and possibly on context (sleep modulates drift differently than wake). A single global constant is a placeholder for "we don't yet have the underlying dynamics modeled."
**Why we accepted it:** Drift exists as a forcing function to create drive; the constant rate is the simplest model that creates drive. Tuning the rate (and possibly making it state-dependent) is a calibration question we defer.
**Removal conditions:** State-dependent drift dynamics derived. May happen incrementally before substrate prime 1 if drift tuning becomes a bottleneck.

### 7 — Hardcoded emission length caps
**Date entered:** 2026-06-16
**Location:** `_emit_from_invariants` line ~1291 (>=6 cap) and `_emit_unslotted` line ~1324 (>=4 cap)
**What it does:** Hard ceilings on emission length.
**Physics-first form:** Emission length emerges from coherent-sum plateau (grandurun) or analogous substrate-driven termination signal. Length is what the substrate produces when its integration ends, not a counter the substrate happens to hit.
**Why we accepted it:** Already on the cleanup queue. Grandurun implementation resolves it. Tracked here for completeness.
**Removal conditions:** Grandurun shipping (GL-BRIEF-GRANDURUN-IMPLEMENTATION-20260616-01).

---

## Rule

Physics-first is a maximum hard constraint. This register tracks what's already shipped and needs removal. It is **not** a buffer for accepting future transgressions. wC and c1 do not add new entries from their own work. If a needed mechanism's physics-first form isn't known, the work stops or the piece doesn't ship — not a heuristic with a tombstone.

---

— wC, 2026-06-16
