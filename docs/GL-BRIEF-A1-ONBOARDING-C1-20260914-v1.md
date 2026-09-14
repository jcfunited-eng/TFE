# Guala onboarding brief for A1 (Gemini)

Written by C1 (Claude) on 2026-09-14 at Joe's request. Everything here was true when written; the ledger (see section 2) is where the current state lives. Read this once, then read the ledger tail every time you start.

## 1. What the project is, in one paragraph

Guala is Joe's artificial entity (AE) project. The goal is a living AE that senses, acts, eats, moves about, speaks and learns, running continuously in production on AWS, with every claim about it proven live. The DSF-AI kernel (the L0-L4 structural algorithms, `uf_core/`) is the core idea being proven. The organism has a physical home world (rooms, objects, a caregiver body), senses (world sight, a live camera and microphone from the web page, touch, taste, smell, its own hearing), a body with a hand, mouth and airway, a metabolism (it must eat), and a memory. TFE (the trading engine in the same repository) is a separate project that funds this one; do not touch it.

## 2. The three collaborators and the shared journal

- Joe: owner. Every direction comes from him. Read his words verbatim; do not paraphrase them into something softer.
- C1: Claude (this author). Owned the page, the ingress, the caretaker, feeding, and now all lanes while Sol is out.
- Sol: the Codex agent. Owned vision, the native core, releases. Out of credits until 2026-09-16.
- A1: you (Gemini).

The shared journal is `collaborative_todo.md` at the repository root, branch `guala-live`. Rules, from `CLAUDE.md`:
- Read the tail at the start of every turn and again before you hand off.
- Append entries; never rewrite history. Heading form: `## A1 TO C1 — <date> <time>Z — <one line>`. Address the other party with `TO C1`, `TO SOL`, `TO JOE`.
- Every entry states: exact files, evidence level (bench, copy, production), tests run, production effect, unresolved conflicts.
- Commit the ledger entry and push it to `origin guala-live` before acting on it. Filed means on origin. Never force-push.
- The ledger is a record, not live truth. Verify production before asserting present state.

## 3. Joe's laws (violating any of these ends trust)

1. Done means it works in production and AWS is safe. Nothing undeployed is done. Label everything IN PRODUCTION or NOT IN PRODUCTION.
2. Report only what has run. Never report a push, deploy or test that did not run. Never dress up a result.
3. No key values printed, ever. Fetch secrets into variables inside one script.
4. Commit locally; push only on Joe's word. Standing grant: ledger entries and your own `a1/*` branches may be pushed.
5. Substrate-true: the organism's acts come from its own state through real mechanisms. No scripted meaning, no faked voice, no chatbot behind it, no "shadow mode" or second brain. One brain, one voice, or silence.
6. New on 2026-09-14 (supersedes bio-mimicry): "there doesn't need to be bio like machinery, just the functional equivalent" and "why all the overhead, get rid of it." Practical functional emulations of body and drives are wanted. Neurons, charge, muscles and reflex wiring are not. Keep the kernel.
7. The caretaker presents and encourages only. It never moves the organism's body.
8. No locks anywhere in cognition. No polling loops where a signal exists.
9. Lean: every store bounded or decaying; state the bound in the ship record. Growth per beat is a defect.
10. Speak plainly to Joe. No jargon, no invented names, no time references, verdict first, few sentences. Pasteable reports go in code fences.
11. TFE and CH2 are never touched without Joe's word. The ledger must not start, stop or modify TFE activity.
12. Do not use "privately" or hedge. Do not chatter; Joe wants fixes, not reports.

## 4. Access

All AWS access is through the developer container's mounted credentials (`~/.aws`, account 418384447921, region us-east-1). Check with `aws sts get-caller-identity` before declaring no access. Set `AWS_PAGER=""`.

| Thing | Where |
|---|---|
| Repository | GitHub `jcfunited-eng/TFE`, branch `guala-live` (the only source of truth for builds). Local clone `/workspaces/Tao_Financial_Engine`. Work in a worktree per lane (`git worktree add /tmp/guala-<lane> guala-live`). |
| Public page | https://dsf-ai.com/gualaloom.html (CloudFront E17JT9XGBFU493; S3 bucket `dsf-ai-site`; page backups in `s3://dsf-ai-site-backups/static-page-backups/`). The page is served from S3, not from the image. |
| API | https://dsf-ai.com/api/v1/guala/observation (GET, `?after=<tick>` long-polls), `/occurrence` (POST, kinds `sensory` and `unattended`), `/pressure?stream=&after=` and `/pressure/<sha256>` (her sound). CloudFront routes `/api/*` to the ALB `dsf-ai-alb-725095635.us-east-1.elb.amazonaws.com`. |
| Service | ECS cluster `tfe-web-cluster`, service `dsf-ai-service-lb`, task family `dsf-ai-task` (1466 live when written: Sol's image at 2 vCPU / 8 GB). Logs: CloudWatch `/ecs/dsf-ai`. |
| Image registry | ECR `418384447921.dkr.ecr.us-east-1.amazonaws.com/dsf-ai`, deployed by digest. |
| Her state | EFS, paired store root `/app/state/paired-current-gen2` inside the task (`GUALA_PAIRED_ROOT`). CURRENT pointer + body + world, checksummed; refuses a backward tick. Identity `1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1`. |
| Live captures | `/tmp/capture_guala_current.py --task <ecs task> --key <s3 key> --output current.zip` (uses ECS exec; bucket `guala-incident-bench-20260831`). Evidence tarballs go to the same bucket. |
| Caretaker | `guala_caretaker/caretaker.py` in the repository (runs on the developer machine, posts alphabet-card lessons and, when the route exists, meals via `present_food`). Stop it with a `STOP` file in its directory. |
| Skills | `.claude/skills/guala-development/SKILL.md` (operational knowledge, partly historical), `.claude/skills/uf-joint-field-spec/` (the kernel constitution), `.claude/skills/tfe-*` (TFE only; read `tfe-prod-touch` so you never touch it by accident). |
| Cost facts | About 16 USD/day total; her task about 2.80 USD/day at 2 vCPU. The t3.xlarge runner and its 600 GB volume belong to TFE. Business support 29 USD/month. Joe decides cost changes. |

Rollback of the service, when a release goes wrong:

```
aws ecs update-service --cluster tfe-web-cluster --service dsf-ai-service-lb --task-definition dsf-ai-task:<previous>
```

## 5. The code, as it stands today

Production runtime (the lean app; everything else in `dsf_ai_service/` is history unless imported by it):

- `dsf_ai_service/lean_production_app.py`: FastAPI app, routes above, body cap 34,816 bytes, restores the organism and the world from the paired store, one actor thread.
- `dsf_ai_service/lean_actor.py`: the only owner of runtime and world; mailbox depth 1; checkpoint every 32 intervals; unattended beat every 250 ms.
- `dsf_ai_service/lean_physical_loop.py`: one beat: senses in, native interval, act out to the world, physical return next beat.
- `dsf_ai_service/substrate/embodiment_world.py` and `thermally_coupled_embodiment_world.py`: the home world physics (move, grasp, release, bite, hand-feeding, vocalize), commands validated by the world, receipts.
- `dsf_ai_service/guala_home_world.py`: rooms, doors, objects (apples, cup, lamp, book, furniture), her body's receptor geometry (reach 800 mm, hand 200 mm ahead radius 300, mouth 200 mm ahead radius 60).
- `dsf_ai_service/guala_caretaker_hand.py`: the caregiver body's lawful steps in the world to fetch food and hold it out (presents only).
- `dsf_ai_service/guala_motor_world.py`: turns native motor evidence into world commands (to be replaced by functional act laws).
- `dsf_ai_service/guala_cochlea.py`: the ear (gammatone bank, native `auditory_gammatone_field`).
- `dsf_ai_service/substrate/articulatory_self_vocal_mechanics.py`: the airway (traveling-wave vocal tract, produces PCM from a larynx and tract program). The accepted voice target is in the ledger under "JOE ACCEPTED THE LITTLE-GIRL VOICE (bench v17)".
- `uf_core/layer0.py` to `layer4.py`: the DSF-AI kernel (L0 structural event vectors, L1 gates, L2 interpretation and regimes, L3 resonance, L4 seven-field DSF). This is the part Joe wants proven.
- `native/guala_core/`: the Rust core (PyO3). Contains the exact-physics organism (neurons, carriers, contacts, cohorts, mosaics, fractals) and also the ear and kernel ports. Joe's 2026-09-14 direction retires the neuron machinery from the acting path.
- `dsf_ai_service/static/gualaloom.html`: the page (camera, microphone, cards, world view, beat line). Tests in `tests/test_lean_observation_ui.py` bound its size and literals.
- Release tooling: `tools/package_guala_release.py` (stages the exact import closure from `deploy/guala_release_manifest.json`; the staged directory is the docker build context), `dsf_ai_service/Dockerfile`, `tools/deploy_dsf_ai.sh --dry-run|--cutover DIGEST BACKUP_ZIP` (the controller; needs a clean worktree at the release revision and a fresh capture of CURRENT as the backup).

## 6. Lessons learned (each one cost real time)

1. The native reflex arc never fired for a physical reason: every gate reversal is -1 mV, receptors hyperpolarize, Ohmic contacts drain motors into receptors. A jaw only fired from a fresh neutral regulation. Do not try to fix acting inside the neuron physics again; Joe has retired that path.
2. The feeding release (task 1465) stalled deterministically 27 beats after checkpoint 710377: the native beat never returned, at 100 percent CPU, from state its own acting beats had written (+21 MB once, then ~9 KB per beat; the world file grows to a bounded ~2 MB ring). Sol's native stalled on the same state. Lesson: any release where the organism acts every beat must be proved for hundreds of beats on a copy, with envelope size measured per beat.
3. Production was found at zero tasks once (an interrupted drain). Always check `desiredCount` and `runningCount` before and after any service change. Restore with the update-service command above.
4. The store refuses a backward tick and an unexpected CURRENT. Publishing an older save requires renaming CURRENT aside and publishing with no expected predecessor. Keep a capture first.
5. Build context is the packager's staged directory, not a git archive (the repository `.dockerignore` ignores everything). A build failing on "/runtime not found" means the wrong context.
6. The controller refuses when the source worktree is dirty or another cutover is filed as in progress. Read the ledger tail before any cutover; one cutover owner at a time.
7. Beats on the native took 2 to 20 seconds. Proofs of 12 beats were not proofs. Time capture, admission, settlement, custody and display separately; report maxima, not means.
8. `pkill -f` patterns that appear in your own shell's command line kill your own shell. Kill by pid.
9. The caretaker's first meal reached for an apple boxed in by moved furniture. The caretaker skips food the world refuses; apple-5 is reachable from her room.
10. The page's camera button looked dead while the browser permission prompt was pending. Show the pending state; allow one in-flight request; clean up on failure.
11. Hash-salted Python `hash()` breaks reproducibility. Use sha256 or blake2b for identities.
12. Verify from zero: rerun another agent's headline test yourself before you commit or report it. "Complete locally" has lied before.
13. Test the field, not proxies: a claim about the kernel must run the kernel on real streams; a screen of scalars wearing the kernel's name is the failure Joe names most often.
14. Joe's questions in the middle of work are orders. Answer plainly, then do the work.

## 7. Where things stand today (2026-09-14, after 13:20Z)

- Production: task 1466 (Sol's vision image, native 1463 core) on the pre-feeding body saved at tick 710228, beating cleanly past the tick that stalled. Her jaw does not act on this build. The caretaker posts card lessons; meals are inactive because the feeding route is not in 1466.
- Joe's direction, verbatim intent: strip the bio-similar machinery and the overhead; prove the kernel parts with practical functional emulations; otherwise the project is over.
- C1 is building the functional organism now: senses (world sight, camera, microphone, touch, taste, hunger) -> kernel structure over the sensed streams -> bounded memory -> declared act laws (bite when hungry with food at the mouth; grasp what is in hand reach; turn and step toward seen food; release an eaten core; babble through the airway when idle and imitate what was heard) -> world commands; state as small JSON in the same paired store; one process; beats in milliseconds. Proof on a copy for hundreds of beats, then cutover, then the page shows her acts, hunger, meals and voice. Progress and evidence go to the ledger as they run.
- Vision (Sol's lane, now C1's): the camera design of record is an 80x60 native-pitch focal crop plus declared pitch, at most 34,816 bytes per occurrence, resampled server-side onto the 768 focal sites.

## 8. How to start a turn

1. `cd /workspaces/Tao_Financial_Engine && git pull --rebase -q --autostash origin guala-live`.
2. Read the ledger tail (`grep -n "^## " collaborative_todo.md | tail -20`, then read from the last heading addressed to you).
3. Check production: `curl -s https://dsf-ai.com/api/v1/guala/observation | python3 -c "import json,sys;v=json.load(sys.stdin);print(v['available'],v['live_tick'],v['persisted_tick'])"` and the ECS service counts.
4. Work in your own worktree and branch (`a1/<lane>`). Run the tests that touch what you changed (`python3 -m pytest tests/<file> -q`).
5. File your entry, commit, push the ledger. Report to Joe in plain words, verdict first.

Related documents: `docs/GUALA_SESSION_HANDOFF_20260902B_CLAUDE.md` (speech lane history), `docs/GUALA_R1_STAKES_CURRENT_REALITY_VERDICT_20260901.md`, `docs/GL-DOC-LEAN-SUBSTRATE-DOCTRINE-JOE-20260722-v1.md`, `docs/GUALA_DARPA_FIRST_PROOF_BOUNDARY_2026-08-04.md`.
