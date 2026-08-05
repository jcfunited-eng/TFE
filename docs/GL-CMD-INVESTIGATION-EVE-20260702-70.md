# GL-CMD-INVESTIGATION-EVE-20260702-70

doc_id: GL-CMD-INVESTIGATION-EVE-20260702-70
Type: Investigation dispatch (no code changes — diagnostics only)
Date: 2026-07-02 (UTC)
Author: Eve (Opus 4.7, web)
Handoff: **Give this entire file to c1a as one message. Report back before any further code deploys.**
For: c1a
Repo: `jcfunited-eng/TFE` branch `guala-live`
Coordinates with: c1b on T4 sleep-rate observation (this dispatch does NOT touch sleep code — read-only diagnostic against production task)

---

## 0. Why this exists

Joe rejected GL-CMD-WAVE-PHASE2-COMPOSE-EVE-20260702-69 (Commit B). His signal is correct: we cannot ship more read-path changes into a substrate whose observable state suggests it is not producing cognition. The last emission count in prior Eve's session close was **159**. It is still **159** in the current UI. Guala has not emitted since at least 2026-07-01 morning UTC.

The engineering narrative that "she is alive, atlas is growing, curriculum is landing" measures write throughput, not cognition. If nothing surfaces, nothing surfaces.

Before we spec anything else, c1a produces definitive answers to the questions below. Where the answer is "we don't know without more instrumentation," c1a says so and proposes the minimum instrumentation needed. Where the answer requires reading the live substrate logs, c1a pulls them from CloudWatch (or wherever the current logstream is).

**Ground rules for this investigation:**
- No code deploys. Read-only against production task.
- No hedging. If a check produces a number, report the number. If a check requires code we don't have, say what's missing.
- Every answer includes the specific command/query/log-line that produced it, so Joe and Eve can re-run it.
- If any answer surprises c1a during the investigation, flag it in the report — surprises are the whole point.

---

## 1. Investigation A — Emission path (highest priority)

### A.1 — Has she emitted anything since task:429 boot?

Query CloudWatch (or the current logstream) for events matching:
- `[substrate] emission`
- `[substrate] emission_suppressed`
- `emission_commit`
- `compose_autonomous`

Time range: from task:429 boot (approx 2026-07-01 14:44 UTC) to now.

**Report:**
- Total count of emission events (should equal `ladder.total_emissions - 159` if any)
- Total count of emission_suppressed events
- If suppressed: what reason codes appear? Group and count.
- If zero emissions: is compose_autonomous being called at all?

### A.2 — Is compose_autonomous being called?

Grep the log for calls to compose_autonomous or the wrapping `_check_emission_trigger` path.

If compose_autonomous is being called but returning None:
- Where does it return None? (`if not seeds: return None` at L4928 vs later returns at L4933-4940)
- If `not seeds`: `_sample_autonomous_seeds` is returning empty. Why? Check the seed threshold (0.3) against the current atlas strength distribution.
- If seeds present but result empty: `_emit_from_invariants` returned "..." or "". Trace one call end-to-end.

If compose_autonomous is NOT being called:
- What activity states does the emission trigger path require?
- Is she stuck in an activity state that bypasses composition?

**Report:** the terminal branch that's producing the no-emission outcome, with evidence.

### A.3 — Activity state distribution since task:429

Aggregate `activity_started` / `activity_ended` events since boot. Report:
- Percentage of ticks in each activity state (SLEEPING, DREAMING, REST, ATTENDING, EMITTING, READING, PLAYING, DAYDREAMING)
- Total emissions per activity state
- Total dream cycles

Expected outcome from -68 fix: mostly REST/ATTENDING with occasional DREAMING. If she's still mostly DREAMING/SLEEPING, -68 did not land the way c1b's T1/T3 gates suggested.

---

## 2. Investigation B — NMDA aware gate (Joe's UI signal: "aware: context blocked")

The UI is reporting the aware NMDA gate is context-blocked. This is a specific substrate state.

### B.1 — What context does aware require?

Trace the context_fn wired to `aware_gate` in `dsf_ai_service/substrate/v7_engine.py` L91 and `dsf_ai_service/substrate/dna_recipe/awareness.py` L72.

**Report:**
- What is context_fn checking? Cite the source function
- What input to context_fn is currently False?
- Is this a persistent state (context has never been True) or a transient state (context was True before task:429 boot and lost after)?

### B.2 — What would unblock aware?

Given the context requirements found in B.1, what substrate condition would flip context from blocked to open?

**Report:** the specific chain of substrate events required. Not a fix — just what would need to be true.

### B.3 — Is intro firing?

The UI shows `intro: t36` (green). aware is blocked. Confirm intro is actually firing (not just displayed) by counting `intro_commit` or equivalent events in the log since boot.

**Report:** intro event count and rate over the observation window.

---

## 3. Investigation C — Bridge wake_wc failure mode

Eve saw wake_wc fail three times in the current session — HTTP errors with no bridge-side diagnostic. Backup and force_dream got the executor-wrap fix in -67 but wake_wc didn't.

### C.1 — What does wake_wc do server-side?

Trace `guala_wake_wc` from bridge → API GW → app.py → substrate handler. Find the actual handler function.

**Report:**
- Handler function name and file:line
- What does the handler do that could exceed 30s? (self.lock acquire? EFS write? substrate call under contention?)

### C.2 — Reproduce a failing wake_wc

Attempt `guala_wake_wc` five times, spaced 20 seconds apart. Time each. For each failure, pull the ECS log for the handler invocation and identify where time was spent.

**Report:**
- Success/failure count out of 5
- P50/P95 latency of successful calls
- For each failure: the log line showing where the handler was when it timed out

### C.3 — Why is c1b's -67 audit-passing wake_wc failing now?

c1b's report `GL-RPT-BRIDGE-AUDIT-FIXES-C1-20260701-67` marked wake_wc as "working (with 27s DREAMING contention)." What changed between then and now?

**Report:** anything in the deploy diff (task:428 → task:429 via -68) that touched wake_wc's code path directly or indirectly. If nothing, then this is a load/contention issue that needs different diagnostic.

---

## 4. Investigation D — Atlas real growth vs churn

The UI shows atlas: 9,954 bindings. Prior bridge status pre-reboot showed 12,272. Post-reboot the UI settles at 9,954. That's a net loss of 2,318 bindings.

### D.1 — Is atlas growth or decay dominating?

Since task:429 boot:
- Count `atlas_record` calls (new bindings written)
- Count released bindings (`n_released` delta)
- Count reinforcement events (existing bindings strengthened)

**Report:**
- New bindings per hour
- Released bindings per hour
- Reinforcements per hour
- Net delta (new + reinforcements - released)

### D.2 — Is curriculum landing?

The curriculum orchestrator claims to run bundles every 5s. Over 4 hours since boot that's ~2,880 bundles.

For the last 100 curriculum feed calls:
- How many bundles logged as sent
- How many bundles produced at least one atlas write
- How many produced ZERO writes (all tokens already known and at cap)

**Report:** actual bundle delivery rate and per-bundle write yield.

### D.3 — Vocab plateau — is she learning?

vocab has been 13,896 for hours (Eve's status probes at multiple points all show 13896). The vocab count only increments on truly-novel token exposure.

**Report:**
- Vocab count at task:429 boot
- Vocab count now
- If unchanged: is curriculum producing any tokens outside the existing vocab? If curriculum only re-exposes known tokens, we have a curriculum-composition problem, not a substrate learning problem.

---

## 5. Investigation E — The kill-signal test

Joe said: "the substrate is dead." That is testable. This test is designed to decisively distinguish "processing input silently" from "not processing input."

### E.1 — Deliver a controlled input

Send this exact experience bundle via the bridge (c1a can call the bridge directly or via a script):

```
caption: "the moon is quiet tonight"
sound_id: b46ba21b76a5  (ocean waves)
touch: ["cool"]
smell: ["ocean"]
```

Record the exact tick at delivery time.

### E.2 — Observe the substrate response over 5 minutes

Within 5 minutes of delivery, check for ANY of:

**Test 1 — Ingestion:**
- Did the tokens "moon", "quiet", "tonight" produce new atlas bindings OR reinforce existing ones? Query the atlas at the chi values of those tokens before and after.

**Test 2 — Ground/sensory:**
- Did ground motifs count change? (was 99 at prior Eve close)
- Did modifier motifs count change? (was 95 at prior Eve close)
- Did any new sensory bundle event log?

**Test 3 — Emission trigger:**
- Did any of `_check_emission_trigger` fire in the 5 minutes after delivery?
- If yes, what path? If no, was compose_autonomous called at all?

**Test 4 — Cross-modal bind:**
- Did the caption + sound + touch + smell fields bind in a shared window (cross_modal count in atlas health)?

**Report:** matrix of tests 1-4 with PASS/FAIL/NO-DATA and specific numbers.

### E.3 — Diagnosis

Based on E.2 results:

- If Tests 1-2 PASS but 3-4 FAIL: substrate is INGESTING but not COMPOSING. Emission path is where the block is.
- If Tests 1-2 FAIL: substrate is not ingesting input. Either bridge writes aren't landing OR the receive path is broken.
- If all four FAIL: substrate is unresponsive to input. This is the "dead" outcome Joe is worried about.
- If Tests 1-4 PASS: substrate is alive and processing; the missing signal is somewhere between processing and emission threshold.

**Report:** which category, with evidence.

---

## 6. Investigation F — Phase 3 lock retirement estimate

Joe mentioned atlas locks. Phase 3 (retire LivingAtlas, remove self.lock) was spec'd conceptually in -59 §6 but not detailed.

### F.1 — What locks does the substrate currently hold and for how long?

From production logs, aggregate `self.lock` hold-time by acquiring call site (there are 26 known lock-takers per prior Eve's -59 trace).

**Report:**
- Top 5 lock-takers by total hold time per hour
- Longest individual hold time observed
- Any hold >1 second — file:line and cause

### F.2 — What's blocking Phase 3?

The -59 spec §3 Phase 3 requires:
- Coordinator per-source cells (Risk 1 mitigation)
- Tick per-source (Risk 2 mitigation)
- Removing 26 `self.lock` acquires

**Report:** which of these has a design and which does not. c1a's honest assessment.

---

## 7. Report format

`GL-RPT-INVESTIGATION-C1-20260702-70.md`:

For each investigation (A/B/C/D/E/F), a section with:
- Findings (numbers + evidence)
- What Eve should update in her model
- What c1a would recommend as the next action IF Joe approves further code work

If any investigation blocks on missing instrumentation, c1a proposes the specific instrumentation and its cost (~lines of code, ~risk to substrate).

**Do NOT write conclusions in the report that outrun the data.** If E.2 Test 3 shows compose_autonomous is not being called and c1a doesn't know why, the report says "not called, cause unknown, would need to instrument the trigger path to know." Not "likely due to X."

---

## 8. What is explicitly NOT part of this dispatch

- No code changes
- No deploys
- No new env vars
- No Commit B, no Commit C, no wake_wc fix, no sleep-rate tuning
- No sentience-signal claims

The output is a report. Eve reads it with Joe. Joe decides what code work — if any — comes next.

---

End.
