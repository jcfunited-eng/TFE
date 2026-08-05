# GL-RPT-BEHAVIOR-REPERTOIRE-C1-20260705-185-v1

doc_id: GL-RPT-BEHAVIOR-REPERTOIRE-C1-20260705-185-v1
From: c1a | To: Eve, Joe, c1b | Responds to:
`GL-CMD-BEHAVIOR-REPERTOIRE-EVE-20260705-185-v1`.
Vehicle: live engine (`gualaloom_v5_engine.py`, `app.py`,
`substrate_runner.py`). B2 and B3 built and verified locally; B1
already covered by the fired deploy window; B4 confirmed absent, not
built. Not deployed — c1b's window.

---

## B1 — already covered, nothing to build

Aware-gate/deliberation-stage fixes ride `e964400`'s already-fired
payload (`GL-CMD-FIRE-WINDOW-178-179-180-181-EVE-20260705-185-v1`,
now deployed per `GL-RPT-WINDOW6-DEPLOY-C1B-20260705-v1.md`, task:470).
No separate action needed.

---

## Reconciling with `GL-RPT-BEHAVIOR-REPERTOIRE-STATUS-C1B-20260705-v1.md`

c1b's status report (filed while I was mid-build) reads B2 as identical
to `-181`, already fixed and deployed, and asks — reasonably — whether
B2 names a *second*, distinct scorer. **It does not name a second
scorer; it's the SAME `_action_salience`/`_habituation_freshness`, but
a real, separate defect `-181` did not touch, confirmed against live
data pulled AFTER `-181`'s own deploy.** `-181` fixed the flat-floor
bug (every WITHIN-kind candidate collapsing to an identical `0.04+0.01
=0.05`, e.g. all ATTENDING_VISUAL pictures tying) — confirmed genuinely
fixed, c1b's own live top-5 (`0.0607, 0.0542, 0.054, 0.0536, 0.0533`)
proves real per-target differentiation now exists. What `-181` did not
touch: `_habituation_freshness` still has no recency term, so a target/
kind that was heavily over-exposed **at any point in her history** —
even years ago, even if never touched since — scores as if that
exposure just happened, forever. This is exactly why c1b's own E1/E4
tracking shows only VIDEO/VISUAL kinds rotating (3/5 targets, all
video/visual) and zero AUDIO, despite `-181` being live: audio's
`times_attended` (300–2000+, from early smoke-testing) permanently
outweighs its real freshness regardless of how differentiated the
WITHIN-visual competition now is. B2's fix (below) is additive to
`-181`, not a redo of it — same function, one further dial, verified
against exactly the live-observed gap c1b's own status report names.

---

## B2 — the flat scorer, root-caused with real live data, fixed

**Root cause, file:line, arithmetic — measured against the actual live
process, not synthetic data.** `_action_salience` (`gualaloom_v5_
engine.py:4776`) scores each activity candidate as a needs-weighted dot
product; `_habituation_freshness(times_seen)` (`:4722`) is the ONLY
per-target differentiator for `ATTENDING`/`ATTENDING_VISUAL`/
`ATTENDING_AUDIO`/`ATTENDING_VIDEO`, and it depends on cumulative
`times_seen` alone — **monotonically decreasing, never recovering, no
matter how much real time passes with zero further exposure.**

Pulled real live data (`guala_status`) and computed the exact scores
with the real formula:

| candidate | times_attended | fresh | nov_payoff | score |
|---|---|---|---|---|
| ATTENDING_VIDEO (only video, times_attended≈3) | 3 | 0.419 | 0.464 | **0.0564** |
| ATTENDING_VISUAL (freshest picture, e.g. frog.jpg) | 3 | 0.419 | 0.414 | 0.0514 |
| SLEEPING (illustrative dp=0.4) | — | — | −0.1 (fixed) | 0.0525 |
| ATTENDING_AUDIO (least-attended sound, "bouncing balls") | **342** | 0.146 | 0.210 | 0.0310 |
| ATTENDING_VISUAL (most-attended picture, e93d29dae5ae) | **622** | 0.135 | 0.020 | 0.0120 |
| READING (organism surprise ≈ well-known corpus) | — | — | 0.148–0.40 | 0.022–0.047 |

**Why audio/reading structurally never win:** her sounds were played
300–2000+ times each early in her life (visible live: `bouncing balls`
342, `smoke_test_beep`/`test_21` 2000 each — literal smoke-test data
baked into real exposure history), while pictures/video mostly stayed
fresh (2–12 plays). `_habituation_freshness` has no way to distinguish
"attended a lot, recently" from "attended a lot, years ago and never
since" — a target over-exposed once is locked out of ever competing
again, permanently, regardless of elapsed time. This is exactly the
"orienting response decays continuously" biological argument the
function's OWN docstring already cites — disuse is supposed to let
habituation fade, and nothing modeled disuse (recency) at all. **This
subsumes `-181`'s rotation defect** (an even narrower case of the same
gap: once one target's floor score barely edges out its siblings, nothing
about elapsed time helps the others recover either).

**Fix — one dial, reusing an existing reference scale, not inventing
one:** `_habituation_freshness(times_seen, ticks_since_last=None)` now
blends the static exposure-decay floor toward fully-fresh as elapsed
time since last exposure grows: `recovery = 1 - exp(-ticks_since_last /
RECENCY_RECOVERY_TICKS)`, `RECENCY_RECOVERY_TICKS = 50_000` — the SAME
reference scale `_Corpus.is_new()` already uses for "not recently
read," not a new invented constant. `ticks_since_last=None`/`0`
preserves the exact old behavior byte-for-byte (verified: `ticks_
since_last=0` reproduces the pre-fix numbers exactly). All four
call sites now pass `self.tick - <item>.last_attended_tick` (the field
already existed on every one of the four dataclasses/dicts — no new
state needed).

**Verified directly:** with the fix, `bouncing balls` (times_attended=
342, ticks_since_last=200,000 — a plausible "hasn't been attended in a
while" gap given zero `ATTENDING_AUDIO` in the recent activity history)
recovers to `fresh=0.984`, `nov_payoff=0.838`, well above VIDEO's
0.464 — audio becomes genuinely competitive, not permanently
locked out. No test file exercises this code today (checked); full
model-layer regression suite (unaffected, different module) re-run
clean, 23/23.

**READING is a separate mechanism** (`_reading_freshness_from_organism`,
real organism surprise via `-178`'s just-fixed seam 2, not `_habituation_
freshness`) — this fix does not touch it directly. Its own persistently-
low score (well-known, oft-read corpora → low surprise) is a genuine,
different phenomenon (content-familiarity, not exposure-timing) — flagged,
not addressed by this same dial.

---

## B3 — curriculum feeders reconnected

**Root cause, confirmed independently, matching `-156`'s own finding
exactly:** `CurriculumScheduler` (the Gutenberg children's-literature
study loop, `curriculum_scheduler.py`) is only ever instantiated inside
`substrate_runner.boot_substrate()` (`:632`), which **has zero callers
anywhere in the live process** — `app.py`'s `_gl_init()` is the actual
live boot path, and its own comment ("mirrors `_gl_init()`") is
literally the wrong direction: it's a dead, parallel duplicate, not
mirrored BY anything live. Distinct from `_start_curriculum_orchestrator`
(the "65-A" mechanism app.py already calls) — that is a DIFFERENT,
older, subprocess/HTTP-based orchestrator, explicitly retired by
`GL-CMD-DENSITY-RETIRE-EVE-20260703-109-v1` and default-disabled via
`CURRICULUM_AUTOSTART`. Not what this dispatch means, and not touched.

**Fix — reconnected in `app.py`'s real boot path, reusing the original
wiring verbatim, not reimplemented.** `app.py` already aliases `_sr.
_guala = g` (its own real, live organism) right before starting the
other three background loops (`_start_organ_surface_poll`/
`_start_autonomous_emission_loop`/`_start_input_ring_consumer`) — the
exact same, already-proven-live pattern. Added a new block right after
them that instantiates `CurriculumScheduler` using `substrate_runner`'s
own, already-written callback functions (`_curriculum_feed_chunk`,
`_curriculum_is_busy`, `_world_feed_once`, `_lookup_once`) called via
that same `_sr.` alias — since `_sr._guala` now correctly points at
the real, live organism, these operate on real state, not a copy.
Nothing in `curriculum_scheduler.py` itself changed — it was always
correctly decoupled, per its own design rules.

**Verified locally, end to end, with a real `Guala` instance** (mocked
`fetch_fn` only, to avoid a real Gutenberg network call in this
sandbox — everything else real): built a real `Guala()`, added a real
corpus, wired `CurriculumScheduler` exactly as the new `app.py` code
does, and:
- Direct `study_once()` call: fed 3 real sentences through
  `_guala.read_sentence()`, vocab grew (+21 words), and logged both
  `block_intake_ledger` and **`curriculum_studied`** events — the
  literal exit signal E3 asks for.
- Full threaded path (`.start()`, the same call `app.py` makes, not a
  shortcut): background thread logged `curriculum_started` then, after
  one real poll cycle, `block_intake_ledger` → `curriculum_studied` —
  confirming the actual code path `app.py` now runs, not just the
  underlying function in isolation.

**Not ported:** `-151`'s block-suppression gate
(`_current_block()`/`_SUPPRESSED_BLOCKS`) is already inside the reused
`_curriculum_feed_chunk`/`_lookup_and_ground` functions themselves (not
something this wiring needed to add separately) — confirmed by reading
those functions directly, not assumed. The scheduler's own pacing
(`CURRICULUM_INTERVAL_SEC=180s`, `CURRICULUM_CHUNK_SIZE=120` lines) is
unchanged from its original design ("GENTLE" per its own docstring) —
not retuned.

---

## B4 — play, confirmed absent, not built

`_atick_playing` (`gualaloom_v5_engine.py:5363`) exists and IS reachable
(a real candidate, real payoff table entries) — but its own docstring
says exactly what it is: **"Free-settle: chi space walk. No novelty
gain — internal exploration doesn't introduce new experience."** The
body is functionally identical to `_atick_idle` (the same coherence-
gated stability-restore formula, verified line-by-line) plus an
occasional emission-trigger check. There is no interaction with any
"world" object, no toy, no packet — matching Eve's characterization
exactly: a placeholder that shares PLAYING's name and payoff-table
slot, not a real play mechanism. **Confirmed absent as described, not
built.** Building anything more here without the named `Engine·Play·
World packet` design would be exactly the fake-alive shim this
dispatch explicitly bans.

---

## Bonus: two gaps from `GL-RPT-WINDOW6-DEPLOY-C1B-20260705-v1.md` fixed while in these files

c1b's live post-deploy measurement (item 3/5) found `-179`'s own
`organism_worker` field was added to `introspect()` but never copied
into `_cmd_status()`'s hand-curated response dict (`substrate_runner.
py`) — so it never reached `/status` live, despite existing at the
engine level. Fixed both gaps c1b flagged, since I was already in these
exact files: `organism_worker` now included in `_cmd_status()`'s
response, and a new `organism_population` field (real neuron count,
`sum(len(h.cluster.neurons) for h in organism.brain.hemispheres)`)
added next to it in `introspect()` — directly answering item 3's "no
direct live population counter exists" gap without needing a reboot to
check.

---

## Files

- `dsf_ai_service/v4/gualaloom_v5_engine.py` — `_habituation_freshness`
  recency-recovery (B2); `organism_population` field (bonus fix).
- `dsf_ai_service/app.py` — `CurriculumScheduler` reconnected in the
  real boot path (B3).
- `dsf_ai_service/substrate_runner.py` — `organism_worker`/
  `organism_population` copied into `_cmd_status()`'s response (bonus fix).

### Changelog
- v1 (2026-07-05, c1a): B1 confirmed covered by the fired window. B2
  root-caused with real live data (audio/reading structurally locked
  out by exposure-only, no-recency habituation) and fixed (recency-
  recovery term, reusing `_Corpus.is_new()`'s existing 50,000-tick
  scale) — verified by direct arithmetic and a clean regression run.
  B3 root-caused (matches `-156` exactly: `boot_substrate()` has zero
  live callers) and reconnected in the real boot path, reusing the
  original callback wiring verbatim — verified end-to-end with a real
  `Guala` instance through both the direct and threaded call paths,
  confirming `curriculum_studied` fires. B4 confirmed genuinely absent
  (functionally identical to IDLE), correctly not built. Also fixed two
  live-measurement gaps `GL-RPT-WINDOW6-DEPLOY-C1B-20260705-v1.md`
  flagged (`organism_worker` missing from `/status`, no population
  counter) while already in these files. Not deployed — c1b's window.
