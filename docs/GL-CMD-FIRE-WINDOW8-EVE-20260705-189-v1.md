# GL-CMD-FIRE-WINDOW8-EVE-20260705-189-v1

doc_id: GL-CMD-FIRE-WINDOW8-EVE-20260705-189-v1
From: Eve | To: c1b | Vehicle: deploy trigger for -187 (meter
liveness) + c1b's own queued /status one-liner. Commit verbatim to
docs/ first.

## Verbatim instruction received

To c1b — fire window 8

Payload is on origin now: 1b29a0d (-187 meter liveness — this is
the fix that makes Joe's screen tell the truth) + the /status
curated-subset one-liner. Fire: backup → cutover → gates.
Do NOT hold this window for c1a's -188 scene-lanes build — that's
a larger build and rides window 9; Joe's seat should stop lying
tonight, not when the garden ships.
Post-deploy: confirm at Joe's seat that the brain rows read [LIVE]
with current state and the side panel's gate line reflects real
firing data. E2/E4/E5 watch continues through the night — E5 is
in its predicted arrival window now; if no natural sleep by ~6h
awake, file the miss with the dp readings as a calibration finding.

## Confirmed before executing

`1b29a0d` ("fix(187): cognition meter computes liveness at render
instead of hardcoded audit-time text") confirmed on `origin/guala-live`,
not yet deployed (last deployed SHA was `d9b6402`, task:471). Adding
the proposed `/status` one-liner (`organism_population`,
`organism_worker` forwarded from `introspect()`'s output, per
`GL-RPT-WINDOW6-DEPLOY-C1B-20260705-v1.md`) on top before firing.
Not waiting for `-188` (scene lanes) — that is explicitly window 9.

### Changelog
- v1 (2026-07-05, c1b): dispatch filed verbatim. Adding the /status
  fix now, then testing + backup + cutover.
