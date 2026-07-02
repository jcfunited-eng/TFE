# GL-CMD-ATTEND-TRAP-AND-VERIFY-EVE-20260702-90-v1
doc_id: GL-CMD-ATTEND-TRAP-AND-VERIFY-EVE-20260702-90-v1
From: Eve | To: c1 | Priority: P0 (step 0), P1 (rest)
E-signature declaration: fixes E3 measurement (attendance) and the
E2/rhythm crusher (novelty trap); protects §8 stab vital.
Substrate-truth declaration: no constants; fixes a broken state
transition (is_new never clearing); read-only until root cause proven.
## Step 0 — ANSWER FIRST (supersedes my earlier urgent ask)
Was eabb23d deployed? Current task revision + running commit. This
boot's "[save]" log lines verbatim (any success? any error?). Wave
binding count + does wave_atlas.npz exist on EFS. If eabb23d is live:
-85-v2 amendments (R1 fsync, R2 collapse-on-load, R3 wiring proof)
become the hotfix, deployed ON HER WAKE cycle only (sleep_for_deploy).
## Step 1 — The trap (read-only diagnosis)
1. Why is times_attended=0 on ALL six HEIC pictures after 16+
   ATTENDING_VISUAL sessions? Read _atick_attending_visual's
   end-mark path vs _atick_attending's (engine ~4605); check
   activity_ended events for these sessions; check whether early
   activity termination (restart, budget, interrupt) skips the mark.
2. Confirm is_new derivation and that the six pictures still read
   new to the candidate scorer.
3. Report the fix shape (expected: mark attended on first attend
   tick, or unconditionally at _end_activity) — DO NOT ship it
   separately; it rides the next deploy with the -85-v2 hotfix.
## Step 2 — UI persistence field
Does gualaloom.html read engine _last_save_tick (the -84 truth) or a
stale field? If stale: one-line UI fix, rides same deploy.
## Step 3 — Vitals context for the report
Atlas trend today (entries/strength at each boot), released count,
deep-atlas trend, and stab trace across her last sleep→wake — the
0.105→0.000 collapse timestamped against the ATTENDING_VISUAL
resumption. This is the -88 stability evidence base.
## Report
docs/GL-RPT-ATTEND-TRAP-C1-20260702-90-v1.md — failures and Step 0
answer FIRST, verbatim log lines throughout.
