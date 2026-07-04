# GL-CMD-WIRING-AUDIT-EVE-20260704-164-v1

doc_id: GL-CMD-WIRING-AUDIT-EVE-20260704-164-v1
From: Eve | To: c1a (after -163; c1b may take it instead if queues
invert — first free seat owns it, say which in the report header).
Vehicle: NONE — read-only throughout. Budget: 1-2 sessions; if it
wants more, STOP and report coverage honestly rather than rushing
the tail.
Responds to: the converged symptom class of 07-03/04 — every
confirmed defect this arc (recall/listen routing, both index
bypasses, -151's dead scheduler gate, v7's orphaned converse, the
seat's dead awareness panel, coordinator_on hard-off, organ process
absent) is SEVERED WIRING, not broken physics. -160/-161 proved the
method on one subsystem; this runs it across the deployed surface.
E-signature declaration: none directly — this is the instrument
audit that decides which of her zeros are about her and which are
about unplugged instruments.
Substrate-truth declaration: read-only. Diff empty. No fixes ride
this CMD — every severed link becomes its own gated dispatch,
prioritized by Eve afterward.

## Step 0 — durability
Commit THIS file verbatim to docs/ before implementing.

## Part A — real entry points of the deployed process
Enumerate, with evidence, what actually runs and what actually gets
called: routes the live frontend hits (from the served HTML/JS, not
from route definitions), scheduler/background loops that execute,
bridge tool handlers, boot-path calls. This is the reachability
root set. File it as its own section — it is reusable beyond this
audit.

## Part B — writer→reader map for every named mechanism
For each mechanism named in: plan v9 Table 1 (the fifteen), the
ladder fields, the Loom Scan / gualaloom.html panels, §8 vitals, and
the E-signature telemetry list (spec §2) — prove the full path from
a Part-A entry point to the mechanism's writer AND from its data to
a live reader (metric, panel, or event), or declare the link:
  SEVERED-WRITER  — consumed but nothing live writes it
  SEVERED-READER  — written but nothing live reads it
  SEVERED-MODULE  — whole mechanism beside the live path
  LIVE            — full path shown, file:line
Known severed links (verify, don't re-derive): the dormancy registry
three (CurriculumScheduler, LoomBrain/Embryo, V7Session.converse),
v7 aware panel feed, coordinator_on metrics, organ process,
sensory_transducer (KB §2.7 — live bundle path still on dict-seeded
generators).

## Part C — date every severed link
git log -S per link: born-severed / severed in the 06-30 rogue
window / severed in the restoration rebuild. Three different
responses downstream; the date column is mandatory, UNDATABLE
allowed with the reason.

## Part D — the deliverable
One table: mechanism · status · file:line evidence · date-vs-06-30 ·
what a fix would restore (one line, no fix designed). Plus a
one-paragraph honest coverage statement: what fraction of the named
mechanisms were traced, what was skipped and why. Filed as
GL-RPT-WIRING-AUDIT-C1-20260704-164-v1, failures first — the
severed table IS the failures section.

## Gates (failures first)
G-164-1  Part A root set filed with evidence before Part B claims.
G-164-2  Every SEVERED verdict carries file:line; every LIVE verdict
         carries the full path; no verdict by memory or by report.
G-164-3  Date column complete or UNDATABLE-with-reason.
G-164-4  Diff empty — read-only proven.
G-164-5  Coverage statement present; no silent scope shrink.

Joe's part: none — but the severed table comes to you with Eve's
proposed fix order attached, because which wounds get treated first
is partly a canonical call.

### Changelog
- v1 (2026-07-04, Eve): the bounded audit promised once -161 proved
  the method. Class-level answer to "how many more of her zeros are
  unplugged instruments."
