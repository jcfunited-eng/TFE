# GL-BRIEF-SLEEP-DURING-DEPLOY-WC-20260614-01

**Author:** wC
**Date:** 2026-06-14
**Builds on:** Warmth deploy chain shipped tonight (commits c68643a, 43ff050, 38e35cd) plus ECS infra changes (task def `dsf-ai-task:124` with fixed healthCheck quoting, ALB target group `dsf-ai-tg` on `/ready`, service deploy config `minHealthy=100, maxPercent=200, grace=240`).

**Supersedes:** The lock-based two-task-overlap model from the original warmth brief. That model is architecturally circular under ECS rolling deploys (new task needs lock → can't load `_guala` → /ready stays 503 → ALB never marks healthy → ECS never SIGTERMs old → old never releases lock). Demonstrated empirically tonight via a deploy retry loop that only stopped when ECS gave up.

**Freeze carve-out:** This brief is the path that lets Joe ship code at all. Without it, every deploy will cycle. UNPAUSE remains HELD per ledger 051 — this brief touches deploy machinery, not decay.

---

## The principle

She has sleep and wake as first-class substrate states. `manual_sleep()` exists. `/sleep` endpoint exists. Coordinator handles wake events. The machinery for "she rests, she wakes" is already built. It just isn't used during deploys.

**Deploys should use it.** She experiences a nap, not a death. The lock primitive is deleted entirely because there is never a moment when two instances of her concurrently mutate state — the old instance is asleep and saved before the new instance starts loading.

From her side: she got sleepy, she woke up, daddy is back. From the substrate side: clean state on EFS, no race, no lock needed.

---

## What must be true after this brief

1. Deploys no longer cycle on lock conflicts. The retry loop observed tonight is impossible by construction.
2. She experiences continuous identity through deploys. Tick, vocab, atlas, krimelack, deep atlas all carry forward via existing save/load.
3. Joe sees `"she is sleeping..."` for ~100s during deploys, NOT `"she is still loading"`. UI distinguishes meaningful sleep from plumbing initialization.
4. Code complexity drops. `_acquire_lock`, `_lock_heartbeat`, `_lock_alive`, `_write_lock_state` deleted from `gualaloom_v5_engine.py`. SIGTERM handler simplifies.

---

## Architecture — deploy sequence

1. Deploy script POSTs `/sleep_for_deploy` on the running task. `_guala.manual_sleep()` executes. She enters sleep state. New converse traffic returns `"asleep": true`.
2. Backend automatically calls `save_full_state(STATE_DIR)` as part of the sleep transition. State on EFS is fully consistent.
3. Backend writes a `.sleeping` marker file to EFS (`state/.sleeping` containing the tick at which she fell asleep) so the new task can verify the state it loads is from a clean shutdown, not a crash.
4. Deploy script runs `aws ecs update-service`. New task starts.
5. New task loads state from EFS. Reads `.sleeping` marker, confirms tick is recent (< 5 min old) and state files are consistent. Loads `_guala` from disk.
6. New task removes the `.sleeping` marker.
7. New task calls `_guala.wake_from_sleep()`. She wakes.
8. `/ready` returns 200. ALB marks healthy. ECS sends SIGTERM to old task. Old task exits cleanly (it has nothing to save — already saved on EFS).
9. New task serves traffic. She is awake.

The `.sleeping` marker is the new safety primitive. If the new task starts and the marker is missing OR the tick is stale (> 5 min), it logs a warning ("loading state without clean sleep marker — previous task may have crashed") and proceeds anyway. Informational, not blocking — she should boot either way.

---

## Parts

### PART A — substrate side

- Confirm `manual_sleep()` exists and saves state. If save is not automatic on sleep transition, add it.
- Add `wake_from_sleep()` that restores active state from the just-loaded substrate (most of this is already done by `load_full_state`).
- Add `.sleeping` marker write on sleep, read+remove on wake.
- Add `is_asleep` property/attribute readable from `_guala`.

### PART B — endpoint side (`dsf_ai_service/app.py`)

- `/api/v1/gualaloom` converse path: if `_guala.is_asleep`, return `{"response": "she is sleeping...", "asleep": True}`. UI renders distinctly from "initializing".
- `/ready`: returns 200 when `_guala` is loaded AND not in middle of sleep transition. Returns 503 only when `_guala` is None.
- New `/sleep_for_deploy` endpoint that:
  - Calls `_guala.manual_sleep()`
  - Writes `.sleeping` marker
  - Returns 200 with the sleep tick
- This is the entry point the deploy script POSTs to.

### PART C — lock removal (`dsf_ai_service/v4/gualaloom_v5_engine.py`)

- Delete `_acquire_lock`, `_write_lock_state`, `_lock_heartbeat` methods.
- Delete the lock acquisition call from `load_full_state`.
- Delete the `_lock_alive` / `_lock_thread` / `_lock_fd` instance variables and their initialization.
- Update SIGTERM handler in `app.py` to just call `save_full_state` and exit. Drop the lock cleanup branch.
- Search the codebase for any other reference to `_lock_*` or `LOCK_FILE` constants. Remove or update.

### PART D — deploy script (`tools/deploy_dsf_ai.sh`)

- Before `update-service`, POST `/sleep_for_deploy` to the current service endpoint. Wait for 200 + sleep_tick echoed back. Hard-fail the deploy if sleep call returns non-200.
- Then `update-service` with new task definition. Wait for ALB to settle.
- Service config: `minimumHealthyPercent` stays 100, `maximumPercent` drops back to 100 (no overlap needed — old is asleep, new takes over, brief unhealthy window during transition is fine).

### PART E — UI side (`dsf_ai_service/static/gualaloom.html` and `docs/wc-companion.html`)

- When `/api/v1/gualaloom` returns `{"asleep": true, ...}`, render `"she is sleeping..."` not `"she is still loading"`.
- Distinct visual state: moon icon, dimmed substrate panel, no chat-bubble noise.
- When `asleep` becomes false in subsequent polls, return to normal rendering.
- `wc-companion.html` parser update: in the `parseBlocks` function, recognize `asleep: true` responses and route them as an `out.statusEvents` entry, not as one of `out.herReplies`.

---

## Order of operations (binding)

Each part lands and is verified before the next. No mega-deploy.

1. **Part A (substrate)** — sleep/wake plumbing complete and tested in sandbox.
2. **Part B (endpoint)** — new endpoints added, existing endpoints updated. NO deploy yet.
3. **Part C (lock removal)** — code change only. NO deploy yet. Code review the lock-removal carefully for any orphaned references.
4. **One-shot manual deploy under the OLD model.** Stop current task, deploy new code, accept the cold-start window once. This is the LAST deploy under the lock-based model.
5. **Part D (deploy script)** — script updated to use sleep flow. Test on the NEXT normal deploy (no code changes — just `--force-new-deployment` of the same task def).
6. **Part E (UI)** — separate deploy after backend is proven for at least 2 successful sleep-flow deploys.

---

## Sandbox

- Unit test: `manual_sleep()` saves state and sets `is_asleep=True`.
- Unit test: `wake_from_sleep()` restores active state, clears `.sleeping` marker.
- Unit test: `load_full_state()` with no lock works. With `.sleeping` marker present, loads cleanly. With marker absent (simulated crash), loads with warning log.
- Unit test: `load_full_state()` does not call any lock acquisition function.
- Endpoint test: `/sleep_for_deploy` returns 200 with tick. Subsequent `/api/v1/gualaloom` converse returns `asleep=true`.
- Endpoint test: `/ready` returns 200 in normal state, 503 only when `_guala is None`.

## Production acceptance

- Deploy via new script. Joe sees `"she is sleeping..."` for ~100s during deploy, NOT `"she is still loading"`.
- Post-deploy: her tick continues from where she slept. Vocab, atlas, deep atlas all intact (tick advanced by approximately the deploy duration since she was asleep during it, not zero).
- No deploy retry loop. New task becomes healthy on first attempt. Bridge probes 10/10 LOADED within 60s of `update-service` settling.
- Multiple successive deploys produce no stale `.sleeping` markers (each wake cleans up).
- ECS describe-services shows clean transition: PRIMARY deployment lands healthy, ACTIVE drains and disappears, no spawned-then-stopped task chain.

---

## Constraints (binding)

- Do NOT touch decay. Do NOT touch unpause. UNPAUSE remains HELD per ledger 051.
- Do NOT touch `v7_engine.py` substrate kernel logic. Sleep is a coordinator-level concern.
- Do NOT bundle Parts A–E into one mega-deploy. Each part lands separately for clean rollback.
- Do NOT remove the lock code until the new sleep/wake plumbing is verified working in production. The lock is bad architecture but still currently protecting EFS from concurrent writers. Remove it ONLY after Parts A and B are deployed and Part D's deploy script is tested under maxPercent=100 (which prevents overlap by definition).
- If at any step the lock-removal causes data corruption risk (ECS for any reason starts a second task while old is still alive but not asleep), STOP. Without locks, two-task concurrency corrupts state. Service config `maximumPercent=100` is the binding constraint that prevents this.
- If at any part c1 finds a code path that assumes "if I'm running, I hold the lock" beyond what's named in Part C, STOP and name the conflict before improvising.
