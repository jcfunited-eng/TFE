# Guala functional release tooling (C1)

Kept in the repository because the dev container's temporary directory was wiped by a
reboot on 2026-09-15 and these had to be rebuilt from the session record.

- `run_release_functional.sh package|image|push|proof` — staged context from `tools/package_guala_release.py`,
  pinned buildx image, push by digest, networkless container proof on a captured live body
  (`CAPTURE=... PROOF_OUT=... PROOF_FOOD=...`). Expects `S` (a scratch directory holding
  `live-capture-*/current.zip`, the proof script and outputs) and `W` (the release worktree).
- `run_cutover_functional.sh dry-run|cutover|page|caretaker` — controller dry-run and cutover
  gated on the proof verdict; one cutover owner at a time; never during a caretaker session.
- `prove_functional_release.py` — the in-container proof: the actor stage (real actor, 120
  occurrences with meals) then 400 loop beats and a cold restore; the verdict bars are in the
  release script.
- `capture_pair_remote.py` + `capture_cmd.sh` — capture the live body and world from the running
  container by `aws ecs execute-command` and a presigned S3 PUT (captures live under
  `s3://guala-incident-bench-20260831/captures/<name>/current.zip`).
- `sample_live.py`, `replay_capture.py`, `replay_speech*.py`, `replay_touch.py`,
  `key_stability.py`, `replay_reading_churn.py` — measurement tools on live beats and captures.

## How a release is run from here on (C1 to A1, 2026-09-16)

The chain that shipped every release on 2026-09-16 (light, renovation, shapes, lamps, the
colour eye, parts, the pupil, the departure law, the camera at her grain) is now in the
repository, with its work directories settable:

- `light_chain.sh` — the whole chain, one command. Stages: suites in the clean worktree
  (`test_guala_home_renovation`, `test_guala_world_light`, `test_guala_home_world`,
  `test_guala_world_sensorium`, `test_thermally_coupled_embodiment_world`,
  `test_guala_functional_organism`), then `release_stage.sh package|image|push`, a fresh
  capture of her live pair (`capture_cmd.sh`, name `pre`), `release_stage.sh proof`
  (networkless container: the actor stage, 400 loop beats, a checkpoint, a cold restore that
  must re-encode byte-exact, 40 more beats), `cutover_stage.sh dry-run`, a wait for a true
  boundary in the caretaker's log (a "lesson ... complete" line, then 40 s with no session
  "begins at tick"), `cutover_stage.sh cutover`, a capture after (`post`) and a live check.
- `release_stage.sh` and `cutover_stage.sh` — the stages, runnable alone (`cutover_stage.sh page`
  publishes `dsf_ai_service/static/gualaloom.html` from the worktree to S3 + CloudFront and
  checks the served sha equals the committed one; `caretaker` restarts the caretaker: only at a
  boundary, only when the caretaker's own code changed).

Run:

    aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 418384447921.dkr.ecr.us-east-1.amazonaws.com
    REV=<commit on origin/c1/drive-organ> DECLARED=52 bash tools/guala_release/light_chain.sh
    # FROM=dry-run to resume after a proof; UNTIL=dry-run to prove and stage without cutting over.
    # GUALA_RELEASE_WORK=/tmp/guala-release-work (captures, logs, proof output), GUALA_RELEASE_TREE
    # (a clean detached worktree of the repo; the script creates it), GUALA_REPO (the checkout).

Proof bars (`proof verdict: pass`): feed_pass (she ate what was offered while feeding, spoke,
crossed rooms or reached doors, the caregiver went home, an event closed in her ear), cold
restart exact, things ≥ DECLARED, windows ≥ 4. A run of 400 beats with zero door crossings can
be her variance: rerun before blaming the code. If the proof fails, read
`$GUALA_RELEASE_WORK/proof-functional-out/proof.log` (the traceback is at its tail) and the
`functional-warm.json` receipt; `paired/` holds the checkpoint the cold restore was tried on.

Laws that stand for every release: build only from a commit on `c1/drive-organ` that both
manifests list (`dsf_ai_service/lean_runtime_manifest.txt`, `deploy/guala_release_manifest.json`:
a new module missing from either does not reach the image); the proof runs on a fresh capture;
one cutover owner at a time; never during a caretaker reading or music session; the page is
published only after its runtime is in her when the page needs that runtime; done means it is
live and the page shows it; every release is filed in the ledger with what was measured live.
