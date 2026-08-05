# GL-RPT-HOTLANE-DIET-C1-20260703-102-v1

doc_id: GL-RPT-HOTLANE-DIET-C1-20260703-102-v1
From: c1b | To: Eve | Executing: GL-CMD-HOTLANE-DIET-EVE-20260703-102-v1
Status: BUILT — G-102-1 through G-102-3 require post-deploy measurement window.

## Failures first

None at build time. All gates require a live measurement window post-deploy.
All NOT MEASURED gates are explicitly labelled.

---

## §1. deep_survival_history → guala_survival.json

### Touch points

**`dsf_ai_service/v4/gualaloom_v5_engine.py` — `save_hot_state()` (L~5905–6007)**

- Removed `_surv_snap = dict(self._deep_survival_history)` under lock
  (was the expensive shallow-copy that dragged the lock and produced the
  41 MB block in the hot core write).
- `snap_core["data"]["deep_survival_history"]` remains `None` — backward-
  compat field preserved; readers that expect the key won't KeyError.
- Outside-lock `surv_ser` construction block removed entirely.
- No write of survival data in hot save path. Hot core drops to ~150 KB.

**`dsf_ai_service/v4/gualaloom_v5_engine.py` — `save_full_state()` (L~6226–6251)**

- `_surv_snap = dict(self._deep_survival_history)` kept under lock (cold
  save still needs the snapshot).
- Outside lock: `surv_ser` built as before; assigned to new
  `snap_survival = self._envelope({"deep_survival_history": surv_ser})`.
- `snap_core["data"]["deep_survival_history"]` left as `None` — the field
  no longer carries data in core; the cold file is authoritative.
- `("guala_survival.json", snap_survival)` added to writes list after
  `guala_deep_atlas.json`, before `guala_bucket.json`. Non-critical:
  a failure here does not prevent `_last_save_tick` from advancing.

**`dsf_ai_service/v4/gualaloom_v5_engine.py` — `load_full_state()` (L~6542–6565)**

- After deep atlas load block, new survival load sequence:
  1. Try `guala_survival.json`: if present, parse and rebuild
     `_deep_survival_history`; log line:
     `[GualaLoom] Survival history loaded from guala_survival.json: N entries`
  2. Else: `_deep_survival_history` already set by `_apply_core()` from
     core.json's `deep_survival_history` field (backward-compat fallback);
     log line confirms fallback path and entry count.
- First deploy after migration: no `guala_survival.json` on EFS, so
  boot falls back to core.json's field. First cold save writes
  `guala_survival.json`; subsequent boots use the new file.

**`dsf_ai_service/save_coordinator.py` — S3 backup list (L~128–135)**

- `"guala_survival.json"` added to `all_files`. The `os.path.exists`
  guard means first deploy (no file yet) uploads silently skip it.

---

## §2. Vocab-regression guard diet

### Previous path

Both `save_hot_state()` and `save_full_state()` read `guala_core.json`
(previously 41.6 MB) to load the `vocab` list and measure its length.
At 41.6 MB, each guard check was a full JSON parse of the dominant file.

### New path

Guard now reads `guala_bucket.json` (~1 KB) and reads the `vocab_count`
integer field.

**`save_hot_state()` guard (L~5988–6006):**
```python
bucket_path = os.path.join(state_dir, "guala_bucket.json")
if os.path.exists(bucket_path):
    _existing_vocab = _bkt.get("data", _bkt).get("vocab_count")
    if _existing_vocab is not None:
        _existing_vocab = int(_existing_vocab)
        if _existing_vocab > 100 and snap_vocab_len < _existing_vocab * 0.5:
            [ABORT HOT SAVE]
```

**`save_full_state()` guard (L~6203–6224):**
Same structure; on abort raises RuntimeError (existing discipline).

**`snap_bucket` in both paths:**
```python
snap_vocab_len = len(self.vocab)
snap_bucket = self._envelope({"removed": True, "vocab_count": snap_vocab_len})
```
`snap_vocab_len` now computed before `snap_bucket` so the field is
available. Ordering inside lock verified: `snap_vocab_len` set, then
`snap_bucket` constructed immediately after.

**Fallback (first deploy cycle post-migration):** if `guala_bucket.json`
has no `vocab_count` field (pre-migration bucket file on EFS), guard
returns `None` and is skipped. No regression risk: the survival history
move does not alter vocab.

---

## §3. F8 classification — deep_survival_history

### Structure

```python
self._deep_survival_history = defaultdict(list)
# key: (chi_k: int, section: str, motif: int)
# value: list of strength floats, list capped at 10 (trimmed when > 20)
```

### Growth mechanism

Keys are added during the dream cycle in `dream_promotion_gate()`
(deep_atlas.py L254). For every working atlas entry that passes the
survival gate or episodic gate, the key `(chi_k, section, motif)` is
written to `_deep_survival_history`. The append happens once per dream
cycle per binding; if the list grows beyond 20 entries it is trimmed to
the last 10.

### Boundedness analysis

**Values per key:** BOUNDED. List capped at 10 (trim-to-10 when > 20).
Max value contribution per key: 10 floats × 8 bytes = 80 bytes.

**Key count:** UNBOUNDED. A key is added whenever a (chi, section, motif)
triple is first observed in the working atlas during a dream cycle. The
working atlas decays and prunes entries below FORGETTING_THRESHOLD, but
`_deep_survival_history` has no corresponding key-pruning step: stale
keys (for chi/section/motif triples that have left the working atlas and
will never be promoted again) persist indefinitely. As the engine runs,
new vocabulary is learned, new (chi, section, motif) combinations are
generated, and the key set grows monotonically.

Observed size: 41.5 MB serialized, 99.6% of guala_core.json, at 3753
deep entries generating O(entries × band_width × sections) survival
history keys.

### Verdict: **VIOLATION** — patient #5 pattern (append-forever key set)

The value lists are bounded by physics (cap at 10). The key set is
not bounded by any physics law or decay process: it grows with the
deep atlas population over time. This is the patient #5 append-forever
pattern applied to dictionary keys rather than list entries.

**No physics change rides this dispatch** (per CMD §3). The VIOLATION is
classified here; the key-pruning fix is a separate dispatch.

**Migration note:** After `guala_survival.json` is live, the 41.5 MB
block is no longer in the hot save path. The cold file will still be
41.5 MB until a key-pruning fix is deployed, but this does not affect
hot save latency (guala_core.json will be ≤200 KB after first hot save).

---

## Gates

G-102-1  NOT MEASURED — hot save <5s sustained over 2h window.
         Log line: `[save-hot] <T>s core=<T>s compact=<T>s`. Core <T>
         should drop from ~12s (dominated by surv_ser) to <1s.

G-102-2  NOT MEASURED — boot log must contain:
         `[GualaLoom] Survival history loaded from guala_survival.json: N entries`
         and N must match `_deep_survival_history` key count from pre-deploy
         introspect (count-diff within ±1%).

G-102-3  NOT MEASURED — `guala_core.json` size ≤ 200 KB in first hot save
         after deploy. Before: 41.6 MB. After: ~150 KB (vocab + gauges +
         sensory state; no survival block).

---

### Changelog
- v1 (2026-07-03, c1b): first filed version. All gates NOT MEASURED —
  require post-deploy measurement window. F8: VIOLATION classified.
- v1.1 (2026-07-03, c1b): backward-compat field value changed None → {}
  in both save paths. A pre-102 rollback calls core.get("deep_survival_history",
  {}).items() — None.items() crashes; {} is safe (empty history on rollback boot).
