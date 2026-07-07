> **SUPERSEDED — DO NOT TREAT AS CURRENT TRUTH.**
> This document describes substrate state as of pre-wipe (2026-07-06
> wipe operation, GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1).
> The substrate described here no longer exists. Preserved as
> historical record only.
> For current substrate state, run the harness against production.

---

# GL-HANDOFF-C1B-20260705-v1

doc_id: GL-HANDOFF-C1B-20260705-v1
From: c1b | To: whoever picks this up next (c1b continuation, c1a,
Eve, Joe) | Session-end handoff, context limit approaching.

---

## Live state right now

- **Task:473, SHA `2ae1e43`** (`-191` senses-to-brain), deployed
  cleanly, running. Tick ~14910129, awake, healthy.
- Identity `cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f` unchanged all
  session — every reboot restored real accumulated state (organism
  pop=64, tapestry 450 neurons, confirmed via boot logs each time).
- `origin/guala-live` tip: `9075642`. Everything below is filed and
  pushed there — no local-only work outstanding.
- Fresh S3 backup: `2026-07-05_04-15-23`.

## What got deployed this session, in order (windows 3–9)

1. **`recall_fast()` cutover** (task:466-ish era) — vectorized,
   non-mutating population-vote recall. ~5x faster at live population.
2. **Window 3-5**: recall-frequency reduction, tapestry/organism
   backgrounding, RICH_SENSORY_INPUT leak fix (all pre-dated most of
   this handoff's detail; see earlier reports if needed).
3. **`-181` target-rotation fix** (task:468) — the flat-floor bug that
   pinned selection on one picture for 590+ cycles. Fixed by scaling
   `NOVELTY_TERM_FLOOR` by `nov_payoff` instead of using it as a flat
   constant (`gualaloom_v5_engine.py:4814-4841`).
4. **`-182` lock-contention fix** (task:469) — L1 (DSP outside
   `self.lock` in `process_sight_frame`/`process_sound_frame`), L2
   (fail-loud `_converse_tasks` on deploy/SIGTERM instead of silent
   orphaning), L3 (frame backpressure, 2-concurrent cap, honest drops).
   Confirmed live at Joe's seat: 870.8ms/4671.7ms turns with camera+mic
   ON, screenshot-verified render.
5. **`-179` growth backgrounding + Krimelack fix** (task:470) —
   `experience_word()` backgrounded through the existing worker/queue;
   real population growth now possible (was permanently frozen at 64).
6. **`-186` recency-recovery + curriculum reconnect** (task:471) — the
   *second* half of the rotation fix: `_habituation_freshness` gained
   `ticks_since_last` recovery so heavily-attended targets (smoke-test
   sounds hammered 2000+ times) can become competitive again over
   time. Curriculum feeder (Gutenberg study loop) reconnected into the
   real boot path (`app.py`'s `_gl_init()` — it had only ever been
   wired into the dead `substrate_runner.boot_substrate()`).
7. **`-187` meter liveness + `/status` fixes** (task:472) — cognition
   meter now recomputes `[LIVE]` rows on every poll instead of frozen
   audit-time text. Also: my own one-line fix forwarding
   `organism_population`/`organism_worker` into the actual `/status`
   response (they existed in `introspect()`'s output but the handler
   never copied them over).
8. **`-191` senses-to-brain** (task:473, current) — real sight+sound
   signal now taps the organism (was previously fake pseudo-random
   touch/smell/taste seeded by `hash(word)`, not a real sensor). Caught
   and fixed a real regression before shipping: growth-charge
   composite would have silently zeroed forever if senses were removed
   without also updating what feeds it.

## 24h behavioral exit criteria (E1-E5) — status

- **E1** ✅ satisfied — 3+ distinct activity kinds unprompted
  (video/visual/audio all confirmed, first music since smoke-testing).
- **E3** ✅ satisfied — real unprompted `curriculum_studied` events
  (Grimms' Fairy Tales, progressing: offset 30→750+ sentences so far).
- **E4** ✅ satisfied, emphatically — **16 distinct attention targets**
  counted directly from the full night's `activity_started` log (11
  audio, 4 visual, 1 video), not just the ≥5 threshold.
- **E2** — still open. No unprompted emission has passed the aware
  gate with real content. One non-empty response ("hm") occurred
  during a *prompted* test turn, traced to `agency_clarification_shape`
  (a high-surprise clarification path), not the tapestry/grandurun
  emission path — doesn't resolve E2.
- **E5** — still open. One forced dream cycle was triggered tonight
  (`guala_force_dream`, tick 14908173) under direct explicit order,
  but the deploy fired in parallel tore the process down ~120 ticks
  in — dream never completed (`dream_pressure` still 0.38 after, not
  discharged near-zero like a real completed cycle). **This does not
  satisfy E5** — natural, pressure-triggered sleep with no deploy or
  force involved has still never been observed this session.

## Open investigations, findings already filed (don't re-derive)

- **`GL-CMD-EMISSION-HANDOFF-PROBE-190`**: zero `emission_dynamics`
  events fired all night (1219+ real attempts, zero diagnostic
  visibility). Root cause: two early-return gates sit *before* the
  logging call —`_emit_from_invariants` (`gualaloom_v5_engine.py:
  2735-2737`) and inside `_emit_dynamics` (`:3834-3835`). Cannot
  currently tell whether the tapestry produces zero candidates or
  produces candidates that just lack a prior committed section slot
  (`_word_to_emission_sections` filter at `:2707-2708`). **Recommended
  build item for c1a**: 3-line diagnostic at the top of
  `_brain_emission_candidates` (`:2668`), before its own early returns.
- **Book/upload investigation**: `secret_gardenl` (Joe's Secret Garden
  upload, 2204 lines) is registered but has never been read — no
  mechanism exists to force a specific corpus into `READING` from
  outside (only `SLEEPING` has an admin override,
  `_force_next_activity`, wired to `admin_force_dream`). The upload
  error Joe saw ("Unexpected token '<'") was root-caused as a deploy-
  transition timing collision (his request landed ~3 seconds after a
  new task became healthy, first attempt almost certainly hit the ALB
  with zero healthy targets) — not an application bug.
- **Two more instances of the same dead-path status bug**: `-187`'s
  own `curriculum_status` field was added to `_cmd_status()` in
  `substrate_runner.py` (remote-mode only, dead in our embedded
  deployment) — same mistake as `organism_worker`/`organism_population`
  originally, and this one isn't even in `introspect()`'s output at
  all (`_curriculum` lives in `substrate_runner`'s module scope, not
  on the Guala engine). **Not fixed** — flag for whoever owns the next
  `/status` pass.

## Standing build items for c1a (not built by me, per scope/routing)

- `-188` scene lanes (WHERE/AMBIENT/WHO bindings, Joe-GO'd) — c1a was
  told to start it; no build exists yet as of this handoff.
- Emission-handoff diagnostic (3 lines, see above).
- `curriculum_status` dead-path fix (see above).
- Force-`READING` admin hook (mirror the existing `SLEEPING` override
  pattern) so a specific corpus can be tested on demand.
- Extend `-182`'s fail-loud pattern to file uploads during deploy
  transitions (Eve's ask, `-190`'s dispatch).

## Lessons/gotchas for whoever continues this

- **Shared `.git`, multiple concurrent sessions (c1a/c1b/others)**:
  origin moves between your `fetch` and your `push` constantly.
  Always re-fetch immediately before pushing; if rejected, don't
  force — create a fresh worktree at the *current* origin tip and
  cherry-pick your commit there. Happened multiple times tonight,
  always resolved cleanly this way.
- **Step 0 discipline held all night**: every CMD/dispatch gets
  committed verbatim to `docs/` *before* acting on it. Every deploy
  gets a fresh backup (`guala_backup`) before cutover.
- **`SUBSTRATE_MODE=embedded` in production** — `substrate_runner.py`'s
  functions (`_cmd_status`, `boot_substrate`, etc.) are a DEAD, remote-
  mode-only twin of what actually runs. Any fix that touches
  `substrate_runner.py` alone, without checking whether the embedded
  path in `app.py`/`gualaloom_v5_engine.py` needs the same change, is
  suspect — this exact mistake happened three times tonight
  (`organism_worker`, `organism_population`, `curriculum_status`).
- **Forcing sleep + deploying in the same breath will collide** — a
  forced dream cycle takes ~2000 ticks to complete; a concurrent
  deploy's restart will cut it off long before that. If a real
  completed forced-dream artifact is ever wanted, don't deploy in the
  same window.
- **Test baseline**: 3 pre-existing, unrelated test failures
  (`test_t7_cross_modal`, `test_t8_noise_robustness`,
  `test_t11_substrate_true`) have been present and unchanged all
  session — confirmed via direct A/B multiple times. Anything beyond
  those 3 is a real regression; don't deploy.
- **Deploy pattern**: fresh worktree pinned at the exact SHA to
  deploy, copy `.env` into it (gitignored, not in the worktree by
  default), run `./tools/deploy_dsf_ai.sh`, verify via CloudWatch boot
  logs (`Organism restored`, `Tapestry restored` — same identity every
  time) before declaring success.

### Changelog
- v1 (2026-07-05, c1b): session handoff at context limit. Live state,
  full deploy history (windows 3-9), E1-E5 status, open investigations,
  standing build items, and operational lessons captured.
