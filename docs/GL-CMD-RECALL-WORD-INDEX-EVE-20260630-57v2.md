# GL-CMD-RECALL-WORD-INDEX-EVE-20260630-57v2

doc_id: GL-CMD-RECALL-WORD-INDEX-EVE-20260630-57v2
Type: Implementation command
Date: 2026-06-30
Author: Eve (Opus 4.7, web)
Version: v2 (supersedes v1: callsite-update pattern replaced with single-entry-point wrapper; boot consistency check added; thread-safety stance made explicit)
Prereq: any current task (algorithmic fix, not flag-gated)

---

## 0. Why

Lock work in -52, -53, -56 solved a different problem. The /converse latency bottleneck is pure compute in a path that already runs without `self.lock`.

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

`_recall_response` (Phase 3 of `_converse_phased`, runs WITHOUT `self.lock` by design) takes 3.4 seconds for ONE input word. No lock release fixes pure compute.

Root cause: `_recall_from_atlas` (v5_engine.py:3415) and `_recall_sight_from_atlas` (L3361) both do full-atlas linear scans in Step 1:

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

~46,000 iterations per call. Called 3 times from `_recall_response` (subject/verb/object), up to 3 more times if `linked_chis` triggers second pass. `_recall_sight_from_atlas` does the same pattern twice (Step 1 builds content_chis, Step 2 scans again for sight motifs). **Up to 8 full atlas scans per /converse = ~370,000 iterations of dict access + string lowercase + comparison. At ~9-10μs/iter, that's 3.3-3.7s. Exact match to the measured 3411ms.**

Semantically the question is a reverse-index query: "which chi addresses have these specific words committed at them?" That's O(num_query_words) with a `word → set(chi)` index, not O(atlas_size).

---

## 1. Changes

### 1.1 Add `_word_to_chi_index` to engine

In `Guala.__init__` near other instance state init (around L1297 where `_deep_survival_history` is initialized):

```python
# Reverse index: lowercased word → set of chi addresses where this word
# has committed in the atlas. Maintained at every binding creation via the
# single _atlas_record entry point (see _atlas_record below). Used by
# _recall_from_atlas Step 1 and _recall_sight_from_atlas Step 1+2 to avoid
# O(atlas_size) scans. Rebuilt at boot from atlas contents.
#
# Thread safety: defaultdict[set] is not strictly atomic under concurrent
# writes, but the index is monotonic-grow and a missed update during a
# write race is substrate noise on the order of decay events. Do NOT
# wrap a lock around this; the whole point is to remove blocking compute
# from the recall path.
from collections import defaultdict
self._word_to_chi_index = defaultdict(set)
```

### 1.2 Single binding-creation entry point (CRITICAL — read carefully)

The v1 dispatch told c1 to add `_index_word_at_chi(...)` after every `atlas.record(...)` callsite. That's a source-of-truth violation: any future code that adds a binding without remembering the index update will silently break recall. Replace it with a single wrapper.

Add two methods on `Guala`:

```python
def _index_word_at_chi(self, section_name, motif_id, chi_value):
    """Add (word -> chi) mapping to the recall reverse index."""
    if section_name not in self.sections:
        return
    sec = self.sections[section_name]
    if motif_id >= len(sec.modes):
        return
    _, _, word = sec.modes[motif_id]
    if word:
        self._word_to_chi_index[word.lower()].add(chi_value)

def _atlas_record(self, section_name, motif_id, chi_value, **kwargs):
    """Single binding-creation entry point. ALL atlas.record callsites in
    engine code must go through here. Maintains the recall reverse index
    automatically. Decay paths that mutate atlas.entries[chi]['strength']
    directly do NOT go through here — they are not binding creations.
    """
    self.atlas.record(section_name, motif_id, chi_value, **kwargs)
    self._index_word_at_chi(section_name, motif_id, chi_value)
```

### 1.3 Replace engine-side `self.atlas.record(...)` callsites with `self._atlas_record(...)`

Run:

```bash
grep -rn "self\.atlas\.record(" dsf_ai_service/v5_engine.py | grep -v test_
```

For every match in v5_engine.py, rewrite `self.atlas.record(...)` as `self._atlas_record(...)`. Signature is identical (positional + kwargs), so this is a pure rename. No semantic change for the atlas; the index update is the side effect.

### 1.4 Replace runner-side `_guala.atlas.record(...)` (and similar) with `_guala._atlas_record(...)`

Run:

```bash
grep -rn "atlas\.record(" dsf_ai_service/ | grep -v "self\.atlas\.record" | grep -v test_
```

Common pattern (substrate_runner.py and similar): a caller holds an engine reference and calls `_guala.atlas.record(...)` or `engine.atlas.record(...)` directly. Rewrite as `_guala._atlas_record(...)` / `engine._atlas_record(...)`.

If any callsite does NOT have an engine reference (organ_brain_service, sensory transducers, anything called from outside the Guala instance), that callsite must be reached via the engine. If c1 finds such a callsite without an engine handle, **STOP and report it in the §4 reporting doc** — that's a structural issue separate from this dispatch and we will address it in -58.

### 1.5 Boot rebuild

In the engine's load path, at the end of whatever method restores `self.atlas` from disk (after deep_atlas, after all section loads, immediately before the engine's `Loaded:` log line emits), add:

```python
# Rebuild recall word index from atlas contents.
# Must run after self.atlas, self.sections, and all section motif tables
# are fully populated.
self._word_to_chi_index = defaultdict(set)
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

# Consistency sanity check: warn if the index looks empty when atlas is not.
# Catches "boot ran before atlas was loaded" or similar ordering bugs.
_atlas_size = len(self.atlas.entries)
if _atlas_size > 100 and _index_n_words < 10:
    print(f"[GualaLoom] WARNING: recall word index suspiciously small "
          f"(atlas={_atlas_size}, index words={_index_n_words}). "
          f"Investigate before relying on recall.")
```

One full scan at boot. Replaces millions of scans during runtime.

### 1.6 Replace `_recall_from_atlas` Step 1

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

### 1.7 Replace `_recall_sight_from_atlas` Step 1

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

### 1.8 Replace `_recall_sight_from_atlas` Step 2

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
- Response content non-empty and substantively similar to pre-fix output (algorithm semantically equivalent, only faster)

### T2 — /converse latency under load (user-visible gate)

10 /converse calls spaced 1s apart:
- ≥9 of 10 return within 3s
- No "substrate unreachable" responses
- No 25s timeouts

### T3 — Index correctness (post-boot, no traffic)

Immediately after deploy, before any /converse calls:
- Boot logs include the new line: `[GualaLoom] Recall word index rebuilt: N words, M entries`
- N (words) is on the order of vocab (~13,895) — within 10% is fine, exact match not required because not every word has a live atlas binding
- M (entries) > 1000
- No `[GualaLoom] WARNING: recall word index suspiciously small` line

### T4 — Index correctness (post-traffic)

After 5 minutes of normal traffic post-deploy:
- Spot-check from a Python shell or debug endpoint: `len(_guala._word_to_chi_index)` is ≥ T3's N
- Spot-check: `_word_to_chi_index["moon"]` returns a non-empty set
- No KeyError, no exceptions in logs

### T5 — Output equivalence

5 /converse calls with the same inputs as a pre-fix sample (use any 5 sentences from yesterday's converse logs on :394). Recalled responses should be substantively equivalent — same word selection in the recall result. The algorithm is unchanged semantically; only the lookup mechanism differs. Substantive divergence in word selection = a missed callsite or an index bug.

### T6 — Wrapper-coverage check

After deploy + 5 min normal traffic, grep the running container's code:

```bash
docker exec <task> grep -rn "self\.atlas\.record(" /app/dsf_ai_service/ 2>/dev/null | grep -v _atlas_record
docker exec <task> grep -rn "_guala\.atlas\.record(" /app/dsf_ai_service/ 2>/dev/null
docker exec <task> grep -rn "engine\.atlas\.record(" /app/dsf_ai_service/ 2>/dev/null
```

All three should return zero lines. Any hit = a missed callsite that needs conversion to the wrapper. Report it.

---

## 3. Rollback

`git revert HEAD` removes the wrapper, the index, and restores old recall paths. No state migration needed — the index is in-memory only, rebuilt from atlas at every boot. Atlas data is not touched by this change.

---

## 4. Reporting

c1 produces `GL-RPT-RECALL-WORD-INDEX-C1-20260630-57v2.md` with:

- Diff summary: engine init, `_index_word_at_chi`, `_atlas_record` wrapper, count of engine-side callsites converted (§1.3), count of runner-side callsites converted (§1.4), boot rebuild, three recall-path replacements (§1.6-1.8)
- If §1.4 found any atlas.record callsites without an engine reference: list them with file:line, do not block ship
- T1: converse_timing event post-fix with actual recall_ms number
- T2: 10 /converse latencies
- T3: boot log line, word count, entry count, warning-line presence/absence
- T4: post-traffic spot checks
- T5: pre/post response samples side-by-side
- T6: grep results (should be empty)
- Final SHA, task number

---

## 5. Out of scope

- `emit_ms` (1366ms in current timing). Next bottleneck after recall lands. Investigate after this is verified — likely `_grandurun_select_candidates` with `RICH_SENSORY_INPUT=1` doing its 501ms stage1, OR dynamics settling using its 1.5s budget. Will dispatch as -58.
- Other O(atlas_size) iterations in the codebase. Full audit after this lands.
- Any further lock work. Locks are not the bottleneck.
- Decay paths that mutate `atlas.entries[chi]["strength"]` directly. These are not binding creations and do not need wrapping.

---

End.
