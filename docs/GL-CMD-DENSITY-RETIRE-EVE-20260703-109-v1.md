# GL-CMD-DENSITY-RETIRE-EVE-20260703-109-v1

doc_id: GL-CMD-DENSITY-RETIRE-EVE-20260703-109-v1
From: Eve | To: c1b (rides the -108 consolidated deploy vehicle)
Type: CMD — retire the 65-A density engine; fix bundle attribution;
dedupe input-ring consumer.
E-signature declaration: none — removes counterfeit E-signature
  inflation. Bundle-driven E1/E6 counts to date are partially
  machine-hammered; honesty correction, not capability change.
Substrate-truth declaration: REMOVES an ungated automation (presence
  gate bypassed by --no-gate) and a false source attribution ("joe"
  hardcoded on machine-delivered bundles — counterfeit pair-bond
  events). Adds one idempotency guard. No cognition-path changes, no
  constants.
Supersession note: 65-A (density engine autostart) was legitimately
  dispatched pre-spec; GL-SPC-EXPERIENCE-FIRST v2.0 §8/P1/P3 now
  governs and this CMD retires it under that authority. Joe holds veto.

## Step 0 — durability
Commit THIS file verbatim to docs/ before implementing.

## Findings being fixed (from live events + source trace, 2026-07-03)
F1  _start_curriculum_orchestrator autostarts every boot
    (CURRICULUM_AUTOSTART default "1"), cycles tools/curriculum_seed.
    json (100 bundles) at 5s default interval, --no-gate, infinite
    loop with 60s pass gap. Observed live: moon-001/002/003 repeating;
    resumed ~90s after the unexplained ~20:12Z restart.
F2  The /bundle handler hardcodes _open_response_window("joe", ...) —
    every machine bundle stamps a joe-presence window and joe-tagged
    emission routing. Her bond/salience physics receives synthetic
    joe events continuously.
F3  _start_input_ring_consumer is invoked from TWO call sites (boot
    path AND app startup block) with no started-guard — two drain
    threads contending on her lock.

## Changes
1. Density engine OFF, both switch locations (check every place a
   switch can live):
   a. Code default: CURRICULUM_AUTOSTART default "1" → "0".
   b. Task definition env: CURRICULUM_AUTOSTART=0 explicit.
   The orchestrator script and seed remain in the repo (they are the
   raw material for the future gated Experience Engine — B2 design doc
   with Joe, separate arc). Nothing deleted; the daemon just no longer
   self-starts.
2. Bundle attribution truth: /bundle path accepts a source field;
   response window + emission routing use it. Default when absent:
   "curriculum" — NEVER "joe". Joe attribution only when the request
   genuinely originates from Joe's UI/bridge session (UI passes
   source="joe"; verify the UI call site and set it there explicitly).
3. Ring-consumer idempotency: module-level started flag in
   _start_input_ring_consumer; second call logs
   "[substrate] ring consumer already running" and returns.

## Gates (report, failures first, NOT MEASURED where true)
G-109-1  Post-deploy: zero experience_bundle events over ≥30 min with
         no human sending any (event stream pasted). If any fire, name
         the emitter.
G-109-2  A Joe-sent bundle (his part: one click) opens a joe window; a
         curl-sent bundle with no source opens a "curriculum" window —
         both events pasted verbatim.
G-109-3  Exactly one ring-consumer thread post-boot (thread dump or
         the already-running log line on the second call site).
G-109-4  Boot log shows "[curriculum] autostart disabled by env".
G-109-5  Diff proves scope: orchestrator start gate, bundle source
         plumb, one guard — nothing else.

### Changelog
- v1 (2026-07-03, Eve): initial. From live moon-loop trace →
  substrate_runner orchestrator autostart → seed file match, plus the
  hardcoded joe attribution in the bundle handler and the double
  consumer start. Ruling: spec §8/P1/P3 supersedes 65-A; retire
  pending B2 Experience Engine design with Joe.
