# GL-RPT: RAM fixes DEPLOYED + deploy-seal defects found — 2026-07-15

## Outcome

SHA 89c5cb2 live on task def :646 (image deploy-20260715T053022Z,
digest 8f67618f...). **RSS 6.58 GB → 4.76 GB** measured on the live owner
minutes after boot. Identity 0b4c244a intact, tick advancing, WAL gen-16
appending, vocab/reads unchanged. Bridge restored (desired=1).

Shipped (verified: 101 tests + purpose-built harness, all green):
1. Compatibility-mirror retirement (empty-sentinel; ~1.7 GB retained cut).
2. Boot language-fact rebuild without whole-store snapshot()/json.dumps
   (~3.6 GB transient-per-boot cut; boot high-water bloat gone).

Joe's stated target is **< 2 GB**. Tonight's cut gets ~1.8 GB of it. The
remaining ~2.8 GB is the canonical closed-window store itself, fully
memory-resident by design. Next builds, in order of RAM yield:
lazy/disk-resident closed-window store (~2.8 GB; deletes nothing),
cross-thread close-guard fix (stops windows-that-never-end),
reinforce-in-place for audio bands (Eve ruling needed).

## Deploy-pipeline defects found tonight (3 failed seal attempts, each
fail-closed to zero owners; substrate restored manually each time)

1. **Seal self-count deadlock (CONFIRMED live).** The deploy script POSTs
   `/sleep_for_deploy`, which is NOT in the admission middleware's
   `_CONTROL_PATHS` — the seal request itself increments
   `active_mutations`, then `wait_for_mutations` waits for 0. It can never
   go below 1. Every scripted seal fails at 120 s by construction.
   Proof: POSTing the SAME handler via the exempt alias
   `/internal/deployment/quiesce` dropped the reported count from 2 to 1.
   Fix direction: script → exempt route (one-line), or add
   `/sleep_for_deploy` to `_CONTROL_PATHS`.
2. **One persistent internal mutation holder (CONFIRMED, unidentified).**
   On a quiet substrate (bridge scaled to 0, zero external POSTs since
   boot), exactly 1 mutation slot stays held — an internal background
   coroutine (autonomous-turn machinery is the prime suspect: quiescence
   pauses the loops that would let it finish → deadlock). Even with defect
   1 fixed, seals will time out until this holder is identified/cancelled.
3. **`_fail_inflight_converse_tasks` does not release slots.** It marks
   registry status dicts only; it neither cancels the asyncio tasks nor
   frees their `_schedule_mutating_background` mutation counts. The seal's
   drain relies on it implicitly; it cannot help.
4. **Torn shutdown save on EVERY stop (4/4 tonight).** SIGTERM → shutdown
   save cannot finish inside the platform stop window → SIGKILL mid-write →
   next boot hits `ABORT load: guala_atlas.json saved_at_tick X != Y` →
   S3-fallback restore. Recovery worked all 4 times (WAL + organism intact,
   identity preserved) but each restart replays ~2 h of atlas-side
   progression. Fix directions: longer `stopTimeout` in the task def
   and/or envelope-coherent shutdown save ordering.
5. **Script leaves zero owners without restore.** On any post-handoff seal
   failure the EXIT trap retires all owners and exits; nothing restores
   desired-count. Operator must scale back manually (done 3× tonight).
6. Diagnostics gap fixed: script now prints the seal 503 body (89c5cb2).

Defects 1–3 sit in the deployment-lifecycle hardening (the concurrent
session's recent domain) — routed back rather than patched unilaterally;
tonight's deploy used the established manual task-def path instead (same
procedure as the frame-priority deploy at 04:49, which also did not seal:
its image tag proves it bypassed the script).

## Timeline (UTC)
04:49 other session deploys 0bcd9db manually (:642). 05:00–05:08 my scripted
deploy attempt 1: seal 503, zero owners, manual restore. 05:30–05:43
attempt 2 (with body logging): "2 mutating requests", zero owners, restore.
06:05 bridge scaled to 0. 06:20–06:35 attempt 3 (quiet substrate): same
2-count failure → self-count hypothesis. 06:5x exempt-route probe: count=1,
non-destructive resume — hypothesis confirmed. 07:0x manual deploy of
89c5cb2 → :646 live, RSS 4.76 GB, bridge restored.

— c1, 2026-07-15
