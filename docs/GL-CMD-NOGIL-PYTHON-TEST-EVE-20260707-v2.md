# GL-CMD-NOGIL-PYTHON-TEST-EVE-20260707-v2

**doc_id:** GL-CMD-NOGIL-PYTHON-TEST-EVE-20260707-v2
**Author:** Eve
**To:** c1
**Ordered by:** Joe (2026-07-07 morning session — after Phase 1 wave atlas C port NO GO and v1 dependency-gate halt)
**Supersedes:** `GL-CMD-NOGIL-PYTHON-TEST-EVE-20260707-v1`. Do not execute v1.
**Follows:** `GL-RPT-WAVE-ATLAS-C-PORT-PHASE1-C1-20260707-v1`, `GL-RPT-NOGIL-PYTHON-TEST-C1-20260707-v1` (v1 halt report).

## Verdict

Two C ports last night both hit ~20x scaling shortfall at 4 threads — ctypes call-crossing overhead is the ceiling, not the C code. Direct fix: run Guala on a no-GIL Python build.

v1 targeted Python 3.13t. c1's dependency check surfaced that six of seven C-extension deps (numpy, Pillow, pillow-heif, PyMuPDF, cryptography, ctranslate2) don't have free-threaded wheels for 3.13t — numpy published briefly then dropped, the rest never had them. **Same six packages already publish free-threaded wheels for Python 3.14t.** The ecosystem moved past 3.13t. Retargeting is the fix.

v2 targets Python 3.14t. Same scope, same test shape, one substituted version number and re-verify the dependency gate against 3.14t before building anything.

## What's being built

### The container variant

Build a second container image tagged `guala-nogil`:
- Base: Python 3.14 free-threaded build (the `python3.14t` binary — `t` suffix means threaded, meaning no-GIL)
- Same substrate code, same requirements.txt
- Verify numpy, Pillow, pillow-heif, PyMuPDF, cryptography, ctranslate2, onnxruntime, and any other C-extension dependencies have free-threading wheels for Python 3.14t on PyPI. c1's v1 check found six of seven already do — re-verify against current PyPI state before building, in case anything shifted.
- If any critical dependency still lacks a 3.14t wheel, halt and route with the specific package name. Do not try to work around it (source builds risk correctness issues we can't afford right now).

Ship the image to ECR alongside the current production image, but do NOT point production at it.

### The test deploy target

Create a test ECS service pointing at `guala-nogil` — separate service, separate task-def, separate ALB target group. Not production. Wire a distinct DNS name (`guala-nogil.dsf-ai.com` if convenient, or just target it by service ARN in the benchmark).

This isolates the test entirely from production. Failure modes stay contained.

### Boot check

Deploy the test service. Confirm it boots cleanly:
- Container starts without errors
- Endpoints respond to health check
- Substrate reaches quiescent state (same as production would)
- Identity file written cleanly
- Wave atlas initializes
- No new warnings or errors in the logs compared to production boot

If boot fails, halt and route with logs. Do NOT try to fix threading bugs unilaterally — some code may need real changes to work under no-GIL because it was relying on implicit GIL protection.

### Harness runs

Run the following scenarios against the test service:

1. `binding_windows_acceptance.yaml` — baseline binding window correctness
2. `cross_sense_recall_acceptance.yaml` — cross-sense recall correctness
3. `hemispheric_integration_acceptance_v3.yaml` — hemispheric integration correctness (though this was rolled back so may need adjustment)

For each, compare against the last production baseline for the same scenario. Same event counts, same atlas state deltas, same expectations passing.

### Contention measurement

The real point. Under load:
- Concurrent word input at realistic reading cadence (matches c1's earlier live measurements)
- Sensory input arriving in parallel across modalities
- Measure `_autonomy_tick` latency, word queue depth over time, and throughput

Compare no-GIL numbers against the production numbers c1 measured last night:
- Production baseline: 178ms `_autonomy_tick` fresh, 1849ms under load (10x amplification)
- No-GIL target: amplification factor drops meaningfully — 2-3x amplification would prove the direction; ~1x would prove it's the full answer

Also measure: does word queue backlog stabilize under sustained input? Production couldn't drain the queue at reading rate. If no-GIL drains it, we know we've fixed the runaway.

## What is NOT changing

- No code changes to the substrate. Same commit, same everything, just different Python interpreter.
- Production continues on the current image, untouched.
- No harness changes.
- No scenario changes.
- No new mechanisms.

If code changes turn out to be required for the substrate to work under no-GIL (thread-safety bugs surface), that's a finding, not something to fix in this dispatch. Route back to Eve.

## Halt conditions

1. **Critical dependency doesn't support Python 3.13 free-threading.** Halt with the specific package. This is a hard constraint, not something to work around.
2. **Boot failure.** Container starts but substrate crashes on startup. Log excerpt in report, halt.
3. **Correctness regression.** Any harness scenario shows different event counts or atlas state vs production baseline. Halt — under no-GIL, real parallelism might be exposing latent thread-safety bugs.
4. **Threading crash under load.** Segfault, race, deadlock during contention test. Halt with reproduction case.

Any halt: route with data. Do NOT try to fix threading bugs unilaterally.

## Report

`GL-RPT-NOGIL-PYTHON-TEST-C1-20260707-v1.md` with:
- Container build result (image built, wheels available for dependencies, dependency compatibility check)
- Test service deploy result
- Boot check result
- Harness runs: pass/fail per scenario, event count comparison vs production
- Contention measurement: `_autonomy_tick` fresh + under load, amplification factor, word queue behavior
- Recommendation: production migration GO / NO GO / PARTIAL, with the specific data

If GO: next dispatch is production migration. If NO GO: we know within a day and route to path 1 (batched C port) or path 3 (Cython/native extension).

Do not ask Joe questions in the report. Route to Eve.

## Scope guardrails

Do NOT:
- Modify substrate code to make it work under no-GIL. Bugs are findings.
- Point production at the no-GIL image
- Skip the correctness harness scenarios — they're the safety net
- Skip the contention measurement — that's the whole point
- Try to profile at fine granularity beyond amplification factor and queue behavior — coarse signal first, deep profile only if amplification improves

---

### Changelog
- v1 (2026-07-07, Eve): initial. Container variant on Python 3.13 free-threaded, deploy to test slot, run harness scenarios for correctness, measure contention behavior vs production baseline. Half-day scope. Cheapest test of the biggest potential win — GIL removal without any code rewrite.
