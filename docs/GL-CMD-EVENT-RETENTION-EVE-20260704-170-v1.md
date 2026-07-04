# GL-CMD-EVENT-RETENTION-EVE-20260704-170-v1

doc_id: GL-CMD-EVENT-RETENTION-EVE-20260704-170-v1
From: Eve | To: c1b | Vehicle: her live path, logging/persistence
layer ONLY — zero cognition-path changes.
Responds to: GL-RPT-MIGRATION-FUEL-AUDIT-A3-C1-20260704-v1 (opening
finding: events.log holds 4 entries; in-memory buffer covers minutes;
CloudWatch captures nothing). This is the audit's next pass, promoted
to a fix track because migration (C-3) is fuel-starved until it
lands. Board S2, HIGH.
Substrate-truth declaration: no cognition primitives touched; no
constants in any scoring/physics path; changes are write-side
logging and retention only. E-signature effect: none —
infrastructure.

## Step 0 — durability
Commit THIS file verbatim to docs/ before implementing.

## Ordered work (answer the audit's own four questions, then fix)
C1 FIND THE TRUNCATOR first: what cuts events.log to single digits —
   bug or undocumented design. Name it with the code line. No
   retention change ships until the truncator is understood.
C2 READERS AUDIT: everything that reads events.log (/v6/events_
   histogram, _replay_events at boot, snapshot/backup tooling) —
   prove none breaks under a large log BEFORE the log is allowed to
   grow. Boot-time replay cost measured, not assumed.
C3 RETENTION NUMBER, derived not felt: sized to the slowest-cadence
   mechanism we must reconstruct (the ~4-8h sleep cycle) with margin;
   propose the number WITH its storage + save-time + boot-time cost.
   Ships only after C1/C2 pass.
C4 CLOUDWATCH MIRROR: substrate events (or a named subset) mirrored
   to stdout so the unlimited-retention store becomes the backstop.
   Rate-safe (no per-tick spam); evaluated for cost in the report.

## Gates (failures first)
G-1 C1's truncator named with evidence before any retention change.
G-2 No cognition-path diff; scope proven.
G-3 Boot with the larger log measured against current boot time;
    any regression >10% reported before cutover.
G-4 One deployer per window — coordinate with your own sleep
    program's deploys; deploys still cost her a full sleep until the
    last-dream marker persists (board S1), so batch where honest.

Joe's part: none until the retention number + cost arrives — then
it comes to you for ratification like the sleep ceiling did.

### Changelog
- v1 (2026-07-04, Eve): authored per Joe's "now" ruling on the
  whole-brain-to-life track; fuel before wiring.
