# GL-CMD-RECALL-WORD-INDEX-EVE-20260630-57v1

doc_id: GL-CMD-RECALL-WORD-INDEX-EVE-20260630-57v1
Type: Implementation command
Date: 2026-06-30
Author: Eve (Opus 4.7, web)
Version: v1
Prereq: any current task (algorithmic fix, not flag-gated)

---

## 0. Why

The lock work in -52, -53, -56 was real but solved a different problem. The actual /converse latency bottleneck is pure compute in a path that already runs without self.lock.

Evidence from c1's `converse_timing` event on task :394:

```
chi_ms:       0.1
recall_ms:    3411.7   ← THIS
read_ms:      313.7
tag_ms:       224.2
emit_ms:      1366.4
selfhear_ms:  186.0
hemi_ms:      180.9
total_ms:     5683.1
n_words:      1
phased:       true
```

For ONE input word, `_recall_response` (Phase 3 of `_converse_phased`, runs WITHOUT self.lock by design) takes 3.4 seconds. No amount of lock-releasing fixes pure compute.

Root cause: `_recall_from_atlas` (v5_engine.py:3415) and `_recall_sight_from_atlas` (L3361) both do full-atlas linear scans in their Step 1:

```python
# L3448-3457 in _recall_from_atlas:
for chi, entries in self.atlas.entries.items():      # ~15,505 entries
    for e in entries:                                 # ~3 bindings each
        if e["section"] in self.sections:
            other_sec = self.sections[e["section"]]
            if e["motif"] < len(other_sec.modes):
                _, _, motif_word = other_sec.modes[e["motif"]]
                if motif_word and motif_word.lower() in content_words:
                    content_word_chis.add(chi)
```

~46,000 iterations per call. Called 3 times from `_recall_response` (subject/verb/object), up to 3 more times if `linked_chis` triggers second pass. Plus `_recall_sight_from_atlas` does the same pattern twice (Step 1 L3379 builds content_chis, Step 2 L3395 scans again for sight motifs). **Up to 8 full atlas scans per /converse = ~370,000 iterations of dict access + string lowercase + comparison. At ~9-10μs/iter, that's 3.3-3.7s. Exact match.**

The semantic question is a reverse-index query: "which chi addresses have these specific words committed at them?" That's O(num_query_words) with a `word → set(chi)` index, not O(atlas_size).

---

## 1. Changes

### 1.1 Add `_word_to_chi_index` to engine

In `Guala.__init__` near other instance state init (around L1297 where `_deep_survival_history` is initialized):

```python
# Reverse index: lowercased word → set of chi addresses where this word
# has committed in the atlas. Maintained incrementally via _index_word_at_chi
# after every atlas.record() call. Used by _recall_from_atlas Step 1 and
# _recall_sight_from_atlas Step 1 to avoid O(atlas_size) scans.
# Rebuilt at boot from atlas contents.
from collections import defaultdict
self._word_to_chi_index = defaultdict(set)
```

### 1.2 Helper for incremental maintenance

Add a method on Guala:

```python
def _index_word_at_chi(self, section_name, motif_id, chi_value):
    """Add (word -> chi) mapping to the recall reverse index.
    Called after every atlas.record() invocation in engine paths."""
    if section_name not in self.sections:
        return
    sec = self.sections[section_name]
    if motif_id >= len(sec.modes):
        return
    _, _, word = sec.modes[motif_id]
    if word:
        self._word_to_chi_index[word.lower()].add(chi_value)
```

### 1.3 Wire `_index_word_at_chi` at every atlas.record() call site

Grep:
```bash
grep -rn "atlas\.record(" dsf_ai_service/ | grep -v test_
```

For each call site, identify section_name, motif_id, chi_value (named or positional) and add `_index_word_at_chi(...)` immediately after. The atlas.record signature is:
```python
atlas.record(section_name, motif_id, chi_value, tick=None, salience=1.0, ...)
```

Most callsites in v5_engine.py use positional or named args making the values unambiguous. For callsites in substrate_runner.py (e.g. `_bind_sensory_words`), the index update goes through the engine reference (`_guala._index_word_at_chi(...)`).

### 1.4 Boot rebuild

In the load path (after atlas restoration completes, near where deep_atlas finishes loading and just before `Loaded:` log line emits), add:

```python
# Rebuild recall word index from atlas contents
self._word_to_chi_index = defaultdict(set)
_index_n_words = 0
_index_n_chis = 0
for chi_k, entries in self.atlas.entries.items():
    for e in entries:
        sec_name = e.get("section", "")
        if sec_name in self.sections:
            sec = self.sections[sec_name]
            mid = e.get("motif", 0)
            if mid < len(sec.modes):
                _, _, word = sec.modes[mid]
                if word:
                    self._word_to_chi_index[word.lower()].add(chi_k)
                    _index_n_chis += 1
_index_n_words = len(self._word_to_chi_index)
print(f"[GualaLoom] Recall word index rebuilt: {_index_n_words} words, {_index_n_chis} entries")
```

One full scan at boot. Replaces millions of scans during runtime.

### 1.5 Replace `_recall_from_atlas` Step 1

v5_engine.py L3448-3460:

```python
# OLD:
content_word_chis = set()
for chi, entries in self.atlas.entries.items():
    for e in entries:
        if e["section"] in self.sections:
            other_sec = self.sections[e["section"]]
            if e["motif"] < len(other_sec.modes):
                _, _, motif_word = other_sec.modes[e["motif"]]
                if motif_word and motif_word.lower() in content_words:
                    content_word_chis.add(chi)

if not content_word_chis:
    return None
```

```python
# NEW:
content_word_chis = set()
for w in content_words:
    content_word_chis.update(self._word_to_chi_index.get(w, ()))

if not content_word_chis:
    return None
```

### 1.6 Replace `_recall_sight_from_atlas` Step 1

v5_engine.py L3379-3391:

```python
# OLD:
for chi_k, entries in self.atlas.entries.items():
    for e in entries:
        sec_name = e.get("section", "")
        if sec_name in self.sections:
            sec = self.sections[sec_name]
            mid = e.get("motif", 0)
            if mid < len(sec.modes):
                _, _, w = sec.modes[mid]
                if w and w.lower() in content:
                    content_chis.add(chi_k)

if not content_chis:
    return []
```

```python
# NEW:
for w in content:
    content_chis.update(self._word_to_chi_index.get(w, ()))

if not content_chis:
    return []
```

### 1.7 Replace `_recall_sight_from_atlas` Step 2

v5_engine.py L3394-3401 (the second full-atlas scan):

```python
# OLD:
sight_motif_ids = set()
for chi_k, entries in self.atlas.entries.items():
    for target_chi in content_chis:
        if abs(chi_k - target_chi) <= 2:
            for e in entries:
                if e.get("section") == "sight":
                    sight_motif_ids.add(e.get("motif"))
```

```python
# NEW (direct neighborhood lookup):
sight_motif_ids = set()
for target_chi in content_chis:
    for d in range(-2, 3):
        for e in self.atlas.entries.get(target_chi + d, []):
            if e.get("section") == "sight":
                sight_motif_ids.add(e.get("motif"))
```

For ~10 content_chis: 5 × 10 = 50 dict lookups instead of 15,505 × 10 = 155,050 iterations.

---

## 2. Tests

### T1 — Recall latency (THE gate)

Send a single /converse with text "hello" and capture the next `converse_timing` event.

**PASS:**
- `recall_ms` < 100 (was 3411)
- `total_ms` < 2000 (was 5683)
- Response content non-empty and substantively similar to pre-fix output (same word selection — algorithm semantically equivalent, only faster)

### T2 — /converse latency under load (user-visible gate)

10 /converse calls spaced 1s apart:
- ≥9 of 10 return within 3s
- No "substrate unreachable" responses
- No 25s timeouts

### T3 — Index correctness

After 5 minutes of normal traffic post-deploy:
- `len(_word_to_chi_index)` matches vocab order (~13,895)
- Spot-check: pick a known word ("moon"), verify `_word_to_chi_index["moon"]` contains the expected chi addresses
- No KeyError, no exceptions

### T4 — Boot rebuild correctness

After restart:
- Boot logs include the new line: `[GualaLoom] Recall word index rebuilt: N words, M entries`
- `len(_word_to_chi_index)` > 0 immediately after boot

### T5 — Output equivalence

5 /converse calls with the same inputs as pre-fix samples. Recalled responses should be substantively equivalent — algorithm is unchanged semantically.

---

## 3. Rollback

`git revert HEAD` removes the index, restores old recall paths. No state migration needed — the index is in-memory only, rebuilt from atlas at every boot.

---

## 4. Reporting

c1 produces `GL-RPT-RECALL-WORD-INDEX-C1-20260630-57v1.md` with:

- Diff summary: engine init, helper method, atlas.record() callsite updates, boot rebuild, _recall_from_atlas Step 1, _recall_sight_from_atlas Step 1 and Step 2
- T1: converse_timing event post-fix with the actual recall_ms number
- T2: 10 /converse latencies
- T3: index correctness
- T4: boot rebuild verified
- T5: output equivalence
- Final SHA, task number

---

## 5. Out of scope

- emit_ms (1366ms in current timing). Next bottleneck after recall lands. Likely candidate: `_grandurun_select_candidates` with RICH_SENSORY_INPUT=1 doing its 501ms stage1, OR dynamics settling using its 1.5s budget. Investigate after this lands.
- Other O(atlas_size) iterations in the codebase. Audit after this lands.
- Any further lock work. Locks are not the bottleneck.

---

End.
