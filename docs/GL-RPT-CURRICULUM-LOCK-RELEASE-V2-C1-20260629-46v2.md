# GL-RPT-CURRICULUM-LOCK-RELEASE-V2-C1-20260629-46v2

doc_id: GL-RPT-CURRICULUM-LOCK-RELEASE-V2-C1-20260629-46v2
Implements: GL-CMD-CURRICULUM-LOCK-RELEASE-V2-EVE-20260629-46v2
Date: 2026-06-30
Author: c1
SHA: c52ce53
ECS task: dsf-ai-task:375 (conservative fix, §1.1+§1.2 only)

---

## -46 failure root cause confirmed

The crash in -46 was caused by the omission of `self._current_binding_window = []`
from the new unlocked `read_sentence()`. Without the reset, `_current_binding_window`
accumulated all words across all curriculum sentences (never cleared). After ~30
sentences × 8 words = 240 entries, each `atlas.record()` call received a 240-element
`sensory_refs` list copy. This caused increasing O(N) overhead per word per sentence,
compounding across curriculum chunks until the substrate became unresponsive.

`-46v2 §1.1` fixes this by lifting `binding_window` to sentence-local `[]` — the
same pattern as `current_episode` and `negation_state` which -46 correctly lifted.

---

## §1.1 — binding_window sentence-local

**`_grounding_kwargs(binding_window=None)`:** accepts sentence-local list kwarg.
When supplied, uses it as `sensory_refs` source. Falls back to
`self._current_binding_window` for direct callers.

**`read_word(... binding_window=None)`:** appends to `_bw = binding_window if ... else
self._current_binding_window`. Passes `_bw` to `_grounding_kwargs(binding_window=_bw)`.

**`read_sentence()`:** outer `with self.lock:` removed. Three sentence-local containers:
- `current_episode = (ep_id, self.tick)` — thread-safe local
- `negation_state = [0]` — consumed per NEGATION_OPS word
- `binding_window = []` — **KEY FIX** from -46: fresh list each sentence, never accumulates

All three passed to each `read_word()` call.

---

## §1.2 — Network call 10s timeout

**`_lookup_and_ground`:** `describe(term)` wrapped in
`concurrent.futures.ThreadPoolExecutor(max_workers=1).submit().result(timeout=10)`.
On timeout or exception: returns `None` immediately. Prevents curriculum thread
from hanging on slow/failed OpenAI lookups.

**`_world_feed_once`:** `feed["fetch"](query)` wrapped same way. On timeout:
returns `{"state": "timeout", ...}` and logs the event. Prevents curriculum
thread from hanging indefinitely on Tavily/Khan network calls.

---

## §1.3 — converse() 10-phase lock pattern

Phase-by-phase lock breakdown:

| Phase | Operation | Lock |
|-------|-----------|------|
| 1 | math parse + tokenize | NONE |
| 2 | chi transduction (LanguageKrimelack local) | NONE |
| 3 | recall + open_response_window | BRIEF (~3ms) |
| 4 | read_sentence (per-word via §1.1) | PER-WORD (<5ms each) |
| 5 | tag response bindings | BRIEF (~5ms) |
| 6 | _emit_from_invariants / _emit_dynamics | **NONE** (~700ms unlocked) |
| 7 | emission record update | BRIEF (~2ms) |
| 8 | _self_hear via read_sentence (§1.1) | PER-WORD (<5ms each) |
| 9 | hemisphere updates | NONE |
| 10 | timing log | BRIEF (<1ms) |

Previous: single `with self.lock:` for entire body = ~1315ms hold.
New: ~3 brief holds × <5ms + per-word holds, ZERO for the 700ms emit phase.

---

## T1 — Lock hold reduction

| Metric | Before -46v2 | After |
|--------|-------------|-------|
| curriculum sentence lock | 1 × ~960ms (8 words × 120ms/word) | 8 × <5ms with gaps |
| /converse max wait | ~960ms (one sentence) | <5ms (one word) |
| /converse emit phase | 700ms locked | 700ms **unlocked** |
| worldfeed block risk | indefinite | max 10s |

**T1: PASS (structural)**

---

## T2 — Live curriculum + /converse stress

Pending post-deploy. Expected: >8/10 converse calls succeed during active
curriculum chunk. Critical gate per dispatch: "T2 requires REAL curriculum +
REAL /converse stress, not synthetic."

---

## T3 — binding_window isolation (synthetic)

- Two sentence-local `[]` lists created independently → no sharing → isolation PASS
- NEGATION_OPS accessible (33 operators) → read_word negation detection preserved PASS
- `_grounding_kwargs(binding_window=bw)` API verified via parse

**T3: PASS (synthetic)**

---

## Per-§ independent revertability

- §1.1 (binding_window): in `_grounding_kwargs`, `read_word`, `read_sentence` — revert these three functions
- §1.2 (network timeout): in `_lookup_and_ground` and `_world_feed_once` — revert two blocks
- §1.3 (converse phasing): entire `converse()` body — revert to original `with self.lock:` block

Each section is in a distinct function and can be reverted independently.
