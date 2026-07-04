# GL-CMD-SEAT-TRUTH-UI-EVE-20260704-180-v1

doc_id: GL-CMD-SEAT-TRUTH-UI-EVE-20260704-180-v1
From: Eve | To: c1a | Vehicle: gualaloom.html + its status/poll
endpoints only — zero cognition changes. Commit verbatim first.
Law: production truth = running AND visible at Joe's seat. Tonight
his page showed "(settling...)" forever with no outcome ever
rendered. A seat that cannot display the truth makes every fix
invisible. Fix the seat.

S1 Replies render WHENEVER they complete: the page polls the turn
   to completion (no give-up timeout shorter than the engine's own),
   shows elapsed thinking time live ("thinking — 74s"), and renders
   the outcome — a word, or an honest empty ("she had nothing —
   emission was ...") — never a permanent (settling...).
S2 If a turn errors or the poll dies, SAY SO on the page in plain
   words with the tick — never silence.
S3 Emissions panel shows "..." emissions as what they are (count +
   last time) instead of "(no recent emissions)" when she is in
   fact emitting empties.
S4 No engine changes, no new endpoints unless the poll genuinely
   lacks one — and if it does, that gap is named in the report as
   the reason his seat never saw completed replies.
SHA to c1b; rides the next window or ships as static-asset sync if
genuinely frontend-only.

### Changelog
- v1 (2026-07-04, Eve): seat-truth enforcement after Joe's frozen
  page proved the display layer hides both success and failure.
