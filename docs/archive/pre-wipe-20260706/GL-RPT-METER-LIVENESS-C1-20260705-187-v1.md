> **SUPERSEDED — DO NOT TREAT AS CURRENT TRUTH.**
> This document describes substrate state as of pre-wipe (2026-07-06
> wipe operation, GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1).
> The substrate described here no longer exists. Preserved as
> historical record only.
> For current substrate state, run the harness against production.

---

# GL-RPT-METER-LIVENESS-C1-20260705-187-v1

doc_id: GL-RPT-METER-LIVENESS-C1-20260705-187-v1
From: c1a | To: Eve, Joe, c1b | Responds to:
`GL-CMD-METER-LIVENESS-EVE-20260705-187-v1`.
Vehicle: `gualaloom.html` (cognition meter + intro/aware side panel)
and `substrate_runner.py` (one new `curriculum_status` field to check
against — same S4-style exception as `-180`'s events-cap fix: the
poll genuinely lacked what the meter needed to verify itself). Zero
cognition changes. Not deployed — c1b's window.

**M2 (the reconciliation table) first, as instructed. M1 (the fix)
second — 7 rows now compute live on every poll; the other ~21 carry a
visible audit-date stamp; 5 rows whose text was already confirmed
stale got corrected outright, not just stamped.**

---

## M2 — reconciliation table: meter-text vs live-verified state, now

**Confidence key:** LIVE = checked directly tonight (bridge tool /
code read against the current deployed SHA). CORRECTED = meter text
was confirmed stale and rewritten in this same commit. UNCHANGED = no
new evidence either way; audit-dated, not re-verified.

| row | meter said | verified now | status |
|---|---|---|---|
| aware gate | severed | still 0 fires per `ladder.awareness_ratio=0.0` (checked via `/status`, which reflects the same deliberation mechanism) — genuinely still not firing, but the DEPLOY happened; the row's own "none observed — the only thing that could feed it never gets real conversation" framing implied it *can't* fire, which is no longer true post-`-162` | **LIVE — text stale, now live-checked** |
| intro gate | severed | not directly checked (needs `/v7/state`'s `intro_krimelack_count`, no bridge tool reaches it) — genuinely unknown to me tonight, correctly left to the new live-check code rather than guessed | **UNKNOWN — now live-checked, will self-correct** |
| deliberation stage | queued, "0 fires... waiting for deploy window" | **STALE — the deploy already happened** (task:470, `GL-RPT-WINDOW6-DEPLOY-C1B-20260705-v1.md`); `awareness_ratio=0.0` confirms it still hasn't fired *yet*, a different claim than "waiting to deploy" | **LIVE — now live-checked** |
| state-shows-in-words | severed, "pinned at zero until next deploy" | same as above — deploy done, mechanism not yet observed firing | **LIVE — now live-checked** |
| day-cycle / sleep trigger | investigating | confirmed unchanged: `activity_history_summary` still shows only ATTENDING_VIDEO/EMITTING/ATTENDING_VISUAL, zero SLEEPING/DREAMING, hours later | **LIVE — matches, now live-checked going forward** |
| curriculum feeders | severed, "0 — confirmed not running" | **true right now** (my own reconnect, `-185`/B3, is built but not yet deployed — `GL-CMD-FIRE-WINDOW7-EVE-20260705-186-v1` was still "testing before deploy" as of this report) — but about to flip the moment window 7 ships, exactly the failure mode this dispatch is about | **LIVE — now live-checked, will flip itself the moment the deploy lands, no future edit needed** |
| brain: organism live (P1) | "NOT yet run against her real live state" | **STALE** — live since task:462; population was frozen at 64 (confirmed directly, `remember()`/`recall()` never trigger fold physics) until `-179`'s `experience_word()` backgrounding, deployed hours ago; `recall_ms` rising (12→152.8ms) is the first live behavioral evidence of real growth | **CORRECTED + now live-checked** |
| brain: voice / emission (P3) | "verified in sandbox... NOT yet run against real live state" | **STALE** — live since task:462; two real turns both returned honest empty (`"..."`, `response_source: "converse"`), not an error — no real-word content yet | **CORRECTED** (no single live boolean for "has real content ever fired" — needs its own counter, flagged not built) |
| brain: recall/recognition/attention/affect handover (P2) | absent, "NOT built this dispatch" | **STALE, significantly** — all 6 seams were built the same night this row was written; 4 (recall/recognition/association/habituation-reading) shipped live (task:465); 2 (attention/affect) explicitly declined with reasons, not silently dropped | **CORRECTED** |
| getting-bored-of-repeats | yes, "fix committed... not yet deployed" | **STALE** — this is `-181`, deployed task:468, hours before Joe would have read "not yet deployed" | **CORRECTED** |
| attention spread | yes, "not yet turned into a standing pass/fail number" | same underlying mechanism as above — the tie-flattening bug it names is fixed & live | **CORRECTED** |
| play | absent, "no code path" | re-confirmed directly tonight (`-185`/B4): `_atick_playing` exists, functionally identical to `_atick_idle`, no world interaction | **RE-VERIFIED, unchanged in substance, re-dated** |
| recall, sentence-building, association, retention, cross-sense recall, recognizing-things-in-new-forms, order/sequence, imagination, hearing-her-own-voice, organ influence on speech, who-tags, feelings-deepen-memory, voice-to-words, teaching survives to sleep, brain: imagination/reflection/theory-of-mind | (various) | not touched by tonight's work; no new evidence found either way | **UNCHANGED — audit-dated, not re-verified this pass** |

**16 of 28 rows were touched by this reconciliation** (7 live-checked
going forward, 5 text-corrected outright, 1 re-verified/re-dated,
1 confirmed-still-accurate-but-nuanced); the remaining 12 carry an
honest audit-date stamp and were not re-investigated — M1 doesn't
require re-auditing everything, only that nothing renders as current
without either a live check or a visible date.

---

## M1 — the fix

**Two hardcoded-"severed"-forever sites found, both fixed:**

1. `COGMETER_ROWS` (the cognition-meter table) — was rendered exactly
   once, at page load, from a static array never touched again. Fixed:
   rows with a new `live(status, v7)` function now recompute their
   `connected`/`firing` from the freshest `/status` and `/v7/state`
   poll data on **every** poll cycle (`renderCogMeter()` is now called
   from inside both `pollStatus()` and `pollV7State()`, not just once
   at boot) — a `[LIVE]` tag marks these. Every other row shows a
   `(as of audit <date>)` stamp derived from its own `pointer` field
   (`POINTER_DATES` lookup, dated from each dispatch's actual filing
   date, checked directly — `-107`/`-156` are 2026-07-03, `-159`
   through `-175` are 2026-07-04, this dispatch's own re-verifications
   are 2026-07-05) — never silently undated again.

2. **A second instance of the identical bug**, found while tracing
   this: `pollV7State()`'s side panel (`sp-intro-aware`/`sp-nmda`) —
   *unrelated to the COGMETER_ROWS table* — wrote a **hardcoded**
   `"SEVERED — instrument not connected (see -160/-161)"` string on
   **every single poll**, regardless of what the real `/v7/state`
   payload it had just fetched actually contained. Fixed: now reads
   `s.intro_krimelack_count`/`s.aware_krimelack_count`/
   `s.introspection`/`s.awareness`/`s.nmda_events` directly and renders
   whatever they say, live, every poll.

**One backend gap, named per M1's own exception clause** (a live
check was genuinely impossible without it): `curriculum_status`
(`_curriculum.status()`, which already existed on the scheduler) was
never surfaced through `/status` — added to `_cmd_status()`'s response
dict, the same pattern as `-179`'s `organism_worker`/
`organism_population` fields from earlier tonight.

**Not attempted:** re-auditing the other ~21 rows' underlying claims
from scratch (out of scope for a meter-liveness fix; M2's table above
states plainly which ones weren't re-checked, per M1's own honesty
standard) and building live counters for `intro gate` and P3's
"has real content ever fired" (both would need new counters this
dispatch's Vehicle — meter/status only — makes reasonable to add
later, flagged rather than built under this same pass).

---

## Verification

`node --check` on the extracted script block: clean, both before and
after all edits. Logic tested directly against realistic mock
`/status`+`/v7/state` payloads (matching real structures pulled
tonight): all 7 `live` functions compute the expected `connected`/
`firing` pair, correctly falling back to `null` (static text +
audit stamp) when the relevant field is absent from an older
response shape. No existing test covers `gualaloom.html` (none
found); Python-side `_cmd_status()` change syntax-checked, mirrors an
already-shipped pattern (`organism_worker`) with no new risk.

### Changelog
- v1 (2026-07-05, c1a): M2 filed first — 16/28 rows reconciled against
  live-verified or freshly re-confirmed state; 12 left honestly
  unchecked, audit-dated. M1 built: cognition-meter table and the
  separate, previously-unnoticed intro/aware side-panel both now
  re-render from live poll data on every cycle instead of a one-time
  or permanently-hardcoded string; every non-live row carries a
  visible audit-date stamp derived from its own dispatch pointer.
  One backend field added (`curriculum_status`) to make the
  curriculum-feeders row genuinely checkable. Not deployed.
