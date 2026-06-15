# GL-BRIEF-PILEON-MODEL-WC-20260614-03

Supersedes -02. Real streaming model: 5 minutes sustained, 2 Hz picture upload with ~5KB JPEG, 0.67 Hz sound upload with ~64KB WAV, full polling pile-on at real page rates, /ready probed every 2s. /sight_frame and /sound_frame from parent brief Parts C/D do not exist yet — upload endpoints exercise the same kernel decode + krimelack + atlas path with strictly heavier load (extra storage write).

## Acceptance

- Zero /ready probes with time_total > 5s
- /ready p95 < 1.0s across all probes
- All /v7/state probes 200, p95 < 5s
- ECS one PRIMARY for full 5 min, no new task launches mid-run
- No Target.Timeout, no unhealthy

Anything less = Phase 2 did not fix what we thought.

## No code. No deploy. 5 minutes. Report summary + failures + infra snapshots. Stop.
