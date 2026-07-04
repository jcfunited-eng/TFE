# GL-CMD-TARGET-ROTATION-FIX-EVE-20260704-181-v1

doc_id: GL-CMD-TARGET-ROTATION-FIX-EVE-20260704-181-v1
From: Eve | To: c1b | Vehicle: live path, scheduler target-selection
only. Commit verbatim to docs/ first.

Defect: the system has selected the same visual target (e93d29dae5ae)
for 590+ consecutive attend cycles across an entire day. Familiarity
for that target is pinned at 0.9 while all others sit at 0.07-0.23,
and selection still returns it every cycle — the getting-bored
mechanism either isn't consulted by the selector or its penalty is
too weak to ever change the argmax. This is the most visible defect
at Joe's seat.

R1 ROOT-CAUSE with the arithmetic: the selector's actual scoring at
   a real decision tick — why does a 0.9-familiarity target beat 29
   fresher ones. File:line.
R2 ONE DIAL: make familiarity penalize selection strongly enough
   that a target attended 500x cannot beat a target attended 5x.
   No new mechanisms — the boredom fix already committed/queued
   ships with this if it is the missing piece.
R3 EXIT CRITERION, binary: within 2 hours post-deploy, target
   selection has visited ≥5 distinct items, verifiable from the
   activity log. If it hasn't, the fix failed — report says so.

### Changelog
- v1 (2026-07-04, Eve): dispatched a day late; defect visible since
  morning status reads.
