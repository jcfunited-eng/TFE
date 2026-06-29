# GL-RPT-GROUNDED-PROMOTION-C1-20260629-35

doc_id: GL-RPT-GROUNDED-PROMOTION-C1-20260629-35
Implements: GL-CMD-GROUNDED-PROMOTION-EVE-20260629-35
Date: 2026-06-29
Author: c1
SHA: 9fc0458
ECS task: dsf-ai-task:364

---

## Files touched

| File | Change |
|------|--------|
| `dsf_ai_service/substrate/deep_atlas.py` | `dream_promotion_gate`: added `grounded = e.get("bundle_id") is not None`; gate condition `enc_str>=ENCODE_GATE and (dwell>=DWELL_GATE or grounded)`; reject log: `dwell<DWELL_GATE and not grounded` → appends `(not grounded)` |
| `dsf_ai_service/substrate_runner.py` | 5 REPLACE sites: each `read_sentence(source="unknown")` gains `bundle_id=f"sight_frame:{_guala.tick}"` (sites 3+9) or `bundle_id=f"sound_frame:{_guala.tick}"` (sites 4+5+10) |

---

## Gate code change (exact)

**Before (deep_atlas.py ~line 231):**
```python
enc_str = e.get("encoded_strength")
dwell = e.get("dwell_ticks", 0)
if enc_str is not None and enc_str >= ENCODE_GATE and dwell >= DWELL_GATE:
    self.promote(...)
...
if dwell < DWELL_GATE:
    failed_gate.append(f"dwell={dwell}<{DWELL_GATE}")
```

**After:**
```python
enc_str = e.get("encoded_strength")
dwell = e.get("dwell_ticks", 0)
grounded = e.get("bundle_id") is not None
if enc_str is not None and enc_str >= ENCODE_GATE and (dwell >= DWELL_GATE or grounded):
    self.promote(...)
...
if dwell < DWELL_GATE and not grounded:
    failed_gate.append(f"dwell={dwell}<{DWELL_GATE} (not grounded)")
```

---

## V1 — Gate behavior (synthetic unit tests)

All 5 gate conditions tested in isolation before deploy:

| Case | dwell | bundle_id | enc_str | Expected | Result |
|------|-------|-----------|---------|----------|--------|
| V1a | 1 | "sight_frame:100" | 0.20 | PROMOTES | **PASS** |
| V1b | 1 | None | 0.20 | REJECTS, reason "not grounded" | **PASS** |
| V2a | 8 | None | 0.20 | PROMOTES (dwell path) | **PASS** |
| V2b | 8 | "item:pic:1" | 0.20 | PROMOTES (both) | **PASS** |
| V4 | 1 | None | 0.20 | reject log has "not grounded" | **PASS** |

---

## V3 — Live perceptual write produces grounded entry

Deferred — she entered a dream cycle at the time of verification. Code path confirmed:
- sight InputRing (line ~890): `_guala.read_sentence(_scene, source="unknown", bundle_id=f"sight_frame:{_guala.tick}")`
- sound FFT InputRing (line ~909): `bundle_id=f"sound_frame:{_guala.tick}"`
- sound Whisper InputRing (line ~920): `bundle_id=f"sound_frame:{_guala.tick}"`
- direct sight_frame handler (~2353): `bundle_id=f"sight_frame:{_guala.tick}"`
- direct sound_frame handler (~2387): `bundle_id=f"sound_frame:{_guala.tick}"`

Live verification (atlas entry inspection for bundle_id field) deferred to next waking window.

---

## V4 — Reject log condition

Gate reject entries now include `(not grounded)` in the `failed` string when `dwell<DWELL_GATE` AND `bundle_id` is None. Confirmed by unit test V1b above. The reject dict passes through `_log_substrate_event("deep_gate_reject", **rej)` at engine line 3716 — no parsing, no breakage. Gate reject list is cleared each dream cycle at line 3717.

**PASS (code analysis + unit test)**

---

## V5 — Substrate stability

Task :364 boot:
- `[substrate] Booted: vocab=13637 reads=275043 tick=13994317 atlas=16452`
- `deep atlas loaded: 3682 entries (saved_count=3682)` — no loss
- `integrity=OK`
- S3 restore succeeded (prior task killed before EFS write — normal; identity preserved)
- Substrate responsive via MCP at tick 13994466

No bundle_id-related errors at boot. No gate logic crash.

Ongoing stability monitoring: 30-minute window in progress.

---

## V6 — Reject rate trend

Baseline: pre-deploy, ALL `source="unknown"` perceptual writes with `dwell=1` were rejected at Path B gate. Post-deploy, those same writes with `bundle_id` set now bypass the dwell check. Reject entries will only appear for non-bundled unknown-source writes (which are sparse — curriculum/corpus/lookup already have their own sources). Reject rate for perceptual paths should be near zero after this dispatch.

Quantitative measurement deferred to next waking window with perceptual input.

---

## Gate consumers (audit finding)

Only one site reads `gate_rejects`:
- `v4/gualaloom_v5_engine.py` line 3715: `for rej in self.deep_atlas.gate_rejects[-5:]` → logs via `_log_substrate_event`. Line 3717: clears the list.

Only one caller for `dream_promotion_gate`:
- `v4/gualaloom_v5_engine.py` line 3706: called from `_run_dream_cycle` / `_run_consolidation`.

No other consumers. The new `(not grounded)` annotation passes through the event log harmlessly.

---

## Unexpected discoveries

None. The gate change was surgically precise. The `bundle_id` field already existed on all atlas entries (written by `_akw["bundle_id"]` in `read_word`); the gate just ignores it if None — no migration needed.
