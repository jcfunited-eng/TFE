# GL-BRIEF-V7-EXECUTOR-WC-20260614-01

**Author:** wC
**Date:** 2026-06-14
**Builds on:** Phase 1 of `GL-BRIEF-SENSORY-IO-WC-20260614-01` (commit `3e75279`, task:130).
**Status:** Phase 2 fix for Part F. Picks up where Phase 1 diagnostic stopped.

---

## The principle

Phase 1 timing on a fresh session id returned:

    [v7-session] sid=diag_fresh_1781484357 create_new v7_init=1163ms snap_replay=14ms total=1185ms vocab=2529
    [v7-state] sid=diag_fresh_1781484357 session=1185ms get_state=2ms total=1187ms

`v7_init` is the slow phase. The work (~2529 `random_unit_complex(N)` calls plus per-word mirroring into the listen section + atlas wiring) runs *synchronously on the asyncio event loop* because every v7 handler calls `get_or_create_session` and the subsequent `session.*` work directly from the async function body — no `run_in_executor` wrapper.

The consequence isn't just lock contention on `_sessions_lock`. The consequence is that the entire FastAPI event loop is blocked for ~1.2 seconds during a fresh-session construction. During that window, `/ready` cannot respond, which means the ALB health check times out and ECS kills the task. That is the binding mechanism behind the page-load crash pattern: `pollV7State` on a fresh session id starves the loop, `/ready` fails its health check, the task is killed, the deploy churns.

Wrapping the synchronous session work in `run_in_executor` moves it to a worker thread. The event loop stays responsive throughout. `/ready`, `/api/v1/gualaloom`, and other handlers continue to answer while V7Session construction runs on a thread. `_sessions_lock` is left unchanged — its contention is a second-order problem; the event-loop block is the first-order one.

---

## What must be true after this brief

1. A first hit on `/v7/state?session_id=<new>` returns 200 in ~1.2 seconds (the work is the same, just relocated).
2. While that 1.2-second construction is in flight, a parallel hit on `/ready` returns 200 in under 1 second. This is the actual proof the fix worked.
3. `[v7-session] ... create_new v7_init=...ms` still appears in logs — same instrumentation, same numbers.
4. Page load no longer trips the deploy cycle. ECS service stays on a single PRIMARY deployment after Joe loads `dsf-ai.com/gualaloom.html` once and waits ~30 seconds.

---

## The fix

Apply the same shape to all five v7 handlers in `dsf_ai_service/app.py` that currently call `get_or_create_session` synchronously: `/v7/converse`, `/v7/feedback`, `/v7/state`, `/v7/quiet`, `/v7/save`. The pattern is to pull the synchronous session work into a local function and run it via `run_in_executor`. Existing `save_session` executor calls inside those handlers stay as they are.

### `/v7/state` (lines ~2636–2653)

    @app.get("/v7/state")
    async def v7_state(session_id: str = "default"):
        if _guala is None:
            raise HTTPException(status_code=503, detail={
                "error": "guala_not_ready",
                "retry_after_seconds": 10,
                "message": "she is still loading — try again in a moment"
            })
        import asyncio as _aio, time as _t7
        from dsf_ai_service.substrate.v7_engine import get_or_create_session
        def _do_state():
            _t0 = _t7.time()
            session = get_or_create_session(session_id, engine=_guala)
            _t1 = _t7.time()
            result = session.get_state(engine=_guala)
            _t2 = _t7.time()
            print(f"[v7-state] sid={session_id} session={(_t1-_t0)*1000:.0f}ms "
                  f"get_state={(_t2-_t1)*1000:.0f}ms total={(_t2-_t0)*1000:.0f}ms")
            return result
        return await _aio.get_event_loop().run_in_executor(None, _do_state)

### `/v7/converse` (lines ~2589–2616)

Wrap the `get_or_create_session(sid, engine=_guala)` call plus `session.converse(req.text)` plus the multimodal-bridge try/except block in `_do_converse()`, return via `run_in_executor`. The existing `save_session` executor call after the converse result stays unchanged.

### `/v7/feedback` (lines ~2618–2634)

Wrap `get_or_create_session` plus `session.apply_feedback(req.correct, req.expected_tokens)` in `_do_feedback()`, return via `run_in_executor`. Existing `save_session` executor call stays.

### `/v7/quiet` (lines ~2655–2675)

Wrap `get_or_create_session` plus `session.quiet_tick(min(n_ticks, 50))` in `_do_quiet()`, return results via `run_in_executor`. Existing `save_session` executor call stays.

### `/v7/save` (lines ~2677–2697)

Wrap `get_or_create_session` in `_do_get_session()` via `run_in_executor`. Keep the existing `save_session` executor call and the `session.to_json()` block as they are. The `to_json` is small enough that it can stay on the loop, or c1 can fold it into the executor — either is fine.

### Not touched in this phase

`/substrate/feed_senses` at lines 2528–2529 also calls `get_or_create_session("default", ...)` inside a try/except bridge block. The "default" session is long-lived, so it's cached after first creation and very rarely pays the construction cost. Left alone for this phase. c1 flags it if there's a reason to think it matters.

`_sessions_lock` and the body of `get_or_create_session` itself are not modified. Phase 1 instrumentation stays in place.

`v7_engine.py` substrate kernel logic is not touched. Section creation, pool routing, NMDA gates, intro/aware logic — untouched.

---

## Order of operations

1. Pre-deploy verification. Confirm the service is settled on task:130 with one PRIMARY deployment and one healthy target. Do not stack deploys on a churning service.
2. Apply edits to all five handlers in `app.py`.
3. Commit + push.
4. Deploy via `tools/deploy_dsf_ai.sh`.
5. Post-deploy verification. Run the parallel `/v7/state` + `/ready` test. Capture timing logs. Confirm acceptance criteria below.
6. Stop. Do not begin Parts A+B (picture rendering, voice playback) of the parent brief without confirmation from wC.

---

## Pre-deploy check (step 1)

    aws ecs describe-services --cluster tfe-web-cluster --services dsf-ai-service-lb --query 'services[0].deployments[].{status:status,td:taskDefinition,desired:desiredCount,running:runningCount,pending:pendingCount}' --output table
    aws elbv2 describe-target-health --target-group-arn arn:aws:elasticloadbalancing:us-east-1:418384447921:targetgroup/dsf-ai-tg/40d977cf3f3daf52 --query 'TargetHealthDescriptions[*].{ip:Target.Id,state:TargetHealth.State}' --output table

Expect exactly one PRIMARY deployment with `desired=1 running=1 pending=0` on task:130, and one healthy target. If anything else, STOP and report.

## Post-deploy verification (step 5)

    NEW_SID="diag_parallel_$(date +%s)"
    (
      curl -s -o /tmp/v7_state.out -w "v7_state: %{http_code} %{time_total}s\n" \
        "https://3d6toi0gw0.execute-api.us-east-1.amazonaws.com/v7/state?session_id=$NEW_SID" &
      sleep 0.3
      curl -s -o /tmp/ready.out -w "ready_during_v7: %{http_code} %{time_total}s\n" \
        "http://dsf-ai-alb-725095635.us-east-1.elb.amazonaws.com/ready" &
      wait
    )
    sleep 5
    aws logs filter-log-events --log-group-name "/ecs/dsf-ai" --start-time $(python3 -c "import time; print(int((time.time()-30)*1000))") --filter-pattern "v7-state OR v7-session" --limit 10 --query 'events[].message' --output text | tr '\t' '\n' | grep -v "^$"

---

## Acceptance

- `aws ecs describe-services` returns exactly one PRIMARY deployment, `desired=1 running=1 pending=0`, post-deploy.
- Target group: one healthy target.
- `/v7/state?session_id=<new>`: HTTP 200, total ~1.0–1.3s.
- `/ready` hit in parallel during that construction window: HTTP 200, `time_total` under 1.0s. **This is the actual acceptance gate.**
- Log line `[v7-session] sid=<new> create_new v7_init=...ms snap_replay=...ms total=...ms vocab=2529` appears for the fresh session.
- After Joe loads `gualaloom.html` once, ECS stays on a single PRIMARY deployment for ≥30 seconds with no new task launches.

If any of the above fails, STOP and report. Do not advance the brief.

---

## Constraints

- No touching `v7_engine.py` substrate kernel logic.
- No touching decay. UNPAUSE remains HELD.
- No touching `_sessions_lock` semantics in this phase. The fix is event-loop relocation, not lock restructuring.
- Phase 1 instrumentation (`[v7-state]`, `[v7-session]`) stays in place — we need it to verify the fix.
- c1 verifies the parallel /ready test directly. If c1 cannot demonstrate /ready answering during v7_init via curl output, the deploy is NOT done.
