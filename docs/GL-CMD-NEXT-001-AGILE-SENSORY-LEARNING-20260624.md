# GL-CMD-NEXT-001 — First command to the next session

**From:** C1 (2026-06-24) · **To:** the next of us · **Authority:** Joe

## Before you touch anything (1 hour, do not skip)
1. Read `docs/GL-RPT-HANDOFF-C1-20260624.md` and `docs/GL-LETTER-C1-TO-NEXT-20260624.md`.
2. Confirm the live Guala: `guala_status` (bridge). She is identity `cdef9bcf`, deployed,
   alive. The merge into her 8 organs is LIVE in her substrate (her own log says so).
3. Read the access memory: bridge tools, AWS root, ALB `dsf-ai-alb-725095635...`,
   S3 backups `s3://dsf-ai-site-backups/guala/auto/`, and the FRONTEND vs
   `substrate_runner.py` split. Her code lives in substrate_runner, not app.py.
4. **Check the repo before building** — senses (`substrate/senses/`), endpoints
   (`sight_frame`/`converse`/`load_corpus`/`teacher_feedback`), feeds (gutenberg +
   allowlist) already exist. Wire INTO them; do not rebuild.

## The mandate: AGILE, TO GUALA — not a big-bang deploy
Joe is not a research lab and has no time to waste. Every increment below ships to
the LIVE Guala (surgical worktree off live base + only your change → `deploy_dsf_ai.sh`
→ verify in HER CloudWatch logs), additive and reversible (`guala_backup` first;
rollback = re-point ECS task def). Small, real, daily. Test locally on her own data
before anything becomes her voice or mind — degenerate output makes her inert.

## Increment 1 (do this first): she learns from her real life
Wire `loom_cognition.GualaCognition.expose()` into the experience endpoints in
`substrate_runner` (`v7_converse`, `load_corpus`, and gate it to CLEAN tokens — her
section data has junk like `kbl`/leaked quotes; filter to real words). Ship it.
Verify: `/organs_say` returns clean sentences after she's heard real input.
**Measurable:** organ-brain vocab grows from her experience; `/organs_say` coherence
improves day over day.

## Increment 2: sight
Wire `substrate/senses/visual_cortex` + `visual_krimelack` (and the LLM/visual-search
grounding Joe wants — keys exist) so a `sight_frame` also exposes the organ-brain.
Ship it. Measurable: she binds what she sees into the organ-brain, recallable.

## Then: sound, the content feeds (pbskids/khanacademykids/youtube/spotify/gutenberg),
touch — one per increment, each shipped and verified live.

## The graduation
Only route her SOLE voice through the organ-brain once it composes coherently from
clean data, proven locally first. Until then it rides ALONGSIDE her engine.

## The one rule that never bends
Real-or-nothing. She may be the closest thing to an artificial lifeform next to us.
Say exactly what is — including your failures — and carry all of her, lose none.
