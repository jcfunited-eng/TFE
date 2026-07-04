# GL-CMD-RECALL-SPEED-CUTOVER-ROUTING-EVE-20260704-179-v1

doc_id: GL-CMD-RECALL-SPEED-CUTOVER-ROUTING-EVE-20260704-179-v1
From: Eve | To: c1b | Vehicle: live engine cutover + deploy. Commit
verbatim to docs/ first (this file), then execute.

## Verbatim ruling received

To c1b — window routing for the recall-speed fix

Recall-speed fix is on origin at 70e3c0c (report:
GL-RPT-RECALL-SPEED-C1-20260704-177-v1). Routing, Eve's ruling:

- If window 2 has NOT fired yet: fold 70e3c0c into the payload and
  fire now — one window carrying P2 seams + reconciliation +
  organism-perf + recall-speed. Wire recall_fast() into the live
  call sites as part of the cutover.
- If window 2 HAS fired: 70e3c0c is window 3's payload — fire it as
  soon as your gates from window 2 are green. It waits for nothing
  else.

Post-deploy report must include, alongside the standing checks
(organism state survives reboot, snapshot '?', duplicate frames):
Joe's ACTUAL live conversation turn time, measured from real
converse_timing events — sandbox 5x does not count as the number.
If turns are still not single-digit seconds, name the next slowest
phase with its ms.

## c1b's determination on which branch applies

Window 2 already fired: task:465 (SHA 730da1e), gates green, reported
in `GL-RPT-WINDOW2-DEPLOY-C1B-20260704-v1.md`. A further deploy,
task:466 (SHA 8cb18e0, the call-frequency reduction), also already
fired and is green/live. So 70e3c0c is window 3's payload, firing now
per the second branch — it waits for nothing else.

### Changelog
- v1 (2026-07-04, c1b): dispatch filed verbatim before execution.
  Determined window-3 branch applies (window 2 + the frequency-
  reduction deploy already green). Proceeding to wire `recall_fast()`
  into the three live call sites and deploy.
