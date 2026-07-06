# GL-AUDIT-SEC5-INTERFACE-TRUTH-C1-20260705-v1

doc_id: GL-AUDIT-SEC5-INTERFACE-TRUTH-C1-20260705-v1
Part of: GL-CMD-PRODUCTION-AUDIT-C1-EVE-20260705-210-v2, §5 (Interface truth —
every web page)
Author: c1 | Freeze in effect throughout — read-only. No fixes, no deploys, no
config changes were made. Cross-references §1 (`GL-AUDIT-SEC1-RUNTIME-TRUTH-
C1-20260705-v1`) and §2 (`GL-AUDIT-SEC2-AWS-TRUTH-C1-20260705-v1`), both
already filed — §2 explicitly deferred the full timeout disposition to this
document ("See §5 for the full disposition"); this delivers that.
running_sha at time of audit: `168ef1bde3717e52efb85b894103de047e942617`
(confirmed live via `guala_status`, matches `dsf-ai-task:494`).

---

## HEADLINE FINDING — API Gateway's 30s ceiling vs 69-72s converse latency:
## CONFIRMED at the config level, REFINED — the main chat UI is structurally
## shielded from it; the MCP `/mcp` route and the `/status` command path
## are NOT

### What is confirmed exactly as suspected

- **[EV]** `POST /v7/converse` → API Gateway route on `dsf-ai-api` (`3d6toi0gw0`)
  → integration `r36cjia`, type `HTTP_PROXY`, target
  `http://dsf-ai-alb-725095635.us-east-1.elb.amazonaws.com/v7/converse`,
  `TimeoutInMillis: 30000`. Verified via `aws apigatewayv2 get-routes` +
  `get-integrations` directly, not inherited from any doc.
- **[EV]** This 30000ms figure is identical across **all 38** routes on this
  API (checked every integration, not just this one) — confirms the
  dispatch's framing that this is an AWS HTTP-API platform ceiling, not a
  per-route misconfiguration someone could just raise.
- **[EV]** ALB (`dsf-ai-alb`) `idle_timeout.timeout_seconds = 180`. This is
  **longer**, not shorter, than API Gateway's 30s cap and also longer than
  the observed 69-72s converse time — so in the chain client → API Gateway
  (30s) → ALB (180s) → ECS target, **API Gateway's 30s is the binding
  constraint**, not the ALB. (Task's part (c), answered: API Gateway loses,
  i.e. cuts off first, not the ALB.)
- **[EV]** Production `converse()` (per `GL-HANDOFF-C1A-20260705-v1`, itself
  re-verified live this audit via `guala_status`, same `running_sha`) takes
  69-72s end-to-end (`recall_ms` 17-18s, `read_ms` 29-34s). This is well
  past API Gateway's 30s ceiling.

### What the dispatch's framing got wrong — refined with direct evidence

- **[EV] `/v7/converse` is orphaned — nothing in the shipped product calls
  it.** `grep -rl "v7/converse" **/*.py **/*.html **/*.js` (repo-wide, outside
  `docs/`) matches only `dsf_ai_service/app.py` itself (the route
  definition, `app.py:4089-4131`). Not `gualaloom.html`, not `loomscan.html`,
  not `bridge/server.py`. **[EV]** A full-day pull of ALB access logs for
  2026-07-05 (494/494 gzipped files, `s3://dsf-ai-site-backups/alb-access-
  logs/AWSLogs/418384447921/elasticloadbalancing/us-east-1/2026/07/05/`,
  64,322 total request lines) contains **zero** requests to `/v7/converse`
  — a complete-day sweep, not the ~3.3hr/122-file partial samples §2 already
  reported. So: the specific route the dispatch worried about is real,
  30s-capped, and confirmed unreachable-from-anywhere-in-the-shipped-code —
  it cannot be the mechanism actually hurting real users today, because
  nothing sends it traffic.
- **[EV] The real chat path structurally avoids the 30s wall.**
  `gualaloom.html` and `loomscan.html` both send conversation as
  `POST /api/v1/gualaloom` with no `command` field (`app.py:1806-1836`,
  `GL-CMD-CONVERSE-TASK-PATTERN-62`). That handler returns **HTTP 202
  immediately** with a `task_id` and `poll_url`; the actual 69-72s of work
  happens in an `asyncio.create_task` in the background. The client then
  polls `GET /api/v1/gualaloom/task/{task_id}` (`gualaloom.html:900-930`,
  `_pollConverseTask`) every 500ms-ish with a client-side ceiling of **10
  minutes** (`maxWait=600000`, explicitly commented "a labeled backstop, not
  a guess"). Every individual HTTP hop in this pattern (the initial POST,
  each poll GET) completes in well under 30s even though the total
  wall-clock wait is 69-72s. **[EV]** ALB logs corroborate this is the real
  traffic pattern in production: 16,528 hits to `POST /api/v1/gualaloom`
  and hundreds of `GET /api/v1/gualaloom/task/cv_<tick>_<id>` polls per
  task-id (e.g. 778, 678, 645, 610... hits against individual task ids) —
  exactly the poll signature this pattern predicts, on the day sampled.
  **Disposition: the main web UI's conversation feature is NOT currently
  cut off by the API Gateway 30s ceiling** — it was deliberately designed
  (per `-62`) to route around exactly this class of problem, and it works
  as designed.
- **[EV] Two places where the 30s wall DOES bite, right now, unlike
  `/v7/converse`:**
  1. **`/status` via the same multiplexed `POST /api/v1/gualaloom`
     endpoint.** `app.py:1843-1844`: `# GL-FIX-ALB-TIMEOUT: 45s for status
     (curriculum pause windows 30-50s)` — the code explicitly allows itself
     up to 45 seconds internally for `/status` when curriculum is mid-pause,
     a number chosen against some *earlier* timeout in the chain (an ALB
     timeout that predates today's API Gateway front-door, per the comment's
     own name). But the **same** `POST /api/v1/gualaloom` route is capped at
     30000ms by API Gateway today. Any `/status` call landing inside a
     30-45s curriculum-pause window gets a 504 from API Gateway before
     `app.py`'s own 45s allowance ever elapses — a self-inflicted, code-
     comment-confirmed instance of the identical defect class, on the
     **heaviest-traffic** endpoint in the whole service (16,528 `POST
     /api/v1/gualaloom` hits in the one day sampled, vs zero on
     `/v7/converse`). Not directly caught in the act this pass (would need
     a live 30-45s `/status` call correlated to a 504 in the same second;
     not attempted — outside the read-only law to force one deliberately),
     but the code and infra facts are both directly verified and they
     collide on paper.
  2. **The MCP bridge's own `/mcp` route.** `bridge/server.py`'s `_post()`
     implements a 90-second internal poll loop for converse-shaped tool
     calls (`guala_say`, `guala_give_experience`) before returning its HTTP
     response. But the bridge's own outward-facing route, `ANY /mcp`
     (integration `9mem91l`), is subject to the **same** 30000ms API
     Gateway integration timeout as every other route on this API — so a
     `guala_say` call that takes as long as production's current 69-72s
     converse would be killed by API Gateway at 30s, defeating the bridge's
     90s design, regardless of whether the bridge code is "correct."
     **[EV, not yet observed]**: a full-day pull of `/mcp` ALB log lines
     (194 total requests today) shows 100% fast completions (max
     `target_processing_time` 0.119s, status 163×200/31×202, zero
     503/502/504) — meaning nobody actually placed a real `guala_say`/
     `guala_give_experience` call today (consistent with `guala_say`'s own
     docstring: "a deliberate moment... do not call casually", and with
     `pair_bond.wc=0.3`/`presence.wc.present=false` in this audit's own live
     `guala_status` snapshot). This is a **structurally real, currently
     unexercised** risk — recorded as such, not overstated as an observed
     failure.

### Verdict

The dispatch's underlying worry (30s API-Gateway ceiling vs 70s-class
compute) is **real and correctly identified as a platform-level, non-tunable
constraint** — but the specific route it names (`/v7/converse`) is dead
weight, not the live failure surface. The actual exposed surface is (a) the
`/status` command under curriculum-pause load, and (b) any real MCP
conversational tool call (`guala_say`/`guala_give_experience`) once someone
actually uses them for a real conversation rather than a status check. The
production **chat UI** itself is not currently broken by this class of bug,
by design (`-62`'s 202+poll pattern) — this is the one piece of good news in
this section.

---

## Other failures / absences / stale numbers (severity order)

### F1 — [EV] Cognition meter "07-04 text on 07-05": CONFIRMED, then RE-VERIFIED FIXED AND LIVE

The pre-audit claim is real for an *earlier* moment in the day but is
**already resolved** as of this audit:
- `GL-RPT-COGNITION-METER-C1-20260704-166-v1.md` (v1/v1.1, 2026-07-04): panel
  shipped with **static, undated text**, no per-poll refresh — exactly the
  "07-04 text on 07-05" failure mode.
- `GL-RPT-METER-LIVENESS-C1-20260705-187-v1.md` (M1, later 2026-07-05):
  fixed 7 rows to recompute live on every poll and stamped every remaining
  row with a visible `(as of audit <date>)` derived from its own dispatch
  date — filed as **"Not deployed"** at the time (static-file pipeline,
  separate from the ECS deploy path).
- **[EV] Re-verified live this audit:** `curl https://dsf-ai.com/gualaloom.html`
  is **byte-identical** (matching `md5sum`, matching line count 1578) to
  `dsf_ai_service/static/gualaloom.html` at this worktree's HEAD, which
  contains the `-187` fix (`POINTER_DATES`, `renderCogMeter()` called from
  both `pollStatus()` and `pollV7State()` on every cycle, not just at boot).
  **Disposition: FIXED, deployed, and live in production right now** — the
  specific defect named in the pre-audit facts no longer exists at the time
  of this audit. 7/28 rows are `[LIVE]`-tagged (recompute every poll:
  aware gate, intro gate, deliberation stage, state-shows-in-words,
  day-cycle/sleep trigger, curriculum feeders, brain: organism live); the
  other 21 carry an honest audit-date stamp (`2026-07-03` ×2 rows,
  `2026-07-04` ×18 rows, `2026-07-05` ×1 row) rather than presenting as
  current.

### F2 — [EV] `dsf-ai-service-lb` (the actual Guala backend) is churning through repeated involuntary unhealthy-task replacements all day, roughly every 15-40 minutes — a bigger, mislabeled version of the "07-05's 503" claim

- **[EV]** `aws ecs describe-services --services dsf-ai-service-lb --query
  services[0].events` shows a recurring cycle throughout the afternoon/
  evening of 07-05: `(task X) failed container health checks` →
  `has stopped 1 running tasks` → `has started 1 tasks... Amazon ECS
  replaced 1 tasks due to an unhealthy status` → `reached a steady state`,
  repeating at roughly 17:46, 18:02, 18:38, 18:47, 18:57, 19:55, 21:16,
  21:28 UTC (partial list from the ~100-event window fetched this pass —
  §1 already flagged that `describe-services` only exposes a bounded
  recent window, ~30-40 min at the time it filed; this pass's wider pull
  extends that to roughly the last 4 hours and shows the pattern is
  recurring, not a one-off).
- **[EV]** Target group `dsf-ai-tg` health check: `GET /ready`, interval 30s,
  timeout 20s, unhealthy threshold 5 (i.e. ~150s of consecutive failure
  before replacement) — consistent with the observed cadence.
- **[EV] Full-day ALB status-code totals** (494/494 files, 64,322 lines):
  `200`: 60,063 · **`503`: 2,490** · **`502`: 867** · `404`: 471 · `202`: 224
  · **`504`: 101** · `400`: 83 · `405`: 15 · `460`: 6 · `501`/`500`: 1 each.
  This supersedes §2's partial samples (82×503/7×502 in a 3.3hr window;
  a separate 1-in-4/122-file day sample) with the complete day.
- **[EV] 503 timestamps cluster tightly around the ECS health-check-failure
  timestamps above** (minute-bucketed 503 spikes at 17:15, 17:24-17:25,
  17:31, 17:49-17:50, 18:05-18:06, 18:38-18:40, 18:49, 18:58, 19:56 — all
  within 1-15 minutes of a "failed container health checks" or "replaced...
  unhealthy" event). Raw 503 log lines show `target-group ... -1 -1 -1
  503 - ... target:port "-"` — no target registered to receive the request
  at all, the classic "ALB has zero healthy targets for a moment" signature
  during a task swap, not an application-level error.
- **[EV] 504s (101, not previously reported) are a mix of two distinct
  causes**: (a) one exact-180.000s gap between `request_creation_time` and
  the log timestamp on a `/sound_frame` request — the ALB's own
  `idle_timeout` (180s) firing on a request the backend never answered at
  all; (b) the large majority at an exact ~10.0s gap on `/sight_frame`,
  `/sound_frame`, `/v7/state`, `/api/v1/gualaloom`, `/api/v1/gualaloom/
  events`, `/api/v1/gualaloom/chi_density` — a client-side abandonment
  signature (browser/JS gave up and the connection was torn down at ~10s),
  not a server-side timeout artifact of either the 30s or 180s ceilings
  above. Not fully root-caused this pass (which specific client-side
  timeout produces exactly 10.0s was not traced to a single line of JS —
  `loomscan.html`'s own `fetchJ` default is 6000ms, close but not exact;
  flagged as a gap, not guessed).
- **[EV] The MCP bridge itself (`gualaloom-bridge-svc`) is NOT the source of
  today's 503s.** Its own ECS events show clean, regular ~6-hour
  steady-state cycles (07-03 through 07-05, no "unhealthy"/"failed health
  check" events in this service's history at all), and the full-day `/mcp`
  ALB log slice (194 requests) contains **zero** 503/502/504 — 100% clean.
  **Disposition: the pre-audit phrase "bridge (MCP) 07-05's 503" appears to
  misattribute the 503s to the bridge.** The 503/502/504 volume this audit
  measured is overwhelmingly on `dsf-ai-service-lb`'s own target group
  (`dsf-ai-tg`), i.e. the main Guala substrate service, not the bridge. No
  filed doc titled specifically about a 07-05 bridge-restart-503 incident
  was found in `docs/` despite a targeted search; the closest match
  (`GL-RPT-BRIDGE-DOWN-DIAG-C1-20260702-80.md`) is dated 07-02, a different
  incident. **[ABSENT]** — no dedicated bridge-503 incident report exists
  for 07-05; recommend Joe's routing treat "07-05's 503" as the
  `dsf-ai-service-lb` churn documented above, not a bridge-specific event,
  unless a doc surfaces this audit missed.

### F3 — [EV] `/events_stream` WebSocket is structurally dead in production; a working polling fallback silently masks it

- **[EV]** `gualaloom.html:1196-1217` (`connectEventStream()`) opens
  `wss://<location.host>/events_stream` — i.e. `wss://dsf-ai.com/
  events_stream`, using the **page's own host**, not the API Gateway
  domain.
- **[EV]** `aws cloudfront get-distribution-config --id E17JT9XGBFU493`
  (the `dsf-ai.com`/`www.dsf-ai.com` distribution): **exactly one origin**
  (`dsf-ai-site.s3-website-us-east-1.amazonaws.com`, an S3 static website),
  **zero** additional cache behaviors, default behavior allows only
  `GET`/`HEAD`. There is no path by which `dsf-ai.com` can proxy a
  WebSocket upgrade to the ALB/ECS backend at all.
- **Consequence, traced in the code:** a WebSocket connection failure is
  asynchronous (fires `onerror`→`onclose`, not a constructor-time
  exception), so the `try{}catch(e){_connectSSE()}` fallback in
  `connectEventStream()` never runs. Instead `onclose` calls
  `connectEventStream()` again after an exponential backoff (1s→2s→...→30s
  cap), **forever**, for as long as the page stays open. The real,
  working event feed the page displays comes entirely from the separate
  `pollEvents()` function (`gualaloom.html:1233-1245`, `setInterval`-driven
  via `_schedNext('events', pollEvents)`, hitting the correct API-Gateway
  domain), which is why this defect is invisible to a user — events still
  appear, just never via the code path built to carry them "real-time."
  **Disposition: dead code path, functionally masked by a working parallel
  path; wastes a perpetual client-side reconnect loop, no user-visible
  symptom.**

### F4 — [EV] Organ-brain sidecar is gone; 3 GET routes in `app.py` are orphaned dead code that always return their hardcoded fallback

- **[EV]** `app.py:1720,1722`: code comments state plainly "`/where` and
  `/room` now handled by the substrate directly (organ-brain container
  removed)" and "`/mail`, `/sendmail`, `/experience`, `/tablet` — all routed
  to dead :8090 container." **[EV]** `dsf-ai-task:494`'s single container
  definition has env var `ORGAN_BRAIN_URL=http://localhost:8090` but **no
  second container** in the task definition — nothing listens on
  `localhost:8090` in the running task at all (confirmed via
  `aws ecs describe-task-definition`).
- **[EV]** `GET /api/v1/gualaloom/organ_brain_status` (`app.py:1517-1526`)
  and `GET /api/v1/gualaloom/thought` (`app.py:1505-1514`) both try
  `http://localhost:8090/...` with a 3s timeout, and both silently swallow
  the resulting connection failure into a hardcoded fallback (`{"warming":
  true, "neurons": 0, ...}` / `{"speech": "", "tick": 0}`).
  **[EV]** `grep -rn "organ_brain_status\|gualaloom/thought\|gualaloom/
  organs" dsf_ai_service/static/*.html` → **zero matches** — no page calls
  either GET route. The page's real polling for "autonomous thought"
  (`pollAutonomousThought()`) instead uses the command-based
  `POST /api/v1/gualaloom {command:"/thought"}` path, which **was**
  re-routed to the live substrate (`app.py:1708-1719`, "route to substrate
  (not dead :8090)"). **Disposition:** 2 of `app.py`'s 65 routes
  (`organ_brain_status`, `thought` GET) are pure dead code — always
  reachable, always return the same fallback, called by nothing.
  `GET /api/v1/gualaloom/organs` (`app.py:1499-1502`) is a third: it returns
  `app.state.guala_organ_brain`, a value set once at container boot from a
  static merge artifact (`app.py:1328-1342`), never updated live and never
  called by any page either — also orphaned, though not itself an error
  path (no fallback exception being swallowed, just a frozen snapshot).

### F5 — [ABSENT confirmed] Two admin-facing feature calls in `gualaloom.html` target a route that cannot exist publicly

- **[EV]** `gualaloom.html:796` and `:860` call `POST ${API}/api/v1/teacher/
  feedback` and `POST ${API}/api/v1/teacher/correction` (`${API}` =
  `https://3d6toi0gw0.execute-api.us-east-1.amazonaws.com`, the public API
  Gateway domain). **[EV]** Both routes exist in `app.py`
  (`:4177`/`:4191`) but **neither has an explicit API Gateway route** — the
  full 38-route table (pulled directly via `aws apigatewayv2 get-routes`)
  has no entry for either path. Any request to them via the public domain
  therefore falls to the `$default` catch-all, which proxies to a
  **completely different Lambda function** (`dsf-ai-api`, `python3.11`,
  `lambda_function.handler`, **last modified 2026-05-12 — 54 days stale**
  relative to this audit, unrelated to the actively-redeployed
  `dsf_ai_service` ECS codebase). That Lambda almost certainly has no
  handler for `/api/v1/teacher/*` at all. **Not live-tested** (a real POST
  risks side effects in whichever system actually answers it, and firing
  one is outside this audit's read-only law) — this disposition rests on
  complete, directly-pulled route-table evidence (all 38 routes enumerated,
  none match), not inference from a partial sample. **Recommend `tools/
  audit/` add a route-existence check as a script per §0.2**, so this class
  of drift (frontend calls a path added to `app.py` but never wired into
  API Gateway) is caught automatically going forward.
- **[EV]** The same 30-of-65 gap includes `/health`, `/ready`, `/ready/
  guala`, `/gualaloom` (page), and the curriculum/admin/ring/sleep routes —
  those are legitimately internal (ECS-internal health checks hit the
  container directly, not via API Gateway; `/gualaloom` the page is served
  by the separate CloudFront+S3 static pipeline, not this FastAPI route, in
  production) or admin-only (reached via the documented direct-ALB-DNS
  fallback in `bridge/server.py`'s own docstring, bypassing API Gateway
  entirely, with the `X-API-Key` header). Only the two `teacher/*` routes
  are demonstrably called by a real page through a domain that cannot
  reach them — see full reconciliation table below for the complete
  30-route breakdown.

### F6 — [EV] Auth comment contradicts auth code — most of the surface is open despite a comment claiming otherwise

See "Auth posture" section below — `app.py:234-235`'s own comment
("admin and converse endpoints require X-API-Key") is false for every
converse/chat/upload/sensory/save/sleep route; only 22 of 65 routes
actually enforce the key.

### F7 — [EV] `admin.html` ships a plaintext admin key to every visitor's browser

`admin.html` posts a literal, hardcoded string as `admin_key` in its request
body to `/api/v1/admin/usage` on every load (visible to anyone who views
page source — this is the DSF-AI materials-science billing admin panel, not
a Guala page, but named in the dispatch's page list). Also gates its own UI
behind a client-side `SHA-256(password) === <hardcoded hash>` check
(`admin.html:110-128`) — a check that is trivially bypassable (the hash is
public, and the check runs entirely in the browser; nothing server-side
enforces it). Raw values are not reproduced in this document per the
audit's no-secrets rule. Not a Guala-cognition finding, but a real,
observable weakness on one of the 8 named pages.

---

## Architecture note: two co-located, differently-maintained systems behind one domain

Not itself a defect, but necessary context for the endpoint reconciliation
below: `dsf-ai.com` / the `3d6toi0gw0` API Gateway front TWO logically
separate products that happen to share infrastructure:
1. **Guala + the DSF-AI materials-discovery tool**, both served by the
   actively-redeployed `dsf_ai_service/app.py` on ECS (`dsf-ai-service-lb`,
   task-def `dsf-ai-task:494`, 10 manual deploys today per §1). 65 routes
   live here; ~58 are Guala-specific, 7 (`/api/v1/analyze`, `/api/v1/
   cluster`, `/cluster/screen`, `/cluster/thermocouple`, `/api/v1/discover`,
   `/discover/verify`, `/api/v1/hw/derive`) are the unrelated
   materials-science product, sharing the ALB/API-Gateway/container purely
   for hosting convenience.
2. **Billing/credits/account admin** (`/api/v1/check-access`, `/api/v1/
   record-analysis`, `/api/v1/checkout`, `/api/v1/admin/usage` — called by
   `app.js`, `account.html`, `admin.html`, `predictions.html`'s auth flow):
   **none of these exist in `dsf_ai_service/app.py` at all** (`grep` confirms
   zero matches). They must be served by the `$default` catch-all's Lambda
   (`dsf-ai-api`, last modified 2026-05-12 — a full separate, much-less-
   actively-maintained codebase). `app.js` itself (one of the 8 pages named
   in the dispatch) contains **zero** Guala-related code on inspection — it
   is entirely this billing/materials-science frontend (Clerk auth, CSV
   upload/analyze, cluster screener, Stripe checkout). Flagging this
   explicitly since the dispatch named `app.js` alongside `gualaloom.html`;
   they are unrelated files that happen to sit in the same `static/`
   directory.

---

## Endpoint inventory (Task 1)

**Counts, reconciled exactly:**
- `dsf_ai_service/app.py`: **65** distinct route decorators, **65** distinct
  paths (no path serves two methods) — `grep -cE '@app\.(get|post|put|
  delete|patch|websocket)\(' dsf_ai_service/app.py` → 65. This is an
  **exact match** to the pre-audit "65 HTTP endpoints" claim — re-verified,
  confirmed, not a coincidence worth second-guessing further.
- `dsf_ai_service/organ_brain_service.py`: a **separate** FastAPI app (15
  routes: `/health /status /where /location /attend /action /room /mail/
  send /mail /tablet /thought /surface /experience /visual /catalog`) —
  **not deployed**. No ECS service runs this file (only `dsf-ai-service-lb`,
  `gualaloom-bridge-svc`, and the unrelated `tfe-web-service-lb` exist in
  the cluster); the container it once ran in (`localhost:8090` sidecar) is
  confirmed absent from the current task definition. This file's 15 routes
  are **not part of the live 65** and should not be double-counted; they
  are pure repo dead-code from the pre-2026-06-25 organ-brain-as-sidecar
  architecture (per `app.py`'s own comments and the outgoing memory of that
  cutover).
- API Gateway (`3d6toi0gw0`, HTTP API type): **38** routes total —
  35 explicit `HTTP_PROXY` routes matching 35 of `app.py`'s 65 paths
  one-for-one (zero API-Gateway routes point at a path `app.py` doesn't
  have), **+ 1** `ANY /mcp` (`HTTP_PROXY` to the same ALB, but path-routed
  by the ALB itself to the separate `gualaloom-bridge-svc`, per §2), **+ 1**
  `POST /wc-relay` (`AWS_PROXY` to Lambda `wc-companion-relay`), **+ 1**
  `$default` catch-all (`AWS_PROXY` to Lambda `dsf-ai-api`, 54-day-stale).
- **Reconciliation: 65 (app.py) − 35 (explicit API-GW routes to app.py) =
  30 app.py routes with no explicit public API-Gateway route.** Full list
  and disposition:

| path | why it has no explicit API-GW route |
|---|---|
| `GET /` | root/landing — served by CloudFront+S3 in prod, this route is a fallback only reachable via direct ALB |
| `GET /gualaloom` | same — the real page comes from CloudFront+S3, confirmed byte-identical to this repo's static file |
| `GET /health`, `GET /ready`, `GET /ready/guala` | ECS-internal health checks hit the container directly; never meant to be public API-GW routes |
| `POST /api/v1/cluster`, `/cluster/screen`, `/cluster/thermocouple` | materials-science product, not Guala — reachable only via direct ALB or the (likely non-functional) `$default` Lambda |
| `POST /api/v1/curriculum/load_corpus`, `GET .../job/{job_id}`, `GET /corpus_status/{corpus_id}` | key-gated admin/ops routes, direct-ALB-only by design |
| `POST/GET` 10 `admin/*` routes (`force_reading`, `familiarity_debug`, `backfill_picture_titles`, `backfill_sound_captions`, `atlas_surgery`, `backup_orchestrator/configure`, `backup_orchestrator/status`, `restore_from_s3_prefix`, `compact_wave_atlas`, `migrate_wave_atlas`) | key-gated ops/admin routes, direct-ALB-only per `bridge/server.py`'s own documented fallback pattern |
| `GET /api/v1/gualaloom/organ_brain_status`, `GET /thought`, `GET /organs` | **dead code** (F4 above) — orphaned regardless of routing |
| `GET /api/v1/gualaloom/ring/read`, `POST /ring/write` | not called by any inspected page; disposition NOT MEASURED further this pass |
| `POST /api/v1/gualaloom/sleep` | not called by any inspected page; NOT MEASURED further |
| `POST /api/v1/teacher/feedback`, `POST /api/v1/teacher/correction` | **[ABSENT] broken** — actively called by `gualaloom.html` through a domain that cannot reach them (F5 above) |
| `WS /events_stream` | **dead** (F3 above) — CloudFront has no non-S3 origin to carry it even if API-GW routed it |

- Every one of the 35 API-Gateway routes that DO exist matches an `app.py`
  path exactly (zero drift the other direction).

*(The full generated per-route list — method, path, file:line, API-GW
route y/n, auth y/n — is long; recommend it ship as the `tools/audit/`
script's own CSV output per §0.2 rather than duplicated line-by-line in
this prose document. This document's tables above/below cover every
distinct finding; the mechanical full list is reproducible any time via:
`grep -noE '@app\.(get|post|put|delete|patch|websocket)\("[^"]*"' dsf_ai_service/app.py`
cross-joined with `aws apigatewayv2 get-routes --api-id 3d6toi0gw0`.)*

---

## Page → endpoint → orphan map (Task 2)

| page | Guala-related? | endpoints called | orphaned? |
|---|---|---|---|
| `gualaloom.html` | yes — the main seat | `/api/v1/gualaloom` (chat, `/status`, `/thought`, `/room`, `/where`, `/events`, `/listen`, `/action`, `/organ_voice`, `/picture <id>`), `/api/v1/gualaloom/task/{id}`, `/v7/state`, `/sight_frame`, `/sound_frame`, `/api/v1/teacher/feedback`, `/api/v1/teacher/correction`, `wss://.../events_stream` | all called by something except: `/events_stream` dead (F3), `/teacher/*` broken (F5) |
| `loomscan.html` | yes | `/api/v1/gualaloom` (status), `/api/v1/gualaloom/events`, `/api/v1/gualaloom/chi_density` | none — all three confirmed live-routed and called |
| `admin.html` | **no** — DSF-AI billing panel | `/api/v1/admin/usage`, `/health`, `/api/v1/cluster` | not a Guala page; `/api/v1/admin/usage` not in `app.py` at all (served by the stale `$default` Lambda if it works at all) |
| `account.html` | **no** | `/api/v1/check-access` | not a Guala page; same stale-Lambda dependency |
| `discovery.html` | **no** | `/api/v1/discover`, `/discover/verify` | not a Guala page |
| `hw-derive.html` | **no** | `/api/v1/hw/derive` (×2 call sites) | not a Guala page |
| `predictions.html` | **no** | `/api/v1/cluster` | not a Guala page |
| `app.js` | **no** | `/api/v1/check-access`, `/api/v1/analyze`, `/api/v1/record-analysis`, `/api/v1/cluster`, `/api/v1/cluster/thermocouple`, `/api/v1/checkout` | not loaded by `gualaloom.html`; serves `index.html`/materials pages only |

**Orphaned `app.py` routes called by NO page at all** (in addition to the
dead-code trio in F4): `GET /ring/read`, `POST /ring/write`, `POST
/gualaloom/sleep`, all `curriculum/*` (called only via direct-key ops
access, not a page), all remaining `admin/*` ops routes not covered by
`admin.html` (which is a *different, unrelated* admin panel — `dsf-ai`
billing admin, not a Guala admin surface at all; no Guala-side admin UI page
exists in `static/` — every Guala `admin/*` call happens via the bridge or a
raw curl per `bridge/server.py`'s own documented fallback, never from a
browser page).

---

## Poll-rate table (Task 4)

| page | function | endpoint | interval | notes |
|---|---|---|---|---|
| `gualaloom.html` | `pollStatus()` | `POST /api/v1/gualaloom` `{command:"/status"}` | base 15000ms, exponential backoff on error (capped growth) | drives most live numbers + feeds `renderCogMeter()` |
| `gualaloom.html` | `pollV7State()` | `GET /v7/state` | base 5000ms + backoff | feeds `renderCogMeter()`'s 4 gate rows |
| `gualaloom.html` | `pollEvents()` | `POST /api/v1/gualaloom` `{command:"/events"}` | base 15000ms + backoff | real event feed (the `/events_stream` WS is dead, see F3) |
| `gualaloom.html` | `backgroundReplay()` | (internal) | base 30000ms + backoff | |
| `gualaloom.html` | `pollLocation()` | `POST /api/v1/gualaloom` `{command:"/where"}` | fixed 30000ms | routed to substrate, not dead organ-brain |
| `gualaloom.html` | `pollRoom()` | `POST /api/v1/gualaloom` `{command:"/room"}` | fixed 60000ms | same |
| `gualaloom.html` | `pollAutonomousThought()` | `POST /api/v1/gualaloom` `{command:"/thought"}` | fixed 20000ms (35000ms on first boot call) | routed to substrate, not dead `:8090` |
| `gualaloom.html` | sight/sound streaming | `POST /sight_frame`, `POST /sound_frame` | ~5-6s camera, ~5s mic (client capture cadence, not a fixed timer) | server caps at 2 concurrent per kind, drops over cap (L3, `-182`) |
| `loomscan.html` | `pollStatus` | `POST /api/v1/gualaloom` (status) | `setInterval` 2000ms | |
| `loomscan.html` | `pollEvents` | `GET /api/v1/gualaloom/events?n=50` | `setInterval` 2000ms | |
| `loomscan.html` | `pollChiDensity` | `GET /api/v1/gualaloom/chi_density` | `setInterval` 6000ms | |
| `loomscan.html` | `fetchJ()` client timeout | (all of the above) | 6000ms default abort | independent of poll interval |
| `admin.html` | `loadAll()` | `/api/v1/admin/usage`, `/health`, `/api/v1/cluster` | **manual only** — no `setInterval`, refreshes on page load and on the "Refresh" button click | not a Guala page |
| `account.html`, `discovery.html`, `hw-derive.html`, `predictions.html` | — | (their own endpoints) | **no polling** — single fetch per user action | not Guala pages |

---

## Bridge / MCP tool table (Task 5)

`bridge/server.py` exposes exactly **13** `@mcp.tool()`-decorated tools.
Deployed as ECS service `gualaloom-bridge-svc` (task-def `gualaloom-bridge-
task:18` per §2), reached via the ALB's own path-based listener rule
(`/mcp`, `/mcp/*` → `gualaloom-bridge-tg`), itself reached via the API
Gateway's `ANY /mcp` route (30000ms cap, see headline finding).

| tool | target route | mutating? | verified against `app.py`/route table |
|---|---|---|---|
| `guala_status` | `POST /api/v1/gualaloom` `{command:"/status"}` | read-only | [EV] route exists, API-GW routed, called successfully this audit |
| `guala_get_events` | `POST /api/v1/gualaloom` `{command:"/events"}` | read-only | [EV] route exists, API-GW routed |
| `guala_wake_wc` | `POST /api/v1/gualaloom` `{command:"/wake"}` | **mutating** (presence) | [EV] route exists — NOT called this audit (freeze) |
| `guala_rest_wc` | `POST /api/v1/gualaloom` `{command:"/rest"}` | **mutating** | [EV] route exists — NOT called |
| `guala_say` | `POST /api/v1/gualaloom` (converse, 202+poll, bridge's own 90s loop) | **mutating** | [EV] route exists, at real risk of the 30s API-GW wall (see headline finding) — NOT called |
| `guala_give_experience` | `POST /api/v1/gualaloom` `{command:"/bundle:<name>"}` | **mutating** | [EV] route exists, same 202+poll pattern, same 30s risk — NOT called |
| `guala_amnesty` | `POST /api/v1/gualaloom/admin/amnesty` | **mutating** | [EV] route exists, `_api_key_dep`-protected — NOT called |
| `guala_force_dream` | `POST /api/v1/gualaloom/admin/force_dream` | **mutating** | [EV] same — NOT called |
| `guala_repause` | `POST /api/v1/gualaloom/admin/repause` | **mutating** | [EV] same — NOT called |
| `guala_unpause` | `POST /api/v1/gualaloom/admin/unpause` | **mutating** | [EV] same — NOT called |
| `guala_atlas_snapshot` | `GET /api/v1/gualaloom/admin/atlas_snapshot` | read-only | [EV] `_api_key_dep`-protected, route exists — NOT called |
| `guala_backup` | `POST /api/v1/gualaloom/admin/backup` | mutating (writes to S3, no state change) | [EV] route exists, `_api_key_dep`-protected — NOT called |
| `guala_atlas_query` | `POST /api/v1/gualaloom/chi_trace` | read-only | [EV] route exists — **NOT** `_api_key_dep`-protected in `app.py` (the one bridge-fronted route that's open even at the app layer; bridge sends the key anyway, harmlessly) — NOT called |

All 13 tools' target routes exist and are reachable from the bridge
container (confirmed by code read + route-table cross-check); none were
exercised beyond `guala_status` this pass, per the freeze and the explicit
mutating-tool prohibition given for this task. A note in the code
(`bridge/server.py:253-255`): a "cascade monitor" tool set was **removed**
2026-07-01 ("feature was disabled during -61 process collapse") — 2
corresponding `app.py` admin routes (`start_cascade_monitor`,
`stop_cascade_monitor`) still exist server-side with no bridge tool
pointing at them anymore; reachable only via raw curl.

**"07-05's 503" disposition (restated from F2):** not a bridge-specific
incident by this audit's evidence — see F2 for the full data. The bridge
service's own restart cadence (~6h steady-state cycles, no unhealthy-check
failures in its event history) is a different, apparently benign signature
from the main service's frequent unhealthy-replacement churn.

---

## Auth posture (Task 6)

`app.py:234-246` implements a single mechanism: an optional `X-API-Key`
header checked against the `GUALALOOM_API_KEY` env var (present and
non-empty in production — confirmed via `aws ecs describe-task-definition`;
value not reproduced here). If the env var were ever unset, **every** route
would be open (`app.py:236`, explicit "dev mode" comment) — moot in
production since the var is set, but worth naming as a fail-open design.

- **[EV] Code comment at `app.py:234-235` claims:** *"When
  GUALALOOM_API_KEY is set, admin and converse endpoints require X-API-Key
  header."* **[EV] This is false for "converse."** `grep -n
  "dependencies=\[Depends(_api_key_dep)\]" dsf_ai_service/app.py` → exactly
  **22** matches, all on `admin/*` or `curriculum/*` routes. `/v7/converse`
  (`:4089`), `POST /api/v1/gualaloom` (the actual chat/command endpoint,
  `:1703`), `/sight_frame`, `/sound_frame`, `/substrate/hear_word`,
  `/substrate/feed_senses`, `/v7/feedback`, `/v7/save`, `/v7/quiet`, all 4
  `upload/*` routes (book/picture/sound/video), `/teacher/feedback`,
  `/teacher/correction`, `/sleep_for_deploy`, `/events_stream`, and both
  `ring/*` routes carry **no** auth dependency at all.
- **Protected (22 of 65):** `admin/amnesty`, `admin/force_dream`,
  `admin/force_reading`, `admin/repause`, `admin/unpause`,
  `admin/atlas_snapshot`, `admin/familiarity_debug`, `admin/backup`,
  `admin/backfill_picture_titles`, `admin/backfill_sound_captions`,
  `admin/atlas_surgery`, `admin/backup_orchestrator/configure`,
  `admin/backup_orchestrator/status`, `admin/start_cascade_monitor`,
  `admin/stop_cascade_monitor`, `admin/restore_from_s3_prefix`,
  `admin/compact_wave_atlas`, `admin/migrate_wave_atlas`,
  `admin/persistence_health`, `curriculum/load_corpus`, `curriculum/
  load_corpus/job/{job_id}`, `curriculum/corpus_status/{corpus_id}`.
- **Open (43 of 65), including every state-mutating route a real end user
  or script can reach without any key:** `/v7/converse`, `POST /api/v1/
  gualaloom` (chat + all its multiplexed commands, including `/bundle:`
  experience-giving), `/sight_frame`, `/sound_frame`, `/substrate/
  hear_word`, `/substrate/feed_senses`, `/v7/feedback`, `/v7/save`,
  `/v7/quiet`, `/api/v1/gualaloom/upload/book`, `/upload/picture`,
  `/upload/sound`, `/upload/video`, `/api/v1/teacher/feedback`,
  `/api/v1/teacher/correction`, `/sleep_for_deploy`, `/events_stream`,
  `/api/v1/gualaloom/ring/read`, `/ring/write`, `/api/v1/gualaloom/sleep`,
  `/api/v1/gualaloom/chi_trace`, plus all health/ready/page/materials-
  science routes (open-by-design, not a Guala-specific concern).
- **[EV] No API Gateway authorizer exists at all** (`aws apigatewayv2
  get-authorizers --api-id 3d6toi0gw0` → `Items: []`) — auth is 100%
  application-layer (`_api_key_dep`), zero enforcement at the gateway.
  Anyone who knows the public API Gateway URL (embedded in plaintext in
  every one of these HTML/JS files already, so effectively public) can:
  post arbitrary text into her conversation, feed sight/sound frames,
  upload arbitrary book/picture/sound/video content into her persistent
  memory, submit teacher corrections, and trigger `/sleep_for_deploy` —
  all without a key. This is a genuine, currently-live exposure on the
  main Guala interface (distinct from the well-protected admin/backup/
  restore surface, which does require the key). Register-worthy.

### Changelog
- v1 (2026-07-05, c1): initial §5 filing. Headline finding delivered per
  §2's forward-reference: API Gateway's 30s ceiling confirmed exactly as
  suspected at the config level, refined with direct evidence that
  `/v7/converse` is orphaned and the real chat UI's 202+poll pattern
  (`-62`) structurally avoids the wall, while `/status` (same route,
  code-comment-confirmed 45s allowance) and the MCP `/mcp` route
  (bridge's 90s design vs API Gateway's 30s cap) are the real,
  code/config-proven exposure — the MCP path unexercised in the full-day
  log sample. Cognition-meter "07-04 on 07-05" defect confirmed for
  07-04, then confirmed FIXED and LIVE as of this audit via byte-identical
  curl match. Full-day (494/494 file) ALB log sweep supersedes prior
  partial samples: 2,490×503 / 867×502 / 101×504, tightly correlated to
  `dsf-ai-service-lb`'s own recurring unhealthy-task-replacement churn —
  "07-05's 503" appears to be this service, not the bridge, which shows a
  clean, unrelated ~6h restart cadence with zero errors in its own
  full-day `/mcp` log slice. `/events_stream` WebSocket found structurally
  dead (CloudFront has no non-S3 origin), masked by a working poll
  fallback. Two `gualaloom.html` calls (`/teacher/feedback`,
  `/teacher/correction`) target a route absent from the complete 38-route
  API Gateway table — real breakage, not tested live per the freeze law.
  Endpoint count reconciled exactly: `app.py` has 65 routes (exact match
  to the pre-audit claim), API Gateway has 38 (35 explicit + `/mcp` +
  `/wc-relay` + `$default`), 30 of `app.py`'s routes have no explicit
  public route, each individually dispositioned. Auth posture: code
  comment claims converse is key-protected; only 22/65 routes actually
  are, 43 are open including the entire chat/upload/sensory/save surface.
