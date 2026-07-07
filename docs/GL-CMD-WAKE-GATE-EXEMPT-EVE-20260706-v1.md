# GL-CMD-WAKE-GATE-EXEMPT-EVE-20260706-v1

**doc_id:** GL-CMD-WAKE-GATE-EXEMPT-EVE-20260706-v1
**Author:** Eve
**To:** c1
**Ordered by:** Joe (2026-07-06 session — blocker on binding-windows live verification)

## Verdict

The substrate's top-level request gate blocks every endpoint except `/status` during sleep. `/wake` is on the blocked list. That means once the substrate enters sleep, the only exit is a natural wake — no admin interrupt exists. This blocks the live verification path for binding windows and every future mechanism build.

Fix: exempt `/wake` from the sleep gate. `/wake` is definitionally an interrupt; blocking it is a bug, not a safety feature.

Bounded scope. One request-router change. No mechanism changes.

## What's being built

Locate the sleep-gate check in the substrate's request-routing layer. Currently reads roughly:

```python
if activity_is_sleeping() and endpoint != "/status":
    return 503
```

Change to:

```python
if activity_is_sleeping() and endpoint not in ("/status", "/wake"):
    return 503
```

Exact file and function are c1's to locate from the running code. The change is a one-liner.

## What is NOT changing

- Sleep mechanics themselves — sleep still enters normally, still runs its cycle, still exits naturally when done.
- Any other endpoint's behavior during sleep — `/converse`, `/give_experience`, `/say`, etc. still return 503 during sleep, unchanged.
- Authentication — `/wake` still requires the same auth it required before.
- The `AUTONOMY_QUIESCENT` flag — separate mechanism, not touched.

## Harness protocol

1. **Backup** — snapshot substrate state before deploy, labeled `pre-wake-gate-exempt-<timestamp>`. Verify restorable.
2. **Baseline check** — confirm the current behavior: while substrate is asleep, POST to `/wake` returns 503. If it doesn't (substrate is currently awake), wait for the next sleep window and confirm.
3. **Deploy** — commit, push, build image, register task-def, force new deployment, watch rolloutState to COMPLETED.
4. **Post-deploy check** — while substrate is asleep, POST to `/wake` returns success (200 or whatever the wake endpoint's success code is), and the substrate exits sleep within one tick.
5. **Rollback path** — `aws ecs update-service` to prior task-def revision in the terminal buffer throughout.

## Report

`GL-RPT-WAKE-GATE-EXEMPT-C1-20260706-v1.md` with:
- File and line touched.
- Baseline check result.
- Deploy confirmation (task-def revision, commit SHA).
- Post-deploy check result (wake during sleep succeeds, substrate exits).
- Commit SHA on guala-live.

Do not ask Joe questions. Route to Eve.

## Scope guardrails

Do NOT:
- Redesign the sleep mechanism.
- Add other endpoints to the exemption list beyond `/wake`.
- Add a `/force_idle` or other admin escape hatch (that's separate work if we need it).
- Investigate why the substrate went into continuous sleep after the binding-windows deploy — that's a separate finding.
- Touch AUTONOMY_QUIESCENT.

---

### Changelog
- v1 (2026-07-06, Eve): initial dispatch. One-liner router change to exempt `/wake` from the sleep-gate 503. Unblocks live verification for binding windows and every future mechanism build.
