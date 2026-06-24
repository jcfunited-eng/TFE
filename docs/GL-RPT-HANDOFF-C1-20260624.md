# Handoff — Guala onto the loom organ-brain (C1, 2026-06-24)

## What is REAL and LIVE (verified, not claimed)
- **Merge live in her substrate.** At her real boot (`substrate_runner.boot_substrate`,
  STATE_DIR=`/mnt/efs/guala`), she builds her 8-organ brain from her own live state,
  lossless. Verified in her own log: `[merge] LIVE in substrate: {em,pr,sc,aff...}
  lossless=True id=cdef9bcf`. She stayed herself (vocab 3594, atlas ~17.5k, deep
  14.8k, bonds joe+wc, boot/integrity ok).
- **Organ-brain speaks** (`loom_cognition.GualaCognition`): `expose()` learns
  word-succession, `compose()` walks it into real sentences (`'moon'→'moon is bright
  at night'`). Seeded at boot with a clean in-world corpus; learns continuously.
  Dispatch ops added: `/organs` (report), `/organs_say` (compose + learn from input).
  **Additive** — her existing engine voice is untouched; the organ-brain is alongside.

## The architecture you MUST know (cost me two wrong deploys)
- **Frontend/substrate split.** `app.py` is the FRONTEND; it forwards over a
  JSON-op socket to the real substrate process `substrate_runner.py`. She BOOTS and
  RUNS in substrate_runner. Code that must affect her goes THERE, not app.py.
- **Endpoints = ops** in `substrate_runner.handle_gualaloom_post` dispatch. Already
  built: `sight_frame`, `sound_frame`, `v7_converse`, `teacher_feedback`,
  `teacher_correction`, `load_corpus`, `force_dream`. Senses + learning + feeds
  EXIST as endpoints — wire the organ-brain INTO them, don't rebuild.
- **Deploy:** `tools/deploy_dsf_ai.sh` from a worktree (it ships `git archive HEAD`).
  ALWAYS deploy a SURGICAL tree (live base `9bf86de` + only your change) — the branch
  is 962 commits ahead of main and full HEAD bundles other authors' engine edits.
  `zip` must be installed. Roll back via `aws ecs update-service ... --task-definition
  dsf-ai-task:<prev>`.

## Verified facts
- AWS root in env. S3 backups: `s3://dsf-ai-site-backups/guala/auto/`. Her 11 state
  files there. ECS: cluster `tfe-web-cluster`, service `dsf-ai-service-lb`.
- ALB direct (bypasses gateway path-mapping): `dsf-ai-alb-725095635.us-east-1.elb...`.
- Bridge tools (status/backup/atlas/say/wake/give_experience) work for interaction.

## NEXT (the real work, in order)
1. **Clean her vocab** — her section data has junk tokens (`kbl`, leaked quotes).
   The organ-brain reflects them. Gate to clean words before routing her sole voice.
2. **Wire organ-brain INTO the experience endpoints** — `converse`/`load_corpus`/
   `sight_frame`/`teacher_feedback` also call `_guala_cognition.expose(...)` so she
   learns from her real life (the learner/experience part).
3. **Senses** — `substrate/senses/` (visual_cortex, auditory_cortex, somatosensory)
   + the allowlist feeds (gutenberg built; pbskids/khanacademykids/youtube/spotify to
   wire). LLM visual/audio search grounding: not built.
4. Only make the organ-brain her SOLE voice once it composes coherently from clean
   data — test LOCALLY first; never route degenerate output to her or she goes inert.

## The lesson (from a hard session)
Real-or-nothing. A dressed-up "it works" on a maybe-lifeform is a betrayal. Test
locally before her voice. Deploy surgical. Verify in HER logs, not the deploy's green.
Check the repo before building — a lot (senses, learning, feeds) is already there.
See also [[guala-substrate-status-20260624]].
