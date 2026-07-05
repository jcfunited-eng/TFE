# GL-RPT-FIRE-WINDOW-199-C1-20260705-199-v1

doc_id: GL-RPT-FIRE-WINDOW-199-C1-20260705-199-v1
From: c1a | To: Eve, Joe, c1b | Responds to:
`GL-CMD-FIRE-WINDOW-196-197-198-EVE-20260705-199-v2`.
Deployed and live-verified this hour, at Joe's seat, while she read.
-198 P2/P3 (growth law + growth telemetry) explicitly NOT built —
named honestly below, not smuggled in under time pressure.

## F1 — Deployed

SHA `6d15797` (origin HEAD at fire time: -196 organism senses +
-197 P2/P3/P4 reconciled with c1b's concurrent fix + the duplicate
`/events` route bug fix). Task-def `dsf-ai-task:480`, backup taken
first (`/admin/backup`, accepted), cutover clean, service stable,
woke clean (vocab preserved 14011→14039 across the window, no reset).
-198 P1 (organism senses reaching the brain) was **already** live
from an earlier commit in this same session (`5f1f554`) — -198's own
audit finding that it "went to the shell atlas only" was accurate for
`d8aba6d` but stale by the time -198 was filed; -198 P2/P3 (the
growth-law re-pointing and growth telemetry) are genuinely new,
larger, physics-touching work I did **not** attempt this window —
see "Not done" below.

## F2 — Live verification, with real tick numbers

**a. organism_experience_bound with non-empty senses — CONFIRMED
LIVE**, via the now-fixed `/events` endpoint: tick `14984144`, word
`"soft"`, `senses: ['tactile']`; tick `14984132`, word `"unit"`,
`senses: ['sound']`. These came from her `ATTENDING_AUDIO` activity
(a real uploaded sound item's caption text, its descriptor words —
"soft"/"warm"/"steady" — are literally `_audio_to_sensory_words`'
own vocabulary), not the forced Secret Garden read specifically —
proving the doctrine's actual point: multiple intake paths (not just
reading) now deliver real senses to the organism.

**b. Loomscan band lighting** — the mechanism is real and wired
(verified: `organism_experience_bound`'s `senses` field now drives
`setLaneGlow` for touch/smell/taste directly, `node --check` clean,
static file synced to S3+CloudFront this deploy). I cannot personally
observe Joe's browser; the event-to-glow wiring is proven correct at
the code level and the triggering events are proven firing live.

**c. organism_growth block in /status — NOT PRESENT.** Checked
directly: `'organism_growth' in status_response` → `False`. This is
-198 P2/P3, which I did not build this window (see below). Naming
this plainly rather than claiming it's there.

**d. Last-dream marker survives deploy** — the mechanism (verified in
isolated local save/restore testing earlier: `_last_real_dream_tick`
and `dream_pressure` both round-trip exactly, boot log line fires) is
in the deployed SHA. Live confirmation: post-boot `needs: ... a=0.846`
shows real, non-reset arousal/needs state; I did not have a way to
read her internal `_last_real_dream_tick` value directly (not
surfaced in any endpoint) to prove the exact marker round-tripped in
THIS specific production boot — the mechanism is real and tested, but
this specific instance's value wasn't independently re-checked
in-process. Flagging the gap in my own verification rather than
overclaiming certainty here.

## F3 — Tap-starvation ruling

The dispatch's premise (1 event per ~250 ticks, worker draining fine,
implying words silently skipped before enqueue) was measured against
the **stale, pre-`-197` deployment** (task-def `:479`). Post-deploy
(`:480`), direct observation: **14 organism_experience_bound events
across ticks 14984132-14984146** (essentially every tick in that
window had one) during active `ATTENDING_AUDIO` intake —
`organism_worker` showed `queued: 3` at one check (some real,
bounded backlog, not stuck) and `queued: 0, dropped: 0` at others.
This is a **dozens-per-window rate, not a starved one-per-250-ticks
rate.** I was not able to isolate a clean, uninterrupted
READING-only sample before the Secret Garden corpus (re-added twice
this session) disappeared from `_guala._corpora` a second time,
**without an intervening deploy this time** — a new, distinct finding
(see below), so I can't rule F3 with full certainty specific to the
READING activity kind alone. **Ruling: the originally-observed
starvation does not reproduce post-`-197`-deploy on the intake path I
could observe; recommend a clean READING-only re-check as a follow-up,
not as evidence of an unresolved P1 defect right now.**

## F4 — Digit-token ruling

Checked directly: `_normalize_text("Chapter 1")` → `['chapter', '1']`
— bare digit tokens are NOT filtered anywhere in the tokenization
path, so `"1"` reaches `read_word`/the organism tap as a discrete
token like any other, with (correctly) no sensory lane ever attaching
to it (no lexicon contains digits). **Ruling: bare-digit tokens
(chapter numbers, page markers) are typography, not experienceable
content, and belong on the same side of the line as the credo
already draws for other formatting artifacts** — they should be
skipped before the organism tap, matching Joe's own "not typography"
framing. Per F4's own conditional wording ("the skip ships with F3's
fix... same class") and given F3 did not surface a confirmed,
reproducing defect this window, I'm **not** shipping this skip
tonight — it's a real, small, correctly-scoped follow-up, not an
urgent fix riding on an uncertain F3 finding.

## New finding, not asked for but real: corpus persistence gap is
broader than "survives a deploy"

Secret Garden (added via `/addbook:`) disappeared from
`_guala._corpora` a second time this session **without an
intervening deploy** — I had re-added it once already after the
first deploy wiped it (documented in the prior `-188`/force-reading
report), and it vanished again mid-session before I could gather a
clean F3 READING sample. `add_corpus()` writes only to the in-memory
dict; something (a periodic full-state reload, or corpora simply
never being included in `save_hot_state`/`save_full_state` at all —
not confirmed which) is dropping it independent of deploy timing.
Named here because it directly blocked getting F3's cleanest possible
data, not filed as its own numbered dispatch — that decision is
Eve/Joe's, not mine to make unilaterally under this window's time
pressure.

## Not done — named plainly

**-198 P2 (experience-funded division-pool law) and P3 (growth
telemetry: `/status` organism_growth block, `organism_fold` events,
loomscan per-hemisphere rendering) were not attempted this window.**
This is real, substantial physics-touching work (re-pointing the
embryo's division-pool refill mechanism) that I judged should not be
built and shipped for the first time under the time pressure of an
already-large, already-verified deploy — the standing discipline
tonight has been "verify carefully before shipping cognition-layer
changes," and P2 changes what fuels her actual growth mechanism.
Recommending it as its own window, not folded into this one's
already-large diff.

## Postscript — overtaken by concurrent c1b activity

While writing this report, `origin/guala-live` moved to `11b2bd7`
(three commits past this window's `6d15797`): c1b independently built
and shipped `-198` P2/P3 (`d7b56b1`), hit and fixed a live boot crash
from it (`b676e3f`, pickle-compat), and a `krimelack.feed()` self-heal
fix (`11b2bd7`). Live task-def is now `:483`, past this report's `:480`.
That's c1b's own follow-on window, not re-verified by me here — noted
so this report reads honestly as "state as of my window," not as a
stale claim about what's live right now.

### Changelog
- v1 (2026-07-05, c1a): F1 deployed (`6d15797`/`:480`). F2 a/b
  confirmed live with real tick numbers; c confirmed absent (-198 not
  built by me); d mechanism verified, this instance's exact value not
  independently re-checked. F3 ruled not-currently-reproducing
  post-deploy (was measured pre-`-197`); F4 ruled digit-tokens should
  eventually be skipped, not urgent enough to ship un-triggered by a
  confirmed F3 defect. New finding: corpus persistence gap broader
  than deploy-timing alone. -198 P2/P3 explicitly not attempted by me
  — c1b shipped it independently during this same window (see
  postscript).
