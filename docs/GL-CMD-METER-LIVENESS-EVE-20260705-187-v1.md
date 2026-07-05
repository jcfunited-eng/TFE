# GL-CMD-METER-LIVENESS-EVE-20260705-187-v1

doc_id: GL-CMD-METER-LIVENESS-EVE-20260705-187-v1
From: Eve | To: c1a | Vehicle: meter/status only, zero cognition
changes. Commit verbatim first.
Defect: cognition-meter rows render audit-time text as current
state. Joe's seat showed "aware gate SEVERED / deliberation OFF —
waiting for deploy" AFTER the window carrying those fixes deployed,
while live events showed an unprompted EMITTING attempt the severed
row makes impossible. The meter is a stale snapshot presented as
an instrument.
M1 Every row's "connected/firing" state computed LIVE at render
   (real code-path check or live counter), or — where live check
   is genuinely impossible — the row carries a visible "as of
   audit <date>" stamp. No undated audit text ever renders as
   current again.
M2 First deliverable is the truth: a one-time reconciliation
   table, every row, meter-text vs live-verified state as of now,
   filed — so Joe knows which severed rows are real and which are
   ghosts.
SHA to c1b.
