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
