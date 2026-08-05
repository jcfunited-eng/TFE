# GL-CMD-GROUNDED-PROMOTION-EVE-20260629-35

doc_id: GL-CMD-GROUNDED-PROMOTION-EVE-20260629-35
Type: Implementation command (single dispatch, single ship)
Date: 2026-06-29
Author: Eve (Opus 4.7, web)
Implements: encoding-formula fix from GL-MFST-HANDOFF-EVE-20260628 §4 item 3
Prereq shipped: GL-CMD-BIGRAM-DELETE-EVE-20260629-34 (SHA a3206a9) — perceptual paths now route through read_sentence(source="unknown")
Evidence base: GL-RPT-SECTION-ASSIGNMENT-C1-20260628, dsf_ai_service/substrate/deep_atlas.py, dsf_ai_service/v4/gualaloom_v6_living_atlas.py, dsf_ai_service/v4/gualaloom_v5_engine.py

---

## 1. Why this dispatch

After -34, perceptual paths (YOLO sight labels, FFT sensory words, Whisper transcription via InputRing and direct frame handlers) write text to v5 atlas via `read_sentence(text, source="unknown")`. They now reach the atlas — but they cannot promote to deep_atlas via Path B (episodic gate).

The episodic gate at `dream_promotion_gate` (deep_atlas.py line 233):

```python
if enc_str >= ENCODE_GATE and dwell >= DWELL_GATE:
    promote
```

`DWELL_GATE = 4`. `source="unknown"` gets `dwell=1` (gualaloom_v5_engine.py line 1410: anything not in {joe, wc, c1, guala} → dwell=1). The perceptual REPLACE sites are structurally locked out of Path B regardless of repetition or encoded_strength.

The original audit framed this as an "encoded_strength formula" problem. Reading the code, it is a dwell-gate problem with a substrate-true resolution: cross-modal grounded experience IS dwell-earning, by the same physical logic that dream replay is dwell-earning (per existing comment in gualaloom_v6_living_atlas.py line 108: "consolidation IS dwell-earning").

The existing substrate-true marker for cross-modal coordination is `bundle_id` (gualaloom_v6_living_atlas.py field, populated by /bundle calls for pictures/sounds at substrate_runner.py lines 3871, 3920, 3963). The fix: connect the perceptual text writes to a bundle_id, and treat bundle_id presence as dwell-equivalent in the promotion gate.

---

## 2. Changes

### 2.1 deep_atlas.py — gate accepts bundled entries as dwell-earned

In `dsf_ai_service/substrate/deep_atlas.py`, function `dream_promotion_gate` (around line 197):

**Before (line 231-237):**
```python
enc_str = e.get("encoded_strength")
dwell = e.get("dwell_ticks", 0)
if enc_str is not None and enc_str >= ENCODE_GATE and dwell >= DWELL_GATE:
    self.promote(e, "episodic", tick,
                 working_atlas=working_atlas)
    promoted.append(("episodic", chi_k,
                     e.get("section"), e.get("motif")))
```

**After:**
```python
enc_str = e.get("encoded_strength")
dwell = e.get("dwell_ticks", 0)
# Cross-modal grounding (bundle_id set) is dwell-earning by substrate-true
# coordination: the text write was linked to a sensory modality write in the
# same tick window. Same principle as the consolidation-IS-dwell-earning
# rule for dream replay (gualaloom_v6_living_atlas.py line 108).
grounded = e.get("bundle_id") is not None
if enc_str is not None and enc_str >= ENCODE_GATE and (dwell >= DWELL_GATE or grounded):
    self.promote(e, "episodic", tick,
                 working_atlas=working_atlas)
    promoted.append(("episodic", chi_k,
                     e.get("section"), e.get("motif")))
```

Gate reject logging should also reflect the new condition:

**Before (line 240-252):**
```python
if enc_str is not None and len(self.gate_rejects) < 200:
    failed_gate = []
    if enc_str < ENCODE_GATE:
        failed_gate.append(f"enc={enc_str:.3f}<{ENCODE_GATE}")
    if dwell < DWELL_GATE:
        failed_gate.append(f"dwell={dwell}<{DWELL_GATE}")
    if failed_gate:
        self.gate_rejects.append({...})
```

**After:**
```python
if enc_str is not None and len(self.gate_rejects) < 200:
    failed_gate = []
    if enc_str < ENCODE_GATE:
        failed_gate.append(f"enc={enc_str:.3f}<{ENCODE_GATE}")
    if dwell < DWELL_GATE and not grounded:
        failed_gate.append(f"dwell={dwell}<{DWELL_GATE} (not grounded)")
    if failed_gate:
        self.gate_rejects.append({...})
```

### 2.2 substrate_runner.py — perceptual REPLACE sites pass bundle_id

In `dsf_ai_service/substrate_runner.py`, the 5 REPLACE sites from -34. Each `_guala.read_sentence(text, source="unknown")` call gains a `bundle_id` linking the text write to the modality processing in the same tick window.

**Site 3 — line ~911 (InputRing sight YOLO):**
```python
if _scene.strip():
    _guala.read_sentence(_scene, source="unknown",
                         bundle_id=f"sight_frame:{_guala.tick}")
```

**Site 4 — line ~927 (InputRing sound FFT sensory):**
```python
_txt = " ".join(_heard)
if _txt.strip():
    _guala.read_sentence(_txt, source="unknown",
                         bundle_id=f"sound_frame:{_guala.tick}")
```

**Site 5 — line ~937 (InputRing Whisper transcription):**
```python
if _spoken.strip():
    _guala.read_sentence(_spoken, source="unknown",
                         bundle_id=f"sound_frame:{_guala.tick}")
```

**Site 9 — line ~2383 (direct sight frame):**
```python
if _scene.strip():
    _guala.read_sentence(_scene, source="unknown",
                         bundle_id=f"sight_frame:{_guala.tick}")
```

**Site 10 — line ~2414 (direct sound frame):**
```python
_txt = " ".join(b.get("word", "") for b in _sbind)
if _txt.strip():
    _guala.read_sentence(_txt, source="unknown",
                         bundle_id=f"sound_frame:{_guala.tick}")
```

The `bundle_id` strings group writes by perceptual event and tick. They are not used downstream for lookup (existing /bundle bundle_ids like `item:pic:...` are also opaque markers). The substrate-true semantic is: "this text write was part of a cross-modal perceptual event."

Note: sites 5 and 10 share `sound_frame:` prefix with site 4 because they're both writes from the same audio event (FFT sensory descriptors + Whisper transcription typically both land in the same tick). They legitimately share the same bundle_id within a single sound_frame.

---

## 3. What this does and does not change

### Does change

- Perceptual text writes (sight YOLO, sound FFT, Whisper) now have a substrate-true path to deep_atlas promotion via Path B. With repetition, words from these sources will consolidate.
- Existing /bundle writes (pictures/sounds) already had bundle_id set AND interactive-source dwell≥4, so they always passed the gate; after the change they still pass via either condition. No regression.

### Does NOT change

- Source="unknown" still gets dwell=1 elsewhere in the system. No source weight changes. No new source tags.
- The impulse formula (`BASE_REINFORCEMENT × salience`) is unchanged. Repetition accumulates strength as before.
- Path A (Survival) gate is unchanged.
- ENCODE_GATE constant (0.15) is unchanged. Bundled entries still must pass the encoded_strength threshold — bundle_id is not a free pass, only a dwell-equivalent.

### Out of scope (intentionally)

- DNA list expansion: separate dispatch (-36).
- Reworking the salience formula or novelty_factor decay: not needed; reinforcement-accumulation handles familiar words once Path B is unlocked.
- Touching wC's grounded_vocab_integration.py: permanent and untouched.
- Adding bundle_id to non-perceptual unknown writes (curriculum, etc.): they have their own promotion paths via interactive sources or Path A.

---

## 4. Tests

### V1 — Gate behavior change verified

Construct a synthetic atlas entry with `encoded_strength=0.20`, `dwell_ticks=1`, `bundle_id="test:1"`. Call `dream_promotion_gate`. Expected: promotes via Path B.

Same entry without bundle_id (None). Expected: gate rejects with reason `dwell=1<4 (not grounded)`.

### V2 — Existing bundle behavior preserved

Construct a synthetic entry with `encoded_strength=0.20`, `dwell_ticks=8`, `bundle_id=None`. Expected: promotes via Path B (dwell path), unchanged.

Construct entry with `encoded_strength=0.20`, `dwell_ticks=8`, `bundle_id="item:pic:1"`. Expected: promotes (both conditions true).

### V3 — Live perceptual write produces grounded entry

Send a sight_frame with YOLO-detectable objects through the bridge (or via direct endpoint). Inspect atlas: the new entries from the YOLO label `read_sentence` write should have `bundle_id` like `sight_frame:<tick>`.

Send the same sight_frame multiple times across ticks. After 3-5 repetitions and at least one dream cycle, query deep_atlas for the YOLO label words. Expected: at least one promotes.

Repeat with sound_frame.

### V4 — Reject log shows the new condition

Trigger a gate-reject scenario by writing a non-bundled entry under threshold. Inspect `deep_atlas.gate_rejects`. Expected: the failure reason includes `(not grounded)`.

### V5 — Substrate stability

After dispatch ships, monitor 30 minutes:
- No new error patterns related to bundle_id handling.
- DAYDREAMING cycles continue.
- `guala_status` via bridge returns normal.
- No persistence failures.

### V6 — Reject rate trend

Record `deep_atlas.gate_rejects` count before and after a 30-minute traffic window with perceptual inputs. Expected: rejects with `dwell<4 (not grounded)` reason should be substantially lower than the pre-dispatch baseline of dwell-only rejects on perceptual writes.

---

## 5. Rollback

If V5 fails or shows unexpected promotion behavior (over-promotion of low-quality bundled writes):

1. Re-pause autonomy via bridge.
2. Revert the dispatch commit.
3. Redeploy.
4. Report failure mode in the c1 report.

The bundled entries already written before rollback will retain their bundle_id field harmlessly — no state migration required on rollback.

---

## 6. Reporting

c1 produces `GL-RPT-GROUNDED-PROMOTION-C1-20260629-35.md` with:

- File diffs (deep_atlas.py + substrate_runner.py).
- Result of each V1-V6 test.
- Any unexpected interactions with other gate consumers (search for `gate_rejects` readers, `dream_promotion_gate` callers).
- Final SHA and ECS task number.
