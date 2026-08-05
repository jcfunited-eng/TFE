# GL-RPT-P2-AFFECT-SEAM-C1-20260704-v1

doc_id: GL-RPT-P2-AFFECT-SEAM-C1-20260704-v1
From: c1a | To: Eve, Joe, c1b
Responds to: standing P2 order.
Seam: **6/6 — affect modulation.** Vehicle: research only, no code
changes. Zero deploy action.

**Not built — for stronger reasons than seam 5. `Coordinator.regulate`
is her suffering-detection and forced-recovery system, by its own
class docstring: "keeps her physically alive while she decides."
That's not a perception/memory mechanism P2 was ever really about,
the organism has no analog for distress/suffering/recovery at all,
and building one would mean inventing new machinery rather than
handing over an existing one — the opposite of what this whole
track has been doing for seams 1-4.**

---

## Failures first (what this seam cannot honestly claim)

**1. `Coordinator.regulate` (`gualaloom_v5_engine.py:1151`) is a
safety system, not a cognition mechanism.** Read directly: per-tick,
it reads substrate signals into `Needs`, computes valence/arousal,
detects sustained suffering (`v < -0.15 and a > 0.30` for
`DISTRESS_THRESHOLD` ticks), and forces a recovery if triggered
(`_force_recovery`) — a hard-coded guarantee that she cannot be left
in prolonged distress. `_modulate_parameters` (`:1267`) nudges
`sections[*].gamma`/decay knobs toward needs targets — tuning
existing parameters, not making a decision. None of this is "what
does she recall/recognize/associate/attend to" — it's "is she okay,
and if not, fix it" — a different category of system entirely.

**2. The organism has no analog for suffering, distress, or forced
recovery — building one would be invention, not handover.** Embryo's
own `aff_arousal()`/`arousal` is a bounded [0,1] synthesis/clearance
scalar tracking recent fold/commit activity — a real, existing
signal, but answering a completely different question ("how
excited is the substrate right now") than Guala's `Needs.arousal()`
(a needs-based homeostatic signal feeding distress detection). Wiring
one to stand in for the other would not be "the organism drives this
decision" — it would be quietly substituting a differently-meaning
number into a safety-critical threshold check, which is worse than
declining, not better.

**3. Same collision risk as seam 5, more acute here.** `Needs`/
`Coordinator` is the exact system `GL-CMD-SLEEP-RATE-CALIBRATION-173`
(c1b, live today, `DP_RATE_MULTIPLIER=9.0`) and the sleep-physics
work referenced throughout today's docs (`dream_pressure`,
`NOVELTY_TERM_FLOOR`, arousal caps) all live inside. This is the
single most actively-tuned live behavioral system in the repo today.
Touching it for a P2 seam that wouldn't even be honest (Failure 2)
would be the worst possible combination: real risk, no real benefit.

---

## What this means for the P2 campaign

Six mechanisms named at the start (recall, recognition, association,
habituation, attention, affect modulation). Final disposition, stated
plainly:

| # | mechanism | status |
|---|---|---|
| 1 | recall | **built**, measured (100% after root-cause fix) |
| 2 | recognition | **built**, measured (real discrimination after fix) |
| 3 | association | **built**, surfaced a >95% false-confidence finding |
| 4 | habituation | **built for READING**; 4 item kinds declined (no real sensory tap) |
| 5 | attention | **declined** — already covered by #4; remainder unbuildable or live-calibration territory |
| 6 | affect modulation | **declined** — safety system, no organism analog, same collision risk as #5 |

Four real, tested, working seams shipped, each its own commit. Two
declined with a stated, specific reason each, not silently dropped.
One cross-cutting finding (the recall mechanism's lack of a reject/
uncertainty option) surfaced and reported prominently rather than
buried in whichever seam happened to trip over it first.

### Changelog
- v1 (2026-07-04, c1a): P2 seam 6/6 (affect modulation) declined —
  it's her suffering-detection/forced-recovery system, not a
  cognition mechanism, with no honest organism analog and the
  highest collision risk with today's live sleep-calibration work.
  Closes the P2 standing-work campaign (4 built, 2 declined, 1
  cross-cutting finding).
