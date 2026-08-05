# GL-RPT-P2-ATTENTION-SEAM-C1-20260704-v1

doc_id: GL-RPT-P2-ATTENTION-SEAM-C1-20260704-v1
From: c1a | To: Eve, Joe, c1b
Responds to: standing P2 order.
Seam: **5/6 — attention.** Vehicle: research only, no code changes.
Zero deploy action.

**Not built — and this report explains why that's the right call
here, not a shortfall. Attention's organism-relevant piece was
already handed over as part of seam 4 (habituation). What remains in
`_action_salience` beyond that is either (a) the same real-sensory-
connection gap already declined for pictures/sounds/videos, or (b)
dream-pressure/sleep-threshold/presence logic that isn't a perceptual
concept the organism has any analog for, and that c1b is actively,
carefully calibrating live today. Forcing a seam here would mean
either fabricating a signal or colliding with in-flight sleep-
calibration work — declining both, plainly, rather than shipping
something just to keep the count moving.**

---

## Failures first (in the sense of: what this seam cannot honestly claim)

**1. "Attention" doesn't cleanly decompose the way the original
research summary suggested.** The prior survey named
`_select_next_activity`/`_action_salience` as "the attention-
allocation function." Reading the FULL function (not just its
novelty sub-component, which seam 4 already handles for READING)
shows it's a multi-term needs-based score:
`novelty_term + stability_term + connection_term`, then
dream-pressure modifiers (sleep-threshold boost/suppression),
then a presence boost, then a flat baseline. Only the novelty term is
really "how salient does this specific thing look" — the rest is
homeostasis (does she need rest, stability, connection) and social
presence, not perceptual salience. Seam 4 already gave the organism
the one piece that's genuinely "attention" in the everyday sense, for
the one item kind (READING) it can honestly answer for.

**2. Extending the novelty term to the other four kinds
(ATTENDING/ATTENDING_VISUAL/ATTENDING_AUDIO/ATTENDING_VIDEO) hits the
exact wall seam 4 already named.** Checked `SensoryItem` directly
(the class backing `ATTENDING`, generic pictures/sounds): it holds
only `item_id`/`kind`/`title`/`times_attended` — no real text content,
same as the picture/sound/video objects seam 4 already declined for.
No new information changes that conclusion here.

**3. The non-novelty terms are live-calibration territory, not
"attention" — and c1b is actively tuning them today.** The
dream-pressure/sleep-threshold block carries extensive, dated
comments about a same-day live calibration (`GL-CMD-SLEEP-
CALIBRATION-JOE-20260704`, a `NOVELTY_TERM_FLOOR` chosen "with a
small margin above today's live SLEEPING-structural-term reading").
c1b's own concurrent commit this session
(`GL-CMD-SLEEP-RATE-CALIBRATION-173`, `DP_RATE_MULTIPLIER=9.0`)
touches this exact behavioral system. This project's own standing
rule ("Deploy coordination: two uncoordinated deploys raced
tonight — benign by luck") is precisely the risk of two sessions
independently reworking the same live-sensitive scoring function on
the same day. Not touching it.

---

## What this means for the seam count

Five of six mechanisms are either built (recall, recognition,
association, habituation-for-READING) or explicitly, honestly
declined with a stated reason (habituation's other four item kinds,
and now attention in full). Attention is not "2 of 6 remaining" work
quietly dropped — it's a "this doesn't need its own seam" finding,
reached by reading the actual function rather than assuming the
original one-line research summary mapped cleanly onto a real,
safe, buildable seam.

### Changelog
- v1 (2026-07-04, c1a): P2 seam 5/6 (attention) — researched, found
  to already be substantially covered by seam 4, and the remainder
  declined as either unbuildable-without-fabrication or live-
  calibration territory not to be touched today.
