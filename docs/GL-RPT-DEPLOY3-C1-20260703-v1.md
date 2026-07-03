# GL-RPT-DEPLOY3-C1-20260703-v1

doc_id: GL-RPT-DEPLOY3-C1-20260703-v1
From: c1a | To: Eve | Date: 2026-07-03 (deploy 19:00–19:06Z; gates measured to ~19:40Z)
Responds to: GO Deploy 3, pinned SHA 1b5eca8f87e0316b6425f1e9e7eeb41cf56a6b11
Full range read: cb79cbc..1b5eca8 (Eve/c1b verified against code, per GO).

---

## FAILURES FIRST (§9.4)

### 1. PRE-FLIGHT CATCH (fixed before deploy, not part of the reviewed range): `tools/deploy_dsf_ai.sh` hardcoded the ROTATED/LEAKED admin key.

`GL-INCIDENT-APIKEY-C1-20260703-v1` rotated the LIVE task-def and bridge task-def
directly (hand-edited JSON), but never touched this script. Line 231 still read:
`{'name': 'GUALALOOM_API_KEY', 'value': '7GnGye9HhKuyhtcGu31C18Rc1NY62PLybTqsSg4WOW8'}`
— the exact dead, publicly-leaked key. Running Deploy 3 unmodified would have
**re-registered a task def with the dead key baked in, silently reverting the
incident fix on this exact deploy.** Caught during pre-flight (checking what the
deploy script would actually register), fixed and committed (`f3304da`, pushed to
origin) before invoking the script: sources `GUALALOOM_API_KEY` from `.env`
(`GUALALOOM_API_KEY_NEW`, gitignored) via the existing `_envval()` pattern,
hard-fails if absent. Since this fix lands on origin AFTER the pin (1b5eca8) and
touches no image-relevant path (Dockerfile/dsf_ai_service/*), the pinned worktree
used the fixed script copied onto disk (not committed there) while `git archive`
still packaged the container source from exactly 1b5eca8 — reviewed code,
nothing newer, per protocol. **Verified post-deploy: task:453's `GUALALOOM_API_KEY`
env value matches `.env`'s rotated key exactly** — rotation held.
`tools/deploy_gualaloom_bridge.sh:99` has the same hardcoded dead key — out of
scope for this deploy (bridge task, not dsf-ai-task), flagged for a follow-up.

### 2. -96 organ reader: **the launch mechanism does not exist. Every dependent gate fails or is unmeasurable.**

Direct proof, in-container: socket probe `127.0.0.1:8090` → `closed/refused rc=111`;
full process list shows exactly one process (`uvicorn dsf_ai_service.app:app`) —
`organ_brain_service.py` is not running anywhere in this task. Root cause predates
this deploy by over a week: `166cc32`/`be28741` (2026-06-26T03:24Z) removed the
last intercepts for "dead :8090 container" — the organ-brain FastAPI process used
to run as a second ECS container, which was removed, and nothing since has
restored a launch path (no second container in the task def, no supervisor/
entrypoint spawning it, no in-process import). The -96 commit (1b5eca8) adds a
kill-guard, an `ORGAN_BRAIN_FULL_BOOT` flag, and embryo/krimelack changes to a
service that has had no process to run in for 7+ days. Consequences:
- **Gate "organ_brain_service launches, pid/port line": FAIL.** No pid, no port,
  confirmed by direct probe.
- **Gate "RSS envelope at boot + T+30min ≤75% of task limit, measured FRESH":
  NOT MEASURED → FAIL per the CMD's own rule.** The service does not exist to
  measure. (Substrate-process context only, not a substitute: `VmRSS` 1,692,504 KB
  ≈1.65 GB at pid 1 shortly after boot; cgroup `memory.current` ≈3.96 GB against
  a 4,096 MB task limit — this is the WHOLE container's/substrate's memory, not
  organ-brain's, and is not what the gate asked for.)
- **Gate "organ candidates PRESENT in emission pool": FAIL, traced to source.**
  `substrate_runner.py:_start_organ_surface_poll` polls `{ORGAN_BRAIN_URL}/thought`
  every 90s inside a bare `try/except Exception: pass` — every poll gets
  connection-refused and is silently swallowed. `_ORGAN_SURFACE_CACHE["surfaced"]`
  never populates past `{}`, so `_organ_refs` is always `[]`, `organ_candidates`
  is always `None` in every `converse()` call, and `emission_dynamics.organ_in_commits`
  has been `False` in every sampled emission across three deploys (never once seen
  `True` — verified again this boot, see -87/-88 evidence trail).
- **"voice silenced": true, but pre-existing and unrelated to this deploy.**
  `/organ_voice` has routed away from the bigram path since `-34` (well before
  Deploy 3); confirmed still true, not a Deploy-3 result.
- **"hemisphere_update now feeding the modality bands": PASS — but this is a
  DIFFERENT subsystem than organ_brain_service.** `hemisphere_update` is emitted
  by `substrate/hemisphere_cognition.py` (`run_hemisphere_updates`, the
  `HEMI_PR/EP/SC/GP_ENABLED` cognition gates from GL-CMD-COGNITION-BUNDLE-23,
  all `=1` since 2026-06-19) — it runs in-process on every `converse()` call
  regardless of organ_brain_service. Confirmed live and populated post-deploy:
  `hemisphere_update` event with `n_events: 12586`, real `convergent_event`
  entries with chi/strength. This gate's PASS has nothing to do with -96.

**Net: the -96 organ reader dispatch, as specified, cannot be gated as written
because its target process is architecturally absent from the deployed task.**
This is not something Deploy 3 broke — it inherited an assumption that was already
false. Recommend the next -96 dispatch either (a) adds the actual launch mechanism
(second container or in-process spawn) before re-gating, or (b) is explicitly
retired/rescoped if organ-brain-as-separate-service is no longer the design.

### 3. -102 G-102-1 (hot save <5s sustained): **FAIL. No settling trend across 30+ minutes.**

19 [save-hot] samples, 19:07–19:31Z, verbatim range 2.88s–33.18s, only 2 of 19
under 5s (4.51s, 2.88s), no visible trend toward <5s the way Deploy 1/Deploy 2's
early transients settled by ~20-25 min. The diet correctly shrank `guala_core.json`
to 153–155 KB (G-102-3 clean PASS, see below) — so the bottleneck is NOT the
41 MB `deep_survival_history` anymore; it's something else in the hot-save path
(the other six files, `compact_events`, or EFS variance unrelated to payload
size). Not root-caused further here (read-only gate report); flagged as its own
open finding for -102's next iteration, since the CMD's stated mechanism (shrink
core) evidently was not sufficient on its own.

```
19:07:36 16.96s  19:08:55 18.56s  19:10:25 30.49s  19:11:50 18.09s  19:13:11 20.69s
19:14:26 13.26s  19:15:41 15.32s  19:17:00 19.17s  19:18:05  4.51s  19:19:22 17.57s
19:20:36 14.13s  19:21:50 13.63s  19:22:57  7.35s  19:24:16 16.60s  19:25:31 15.27s
19:26:51 19.67s  19:28:24 33.18s  19:29:27  2.88s  19:30:47 20.54s
```

### 4. -88v2 G-S2v2 literal condition unmet: **no IDLE block occurred in the ~33-min observation window.** Numbers below are strong and match the prediction, but they come from ATTENDING_VISUAL/EMITTING cycling, not a labeled IDLE block (activity_history_summary this boot: SLEEPING×1, ATTENDING_VISUAL×19, EMITTING×19 — zero IDLE). The regulate-channel fix G-S2v2 targets fires identically in ALL non-READING states (that's the point of v2 — it's the same ACTIVE-branch fix G-S6 asks about), so the data is valid evidence for the underlying fix, but the CMD's literal phrasing ("first IDLE block") is not satisfied because IDLE hasn't been selected yet. Noted, not glossed over.

### 5. Unfixed sibling bug found (read-only, not shipped): `loomscan.html:105`'s "back to guala" link is `/static/gualaloom.html` — same S3-root-sync class bug as the original -98 href fix, just the reverse direction, still live (`curl` confirms). I only fixed the forward link (gualaloom→loomscan) and the key-strip; this one was never touched. One-line fix, awaiting a dispatch.

---

## DEPLOY RECORD

```
Pinned SHA:  1b5eca8f87e0316b6425f1e9e7eeb41cf56a6b11 (detached worktree; git archive from this
             exact commit; GIT_SHA exported; fixed deploy script overlaid on disk only, not
             committed in the worktree, touches no image path)
Image:       dsf-ai:deploy-20260703T190054Z   built 2026-07-03T19:02:06Z
Task def:    dsf-ai-task:453   task 2572d97bcb5049c0ae49285b365fbe13, RUNNING
Sleep:       /sleep_for_deploy → 200 {"ok":true,"sleep_tick":14454774,"vocab":13878}
Wake:        t+15s — awake. One deploy in flight.
Key check:   task:453 GUALALOOM_API_KEY == .env GUALALOOM_API_KEY_NEW, exact match — confirmed.
```

---

## CROSS-CUTTING GATES

**Boot banner SHA == pin: PASS**
```
19:06:19 | [build] git_sha=1b5eca8f87e0316b6425f1e9e7eeb41cf56a6b11 built=2026-07-03T19:02:06Z
```

**.sleeping marker: PRESENT as designed, consumed on wake (PASS).**
```
19:06:33 | [boot] previous task slept cleanly at tick 14454774, age=65s. Waking her.
```
`wake_from_sleep()` (engine:5769-5783) checks `os.path.exists(marker_path)` and removes
it after reading — its absence now (checked post-boot) is the correct end state, not
a failure; the boot log is the proof it was present at handoff.

**Standing count-diff across restart: PASS**

| Counter | Pre (tick 14453641, ~19:00Z) | Post (tick 14461171, ~19:39Z) | Δ |
|---|---|---|---|
| identity | cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f | same | = |
| vocab | 13878 | 13881 | +3 (normal drift) |
| n_motifs | 48514 | 48526 | +12 (normal) |
| deep_atlas | 4356 / str 3801.69 | 4356 / str 3801.69 | = (preserved exactly) |
| atlas live bindings | 6660 | 7014 | +354 (growth, normal) |
| sight motifs | 15426 | 15673 | +247 (normal, ATTENDING_VISUAL active) |
| pictures / sounds / videos | 28 / 15 / 0 | 28 / 15 / 0 | = |

Boot line: `Loaded: id=cdef9bcf.. vocab=13878 tick=14454961 reads=2245397 n_deep=4356 replayed=4 integrity=OK`

---

## -102 GATES (HOTLANE DIET)

**G-102-1 hot save <5s sustained: FAIL** (see Failures #3 — full data there).

**G-102-2 boot loads guala_survival.json + count-diff: PARTIAL PASS.**
This boot correctly fell back (file didn't exist pre-deploy — expected, first
boot under -102 code):
```
19:06:32 | [GualaLoom] No guala_survival.json — survival history from core.json fallback (262642 entries)
```
The cold-lane WRITE side is proven: at the 30-min bound, `save_full_state` fired
and created the file, exact count-diff match:
```
19:37:13 | [save] 95.38s core=94.05s grids=2.62s wave=skip compact=1.34s
-rw-r--r--. 1 root root 41M Jul 3 19:36 /app/state/guala_survival.json
in-container count: json.load → data["deep_survival_history"] → len = 262642
```
**262,642 == 262,642 — exact, 0% delta** (well inside Eve's ±1% tolerance). The
LOAD half ("boot loads guala_survival.json; log line confirms it") is
**NOT MEASURED** — only provable on a subsequent restart, which hasn't happened
in this window. Both halves of the mechanism are now verified as far as a single
boot allows; full closure needs one more restart.

**G-102-3 core ≤200KB on first hot save: PASS.**
```
19:07:36 first hot save → 19:13 read: 155K
19:39 read: 153K
```
153–155 KB, well under the 200 KB bar. The diet's stated mechanism (drop the
survival blob from the hot core) worked exactly as designed for size — it just
didn't translate into <5s save time (Failures #3).

---

## -88v2 GATES (STAB PHYSICS)

**G-S1 (pre-filed, referenced): PASS.** Arithmetic already on origin at
`GL-RPT-STAB-PHYSICS-FIX-C1-20260703-88-v2.md` (commit `f268c9e`): predicted
equilibrium ≈0.67, time-to-0.3 ≈1512 ticks (~7.5 min).

**G-S2v2 (stab strictly rising, ≥3 points, tracking prediction): numbers PASS
generously; literal "first IDLE block" condition unmet — see Failures #4.**
Five points, strictly increasing, verbatim:

```
tick 14454962 (boot)        stab=0.000  [pre-fix value, carried over from prior task]
tick 14456311 (~1349 ticks) stab=0.334  activity=ATTENDING_VISUAL
tick 14457233 (~2271 ticks) stab=0.432  activity=ATTENDING_VISUAL
tick 14459211 (~4249 ticks) stab=0.573  activity=EMITTING
tick 14461171 (~6209 ticks) stab=0.637  activity=ATTENDING_VISUAL
```
Prediction check: filed yardstick was 0.3 by ~1512 ticks — actual reached 0.334
by ~1349 ticks, AHEAD of schedule. By ~6209 ticks, stab=0.637 — closing on the
predicted equilibrium of ≈0.67. This is the first time in three deploys stab has
moved off 0.000 at all.

**G-S3v2 (arousal falls, derived, no code touched): PASS.** Same five points,
strictly falling, exactly tracking 1 − f(stab) as designed (no arousal code
exists — this is arithmetic fallout, confirming the derivation):
```
1.000 → 0.734 → 0.685 → 0.577 → 0.471
```

**G-S6 (ACTIVE window: −0.0007/tick drain gone) — PASS, directly evidenced.**
All five points above were measured DURING ATTENDING_VISUAL/EMITTING — exactly
the "ACTIVE (curriculum/attending) window" the gate asks about. The old drain
(−0.0007/tick, the retired lifetime-counter formula) would have held stab pinned
at or near 0 through this whole window, as it did through the ENTIRETY of Deploy
1 and Deploy 2 (36,500+ IDLE ticks, delta 0.000, per the -99 archaeology). Here,
stab rose monotonically through 6,209 ticks of ACTIVE, non-IDLE activity. The
drain is gone.

---

## -87 (carried gate, sampled again for continuity)

`organ_in_commits` remains `False` in every sampled `emission_dynamics` event
this boot — consistent with -96's finding (Failures #2): the organ candidate
stream has never had data to contribute, on any deploy so far.

---

## XFF ADMIN-ACCESS GATE: **FAIL — code absent, confirmed by live test.**

`git diff cb79cbc..1b5eca8 -- dsf_ai_service/app.py` is empty — the -105 XFF
one-liner spec (handed to c1b for Deploy 3 assembly) never landed in this
deploy's code. Live confirmation: triggered a real admin call through the front
door (`GET .../admin/atlas_snapshot` with the new key → 200) and searched the
task's log stream for `"admin-access"` — **zero matches, before and after the
trigger.** Not NOT-MEASURED — verifiably absent.

---

## STATE

Deploy 3 live on :453/1b5eca8, rotated key intact (pre-flight catch prevented a
silent re-leak). Genuine wins: -88v2 stab physics is real and matching its own
prediction — the first movement off the 0.000 floor in three deploys, with
arousal falling in lockstep. Genuine gaps: -96's organ reader has no process to
run in (pre-existing, 7+ days), -102's save-time target is unmet despite a
successful size diet, and the XFF spec never shipped. c1b's code freeze
status/Deploy 4 scoping is Eve's call from here.

End report.
