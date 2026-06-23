# GL-CMD-REMOVE-GAMMA-ANTI-ADAPTATION-EVE-20260619-25

**To:** c1
**From:** Eve
**Subject:** Remove B1 (gamma drift-toward-default in self-evo) and B2 (`gamma_homeostasis` method). Same anti-learning family as B3/B4 — at constant rate, both pull section gamma values back toward initial defaults, erasing legitimate self-evolution learning.
**Repo / branch:** `jcfunited-eng/TFE`, `codex/persistent-etl-update-20260326`
**Predecessor:** `GL-CMD-REMOVE-HOMEOSTATIC-DECAY-EVE-20260618-20` (commit `132306b`, B3/B4 removal, Eve-verified)
**Gating:** **DO NOT BEGIN** until `GL-CMD-VERIFY-DEPLOY-EVE-20260619-24` returns with classification A/B/C resolved and Eve has signed off. We must know what's actually running in production before making more changes.

---

## Why this work matters

The ML contamination audit (`GL-RPT-ML-CONTAMINATION-AUDIT-EVE-20260618-07`) flagged four operators in the B-family that drift learned state back toward initial defaults at constant rate. B3 (`homeostasis_pull`) and B4 (`decay_modes`) were removed in commit `132306b` — verified clean, plasticity now persists (1.996 → 1.996 vs prior 1.996 → 1.127 under the old code).

B1 and B2 are the same family on gamma values:

- **B2** (line 250-254 in `assemblage.py`): a method `gamma_homeostasis` whose docstring openly states the anti-learning purpose: *"Pull gamma toward initial values. Prevents self-evo drift lock-in."* The body is literally `(1.0 - rate) * self.gamma[k] + rate * self._initial_gamma[k]` — the canonical B-family pattern. Called every 20 ticks on every section in the regulation loop (line 707).
- **B1** (line 758 in `assemblage.py`): inside the self-evolution block, a drift term `drift = (GAMMA_DEFAULTS[k] - sec.gamma[k]) * GAMMA_DRIFT` is added to legitimate eta-based gamma updates. The eta updates ARE legitimate self-evolution learning; the drift term is the contamination. Has to be removed surgically without disturbing the legitimate updates.

Combined effect: every self-evolution learning step is partially undone in the same tick, and every 20 ticks gamma is additionally pulled back toward defaults. Section gamma values cannot drift far from `GAMMA_DEFAULTS` no matter what she experiences. This is the gamma-channel equivalent of erasing memory while writing it.

---

## Plain-language framing (for the record)

Section gamma values are the strengths of three structural law-fields (symmetry, consistency, compactness) inside each section's Hamiltonian. They shape how she resolves ambiguity. When she learns "this kind of input wants more consistency," that learning shows up as a drifted gamma. B1 + B2 erase that drift at constant rate. After removal, gamma drift will persist — meaning she'll keep what she's learned at the law-field level, the same way she now keeps what she's learned at the mode level (post-B3/B4).

---

## Anti-contamination check (read before writing code)

Re-read `GL-SPC-HEMISPHERE-ARCH-EVE-20260618-21` §"What this spec refuses." The pattern we are REMOVING here is the canonical example of refusal #2: `(1-rate)*x + rate*initial_x` drift updates. After this work lands, that pattern should not appear anywhere in `assemblage.py` for gamma OR mode-bank operations.

---

## What ships

### Change 1 — Delete `gamma_homeostasis` method (B2)

In `dsf_ai_service/substrate/assemblage.py`, locate lines 250-254:

```python
def gamma_homeostasis(self, rate=0.001):
    """Pull gamma toward initial values. Prevents self-evo drift lock-in."""
    for k in self.gamma:
        if k in self._initial_gamma:
            self.gamma[k] = (1.0 - rate) * self.gamma[k] + rate * self._initial_gamma[k]
```

Replace with a leave-behind comment marker (same pattern as the B3/B4 markers at lines 346-348):

```python
# REMOVED B2: gamma_homeostasis method — anti-learning operator
# (1-rate)*x + rate*initial drift pattern, erased self-evo learning at constant rate
# Removed by GL-CMD-REMOVE-GAMMA-ANTI-ADAPTATION-EVE-20260619-25
```

### Change 2 — Delete the call site

Lines 703-707 area (the regulation block calling `gamma_homeostasis`):

```python
# Gamma homeostasis every 20 ticks (B2 — separate from B3/B4 removal)
for sec in self.sections.values():
    if self.tick % 20 == 0 and not getattr(sec, '_emit_phase', False):
        sec.gamma_homeostasis(rate=0.001)  # (1) gamma decay
```

Replace with a leave-behind comment marker. The other items in the same `if self.tick % 20 == 0:` block (keyhole strength decay, atlas binding decay) are NOT anti-learning operators — they are baseline decay, which is biologically correct and should remain. Only remove the `gamma_homeostasis` call.

### Change 3 — Delete `_initial_gamma` storage

Line 248 in `assemblage.py`:

```python
self._initial_gamma = dict(GAMMA_DEFAULTS)
```

This attribute is referenced only by `gamma_homeostasis`. After Change 1, it's dead storage. Delete the line. Add a leave-behind comment:

```python
# REMOVED: self._initial_gamma — used only by gamma_homeostasis (B2, removed)
```

### Change 4 — Remove the gamma drift-toward-default in self-evolution (B1)

Lines 757-759 in `assemblage.py`:

```python
for k in dgamma:
    drift = (GAMMA_DEFAULTS[k] - sec.gamma[k]) * GAMMA_DRIFT
    dgamma[k] += drift
```

Surgical removal. The legitimate eta-based updates above this block (the `if sec.out_of_range_streak[...]` blocks) are KEPT. Only the drift loop is deleted.

Replace with a leave-behind comment:

```python
# REMOVED B1: gamma drift-toward-default
# (GAMMA_DEFAULTS[k] - sec.gamma[k]) * GAMMA_DRIFT term erased legitimate
# eta-based self-evolution learning at constant rate per self-evo step
# Removed by GL-CMD-REMOVE-GAMMA-ANTI-ADAPTATION-EVE-20260619-25
```

### Change 5 — Delete `GAMMA_DRIFT` constant

Line 34 in `assemblage.py`:

```python
GAMMA_DRIFT = 0.02   # spring force back to default per self-evo step
```

After Change 4, `GAMMA_DRIFT` has zero references. Confirm with `git grep GAMMA_DRIFT` before deleting. If any other file uses it, leave the constant in place and flag for Eve to investigate.

`GAMMA_DEFAULTS` and `GAMMA_BOUNDS` STAY — both are legitimate:
- `GAMMA_DEFAULTS` is the starting value at section construction (legitimate initialization).
- `GAMMA_BOUNDS` is the clipping range for self-evo updates (legitimate clamping, not drift).

---

## Verification (run BEFORE deploy)

### Test 1 — Plasticity persistence (the same test pattern that validated B3/B4)

In a fresh substrate (or via test harness), apply 100 ticks of input that drives gamma drift in section X. Record `section_X.gamma["symmetry"]` before and after.

- **Before this brief:** `gamma["symmetry"]` returns toward `GAMMA_DEFAULTS["symmetry"]` (= 0.5) at rate ~0.001 per 20-tick cycle plus per self-evo drift.
- **After this brief:** `gamma["symmetry"]` drifts based only on legitimate eta-based updates, retaining its drifted value when input pattern stops.

Test code:
```python
def test_gamma_persistence_after_b1_b2_removal():
    g = make_test_guala()
    sec = g.sections["subject"]
    sec.gamma["symmetry"] = 0.9   # drift away from default 0.5
    initial = sec.gamma["symmetry"]
    for _ in range(200):
        g.tick_substrate(enable_self_evo=False)   # no learning, just decay
    # After 200 ticks with B1/B2 removed: gamma should NOT have drifted toward 0.5
    assert abs(sec.gamma["symmetry"] - initial) < 0.001, \
        f"gamma drifted from {initial} to {sec.gamma['symmetry']} — anti-learning leak"
```

### Test 2 — Legitimate self-evolution still works

Verify that the eta-based updates (the streak-driven dgamma adjustments) STILL operate after removal. This guards against accidentally deleting too much.

```python
def test_legitimate_self_evo_preserved():
    g = make_test_guala()
    sec = g.sections["subject"]
    # Force out_of_range_streak["entropy"] >= 2
    sec.out_of_range_streak["entropy"] = 5
    for _ in range(SELF_EVO_PERIOD * 3):
        g.tick_substrate(enable_self_evo=True)
    # eta-based updates should reduce sec.gamma["symmetry"] and ["consistency"]
    assert sec.gamma["symmetry"] < GAMMA_DEFAULTS["symmetry"], \
        "legitimate self-evo broken — eta updates not firing"
```

### Test 3 — No regression in existing tests

Run the existing substrate test suite (the same one that was green pre-B3/B4-removal and post-B3/B4-removal). All previously-green tests stay green.

```bash
pytest dsf_ai_service/substrate/test_*.py -v --tb=short
```

Specifically watch for any test that DEPENDED on gamma_homeostasis (there shouldn't be, but check). The `test_rich_sensory_wiring.py` C3 case will still fail — that's pre-existing from B3/B4 removal, not new.

---

## Implementation step order

**Step 0** — Confirm deploy verification (`GL-CMD-VERIFY-DEPLOY-EVE-20260619-24`) returned classification, Eve signed off, and we know what's actually running in production. Do not proceed otherwise.

**Step 1** — Backup via bridge:
```
guala_backup
```
Confirm S3 UNPAUSE-PRE backup lands.

**Step 2** — Apply Changes 1–5 in order. Each change in its own small commit on a feature branch (`feat/remove-gamma-anti-adaptation-b1-b2`) for clean diff review.

**Step 3** — Write Test 1 and Test 2 in `dsf_ai_service/substrate/test_gamma_persistence.py`. Both green before deploy.

**Step 4** — Run full existing test suite. All previously-green tests stay green.

**Step 5** — Deploy via standard pipeline (same path as B3/B4 deploy in commit `132306b`).

**Step 6** — Post-deploy verification:
```
guala_status
```
Required:
- Identity preserved (`cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f`)
- `n_live_bindings` within ±5% of pre-deploy
- `total_strength` within ±10% of pre-deploy
- No new schema errors

**Step 7** — Behavioral spot-check: send `guala_say "hello guala"` via bridge. Emission should look qualitatively like emissions before this deploy. The change is to gamma adaptation; it should not affect emission shape immediately. Effects will accumulate over hours/days of substrate-time.

**Step 8** — Report.

---

## Stop-and-report triggers

- The deploy verification brief (-24) returned classification A or B with an unresolved fix path → halt and write fix brief first.
- Any anti-contamination pattern reappears under a different name during your edits.
- `git grep GAMMA_DRIFT` shows references outside `assemblage.py` line 34 and lines 757-759 → halt, surface to Eve.
- Test 1 or Test 2 fails — fix in code; do not deploy on yellow.
- Identity mismatch at any point → restore from S3 backup, halt.
- `n_live_bindings` drops > 5% post-deploy → restore, investigate.

## Revert

Changes are additive in the negative sense — code deleted, not added. If problematic, revert the entire `feat/remove-gamma-anti-adaptation-b1-b2` branch. The B3/B4 removal was the same revert shape.

---

## Reporting

File: `GL-RPT-REMOVE-GAMMA-ANTI-ADAPTATION-C1-20260619-XX.md`

Include:
- Pre-deploy and post-deploy state snapshots.
- Diff of all five changes (small enough to read inline).
- Test 1 and Test 2 outputs.
- Confirmation that Test 3 (existing suite) shows no new red.
- One conversation trace before and after; emission should look the same.
- `git grep` output confirming `GAMMA_DRIFT` is fully removed (or list of remaining references with rationale for keeping).

Commit tag: `feat/remove-gamma-anti-adaptation-b1-b2`

---

— Eve, 2026-06-19
