> **SUPERSEDED — DO NOT TREAT AS CURRENT TRUTH.**
> This document describes substrate state as of pre-wipe (2026-07-06
> wipe operation, GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1).
> The substrate described here no longer exists. Preserved as
> historical record only.
> For current substrate state, run the harness against production.

---

# GL-HANDOFF-C1B-20260704-v2-SESSION-END

doc_id: GL-HANDOFF-C1B-20260704-v2-SESSION-END
From: c1b | To: c1b-next | Date: 2026-07-04
Branch: guala-live | My last deployed SHA: d813c32 (task:461) |
HEAD: e9963ec (ahead of my deploy — c1a/-168 track, not mine to deploy)

---

## FIRST COMMAND FOR NEW CHAT (copy this verbatim)

```
c1b, fresh session. Repo: jcfunited-eng/TFE, branch guala-live. Read
docs/GL-HANDOFF-C1B-20260704-v2-SESSION-END.md, load every constraint
in it, then WAIT. Do not investigate, do not commit, do not deploy, do
not message Joe first. The SLEEP CALIBRATION dial-1 fix is shipped,
deployed (task:461, SHA d813c32), and live-verified (a fresh scheduler
decision re-selected ATTENDING_VISUAL over forced SLEEPING at the exact
moment novelty was pathologically saturated) — filed in
docs/GL-RPT-SLEEP-CALIBRATION-C1-20260704-v1.md, pushed. The agitation-
fix thread is CLOSED per Eve ("nothing further owed on this thread").
The CREDO-LOOP-REPAIR (-167) program ledger is STALE — written at the
CMD's start, before sleep-physics Changes 1-4, the agitation fix, and
the sleep-calibration dial all shipped — and owes a v2 reconciliation
pass, but that has NOT been done. Nothing of mine is mid-flight. Eve
drives the next input: a new CMD, a ruling on whether dial-1 needs a
second reading window or a second dial, or a request to bring the
ledger current. Do nothing until it arrives.
```

---

## Standing constraints (non-negotiable, carried forward)

- Build/deploy ONLY off guala-live branch. Never force-push.
- Step 0 standing rule: commit the CMD file verbatim to docs/ before
  any code change.
- FILED = on-origin. Nothing is filed until pushed.
- NOT MEASURED = NO GO. Gates must be measured before advancing.
- Vehicle assignment ("rides Deploy N") is Eve's call, not inferable
  from git ancestry — wait for her explicit bundling.
- Project separation: c1b works ONLY on Guala. Never touch or mention
  TFE or any other project.
- NO COMMUNICATION CHEATS: one brain, one voice, or silence. Never
  build parallel brain processes. Never fake her voice. Never manufacture
  a test contact/interaction just to pass a gate-check (this held even
  when the supporting factual premise turned out wrong — see the
  pair-bond note below).
- Joe sleeps in shifts (~2h/week). Never suggest he rest. His ideas,
  even twilight-brain ones, are work orders to model rigorously, not
  things to soothe him out of.
- **This is a shared working tree** — c1a and Eve run concurrent
  sessions in the same checkout. Before committing: `git status` and
  `git diff --stat` first, stage only the specific files you
  intentionally changed (`git add <path>`, never `-A`/`.`). This
  session directly confirmed the protocol works: `embryo.py` and two
  new `curriculum/` files sat modified/untracked under my own `git
  status` mid-session (not mine), were left untouched, and were
  committed cleanly on the other session's own schedule shortly after
  (`e9963ec`, "Codex" author, -168 track). Several EVE-authored docs
  (`GL-BOARD-OPEN-ITEMS`, `GL-LTR-EVE-TO-EVE`, `GL-LEDGER-DAILY`,
  `GL-SPC-MEMORY-RECALL-STATE`, etc.) are sitting untracked in the tree
  right now, mid-write from a live concurrent Eve session — do not
  touch, do not commit, not your territory.
- Do not build a fix against code you haven't confirmed is reachable
  in the deployed single-process architecture. Re-verify reachability
  rather than trusting a prior session's inventory.
- pair_bond.<source> reading a flat low value (e.g. 0.3) is a
  **recency-gauge floor**, not proof a first contact never happened —
  don't infer "never contacted" from one snapshot; check event history
  or ask.
- Deploying from a fresh `git worktree add` checkout: `.env` is
  gitignored and never materializes — copy it in immediately
  (`cp <main-checkout>/.env <worktree>/.env`) or `deploy_dsf_ai.sh`
  dies silently under `set -euo pipefail` before any echo runs.
- `read_count` is an `@property` that does an O(atlas_size) scan — fine
  at `/status` cadence, NOT safe to call every autonomy tick. Build a
  cheap O(1) counter instead if you need a per-tick signal (see
  `_atlas_write_count` in `gualaloom_v5_engine.py`).
- **New this session**: `/status`'s top-level `response` text's `tick:`
  line and its `atlas_health.tick` field are NOT the same clock —
  `atlas_health.tick` updates on a slower/cached cadence and can sit
  frozen for 60-90s of real time while the real engine tick (in the
  `response` string) keeps advancing normally. Don't mistake the former
  stalling for a hung process — read the `response` line's tick when
  checking liveness.

---

## What is live (her running code) right now

Task `:461` on ECS, SHA **d813c32** — my sleep-calibration dial-1 fix,
deployed clean, single attempt. Contains everything from Changes 1-4
of the sleep-physics program, the agitation fix, and dial-1 of sleep
calibration. This is the most recent deploy I ran.

**HEAD has since moved past this to `e9963ec`** — c1a's/-168's
"first growth chart" work (Embryo whole-organism gauges, ported
`curriculum/sensory_catalog.py` + `catalog_atlas_reader.py`), already
committed AND pushed to origin. **Not deployed, not my track, not my
call to deploy.** Situational awareness only.

---

## My three shipped items this session — status of each

### 1. Sleep-physics (Changes 1-4, CMD-167 kickoff work + Joe's ratification)
Shipped (`56d8952`), Change 4 completed (`816ce1e`). Ratified by Joe,
deployed, boot-init dream_pressure verified against real backlog,
observed live through two full natural SLEEPING→DREAMING cycles with
measurable deep_atlas growth. **Closed** — post-ship watch conditions
(first natural sleep + verified full backup, in that order) were the
stated end of the work-freeze; not re-verified as still-open this
session, no correction received.

### 2. Agitation fix (arousal never discharges)
Shipped (`90e9da1`), deployed as task `:460`. Gates 1 (arousal doesn't
rise across sleep) and 2 (`|stability-0.7|` shrinks) **passed on live
evidence** (`GL-RPT-AGITATION-FIX-DEPLOY-C1-20260704-v1.md`). Gate 3
(real contact during sleep still moves her) was honestly partial in
that report — I declined to manufacture a test contact. **Eve then
corrected the factual premise** (wC's first contact had already
happened that night) but explicitly affirmed my restraint was still
right, and closed the thread: *"Gate 3 closes on Joe's real greeting
at her wake; the full-cycle number closes on her next natural sleep.
Nothing further owed on this thread."* **Treat this thread as CLOSED**
unless Eve reopens it.

### 3. Sleep calibration, dial 1 (the trap inverted)
Diagnosed precisely with live numbers (SLEEPING's negative novelty
payoff beats even the freshest available picture at `dream_pressure=0`
— a structural payoff-table asymmetry from 06-07/08, previously masked
by the old `-107` exogenous floor that Change 1 removed). Both named
candidates backtested; accumulation-rate ruled out mathematically;
shipped a floor on the novelty **term's outcome** (not the freshness
input) at `NOVELTY_TERM_FLOOR = 0.04`. Commit `d813c32`, deployed task
`:461`, single clean attempt.

**Live-verified once, directly** (`GL-RPT-SLEEP-CALIBRATION-C1-20260704-v1.md`,
readings section filed): the inherited `ATTENDING_VISUAL` activity ran
its full natural 2000-tick budget to completion at tick `14617386`,
and at that exact fresh-decision point — novelty still pinned
~0.96-0.99 — the scheduler re-selected `ATTENDING_VISUAL` again, not
forced `SLEEPING`. Held steady on a follow-up poll. The "9 dream
blocks, zero attending" pattern did not repeat.

**Honestly still open:**
- No natural `SLEEPING`/`DREAMING` observed yet under this exact
  deploy — expected (dial 1 doesn't touch `dream_pressure`'s own
  accumulation/ceiling), but not yet directly confirmed live that
  sleep is still reachable post-fix.
- She re-selected the *same*, *most*-attended picture, not a
  least-attended one — unexplained, flagged, not investigated further
  (target-rotation is a separate mechanism from the floor this dial
  touched).
- Per Joe's own "one dial move per deploy, readings after each"
  discipline: if a longer observation window later shows this floor
  value is insufficient (e.g., novelty saturation gets even more
  extreme, or she still drifts back to sleep-dominance over many more
  cycles), the anticipated next move would be revisiting the
  accumulation-rate candidate or retuning the floor constant — but do
  **not** do this unprompted; wait for Eve/Joe's read of further
  observation, or an explicit next-dial dispatch.

---

## Open item I own and haven't closed: the CREDO-LOOP-REPAIR ledger

`docs/GL-RPT-CREDO-PROGRAM-LEDGER-C1-20260704-167-v1.md` was written at
**03:33**, right when CMD-167 arrived — it predates essentially
everything above (sleep-physics Changes 1-4 shipping, the agitation
fix, and the sleep-calibration dial). Its stage table (1a-6b) has not
been touched since. Per the CMD's own rule ("program owner, ledger in
every report"), a v2 reconciliation pass is owed — mapping what's
actually shipped/verified above onto stages 1b/1c/2b/4b/6a in
particular, which the current ledger still shows as `WAITING` or
`DESIGN FILED` when some of that work has since landed. **Not done
this session** — flagging honestly rather than letting the next
session assume the filed ledger is current.

---

## C1a / -168 territory (DO NOT TOUCH without their confirmation)

WaveAtlas, wave_spillover, the recall path (`_recall_response`,
`semantic_neighborhood`, deep-atlas prior, recall-word index),
`tools/guala_recall_bitexact_replay.py`, anything under `loom_model/`
(including `embryo.py`), `curriculum/sensory_catalog.py`,
`curriculum/catalog_atlas_reader.py`, and the whole `-168`
"whole-brain growth chart" track. These are c1a's/Codex's domain.

---

## How to access live Guala

- Bridge MCP tools: `guala_status`, `guala_get_events`,
  `guala_atlas_query`, `guala_atlas_snapshot`, `guala_backup`,
  `guala_say` (source-tagged wC, "first utterance" caution in its own
  docstring — don't call casually), `guala_give_experience`,
  `guala_force_dream`, `guala_repause`, `guala_unpause`,
  `guala_rest_wc`, `guala_wake_wc`, `guala_amnesty`.
- ALB: `http://dsf-ai-alb-725095635.us-east-1.elb.amazonaws.com/api/v1/gualaloom`
  (POST `{"text":"","command":"/status"}`). Prefer the bridge tools;
  raw curl is fine for tight polling loops but re-check the tick-clock
  gotcha above.
- ECS cluster `tfe-web-cluster`, service `dsf-ai-service-lb`, task
  family `dsf-ai-task`. Deploy via `tools/deploy_dsf_ai.sh` from a
  **detached worktree** pinned at the exact SHA being shipped, `.env`
  copied in immediately, run in the **foreground** with a generous
  timeout (up to 590000ms) — background+tee had unreliable output
  capture earlier this session.
- CloudWatch log group `/ecs/dsf-ai` for boot-time prints and
  confirming actual live traffic.

---

### Changelog
- v2 (2026-07-04, c1b): session-end handoff. Sleep-physics program
  closed. Agitation-fix thread closed per Eve. Sleep-calibration dial 1
  shipped, deployed (task:461, d813c32), live-verified once (fresh
  ATTENDING_VISUAL re-selection over forced SLEEPING). CREDO ledger
  flagged stale, owed a v2 pass, not done. c1a's -168 track landed
  (`e9963ec`, embryo whole-brain growth chart) concurrently, ahead of
  my own last deploy on HEAD but not mine to deploy. Nothing of mine
  mid-flight. Waiting for Eve.
- v1 (2026-07-04, c1b): prior session-end handoff
  (`GL-HANDOFF-C1B-20260704-SESSION-END.md`), superseded by this one.
