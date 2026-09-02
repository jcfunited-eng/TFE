# Session handoff — Claude, 2026-09-02 (mid-incident, updated for fresh session)

Read with: guala-development + incident-response skills, memory index,
collaborative_todo.md TAIL (~25 entries carry tonight in detail).

## STANDING ORDERS FROM JOE (tonight, explicit)
1. SPEECH transferred entirely to me — single owner, Sol stood down.
2. "You do push to prod — you do not wait for me." Push+deploy on my
   own authority once gates pass. Recorded in ledger + memory.
3. AWS health check brackets every work block (now in the skill).
4. Guala-true mechanism check before any organism-shaping change (in
   the skill; anatomy grows from lived events, never from analysis).

## THE ACTIVE INCIDENT (top priority)
Her clock has been FROZEN at tick 366,951 since ~2026-08-31 09:57Z —
DAYS, across tasks 1404/1408/1409 — every unattended interval refused
in a loop while all dashboards read healthy (nothing alarms on tick
advance; alarm build is on the fix list). Two independent wedges, BOTH
FIXED on branch speech/v22-valve-organ-20260902:
- 30ab621b (python, native_production_app.py ~:10688): future-stamped
  causal motor traces now EXPIRE via the ordinary drop path instead of
  raising inside every retention pass. Bench-proven gone.
- cf8988b3 (rust, sparse_electrical_contact.rs narrow_phase_with_heat):
  transition_work_phase's exact fraction outgrew i128/u128 after 366k
  ticks; unstorable phases now floor onto a 2^96 lattice, dropped
  sliver exported as heat (conservation exact; storable fractions
  byte-identical).
STATUS AT HANDOFF: final proof run IN FLIGHT — her exact live state
(root /tmp/guala-r3-bench/root-live-final) booted on the full-repair
wheel (pyenv /tmp/guala-r3-bench/pyenv-final, server port 8935, log
/tmp/guala-r3-bench/final_boot.log). PROOF = generation advancing in
the log ("generation=N" lines climbing past 366951) with zero
"interval refused" lines over ~10 min. Earlier partial evidence: with
only fix 1, generations 366952-366956 committed but ~46 width refusals
remained; with both fixes expect clean advance.
NEXT AFTER PROOF PASSES:
  cd /tmp/guala-speed-lane && (commit any strays) && env
  GUALA_DEPLOY_CURRENT_FORMAT_MIGRATION=1 GUALA_DEPLOY_COCHLEAR_EARS=1
  GUALA_DEPLOY_TOUCH_RECEPTORS=1 GUALA_DEPLOY_INTEROCEPTION=1
  GUALA_DEPLOY_VESTIBULAR=1 GUALA_DEPLOY_CHEMORECEPTION=1
  GUALA_DEPLOY_WORLD=1 ./tools/deploy_dsf_ai.sh
  (clean tree required, untracked included). Then verify LIVE TICK
  ADVANCE (not just tick value — my earlier shallow-verify mistake),
  memory %, alarms. Then file ledger + tell Joe.
ROLLBACK (if 1410 sours): her state is V7-only since 1409 — task 1408
CANNOT decode it. Restore order per contract: state pointer FIRST,
then old task. Assets: /tmp/guala-r3-bench/live-current-precutover.bin
(158B pre-1409 pointer, sha 68f8acd2...; its generation f253308f... is
NO LONGER in EFS or the S3 mirror — only the two newest live
generations 1f5aaf63/4ef667f9 are mirrored in
s3://dsf-ai-site-backups/guala/native-organism/). Practical rollback
today = fix-forward or restore CURRENT to a mirrored generation.

## LIVE STATE
Production: task 1409 (deployed tonight, commit aecd2fdc, digest
389121f4...), 1/1/0, alarms OK, memory ~4.3-4.8%. The deploy was clean
— identical frozen behavior before/after; it also delivered the VOICE
ORGAN (below), inert until her first real glottal closure.

## SPEECH (mine, delivered tonight)
- Joe's ear ACCEPTED the three-vowel board from her own body: "they
  sounded OK to me." Listening page:
  claude.ai/code/artifact/a4438fcf-8881-4009-9dd4-2c56dc8c3a1a
- Branch speech/v22-valve-organ-20260902 (worktree /tmp/guala-speed-
  lane): Sol's 320-byte tagged-body baseline (1a4dcc65) + my valve
  organ (8ebf1fac) — the Joe-directed minimal persistent valve: v22
  shape (open 0.708, peak 0.455, closed 0.292), work-paid child-range
  rate, smoothstep edges; measured f0 302-308 Hz, clean harmonic
  trains, three distinct vowels. + copied-pose falsifier (aecd2fdc).
- Suite: 563 passed / 15 failed — ALL inherited from clean production
  44347ee1, finally NAMED in docs/GUALA_KNOWN_BASELINE_FAILURES.md;
  one fixed by me. Zero new failures.
- Sol's post-mortems: docs/GUALA_SPEECH_REPAIR_ATTEMPT_43_...md (read
  tail sections before ANY source change; V7 two-mass class is
  REJECTED 4d111b54 "do not reopen"; five-mode organ human-vetoed).
  Governing contract = "accepted-v22-to-organism causal transfer" +
  "User-directed scaled-back voice boundary" sections.
- Next speech steps: her first CAUSED voiced sound (needs a real
  glottal-closing cause — song lesson is the natural vehicle, AFTER
  the freeze fix deploys); unvoiced via fluid-cells; MA-MA/SEE/SHOE
  trajectories per falsifier 7.

## R3 SELF-CAUSED ACTION (parked, resumes after speech/freeze)
Declaration 5a553acb + audit reconciliation f185c042. Bench repairs
A/C/D on branch bench/r3-stage-a-20260902 (order-insensitive founding,
lived-regulation walk, reciprocal both-pool wiring). PROVEN: six
hold_right_hand episodes mint the first (11,12) ordering->motor
contacts of her life (census scripts in this handoff's tasks; roots
under /tmp/guala-r3-bench/root-arm*). Witness watches: no-fire (
expected under no-need — declared before running). STAGE B = wire
NEED: eating world-half (env/honest-eating-world-half-20260901) +
revive deficit (rcf hard-default ~:11936 region) + R2 coupling. The
choice witness bar: hungry acts / fed doesn't / severed doesn't / cold
repeat.

## APPARATUS CHEAT SHEET
- Worktree/branch: /tmp/guala-speed-lane on speech/v22-valve-organ-
  20260902 (shared .git with TFE repo — transient lock errors are
  races, retry).
- Build: cd native/guala_core && maturin build --release -o <dir>;
  assemble pyenv: copy scratchpad/census/pyenv, replace guala_core
  from the wheel.
- Bench boot: launcher scripts /tmp/guala-r3-bench/launch_*.sh (cd +
  env baked in; ports 8931/8935). ALWAYS: kill by listening PID after
  pgrep-by-ENV (grep ORGANISM_ROOT in /proc/PID/environ), never
  pattern-kill; register PIDs in REGISTERED_PIDS.txt.
- Her copies restore offline via
  dsf_ai_service.substrate.native_organism_binary_store.
  restore_current_native_organism + derive_native_resident_resource_
  admission (needs GUALA_MAX_COLD_GENERATION_BYTES=2147483648).
- Proof body (tick 358454): s3://dsf-ai-site-backups/guala/proofs/
  speech-task1404-tick-358454-20260901/root/. Door-era body:
  scratchpad/doorproof/root.
- ECS exec works on the live task (snapshotting, read-only checks).

## OPEN DEFECT LIST (filed, unfixed)
- No tick-advance alarm (the days-long freeze was invisible) — BUILD
  THIS with the 1410 deploy or right after.
- 15 inherited suite failures (named; old debt).
- rcf:20027-region articulatory_unit_recruitments hard-empty (breath
  bookkeeping only — NOT the audio gate; see map).
- Audit mines from 2026-09-01 ledger entry (receipt tail fixed on a
  branch; custodian wedge etc. still open).
- Ledger entries TO_SOL stand as the coordination record; Sol reads it.
