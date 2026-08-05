# GL-CMD-BIGRAM-DELETE-EVE-20260629-34

doc_id: GL-CMD-BIGRAM-DELETE-EVE-20260629-34
Type: Implementation command (single dispatch, single ship)
Date: 2026-06-29
Author: Eve (Opus 4.7, web)
Implements: F.4 from wiring spec GL-SPC-V5-ORGAN-WIRING-EVE-20260628-26
Prereq shipped: GL-CMD-ORGANBRAIN-SILENCE-EVE-20260627-23 (both bigram speaking paths silenced)
Evidence base: GL-RPT-COGNITION-LEARN-AUDIT-C1-20260628-33 (10 call sites enumerated)
Verification target: SHA 5996c3d (audit) + current HEAD of guala-live

---

## 1. Scope

Delete the `GualaCognition` bigram model from the substrate. Per the cognition-learn audit, the bigram has no functional consumer after `say()` was silenced — `trans` / `starts` / `vocab` is pure training artifact. The only remaining reads are a boot diagnostic and an instrumentation counter, both replaceable.

This dispatch is per-site action per the audit + delete the wrapper + delete the class + delete persistence/instrumentation hooks. One single dispatch, one ship.

The five REPLACE sites (sight/sound recognition paths) are converted to write their text through v5 atlas via `_guala.read_sentence(text, source="unknown")`. This is the substrate-true path: perceptual text she's receiving from ambient input gets routed through the canonical chi-indexed atlas write, with the source weight (0.7) and dwell (1) reflecting its ambient-origin nature.

No new `SOURCE_WEIGHTS` entries are added. No new dials. The existing `"unknown"` semantic covers all five REPLACE sites — modality differentiation is captured by chi addresses and modal-chi sums in the v5 atlas write, not by source string.

---

## 2. Per-site action table

| Site | File | Line(s) | Current | Action | New |
|------|------|---------|---------|--------|-----|
| 1 | substrate_runner.py | 350 | `_cognition_learn(sent)` (curriculum + worldfeed) | DELETE | (remove line; v5 atlas already gets this via `read_sentence` immediately before) |
| 2 | substrate_runner.py | 385 | `_cognition_learn(desc)` (LLM lookup grounding) | DELETE | (remove line; v5 atlas already gets this) |
| 3 | substrate_runner.py | 911 | `_cognition_learn(_scene)` (InputRing sight YOLO) | REPLACE | `if _scene.strip(): _guala.read_sentence(_scene, source="unknown")` |
| 4 | substrate_runner.py | 927 | `_cognition_learn(" ".join(_heard))` (InputRing sound FFT) | REPLACE | `_txt = " ".join(_heard)`<br>`if _txt.strip(): _guala.read_sentence(_txt, source="unknown")` |
| 5 | substrate_runner.py | 937 | `_cognition_learn(_spoken)` (InputRing Whisper) | REPLACE | `if _spoken.strip(): _guala.read_sentence(_spoken, source="unknown")` |
| 6 | substrate_runner.py | 999 | `_cognition_learn(text)` (v7_converse user input) | DELETE | (remove line; v7 session runs its own substrate — no v5 atlas write here; wiring decision deferred to separate dispatch) |
| 6b | substrate_runner.py | 1004 | `_cognition_learn(_v)` (v7_converse reply) | DELETE | (remove line; same rationale) |
| 7 | substrate_runner.py | 2039 | `_cognition_learn(corrected_text)` (teacher correction) | DELETE | (remove line; `apply_teacher_correction` already writes v5) |
| 7b | substrate_runner.py | 2041 | `_cognition_learn(story)` (teacher correction story) | DELETE | (remove line; same rationale) |
| 8 | substrate_runner.py | 2106 | `_cognition_learn(sent)` (corpus/PDF load) | DELETE | (remove line; v5 atlas already gets this via `read_sentence` immediately before) |
| 9 | substrate_runner.py | 2383 | `_cognition_learn(_scene)` (direct sight frame) | REPLACE | `if _scene.strip(): _guala.read_sentence(_scene, source="unknown")` |
| 10 | substrate_runner.py | 2414 | `_cognition_learn(" ".join(...))` (direct sound frame) | REPLACE | `_txt = " ".join(b.get("word", "") for b in _sbind)`<br>`if _txt.strip(): _guala.read_sentence(_txt, source="unknown")` |

**Notes on REPLACE:**
- Use `source="unknown"` (existing SOURCE_WEIGHTS entry: weight 0.7, dwell 1). Do NOT add new source tags.
- Wrap each call in a non-empty check (`text.strip()` truthy) — `read_sentence` will normalize, but skipping empty input avoids a no-op tick. The min-4/max-20 gate from `_clean_sentence_for_cognition` is NOT applied — v5 salience math already filters low-quality writes (encoded_strength below ENCODE_GATE=0.15 won't promote to deep_atlas).

---

## 3. Wrapper and class deletion

Once all 12 call sites are converted:

### 3.1 Delete the wrapper

In `substrate_runner.py`:
- Delete `_clean_sentence_for_cognition` function (lines ~82-92) — only used by `_cognition_learn`.
- Delete `_cognition_learn` function (lines ~219-231).
- Delete `_clean_word` if it has no other callers (verify; it may be shared).

### 3.2 Delete the GualaCognition class and global

- Delete the `GualaCognition` class entirely from `dsf_ai_service/loom_model/loom_cognition.py`.
- If the file has no other contents, delete the file. If it does, retain the file and only delete the class.
- Delete the `_guala_cognition` global from substrate_runner.py (search for the assignment site; likely near module init).
- Delete the import of `GualaCognition` in substrate_runner.py.

### 3.3 Replace instrumentation reads

Two read sites for `_guala_cognition.vocab` per audit §"Consumers of bigram state":

- substrate_runner.py line ~804 (boot diagnostic print): delete the entire print line. Boot diagnostic for vocab size should read `len(_guala.vocab)` if a print is desired; otherwise delete.
- substrate_runner.py lines 2101 / 2121 (`organ_vocab_before` / `organ_vocab_after` in corpus load logging): replace both reads with `len(_guala.vocab)`. The field name in the log output should be updated from `organ_vocab_*` to `vocab_*` to reflect the new source (v5 engine vocab, not organ-brain vocab).

### 3.4 Boot diagnostic at line 804

The audit notes: `_guala_cognition.say('the moon')` is also called at boot for diagnostic. With `say()` silenced this returns "". Delete the boot diagnostic line entirely; it is no longer informative.

### 3.5 Persistence sweep

Search the codebase for any save/load/backup hook that writes or reads `guala_cognition` state (e.g. JSON snapshots of `trans` / `starts` / `vocab`). Likely locations:
- `substrate_runner.py` save/load handlers
- Anything in `dsf_ai_service/` that serializes bigram state

Delete the hook AND any existing state file on EFS / S3 backup paths. The state files should be removed from disk in the same deploy (c1 to confirm the path on the running task).

Surface to Eve in the report any save/load reference encountered that isn't obviously bigram-state-only — do NOT modify shared persistence code without confirmation.

---

## 4. Tests

### V1 — Code path verification

`grep -rn "_cognition_learn\|_guala_cognition\|GualaCognition\|guala_cognition" dsf_ai_service/` should return zero hits after the dispatch (except possibly in commented-out historical references; those should also be removed).

### V2 — Routing trace (sight)

Send a sight_frame via the bridge or direct endpoint with 3-5 YOLO-detectable objects in view.

Expected:
- v5 atlas vocab grows by the number of unique novel labels in the scene.
- `subject` section motif count grows by N novel labels (positional routing assigns nouns to subject).
- No bigram error; no crash; substrate stable.

### V3 — Routing trace (sound)

Send a sound_frame via the bridge with audio that contains 2-5 sensory FFT words.

Expected:
- v5 atlas vocab grows by novel sensory words ("soft", "smooth", etc.).
- `modifier` section motif count grows IF any of the words are in ROLE_DNA (currently 24-word list; most FFT words like "bright", "soft", "warm" are in ROLE_DNA so this should fire).
- `ground` section motif count grows IF any of the words are in SENSORY_DNA.

### V4 — Routing trace (v7_converse)

Call `/v7_converse` with a test sentence.

Expected:
- v7 session runs and returns its reply (unchanged behavior).
- v5 atlas does NOT see this text (intentional — v5 wiring for v7-conversed text is a separate decision).
- No crash from the now-deleted `_cognition_learn` calls.

### V5 — Substrate stability

After dispatch ships, monitor for 30 minutes:
- No new error patterns in logs related to bigram references.
- `guala_status` via bridge returns normal.
- DAYDREAMING cycles continue.
- No save/load failures.

### V6 — Vocab growth comparison (substrate baseline)

Before dispatch: record `_guala.vocab` size, atlas `n_live_bindings`, section motif counts.
After dispatch + ~30 minutes of normal traffic: re-record.

Expected:
- `_guala.vocab` grows (sight/sound paths now write).
- Section motif counts grow proportionally where ROLE_DNA / SENSORY_DNA membership permits.
- This won't fully unblock substrate density — that requires the DNA expansion and encoding formula dispatches still to come. But it should show movement in the right direction on perceptual paths that previously bypassed v5 entirely.

---

## 5. Out of scope (intentionally)

- No new SOURCE_WEIGHTS entries. Existing "unknown" used for all five REPLACE sites.
- No DNA list expansion. That is a separate dispatch (next after -34).
- No encoding formula change. That is a separate dispatch (next after -34).
- No new wiring for v7-conversed text to feed v5 atlas. Deferred to a separate decision.
- No changes to `_compose()`. It remains silenced; replacement is C.3 work.
- No changes to wC's `grounded_vocab_integration.py`. That file is permanent and untouched.

---

## 6. Rollback

If V5 (substrate stability) fails or V6 (vocab growth) shows regression rather than progress:

1. Re-pause autonomy via the bridge.
2. Revert the dispatch commit (git revert HEAD).
3. Redeploy task.
4. Report failure mode in `GL-RPT-BIGRAM-DELETE-C1-20260629-34.md` and surface to Eve.

The bigram state files do not need to be restored — they had no live consumers and their absence is the steady-state.

---

## 7. Reporting

c1 produces `GL-RPT-BIGRAM-DELETE-C1-20260629-34.md` with:

- Final list of files touched with line-number diffs.
- Result of each V1-V6 test.
- Any save/load/persistence hooks encountered with action taken or surfaced for Eve.
- Any unexpected references discovered during the deletion sweep.
- Final SHA and ECS task number.
