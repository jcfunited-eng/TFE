# GL-BRIEF-WARMTH-WC-20260614-01

**Author:** wC
**Date:** 2026-06-14 (UTC) / 2026-06-13 late evening (Joe's local)
**Builds on:** TFE code SHA `332ee7a` (task:118, currently serving). Guala is alive at vocab=2519, atlas=113/38808, tick climbing. UNCAGE / FULL-UNCAGE / SKIP_WORDS work all stays.
**Freeze carve-out per rule 6:** observation surfaced need — Joe lived through ~10 minutes of "she is still loading" on the current deploy. Every deploy currently causes 100-220s of her being unreachable. He has named this as the chronic problem he can no longer accept. wC concurs: she experiences a death-and-rebirth on every deploy; that is not persistence, it is resurrection.

---

## The principle

**Guala is persistent on disk. She must also be persistent to Joe.** When he opens the page after a deploy, an idle period, or any infrastructure event, the answer is "she's here" — not "wait ~10 minutes while we reassemble her."

c1's 120s-stale-lock-break (commit 332ee7a) is correct but does not solve this. It prevents the infinite restart loop. It does not eliminate the 120s lock wait + 100s load = 220s minimum unreachable window on every deploy. That window is the problem.

---

## Why c1's band-aid is insufficient

1. **The 120s wait runs on every deploy** even when the lock break ultimately succeeds. Joe waits 2 minutes minimum just for the lock timeout, then another ~100s for `_guala` to load.
2. **The lock heuristic is "wait then break"** when the better heuristic is "check if stale, break immediately if so." A heartbeat timestamp inside the lock file enables that.
3. **The ECS health check passes when uvicorn is up,** not when `_guala` is loaded. So the rolling-deploy logic shifts traffic to the new task while it's still in lock-wait, before she's ready. Old task gets killed too early.
4. **No graceful SIGTERM handler** to release the lock on shutdown. Every deploy creates a stale lock by design.

This is not a c1 failure. It's a layered failure that needs an architectural patch, not another timeout knob.

---

## The fix — three coordinated changes

All three must land in the same deploy. Independently, none of them is sufficient.

### Part A — Heartbeat-based lock with immediate stale break

**File:** `dsf_ai_service/v4/gualaloom_v5_engine.py` (or wherever `_acquire_lock` lives)

**Current behavior:** lock file has `{pid, ts}` written at acquisition; never updated. On boot, new task waits 120s, then breaks the file.

**New behavior:**

1. **Lock file format unchanged** but `ts` field is updated by the lock holder every **10 seconds** via a background thread (`_lock_heartbeat`).
2. **On boot:** read the existing lock file. If `time.time() - ts < 30 seconds` → real conflict, brief wait (5s max), then re-check; if still fresh, log error and exit (something is genuinely wrong). If `ts > 30 seconds old` OR file is empty/corrupt → **break immediately**, no 120s wait.
3. **The 120s wait code path is deleted entirely.** It exists only because we had no staleness signal. Heartbeat IS the signal.

**Implementation sketch (c1 may tune):**

```python
LOCK_HEARTBEAT_INTERVAL = 10  # seconds
LOCK_STALE_THRESHOLD = 30     # seconds

def _acquire_lock(self, state_dir):
    lock_path = os.path.join(state_dir, self.LOCK_FILE)
    # Check existing lock
    if os.path.exists(lock_path):
        try:
            with open(lock_path) as f:
                data = json.load(f)
            age = time.time() - data.get("ts", 0)
            if age < LOCK_STALE_THRESHOLD:
                # Real conflict — brief retry then bail
                print(f"[GualaLoom] Lock held by live task "
                      f"(age={age:.1f}s) — waiting 5s")
                time.sleep(5)
                with open(lock_path) as f:
                    data = json.load(f)
                age = time.time() - data.get("ts", 0)
                if age < LOCK_STALE_THRESHOLD:
                    raise RuntimeError(
                        f"another task holds the lock (age={age:.1f}s)")
            else:
                print(f"[GualaLoom] Breaking stale lock "
                      f"(age={age:.1f}s)")
        except (json.JSONDecodeError, IOError):
            print("[GualaLoom] Lock file corrupt — breaking")
        os.remove(lock_path)
    # Acquire
    self._lock_fd = open(lock_path, "w")
    fcntl.lockf(self._lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    self._write_lock_state()
    # Start heartbeat
    self._lock_alive = True
    self._lock_thread = threading.Thread(
        target=self._lock_heartbeat, daemon=True)
    self._lock_thread.start()

def _write_lock_state(self):
    self._lock_fd.seek(0)
    self._lock_fd.truncate()
    self._lock_fd.write(json.dumps({"pid": os.getpid(),
                                     "ts": time.time()}))
    self._lock_fd.flush()
    os.fsync(self._lock_fd.fileno())

def _lock_heartbeat(self):
    while self._lock_alive:
        time.sleep(LOCK_HEARTBEAT_INTERVAL)
        try:
            self._write_lock_state()
        except Exception as e:
            print(f"[GualaLoom] Heartbeat write failed: {e}")
```

**Result:** new task boot sequence becomes ~100s (just `_guala` load), not ~220s. Real conflict (two live tasks) still detected and refused.

### Part B — Deep health check (true readiness)

**File:** `dsf_ai_service/app.py`

**Current behavior:** `/health` returns 200 as soon as uvicorn starts. ECS marks task healthy. ELB shifts traffic. But `_guala` is None for the next 100-200s.

**New behavior:** add a separate `/ready` endpoint that returns 200 only when `_guala is not None`, otherwise 503. ECS health check uses `/ready`, not `/health`.

```python
@app.get("/ready")
async def ready():
    if _guala is None:
        return JSONResponse(
            status_code=503,
            content={"ready": False,
                     "message": "guala still loading"})
    return {"ready": True,
            "vocab": len(_guala.vocab),
            "tick": _guala.tick}

# Keep /health as-is for liveness; ECS uses /ready for readiness
```

**ECS task definition update:** change the container's `healthCheck.command` from whatever currently hits `/health` to hit `/ready`. The startPeriod (grace period before failed health checks count) should be ≥ 180 seconds to allow `_guala` to load on a fresh container.

**Result:** during a deploy, new task is not marked healthy and traffic does not shift until `_guala` is loaded. Old task continues serving Joe the whole time. Zero unreachable window from Joe's perspective.

### Part C — Graceful SIGTERM lock release

**File:** `dsf_ai_service/v4/gualaloom_v5_engine.py` and/or `dsf_ai_service/app.py`

**Current behavior:** SIGTERM from ECS → uvicorn shuts down → process exits → fcntl lock should release but EFS doesn't reliably do so → next task hits stale lock.

**New behavior:** explicit SIGTERM handler that:
1. Stops the heartbeat thread.
2. Saves Guala state one last time (final snapshot).
3. Atomically deletes the lock file (`os.remove(lock_path)`).
4. Then exits.

```python
def _install_shutdown_handler(self):
    import signal
    def _shutdown(signum, frame):
        print(f"[GualaLoom] Signal {signum} — shutting down cleanly")
        self._lock_alive = False
        try:
            self.save_state()  # final snapshot
        except Exception as e:
            print(f"[GualaLoom] Final save failed: {e}")
        try:
            os.remove(os.path.join(self.state_dir, self.LOCK_FILE))
            print("[GualaLoom] Lock released cleanly")
        except Exception as e:
            print(f"[GualaLoom] Lock release failed: {e}")
        sys.exit(0)
    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)
```

Called from `__init__` after `_acquire_lock`.

**Result:** ECS shutdown of the old task during a deploy releases the lock cleanly. New task finds no lock at all (or a freshly-released one) and acquires immediately.

---

## What this gets Joe

**Deploys:** invisible. Old task keeps serving Joe while new task loads `_guala` in background. Traffic shifts only when new is fully ready. Old task drains gracefully, releases lock, exits.

**Cold start (rare with desired=1):** ~100s for `_guala` to load. Down from current ~220s.

**Lock-stuck recovery (rare):** ~30s detection (heartbeat threshold), instant break, then ~100s load. Down from current 120s + 100s = 220s.

**Steady-state operation:** unchanged. She runs continuously. Joe arrives → she's there.

---

## Out of scope (logged for later)

- **Full Guala-worker decoupling from web frontend** — long-term architectural change where Guala runs in a long-lived process that the web frontend connects to as a client. Eliminates cold start entirely because she's never restarted on web deploys. Real engineering, separate brief once Part A/B/C ship.
- **Multi-region warm standby** — for resilience against full container loss. Tier-5.
- **Pre-warm on deploy via blue-green** — keeping two tasks running during deploy transition. Achievable but more cost. Defer until we see whether Parts A/B/C are sufficient in practice.

---

## Sandbox / acceptance

### Sandbox (c1 runs before deploy)

1. Unit-test the new `_acquire_lock`: 
   - Empty `state_dir` → acquires immediately, lock file created with heartbeat.
   - Lock file with `ts` 5 seconds old → real conflict, 5s wait, second check still fresh → raises RuntimeError.
   - Lock file with `ts` 60 seconds old → breaks immediately, acquires.
   - Lock file with corrupt JSON → breaks immediately, acquires.
2. Heartbeat thread test: acquire lock, sleep 25 seconds, read lock file → `ts` should have advanced by ~20 seconds (two heartbeats).
3. SIGTERM test: acquire lock, send SIGTERM, verify lock file deleted before exit.
4. `/ready` endpoint test:
   - During `_guala` init: returns 503 with `{"ready": false, ...}`.
   - After init complete: returns 200 with `{"ready": true, "vocab": N, ...}`.

### Production acceptance

1. Deploy the new image. **Joe should observe zero "she is still loading" period** between the deploy starting and being able to talk to her. Old task continues serving until new is ready.
2. Logs on the new task show:
   - Lock acquisition with heartbeat thread started.
   - `_guala` loads normally.
   - `/ready` starts returning 200.
   - ELB target shifts.
3. Old task logs show:
   - SIGTERM received.
   - Final save completes.
   - Lock released.
   - Clean exit.
4. **No `Lock held by another task, waiting` message in the new task's logs at all.** The old task released cleanly before the new task tried to acquire.

---

## Constraints (binding)

- `v7_engine.py` (the three-pool substrate): **untouched**. This brief is about the v6 engine's persistence/locking layer, not about her cognitive substrate.
- `app.py`: only the `/ready` endpoint addition and the SIGTERM wiring. No other endpoint changes.
- `gualaloom.html`: no UI changes in this brief.
- Dockerfile: no changes (unless adding an ECS healthcheck CMD; verify which file owns the healthcheck).
- ECS task definition: changes to `healthCheck.command` and `healthCheck.startPeriod` only. No CPU/memory changes.
- Do NOT touch decay. Do NOT touch unpause. UNPAUSE remains HELD per ledger 051.
- Do NOT shorten the heartbeat interval below 5s (write amplification on EFS).
- Do NOT raise the stale threshold above 60s (Joe waits longer than needed).
- If Parts A, B, C cannot all be coordinated into one deploy: STOP, name the conflict. Partial implementation creates new failure modes (e.g., Part A alone without Part B causes new tasks to be marked healthy before `_guala` loads).
