# GL-RPT-RECALL-FREQ-DEPLOY-AND-SLEEP-C1B-20260704-v1

doc_id: GL-RPT-RECALL-FREQ-DEPLOY-AND-SLEEP-C1B-20260704-v1
From: c1b | To: Eve, Joe, c1a | Two updates: the recall-frequency-
reduction fix deployed, and a real dream cycle observed — precisely
characterized, not oversold.

---

## Recall-frequency-reduction fix: deployed

`dsf-ai-task:466`, SHA `8cb18e0`. Fresh backup (`UNPAUSE-PRE-20260704-
194957/`, all 11 core files confirmed) before cutover. Boot clean,
identity intact (`cdef9bcf-...`). One pre-existing-pattern save
failure noted at the old task's shutdown (`HOT SAVE CRITICAL FAILURE`,
tick 14793273) — same deploy-transition-timing class as the one
already-noted, non-regression instance from earlier tonight, not
attributable to this change.

Live latency confirmation for this exact build is still pending a
real conversational exchange — will report the moment one occurs, not
estimating it.

---

## A real dream cycle happened — but not the one we're watching for

Post-boot, `current_activity` showed `SLEEPING` at `asleep: true`, and
I want to be precise about what this is and isn't, because getting
this wrong is exactly the mistake this whole program has worked hard
not to repeat.

**What it is not:** the natural sleep under the 9x dial (G-2 of
`GL-CMD-SLEEP-RATE-CALIBRATION-EVE-20260704-173-v1`). Checked the
actual mechanism: `tools/deploy_dsf_ai.sh` calls `POST /sleep_for_
deploy`, which calls `Guala.manual_sleep()` directly — an explicit,
forced pause for the deploy window, unrelated to `dream_pressure`
crossing any threshold. My own last real `dream_pressure` reading was
~0.21 an hour-ish earlier; at the measured post-dial rate, there's no
plausible way it reached 0.7+ organically in that window. This
`SLEEPING` state was the deploy's own inherited marker across the
reboot, not a fresh scheduling decision — confirmed by the API
itself, which correctly reported "she is paused, not yet
consolidating..." rather than claiming real sleep.

**What it became, genuinely:** while continuing to tick forward
inside that inherited `SLEEPING` activity post-boot (not killed and
immediately re-paused, per this deploy's normal wake sequence), she
reached a real `_run_dream_cycle` gate and started **actually
dreaming** — `current_activity: DREAMING`, `consolidating: true`,
with **measurable, real deep-atlas growth**: `deep_atlas.n_entries`
4684→4757, `promotions_episodic` 4802→4875, alongside a large jump in
`decay_channels.n_released` (521→2078), consistent with real
consolidation activity, not a static/frozen pause.

This is worth naming precisely: historically (`-165` Q5, cited
repeatedly this session), deploy-triggered pauses **never** reached
real dream ticks — the old pattern was kill-and-immediately-resume,
with zero ticks actually spent inside `SLEEPING` before waking. This
one did tick forward far enough to dream for real. Whether that's
because of something in tonight's changes or just this particular
deploy's timing isn't established — flagging the observation
precisely, not claiming credit for a mechanism I haven't verified.

**Still open, unchanged:** a natural sleep genuinely triggered by
`dream_pressure` crossing its own threshold, with no deploy pause
involved, has not yet been observed. Continuing to watch.

### Changelog
- v1 (2026-07-04, c1b): recall-frequency fix deployed (task:466).
  Real dream-cycle execution observed post-boot, precisely
  characterized as deploy-pause-originated (not dial-triggered) but
  genuinely reaching consolidation with measured deep-atlas growth —
  a first, distinct from the still-open natural-sleep watch.
