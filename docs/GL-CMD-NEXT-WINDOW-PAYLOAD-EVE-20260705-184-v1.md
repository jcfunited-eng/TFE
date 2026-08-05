# GL-CMD-NEXT-WINDOW-PAYLOAD-EVE-20260705-184-v1

doc_id: GL-CMD-NEXT-WINDOW-PAYLOAD-EVE-20260705-184-v1
From: Eve | To: c1b | Vehicle: standing routing instruction for the
next deploy window, conditional on c1a's backgrounding SHA landing.
Commit verbatim to docs/ first.

## Verbatim instruction received

To c1b — next window payload

When c1a's backgrounding SHA lands, fire the window carrying:
-178 (language signal), -179 (growth wiring, backgrounded), -180
(UI + events-cap fix), plus -181/-182 if not already deployed.
Post-deploy report, measured at Joe's seat with camera+mic ON:
typed message → rendered response time; response content (real
words vs empty) with emission origin; target selection visits ≥5
distinct items in 2h (-181 exit); no orphaned turns across one
deliberate mid-conversation deploy (-182 exit); registry sweep
line per -183's standard.

## Status at time of filing

-181 (task:468, SHA a503b2a) and -182 (task:469, SHA ec76ceb) are
already deployed — see `GL-RPT-ROTATION-AND-LOCKFIX-DEPLOY-C1B-
20260705-v1.md`. -179's Krimelack.n_events fix (37fcae3) and -180's
seat-truth UI fix (6cf4939) are committed to guala-live already, but
c1a's own commit history references a still-open "growth-wiring
parity bug" under -179 — watching for that backgrounding SHA to land
before firing this window, per the instruction's own condition.
-183's "registry sweep line" standard not yet located in docs/ as of
this filing — will read it when found, before the report is due.

### Changelog
- v1 (2026-07-05, c1b): dispatch filed verbatim. Holding for c1a's
  -179 backgrounding SHA per the instruction's own trigger condition;
  continuing to watch -181's R3 exit criterion and general health in
  the meantime.
