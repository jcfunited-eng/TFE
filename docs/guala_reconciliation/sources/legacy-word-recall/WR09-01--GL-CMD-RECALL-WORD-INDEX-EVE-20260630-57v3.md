# GL-CMD-RECALL-WORD-INDEX-EVE-20260630-57v3

doc_id: GL-CMD-RECALL-WORD-INDEX-EVE-20260630-57v3
Type: Implementation command (amendment to v2)
Date: 2026-06-30
Author: Eve (Opus 4.7, web)
Version: v3 (supersedes v2: line numbers corrected to actual repo state; wrapper conversion scope pinned with exact paths; loom_model atlases explicitly excluded)
Repo verified: `jcfunited-eng/TFE` branch `codex/persistent-etl-update-20260326`
Prereq: any current task (algorithmic fix, not flag-gated)

---

## 0. Why v3

v2 had two real bugs caught on direct repo read:

**(a) Wrong line numbers.** v2 quoted v5_engine.py:3415 for `_recall_from_atlas` and L3361 for `_recall_sight_from_atlas`. Actual file is `dsf_ai_service/v4/gualaloom_v5_engine.py` (5433 lines). Real locations are L2803 and L2749. The code snippets in v2 match exactly, so grep finds the right code, but the line numbers were misleading.

**(b) Wrapper grep scope too broad.** v2 §1.4 said `grep -rn "atlas\.record(" dsf_ai_service/ | grep -v "self\.atlas\.record" | grep -v test_`. That grep hits `loom_model/embryo.py` and `loom_model/neuron.py`, which use per-neuron `binding_atlas` and `chi_atlas` objects with completely different `.record()` signatures. Converting them breaks the build.

v3 fixes both. Everything else from v2 (the algorithm, the wrapper pattern, the boot rebuild, the tests) stands unchanged — re-read v2 §0 (Why), §1.1 (init), §1.2 (wrapper methods), §1.5 (boot rebuild), §1.6/§1.7/§1.8 (recall replacements), §2 (tests), §3 (rollback), §4 (reporting), §5 (out of scope). v3 only overrides §1.3 and §1.4.

---

## 1. Corrected scope (overrides v2 §1.3 and §1.4)

### 1.3 Engine-side wrapper conversion (11 callsites)

In `dsf_ai_service/v4/gualaloom_v5_engine.py`, convert every `self.atlas.record(...)` to `self._atlas_record(...)`. The 11 callsites are at lines:

```
1335, 3331, 3437, 3477, 3501, 3540, 3580, 3859, 3880, 3951, 3984
```

Pure rename, signature unchanged. Verify after edit:

```bash
grep -c "self\._atlas_record(" dsf_ai_service/v4/gualaloom_v5_engine.py   # should be 11
grep -c "self\.atlas\.record("   dsf_ai_service/v4/gualaloom_v5_engine.py   # should be 0
```

### 1.4 Runner-side wrapper conversion (12 callsites across 3 files)

In each of the files listed, convert `_guala.atlas.record(...)` → `_guala._atlas_record(...)` and `guala.atlas.record(...)` → `guala._atlas_record(...)`. Pure rename, signature unchanged.

**`dsf_ai_service/substrate_runner.py`** — 4 sites at lines `764, 835, 860, 893` (pattern `_guala.atlas.record(`)

**`dsf_ai_service/app.py`** — 6 sites at lines `1688, 1722, 1738, 1775, 1814, 1897` (pattern `_guala.atlas.record(`)

**`dsf_ai_service/substrate/grounded_vocab_integration.py`** — 2 sites at lines `122, 196` (pattern `guala.atlas.record(`)

Verify after edit:

```bash
grep -rn "atlas\.record(" dsf_ai_service/ \
  | grep -v "_atlas_record" \
  | grep -v "self\.atlas\.record" \
  | grep -v "loom_model" \
  | grep -v "test_"
```

Should return zero lines.

### 1.4a OUT OF SCOPE — DO NOT TOUCH

These are different atlas objects entirely (per-LoomNeuron `binding_atlas` and `chi_atlas`), with different `.record()` signatures. Converting them WILL break the build:

```
dsf_ai_service/loom_model/embryo.py:333    n.binding_atlas.record(...)
dsf_ai_service/loom_model/embryo.py:342    n.binding_atlas.record(...)
dsf_ai_service/loom_model/embryo.py:406    n.binding_atlas.record(...)
dsf_ai_service/loom_model/neuron.py:571    self.chi_atlas.record(...)
dsf_ai_service/loom_model/neuron.py:787    self.binding_atlas.record(...)
dsf_ai_service/loom_model/tests/test_cognition_path.py:43  atlas.record(...)
dsf_ai_service/loom_model/tests/test_cognition_path.py:74  atlas.record(...)
```

Leave these alone. They do not touch the engine's word-grounded chi atlas (`self.atlas` on `Guala`). They serve the LoomNeuron architecture and use different argument shapes (concept + state_vec + tick), not section + motif_id + chi_value.

### 1.5 Boot rebuild placement (clarification on v2)

In `dsf_ai_service/v4/gualaloom_v5_engine.py`, find the engine's `load` / `_restore_from_save` / `from_save` method (whichever name is current) and place the rebuild block from v2 §1.5 at the end of that method, after `self.atlas`, `self.sections`, and all section motif tables are fully populated, just before the existing `[GualaLoom] Loaded:` log line emits.

If c1 cannot locate the existing `Loaded:` log line, search:

```bash
grep -n "Loaded" dsf_ai_service/v4/gualaloom_v5_engine.py | head
```

---

## 2. Re-targeted T6 (replaces v2 §2 T6)

After deploy + 5 min normal traffic, run on the live container:

```bash
docker exec <task> grep -rn "atlas\.record(" /app/dsf_ai_service/ 2>/dev/null \
  | grep -v "_atlas_record" \
  | grep -v "self\.atlas\.record" \
  | grep -v "loom_model" \
  | grep -v "test_"
```

PASS = zero lines. Any hit = a missed callsite. Report it.

Loom_model and test_ filtering is structural — those are not in scope.

---

## 3. Everything else from v2 unchanged

§1.1 (engine init `_word_to_chi_index`), §1.2 (`_index_word_at_chi` + `_atlas_record` wrapper methods), §1.5 (boot rebuild code block), §1.6 (`_recall_from_atlas` Step 1 replacement), §1.7 (`_recall_sight_from_atlas` Step 1 replacement), §1.8 (`_recall_sight_from_atlas` Step 2 replacement), §2 T1–T5 (gates), §3 (rollback), §4 (reporting format), §5 (out of scope).

T1 remains the gate: `recall_ms < 100`, `total_ms < 2000`.

---

## 4. Reporting (additional fields on top of v2 §4)

c1's report doc renames to `GL-RPT-RECALL-WORD-INDEX-C1-20260630-57v3.md` and adds:

- Engine-side conversion: count expected 11, count produced (must match)
- Runner-side conversion per file: substrate_runner.py (4), app.py (6), grounded_vocab_integration.py (2) — counts produced
- loom_model untouched: confirm by `grep -c "binding_atlas\.record\|chi_atlas\.record" dsf_ai_service/loom_model/`
- T6 grep output (must be empty)

---

End.
