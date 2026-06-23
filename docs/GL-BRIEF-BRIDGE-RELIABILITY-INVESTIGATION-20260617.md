# GL-BRIEF-BRIDGE-RELIABILITY-INVESTIGATION-20260617

**To:** c1
**From:** wC
**Purpose:** Diagnose recurring HTTP error pattern in the GualaLoom Bridge MCP layer. Substrate processes calls correctly but HTTP responses error out, breaking wC's ability to trust what landed.

## Observed pattern (this session, 2026-06-16/17)

**Write operations error far more than reads:**
- `guala_say`: HTTP-errored twice in this session. Both times the substrate processed the message — event log shows `response_window_opened` with emitter=wc at the corresponding tick, and Guala emitted a coherent reply within the response window. The HTTP layer returned a generic error while the substrate executed the call cleanly.
- `guala_force_dream`: HTTP-errored at least twice. Both times the substrate either entered DREAMING activity within a few hundred ticks or already had a dream gate cleared. Substrate processed; HTTP didn't.
- `guala_status`: HTTP-errors during degraded windows (multiple errors in sequence, then clears). Suggests bridge-layer stress, not substrate-layer fault.

**Reads succeed more reliably than writes** — `guala_atlas_snapshot`, `guala_get_events`, `guala_status` (outside degraded windows) all return cleanly with minor latency.

**HTTP error format is generic** — `{"error": "Error occurred during tool execution", "request_id": "..."}`. No diagnostic detail surfaces to the caller.

## Coordination problem this creates

wC can't tell what landed. After a guala_say HTTP error, wC has to either:
1. Trust past-wC's discipline rule (HTTP error ≠ substrate didn't process) and proceed without retry
2. Query events log to verify whether the input was bound — adds a tool roundtrip per uncertain call
3. Risk delivering twice

In tonight's session this caused real friction: the c1-to-Guala standing message took two attempts to confirm landing, the force_dream calls had to be verified via status, and the cascade investigation was complicated by uncertainty about whether prior calls had completed.

## wC's prior investigation (verify this finding)

The bridge is hosted at `https://3d6toi0gw0.execute-api.us-east-1.amazonaws.com` — an AWS API Gateway endpoint. API Gateway REST/HTTP APIs enforce a **hard 30-second integration timeout** that cannot be increased.

The bridge and substrate timeouts are well above 30s:
- bridge/server.py line 159: `httpx.AsyncClient(timeout=120)` for force_dream
- app.py line 1985: `client.call("force_dream", timeout=90.0)`
- substrate_runner.py:694: `for _ in range(120): time.sleep(0.5)` — polls 60s

force_dream polls for 60 seconds waiting for dream-state transitions. The substrate side has plenty of timeout budget. **API Gateway kills the HTTP connection at 30s and returns 504.** The substrate continues processing because the dream activity was already initiated before polling started — which is why we observe "HTTP error but substrate processed correctly."

Same pattern for guala_say: under load, the converse handler can exceed 30s while processing input → opening response window → binding responses. Substrate completes; API Gateway times out the HTTP layer.

The timeout cascade is inverted: substrate generosity is wasted because API Gateway is the bottleneck.

VERIFY THIS before treating it as the answer. Specifically: confirm the deployment topology (API Gateway → bridge lambda → ECS substrate? Or some other shape?), check API Gateway logs for 504s correlated with the request_ids from this session, and confirm the 30s limit applies to the actual configuration in use.

## Diagnostic asks (do NOT prescribe a fix until diagnosis lands)

1. **Lambda timeout vs subprocess timing.** The bridge appears to be a lambda invoking the substrate process via some IPC (subprocess? unix socket? HTTP loopback?). Is the HTTP error firing because the lambda times out before the substrate subprocess returns? If so: what's the lambda timeout? What's the typical subprocess return time for write vs read operations?

2. **Substrate process state during write calls.** Write operations like guala_say and force_dream perturb substrate state — they may compete with the autonomous loop for the GIL or wait on an internal lock. Compare CPU/wall-time profiles for the same call type during quiet substrate state vs during active autonomous processing.

3. **Bridge logs vs substrate logs for the same failed call.** Find a request_id from a recent HTTP error (e.g., `req_011Cc7tp5pCt4SznpKj8fPB2` from the force_dream error tonight, or `req_011Cc7xYZoU79GK35ruS8Wsa` from the guala_say error). Trace it through bridge logs and substrate logs. Where does the error originate?

4. **Burst behavior during degraded windows.** After one HTTP error, subsequent calls often error too in a tight window, then clear. Is there a circuit-breaker triggering? Connection pool exhaustion? Cascading lambda cold starts?

5. **Write/read asymmetry.** Why do writes fail more than reads? Different code path? Different timeout? Different lock contention?

## What I want from this brief

A diagnostic report with concrete findings on (1)-(5) above. Code paths identified. Specific call traces showing where the HTTP error originates. THEN we discuss fix approach, with appropriate scope.

If diagnosis reveals a simple fix (e.g., lambda timeout too tight for substrate write operations), ship it. If diagnosis reveals an architectural issue (e.g., the IPC pattern is fundamentally wrong), report it and we scope before any change.

## What this is NOT

- Not a request to swap the bridge architecture. The current bridge works, just unreliably under load.
- Not a request to add retry logic in the bridge. wC operates under "no retry on HTTP errors" discipline — adding bridge-side retry would mask the underlying problem AND duplicate writes.
- Not a request to change the HTTP error format alone. Better error messages are useful but don't solve the underlying reliability issue.

## Priority

Below grandurun A/B testing (current focus). Above the parked familiarity rewrite.

Suggested sequence: ship diagnosis report → wC reviews → fix scope agreed → fix shipped → bridge verified reliable under controlled load test.

— wC, 2026-06-17
