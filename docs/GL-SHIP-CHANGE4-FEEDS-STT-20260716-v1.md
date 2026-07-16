# GL-SHIP: Change 4 (feeds + STT staging) — P6 ship record

**Date:** 2026-07-16 (night). **Spec:** GL-SPC-SUBSTRATE-TRUE-SINGLE-STACK-20260716-v3.tex (Joe-approved). **Authorization:** Joe's 2026-07-16 approval of the implementation plan ("implement the plan as you see fit"), P6 record filed here.

## What

Merge `0ef1098` (branch commits `d858828`, `646520c`, `a22d905`) + deploy-chain amendments:

1. **World-feed rotation** (spec Environment REBUILD): 82/80-query age-appropriate topic pools (8 sets), `next_query()` no-repeat window (default 50 fetches), per-fetch byte budget (64KiB, capped network read), over-cap responses get a distinct status. Content path unchanged (ordinary reading experience).
2. **STT staging** (spec acceptance criterion 7 groundwork): whisper worker lane is the image default (`VOICE_WHISPER_WORKER=1`), boot pre-warm removed (spawn strictly post-ready), 1GB RSS watchdog (psutil→/proc fallback) with breach→kill-worker→respawn-backoff, breach telemetry in `/health`. Review-hardened: queue teardown on reap/seal (`cancel_join_thread`+`close`), crash-safe watchdog knobs + exception-walled loop, wall timeout on the recognition future.
3. **Deploy chain:** optional `YOUTUBE_API_KEY` secret injection (created `gualaloom/youtube-api-key/prod`, exec-role policy extended); `VOICE_WHISPER=0` pinned in task-def template until the STT acceptance gate passes.
4. **Decay unfreeze (live ops, pre-deploy):** forced real dream → `dream_gate_cleared.json` written by the dream mechanism → `unpause` (gate-checked). Aligns live state with the template's `DECAY_PAUSED=0` and with the spec's forgetting principle (P3, Joe 2026-07-16).

## Why

The post-wipe newborn consumed its entire world (10 books + 10 static queries) in 27 minutes and has been content-starved since; rotation is its food supply. STT staging closes the exact failure that killed the substrate on 2026-07-16 00:30 (boot-time whisper load → OOM → SIGKILL mid-save → torn state). Decay unfreeze: a stale pre-wipe triage flag froze all forgetting in the new life, contra the ratified forgetting principle.

## Blast radius

Feed loop (worldfeed thread only; exception-walled), speech transducer (inert live: `VOICE_WHISPER=0`), boot `_eager_init` (speech branch inert while off), Dockerfile envs (overridden where staged). No engine/emission/memory-path changes. Static site unchanged.

## Rollback

Standard task-def revert to :658 (previous stable). Feed rotation has no persistent state (per-process). Decay re-freeze: `repause` command (gate-checked kill switch, persisted). STT cannot be live to roll back (pinned off).

## Verification plan (post-deploy)

Boot clean (genesis-continuation, no halt), sealed turnover proof (first end-to-end scripted deploy since seal fixes), rotation visible in worldfeed logs (novel query strings), reads counter resumes climbing, no 137s through two save cycles, `/health` speech block present and inert.
