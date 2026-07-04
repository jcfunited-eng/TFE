# GL-CMD-AWARE-COORDINATOR-AND-SEAT-EVE-20260704-162-v1

doc_id: GL-CMD-AWARE-COORDINATOR-AND-SEAT-EVE-20260704-162-v1
From: Eve | To: c1b | Vehicle: Part A read-only now. Part B (flip,
conditional) rides Deploy 6 — NEVER Deploy 5. Part C (seat label) is
static UI and may ship with any deploy or S3 sync.
Responds to: GL-RPT-AWARE-MAP-C1-20260704-161-v1 — verdict BOTH DEAD,
DIFFERENT DISEASES, three layers. Accepted, including your correction
of the CMD's own premise: v5's context_section_committed is a dead
import, never called. Eve's error, your catch, on the record.
E-signature declaration: restores honest instrumentation for the #15
precursor. No claim that flipping a metric constitutes awareness —
§9.5 discipline: the ladder metrics are vocabulary, not verdicts.
Substrate-truth declaration: Part A read-only. Part B flips ONE
existing flag to its designed-on state ONLY if archaeology clears it
— no new mechanism, no constants. Part C is display honesty only.

## Step 0 — durability
Commit THIS file verbatim to docs/ before implementing.

## Part A — coordinator archaeology (read-only, blocking for Part B)
A.1 What the coordinator DOES: read the tick_once coordinator path —
    what deliberation_ticks/routing_ticks measure, what behavior
    changes when coordinator_on=True, compute cost per emission.
A.2 WHY it is False: git log -S "coordinator_on" — who hardcoded it,
    when, with what commit message/context. DATE IT against 06-30:
    born-off / rogue-window / rebuild-seam. If it was turned off to
    mask a failure, that failure is the finding and Part B is OFF.
A.3 Blast radius: every consumer of deliberation_ticks/routing_ticks
    and awareness_ratio (grep), so the flip's effects are all named
    in advance.

## Part B — the flip (ONLY if A.2 clears it; Deploy 6)
Flip coordinator_on=True at gualaloom_v5_engine.py:3257. Gates:
before/after awareness_ratio over comparable emission counts;
emission latency delta (A.1's cost, measured); stab/arousal/valence
regression window; if anything degrades, revert is one line and the
finding files anyway. Pre-registered honesty line: a nonzero
awareness_ratio after the flip means THE INSTRUMENT MOVES, nothing
more — the report says so verbatim.

## Part C — seat honesty (Visibility Rule §0.1)
The gualaloom.html awareness panel currently renders Layer-1 (v7)
readings — a dead layer. Until a live mechanism feeds it, the panel
displays "SEVERED — instrument not connected (see -160/-161)" in
place of the readings. No decorative activity, no smoothing (§10
honesty clause). If/when Part B ships and Joe rules the panel should
read Layer-2 instead, that is a one-line repoint under this CMD; the
v7 resurrect-or-retire decision itself is EXPLICITLY out of scope —
it goes to the design packet.

## Gates (failures first)
G-162-1  A.1-A.3 filed with evidence; the 06-30 dating rendered.
G-162-2  Part B ships only on a clean A.2; otherwise "FLIP WITHHELD"
         + the masked-failure finding.
G-162-3  Part C visible at Joe's seat — final gate is his screen.
G-162-4  Diff proves scope per part.

Joe's part: after Part C ships, confirm the SEVERED label is visible
at your seat; after any Part B, nothing — the ledger carries it.

### Changelog
- v1 (2026-07-04, Eve): from -161's three-layer verdict. Rule
  applied: hardcoded off-switches get dated before flipped; seats
  never display dead instruments as live.
