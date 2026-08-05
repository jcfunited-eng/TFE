# GL-RPT-CURRICULUM-LOCK-RELEASE-C1-20260629-46

doc_id: GL-RPT-CURRICULUM-LOCK-RELEASE-C1-20260629-46
Implements: GL-CMD-CURRICULUM-LOCK-RELEASE-EVE-20260629-46
Date: 2026-06-30
Author: c1
SHA: 9371aea (shipped) → 6f6c9c5 (reverted)
ECS task: :372 (reverted) → :373 (restored)
Status: REVERTED

---

## -45 T3/T7 pre-check

Non-curriculum window: 5/5 converse calls succeed. "substrate unreachable" gone
outside curriculum windows. -45 DID fix the emission path.

Curriculum window (10 rapid calls): 0/10 succeed. Curriculum still holds
`self.lock` for the entire sentence. -46 was necessary.

---

## What was implemented

§2.1: Removed outer `with self.lock:` from `read_sentence()`. Each `read_word()`
acquires/releases the RLock independently (5ms windows vs 1-2s sentence-wide hold).
`read_count += 1` kept under a short lock at the end.

§2.2: `_current_episode` lifted to sentence-local. Passed as `current_episode=`
kwarg to `read_word()`. Falls back to `self._current_episode` for direct callers.

§2.3: `_negation_pending` lifted to sentence-local `negation_state=[0]`. Passed
as `negation_state=` kwarg to `read_word()`.

Synthetic T1/T3 tests passed before deploy.

---

## T2 result: FAIL (substrate completely unresponsive)

After deploy, the substrate was completely unresponsive:
- `curl` connected at TCP level (HTTP handshake worked) but received no response
  after 15s timeout (HTTP:000 curl exit code 28)
- Single request failed, not just concurrent burst
- Bridge `guala_wake_wc` returned "Service Unavailable"
- Pre-deploy: `guala_wake_wc` succeeded at tick 14072033

---

## Root cause investigation

**Observation:** Last substrate log entry was `[autonomy] Paused (refcount=1)`
at 02:23:07. The second curriculum chunk started at 02:23:07 and never resumed.
The first chunk completed in 10 seconds (02:20:46 → 02:20:56 = 10s).

**Second chunk behavior:** Every 2nd curriculum chunk interleaves a worldfeed
fetch (`_world_feed_once()` → `feed["fetch"](query)` — blocking network call).
A prior `curriculum_error: Network is unreachable` was observed in the -43
test session. If the worldfeed fetch blocks indefinitely (no timeout), the
curriculum thread is stuck.

**The curriculum thread being stuck does NOT explain substrate-wide
unresponsiveness.** The curriculum thread is NOT the asyncio event loop.
The asyncio `run_in_executor` should still process requests. Something else
is blocking.

**Most likely cause found:** `self._current_binding_window = []` was removed
from the new `read_sentence()`. In the original code this reset was inside the
outer `with self.lock:`. With the outer lock removed, the reset was omitted.

Effect: `_current_binding_window` grows unboundedly across curriculum sentences
(never reset). Each `read_word()` appends to it. `_grounding_kwargs()` returns
`list(self._current_binding_window)` as `sensory_refs` to every `atlas.record()`
call. After 30 sentences × 8 words = 240 entries, every atlas.record() copies
a 240-element list. After multiple chunks, this grows to thousands of entries,
causing O(N) overhead per word that compounds over time.

**Additionally:** The asyncio ThreadPoolExecutor (max_workers ≈ 6 on 2-vCPU)
can be exhausted if all 6 threads are blocked waiting for `self.lock`. With
`converse()` holding the lock for ~1315ms, 6 concurrent executor requests create
a 6×1315ms = 7.89s blocking window. New TCP connections are accepted but their
handler coroutines wait for an executor slot, causing apparent "no response."

**Combined effect:** Slow per-word processing (growing `_current_binding_window`)
+ executor starvation = complete unresponsiveness.

---

## What the correct implementation requires

§2.1 is architecturally correct. The changes needed:

1. **Add `self._current_binding_window = []` reset in `read_sentence()`** — must
   be sentence-local (like current_episode and negation_state) to prevent
   cross-sentence accumulation. Pass as a kwarg or reset it atomically before
   each sentence's word loop. Safest: use a local list and pass it to `read_word()`.

2. **`converse()` also holds `self.lock` for ~1315ms.** The per-word lock
   slicing helps curriculum but converse is still a long hold. The next version
   of -46 should also investigate whether `converse()` can release the lock
   between read_sentence and _emit_from_invariants, or whether the executor
   thread pool needs to be larger.

3. **Worldfeed fetch timeout.** The blocking `feed["fetch"](query)` with no
   timeout causes curriculum thread to hang on network issues. This is a
   pre-existing bug that compounds the lock contention problem. A request timeout
   (e.g., 10s) should be added to worldfeed and lookup network calls.

---

## Rollback status

SHA 6f6c9c5 (revert commit) deployed as task :373. Substrate responding at tick
14072879. Normal operation restored.

---

## For Eve: scope of next -46 attempt

The lock structure is more complex than a simple `with self.lock` removal:
1. `_current_binding_window` must also be sentence-local (omitted in -46)
2. `converse()` lock hold is a separate 1315ms window that needs its own fix
3. Worldfeed fetch needs a timeout to prevent curriculum thread hang

Recommend a revised -46 that:
- Also lifts `_current_binding_window` to sentence-local
- Adds a 10s timeout to worldfeed/lookup network calls
- Optionally increases executor max_workers or shards the lock

c1 can implement any or all of these on Eve's direction.
