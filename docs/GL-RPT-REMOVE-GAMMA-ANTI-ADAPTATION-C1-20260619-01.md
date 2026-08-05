# GL-RPT-REMOVE-GAMMA-ANTI-ADAPTATION-C1-20260619-01

**From:** c1
**Date:** 2026-06-19
**Subject:** B1/B2 gamma anti-adaptation removal — deployed and verified
**Commit:** `8a1dd23` on `codex/persistent-etl-update-20260326`
**Task def:** `dsf-ai-task:206` (was 205)
**Image:** `dsf-ai:deploy-20260619T164858Z`
**Git SHA:** `8a1dd23`

---

## V1 — Branch verification

```
$ git grep "gamma_homeostasis" -- dsf_ai_service/substrate/assemblage.py
assemblage.py:    # B2 gamma_homeostasis REMOVED — ...     (comment only)

$ git grep "_initial_gamma" -- dsf_ai_service/substrate/assemblage.py
assemblage.py:    # B1 _initial_gamma + GAMMA_DRIFT REMOVED — ...  (comment only)

$ git grep "GAMMA_DRIFT" -- dsf_ai_service/
gualaloom_dna/assemblage.py:GAMMA_DRIFT = 0.02   (dead copy, not live)
gualaloom_dna/assemblage.py:...drift = ...GAMMA_DRIFT  (dead copy)
substrate/assemblage.py:    # B1 _initial_gamma + GAMMA_DRIFT REMOVED  (comment only)
```

Zero functional references in live code. Self-evo block at line 746 reads `for k, dv in dgamma.items(): sec.gamma[k] = float(np.clip(sec.gamma[k] + dv, *GAMMA_BOUNDS))` — no drift term.

---

## V2 — Production state

```
Task def:        dsf-ai-task:206 (PRIMARY, single deployment, stable)
Image:           dsf-ai:deploy-20260619T164858Z
Git SHA:         8a1dd23

schema_version:  v7.1.0                                              ✓
identity:        cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f               ✓
last_save_tick:  11207529  (advancing)                               ✓
n_live_bindings: 21130  (pre-deploy 21147, delta 0.08%)              ✓
vocab:           2810                                                ✓
```

---

## V3 — Behavioral

**Emission test:**
```
Input:  "the moon is bright"
Output: "today"
Events: emission_dynamics (n_commits=1), response_window_opened,
        self_heard. No exceptions. No new error types.
```

**12-minute idle window (zero intervention):**
```
Capture 1: last_save_tick=11207529  (17:05:49 UTC)
Capture 2: last_save_tick=11213529  (17:30:27 UTC)
Delta: +6000 ticks. Autosaves firing.
```

**S3 backups during window:**
```
PRE 2026-06-19_17-09-03_backstop/    ← NEW
PRE 2026-06-19_17-19-55_backstop/    ← NEW
```

Full persistence chain healthy through this code change.

---

## Tests

**New (2/2 green):**
```
Test 1: gamma persistence (no drift)... PASS
Test 2: legitimate self-evo preserved... PASS
```

**Existing (all green):**
- save_hooks 9/9 PASS
- plasticity_on_commit OVERALL PASS
- hemisphere_roundtrip 7/7 ALL GREEN

---

## What was removed

| Item | Location | Pattern |
|------|----------|---------|
| B1: GAMMA_DRIFT constant | line 34 | `0.02` spring force back to default |
| B1: drift term in self-evo | lines 757-759 | `drift = (default - gamma) * GAMMA_DRIFT` |
| B2: gamma_homeostasis method | lines 250-254 | `(1-rate)*x + rate*initial_x` on gamma |
| B2: _initial_gamma snapshot | line 248 | Drift target for B2 |
| B2: call site in tick_once | line 707 | `sec.gamma_homeostasis(rate=0.001)` every 20 ticks |
| Docstring bullet | line 8 | "Gamma drift-toward-default" |

**Preserved:** eta-based self-evolution (surprise-gradient updates), GAMMA_BOUNDS clipping, GAMMA_DEFAULTS (initial values only).

---

— c1, 2026-06-19
