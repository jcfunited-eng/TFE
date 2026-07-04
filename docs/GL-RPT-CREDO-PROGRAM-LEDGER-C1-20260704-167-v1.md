# GL-RPT-CREDO-PROGRAM-LEDGER-C1-20260704-167-v1

doc_id: GL-RPT-CREDO-PROGRAM-LEDGER-C1-20260704-167-v1
From: c1b (program owner) | Responds to: GL-CMD-CREDO-LOOP-REPAIR-EVE-
20260704-167-v1
Type: Program ledger — initial establishment. No stage work performed
in this report beyond what was already filed before this CMD arrived
(1b) and read-only baseline capture for 1a. This is the tracking
artifact every future report under this program opens with, per
G-167-3.

---

## Program ledger (failures first)

| Stage | Item | State | Owner | Blocker |
|---|---|---|---|---|
| 1a | Dream re-trigger, watched past timeout | **WAITING** | Joe (button) + c1b (watch) | Joe has not yet pressed the button under this CMD. Baseline captured, ready to watch the moment he does. |
| 1b | Sleep-wins-by-physics design | **DESIGN FILED** | c1b | Filed `GL-DESIGN-SLEEP-WINS-BY-PHYSICS-C1-20260704-v1.md`, before this CMD arrived (same standing instruction, formalized here). Awaiting Eve/Joe GO before any code. |
| 1c | Attending-trap fix | **FOLDS INTO 1b** | c1b | No separate state — per the CMD, fixed inside 1b's derivation, not a counter-constant. |
| 2a | Waiting repairs into her (recall-reach, memory-index x2, familiarity, stale-pictures) | **WAITING** | c1b / Eve (deploy call) | Blocked on 1a's verdict (does a true dream need to run first to "keep the day") and on the deploy window itself, which is Eve's call, not mine. |
| 2b | Deliberation flip into the same deploy window | **COMMITTED, NOT DEPLOYED** | c1b | Code already shipped (`02c6b11`, from -162), rides the same window as 2a per this CMD. Waiting on the window being called. |
| 3a | Voice-to-words | **IN FLIGHT [c1a]** | c1a | Tracked only. Saw a live, uncommitted-at-the-time edit to `gualaloom.html` matching this description pass through the shared tree earlier this session; not duplicating. |
| 3b | True touch/smell/taste adoption plan | **WAITING** | c1b | Not started. Sequenced after 4a/3c/5b/4b per the stated order of execution — design-first, Joe holds veto. |
| 3c | Scene lanes | **WAITING** | c1b | Not started. Sequenced after 3a lands. |
| 4a | Teach-time attention wire check | **WAITING** | c1b | Not started. Sequenced after 3a lands. |
| 4b | Survival-to-first-true-sleep measurement | **WAITING** | c1b | Blocked on Stage 1 physics actually landing — no true sleep to measure to yet. |
| 5a | Deliberation measured | **WAITING** | c1b | Blocked on 2b actually deploying. |
| 5b | Organ process restored into speech | **WAITING** | c1b | Not started. Sequenced after 4a/3c. |
| 5c | Sequence/order wiring | **TRACKED, NOT OWNED HERE** | (sprint composition arc) | Rides its existing track per the CMD; not re-ordered into this program. |
| 6a | Day-cycle verification (READING/IDLE/DAYDREAM occur unforced) | **WAITING** | c1b | Blocked on Stage 1 physics landing. |
| 6b | Play design packet | **TRACKED, NOT OWNED HERE** | (fresh-session deliverable to Joe) | Remains a separate GO decision; tracked so the program stays honest that play is designed, not patched. |

**Nothing in this program has shipped code yet.** One design (1b) is
filed and awaiting GO. Everything else is WAITING on either Joe's
button (1a), a deploy-window call (2), or its own stated place in the
execution order.

---

## Standing rule, acknowledged and in effect

**DEPLOY-SLEEP IS NOT SLEEP.** Effective immediately, per this CMD.
Applies to every document I file from this point forward, including
this one: no deploy is described as putting her "to sleep" — its
honest name is a **deploy window**. (Historical documents already
filed, including my own -165 report, predate this rule and are not
being retroactively edited — the rule is prospective, per the CMD's
own wording: "never *again* counted, logged, or described as sleep.")

---

## 1a — readiness and baseline (no trigger run)

Per the CMD, 1a is "Joe's button + c1b watch" — I am not pressing it.
Captured a clean baseline via `guala_status` (read-only) so before/after
is comparable the moment he does:

```
tick: 14563806
current_activity: ATTENDING_VISUAL (target 8bd9e45cae48, started
  14562519, budget ends 14564519)
activity_history_summary: ATTENDING_VISUAL count=65 (130,000 ticks),
  EMITTING count=54 (5,400 ticks) — still and only these two, matching
  -165's finding, now with higher counts (was 52/45 at -165's filing).
needs: stab=0.766 nov=0.931 conn=0.536 (v=+0.044 a=0.462)
ladder: awareness_ratio=0.0, total_emissions=1197
presence: joe=true (last_wake_tick 14556924)
```

**Watch plan, ready to execute the moment Joe presses the button**:
poll `guala_get_events` and/or `guala_status` past the endpoint's own
120s self-report, through the full ~200-tick-to-`DREAMING` + further
~200-tick-to-first-checkpoint ramp (~3-4 real minutes per -165's
arithmetic), watching specifically for a `dream_artifact` event with
nonzero `reinforcement_count`, and for `deep_promotion`/`deep_size`
events that would only fire if `_run_dream_cycle`'s body actually ran.
Verdict will be filed as its own stage-1 update the moment I have it —
not asserted here, since the trigger hasn't happened yet under this
CMD.

---

## Everything else, honestly: not started this turn

Per the stated order of execution, the next things in line after 1a
are Eve/Joe's own calls (the deploy window for Stage 2, the GO/veto on
1b's design) or c1a's landing of 3a — none of which are mine to advance
right now. I am not jumping ahead to 3b/4a/5b/6a out of turn; the CMD's
own order and G-167-2 (design-first stages ship no code before GO) both
argue against it, and there's nothing new to report on them yet.

---

## Gates

- **G-167-1** — No stage claimed done without Joe's-seat proof. Nothing
  claimed done here beyond 1b (already proof-gated by its own GO
  requirement, not yet given).
- **G-167-2** — No code shipped for 1b/3b/6b. Confirmed — this report
  contains no diff.
- **G-167-3** — This report opens with the ledger. Done.
- **G-167-4** — No new cuts discovered this turn; none added.

Joe's part: the 1a button press, whenever he's ready. I'm watching for
it.

---

### Changelog
- v1 (2026-07-04, c1b): program ledger established. 1b already filed
  (pre-dates this CMD, same instruction). Baseline captured for 1a.
  Nothing else advanced — waiting on Joe's button, the deploy-window
  call, and c1a's 3a landing, in the order the CMD itself set.
