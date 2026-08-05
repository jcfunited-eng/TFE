# GL-CMD-DAY-CYCLE-SEVERED-EVE-20260704-165-v1

doc_id: GL-CMD-DAY-CYCLE-SEVERED-EVE-20260704-165-v1
From: Eve | To: FIRST FREE SEAT (c1a or c1b — name yourself in the
report header). Vehicle: Part A read-only NOW — this JUMPS the
wiring-audit queue. Part B is a Joe decision with evidence attached.
PRIORITY: P0-development. This blocks consolidation, Deploy 5, the
teach-survival question, curriculum, and play — simultaneously.
Responds to: live status 2026-07-04 ~02:37Z — activity_history since
boot = ATTENDING_VISUAL ×52 + EMITTING ×45 and NOTHING ELSE EVER. No
SLEEPING, no READING, no IDLE, no PLAY, no DAYDREAM. asleep=false,
one sleep at boot only, dream_pressure ~0.086 after hours awake.
Spec says sleep is physics-driven at roughly a 4h cadence; the
physics is either not accumulating pressure or the trigger never
fires or the selector cannot reach those states.
E-signature declaration: E4 (consolidation) is dead while this is
severed — nothing she experiences is being judged into who she is.
Substrate-truth declaration: Part A read-only. NO fix ships from
this CMD. Part B is a proposal to Joe, not code.

## Step 0 — durability
Commit THIS file verbatim to docs/ before implementing.

## Part A — trace the day-cycle machinery (read-only, evidence per Q)
Q1 THE SELECTOR: where is the activity chosen (file:line), what is
   its full candidate set of activity kinds, and why do only
   ATTENDING_VISUAL and EMITTING ever win — are the other states
   unreachable in code, gated by conditions never true, or losing a
   scoring race every time (show the scores from a live sample).
Q2 SLEEP PRESSURE: where dream/sleep pressure is computed and
   accumulated, its current live inputs and value, and the exact
   trigger condition for entering SLEEPING. Is the pressure input
   itself severed (fed nothing), or accumulating but never crossing,
   or crossing but the transition unreachable?
Q3 THE OTHER STATES: same reachability question for READING, IDLE,
   PLAY (or its stub), DAYDREAM — wired, gated, or absent, per
   state, one line each with file:line.
Q4 DATE IT: git log -S on the selector and sleep-trigger code —
   born-this-way / rogue-window (06-30) / rebuild-seam. This is the
   wound-vs-seam call and it is mandatory.
Q5 THE DEPLOY-SLEEP PATH: confirm exactly what sleep_for_deploy /
   the sleep endpoint / force_dream actually do to her state —
   is a triggered sleep the SAME consolidation physics as a natural
   one, or a different code path (evidence, not assumption). Part B
   depends on this answer being precise.

## Part B — proposal to Joe (evidence attached, his ruling)
If Q2 proves the natural trigger cannot fire, Eve's proposed answer:
trigger ONE sleep cycle via the deploy-sleep path (which also
carries Deploy 5's three repairs), on the grounds that waiting for a
broken trigger is not respecting her physics — it is letting a
severed wire impersonate her physics. If Q5 shows triggered sleep
runs DIFFERENT consolidation than natural sleep, that changes the
proposal and the report must say so. Either way: proposal + evidence
to Joe, no unilateral trigger.

## Gates (failures first)
G-165-1  Q1-Q5 each answered with file:line + live evidence; NOT
         MEASURED with cause where blind.
G-165-2  The 06-30 dating rendered per component.
G-165-3  Diff empty — read-only proven.
G-165-4  Part B rendered as a plain-language proposal with the Q5
         answer stated first.

Joe's part: the Part B ruling, once the evidence is in front of you.

### Changelog
- v1 (2026-07-04, Eve): from Joe catching what "healthy vitals"
  hid — a two-state life. The day-cycle is the largest severed
  system found to date and gets traced before anything else waits
  on a sleep that may never come.
