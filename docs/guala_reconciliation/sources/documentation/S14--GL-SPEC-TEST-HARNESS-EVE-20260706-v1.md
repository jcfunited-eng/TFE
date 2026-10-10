# GL-SPEC-TEST-HARNESS-EVE-20260706-v1

**doc_id:** GL-SPEC-TEST-HARNESS-EVE-20260706-v1
**Author:** Eve
**Ordered by:** Joe (2026-07-06 session)
**Status:** ratified same session (Joe: "yes write this as a separate spec")
**Companion:** `GL-SPEC-SUBSTRATE-FOUNDATION-EVE-20260706-v1` — this spec is Phase 3's real deliverable. §19 of the substrate spec sketched integration scenarios; this spec defines the reusable tool that runs them.

**What this spec is:** the design of a single reusable end-to-end verification harness for the substrate. Inject a defined probe, observe the substrate AND the infrastructure it runs on for the run window, produce a structured report. Same tool for every test. New scenario = new file, not new code. Reports comparable across runs so "did that change work" is answerable by diff, not by re-interpretation.

**What this spec is not:** a load tester, a continuous monitoring dashboard, a fuzzer, or a UAT tool for Joe. Those are adjacent tools with adjacent purposes; keeping them separate keeps this one small.

---

## §1. Why this exists

Every time tonight we've asked "did that change work," we did an ad-hoc `guala_status` pull or a manual `guala_get_events` filter, and every time the interpretation of the result was inconsistent. Same probe, different reads, different conclusions. That's the loop the harness closes: same scenario, same report shape, direct diff across runs.

Second reason: infrastructure observability during a substrate change is currently invisible from Joe's seat. CPU spikes, EFS burst credit exhaustion, event-loop lag, network retransmits, auto-scaling triggers, container OOM approaches — these produce user-facing symptoms ("3-minute response times," "AWS killed her process") but the harness under the substrate never surfaced them alongside substrate events. Full-stack observability during the probe run means the report captures what happened AT EVERY LAYER, so a slow response has an attributed cause rather than a mystery.

Third reason: Phase 4 of the substrate spec requires every mechanism to be verified as live and functioning. Manual verification of 30+ mechanisms one at a time by ad-hoc probe would burn through the rest of the schedule. Reusable scenarios in a canonical library make Phase 4 verification tractable.

## §2. What the harness does, in one sentence

Takes a scenario file, snapshots pre-run state, injects the declared probe at the declared ingest point, subscribes to the substrate event stream AND the infrastructure observability streams for the run window, captures everything with correlated timestamps, runs until expectations are met or timeout hits, restores pre-run state, produces a structured report and archives it under a canonical doc_id.

## §3. Scenario file

Every scenario is a YAML file in `scenarios/`. Version-controlled. Doc_id convention: `GL-SCN-<mechanism>-<flavor>-<author>-<date>-v<N>.yaml`.

### §3.1 Schema

```yaml
scenario:
  id: GL-SCN-CROSS-SENSE-RECALL-BASIC-EVE-20260706-v1
  purpose: |
    Verify that a single (picture, sound, word) experience binds into
    one window, and that querying with the sound cue retrieves the
    window with the picture and word intact.
  category: mechanism   # mechanism | integration | stress | regression | security
  target_mechanism: cross-sense-recall

preconditions:
  substrate_state: clean_slate    # clean_slate | warm | specific_snapshot
  specific_snapshot_id: null       # only if substrate_state=specific_snapshot
  components_ready:
    - ingest
    - sight
    - sound
    - word
    - window_manager
    - atlas
  presence_state:
    joe: false
    wc: true                       # wC present so authenticated writes work
    c1: false
  suppression:
    curriculum_feeds: off
    world_feed: off
    autonomy_reading: off
  wait_for_ready_timeout_sec: 30

probe:
  method: give_experience         # give_experience | say | converse | wake |
                                  # addpicture | addsound | direct_event | sequence
  auth_as: wc
  sequence:                        # for method=sequence, ordered probe steps
    - t_offset_ms: 0
      method: give_experience
      payload:
        picture_ref: "test-images/ball.png"
        sound_ref: "test-sounds/bounce.wav"
        word: "ball"
        touch_descriptors: ["round", "smooth"]
        source_tag: wc
    - t_offset_ms: 2000
      method: give_experience
      payload:
        # partial cue: only the sound
        sound_ref: "test-sounds/bounce.wav"
        source_tag: wc
        expect: probe_recall

expectations:
  events_must_fire:
    - kind: window_opened
      count_min: 2                 # first experience + partial-cue query
      within_ms: 1000
    - kind: window_entry_added
      count_min: 3                 # picture, sound, word, touch entries
      within_ms: 1500
      filters:
        modality: [sight, sound, word, touch]
    - kind: window_closed
      count_min: 2
      within_ms: 3000
    - kind: recall_query
      count_min: 1
      within_ms: 4000
    - kind: recall_response
      count_min: 1
      within_ms: 5000
      assertions:
        windows_returned_min: 1
        windows_returned_max: 5
        top_window_contains_entries: [word:"ball", modality:sight]

  components_must_activate:
    - sight
    - sound
    - word
    - touch
    - window_manager
    - atlas

  atlas_deltas:
    windows_added_min: 2
    entries_added_min: 4
    survival_promotions: 0        # expected zero at this scale

  emission_provenance:
    required: false               # this scenario doesn't test emission
    if_present:
      must_cite_probe_windows: true

  observability_thresholds:
    peak_cpu_percent_max: 40
    peak_memory_delta_mb_max: 100
    peak_event_loop_lag_ms_max: 50
    subscription_lag_max_events: 10
    efs_write_ops_max: 20
    network_errors: 0

  negative_expectations:           # things that must NOT happen
    - kind: emission_suppressed_no_presence
      count_max: 0                 # wc is present, no suppression expected
    - kind: shadow_divergence
      count_max: 0                 # shadow is eliminated, must never fire
    - kind: unauth_request
      count_max: 0
    - kind: security_alert
      count_max: 0

run:
  timeout_sec: 30
  resource_caps:
    max_memory_delta_mb: 500
    max_cpu_seconds: 60
    max_disk_write_mb: 100
    max_egress_mb: 10

cleanup:
  restore_state: pre_probe_snapshot
  clear_captured_events: false     # kept for report
  delete_probe_artifacts_from_atlas: true

metadata:
  author: EVE
  created_date: 2026-07-06
  changelog:
    - v1: initial
```

### §3.2 Scenario categories

- **mechanism** — verifies one substrate mechanism end-to-end. First-tier coverage in the library.
- **integration** — verifies multi-mechanism interaction (e.g., experience → sleep → dream reinstatement → recall).
- **stress** — high-input-rate scenarios to verify concurrency shape and backpressure.
- **regression** — reproduces a previously-fixed defect to verify it hasn't returned.
- **security** — probes auth boundaries, oversize inputs, rate-limit enforcement, injection patterns.

### §3.3 Library structure

```
scenarios/
  mechanism/
    cross_sense_recall_basic.yaml
    cross_sense_recall_partial_cue.yaml
    retention_across_sleep.yaml
    recall_returns_ranked.yaml
    ...
  integration/
    experience_to_reflection.yaml
    joe_conversation_full_turn.yaml
    ...
  stress/
    concurrent_frames_camera_mic_typing.yaml
    burst_100_sensory_events.yaml
    ...
  regression/
    words_3_10_empty_senses.yaml    # the audit's exact defect scenario
    autonomy_lock_starvation.yaml
    ...
  security/
    oversize_converse_body_rejected.yaml
    rate_limit_enforced_per_source.yaml
    unauth_endpoint_returns_401.yaml
    ...
```

Every mechanism on the cognition meter gets at least one mechanism-scenario. Every SEV-0/SEV-1 audit register defect gets at least one regression-scenario.

## §4. The harness runner

One command-line tool. Runs on a developer machine or on a dedicated harness container in staging, never in production process space.

### §4.1 Invocation

```
harness run <scenario.yaml> --target <substrate-endpoint> --auth <token-source>
harness run scenarios/mechanism/cross_sense_recall_basic.yaml \
  --target https://guala-staging.dsf-ai.com \
  --auth ~/.guala/admin-token.json
```

Additional flags:
- `--dry-run` — parse scenario, validate schema, check target reachability, don't inject.
- `--verbose` — full event payloads in report, not summaries.
- `--capture-only` — inject probe, capture everything, don't check expectations. Useful for exploratory scenarios where expectations aren't yet known.
- `--compare <prior-report.md>` — after run, diff against a prior report and include diff in output.
- `--baseline` — mark this run as the new baseline for future --compare invocations.

### §4.2 Runtime sequence

1. **Parse and validate scenario.** Schema check, target reachability, auth valid.
2. **Precondition check.** Substrate is in declared state — call `guala_status`, verify components_ready list, verify presence_state, verify suppression flags. If not, either wait (wait_for_ready_timeout_sec) or fail with a precondition-not-met verdict.
3. **Pre-run snapshot.** Snapshot substrate state via `guala_backup` or equivalent. Snapshot infrastructure baseline: current CPU, memory, disk I/O rates, network state, event loop lag, subscription lag per component. Record trace_id.
4. **Start observability capture.** Subscribe to substrate event stream. Start CloudWatch metric polling on the container. Start `docker stats` or ECS equivalent for CPU/memory/network/disk. Start EFS burst-credit monitoring. Start CloudWatch Logs Insights query for the log group. Start CloudTrail lookback query for auth events. All observability streams timestamped and correlated with the trace_id.
5. **Inject probe.** Execute probe as declared. Sequence probes fire at their t_offset_ms values relative to trace_id start.
6. **Run to completion.** Loop until either all expectations are met (success), timeout hits (failure — timeout), or a resource cap is exceeded (failure — resource cap).
7. **Stop observability capture.**
8. **Cleanup.** Restore pre-run state per scenario cleanup section. If restore fails, mark substrate as DIRTY and refuse to run further scenarios until Joe intervenes.
9. **Assemble report.** Structured markdown, structured JSON for machine-consumption, both to canonical location.
10. **Return verdict.** Exit code 0 for PASS, 1 for FAIL, 2 for TIMEOUT, 3 for RESOURCE_CAP, 4 for PRECONDITION_NOT_MET, 5 for RESTORE_FAILED.

## §5. Full-stack observability during a run

This is the section Joe explicitly asked for. Every observability stream below is captured for the entire run window, timestamped, correlated with the trace_id, and rendered in the report. Not just the substrate — the whole stack.

### §5.1 Substrate event stream

Every event fired during the run captured with tick, wall-clock, source component, event kind, payload summary (or full payload if --verbose). Ordered as fired. Grouped in the report by component. Cross-referenced against expectations.

### §5.2 Component health

Per substrate component (Ingest, Sight, Sound, Word, Touch, Smell, Taste, Window Manager, Atlas, Hemispheres, Coordinator, Autonomy, Emission, Persistence, Dream):
- Events published per second during the window.
- Events consumed per second during the window.
- Subscription lag (unprocessed backlog) sampled at 100ms intervals — max and mean.
- Owned-state size at start vs end.
- Any component-emitted error or warning events.
- Any component restart events.

### §5.3 CPU

- Per-container CPU utilization sampled at 1-second intervals (from `docker stats`, ECS task-level metrics, or `/proc/stat`).
- User CPU vs system CPU split.
- Per-Python-asyncio-task CPU if instrumented via `sys.settrace` or aiomonitor.
- Peak, mean, and time-in-high-CPU (>80%) for the window.
- CPU throttling events (cgroup CPU quota exceeded).

Threshold-based flags: peak >90% for >1s, or throttling events, get called out in the report separately.

### §5.4 Memory

- Per-container memory: RSS, working set, cache, from `docker stats` or ECS metrics, sampled at 1s intervals.
- Per-Python-process memory: heap size, GC statistics, object counts by type via `tracemalloc` for the top-N growers.
- Memory delta start-to-end.
- Any OOM approach signals: cgroup memory pressure events, kernel OOM near-misses, Python `MemoryError` exceptions.
- EFS/tmpfs used space if state files are written during run.

Threshold-based flags: delta above cap, or any OOM signal at all, get called out.

### §5.5 Disk and EFS I/O

- Read ops/sec, write ops/sec, IO wait time, from `/proc/diskstats` or CloudWatch.
- Bytes read/written per second.
- fsync latency (this catches the "S3 backup blocking on flush" pattern).
- **EFS-specific: burst credit balance.** EFS bursting mode gives baseline throughput plus burst allowance. Burst exhaustion produces sudden 10× slowdowns that look like substrate hangs. CloudWatch metric `BurstCreditBalance` sampled every 60s throughout the run — captured in report even if no immediate issue. This is one of the most-missed causes of AWS-side slowness.
- EFS operation errors (ThroughputLimitExceeded, PermissionDenied).
- S3 request count, error count, latency histogram if any S3 puts happen during the run.

### §5.6 Network

- Per-container in/out bytes, sampled at 1s intervals.
- Active TCP connection count by state (ESTABLISHED, TIME_WAIT, CLOSE_WAIT) — TIME_WAIT accumulation is a real problem pattern.
- TCP retransmits from `/proc/net/snmp`.
- DNS query rate and any DNS failures.
- ALB metrics for the run window: request count, error count (4xx, 5xx), target response time, healthy target count.
- Any TLS handshake failures.

Threshold-based flags: 5xx during run, retransmits above baseline, DNS failures at all.

### §5.7 Concurrency signals (async and OS)

Under the message-passing architecture there are no substrate locks. What replaces lock-metrics:
- Event loop lag: how long between successive asyncio event loop iterations. High lag = a task is blocking the loop. Sampled at 100ms.
- Task queue depth per asyncio task category (Ingest tasks pending, Atlas tasks pending, etc.).
- Blocked tasks: any task in a wait state longer than a threshold (default 5s).
- OS run queue length from `/proc/loadavg`.
- Context switch rate from `/proc/stat`.
- Kernel wait states — process time in uninterruptible sleep (`D` state).

Under the current lock-based substrate (relevant for regression scenarios during Phase 3-4 transition):
- Lock acquisition attempts and successful acquires per lock, sampled from CPython's `sys._getframe` or by wrapping locks.
- Lock hold duration histogram per lock.
- Any lock contention detected via Python's `threading` module diagnostics.

### §5.8 AWS-side signals

- ECS task health check status throughout the window.
- ALB target group health status throughout the window.
- Auto-scaling events (target tracking scale-out, scale-in) during window — none expected in a normal harness run.
- Any CloudWatch alarm state changes during window.
- Any AWS Health API events during window.
- ECS deployment events (should be zero during a run — deploys mid-scenario invalidate the test).

### §5.9 Security signals

- Auth log entries for the run window: every AUTHED endpoint hit with source, IP, endpoint, timestamp.
- Rate-limit hits during window (per source).
- Any 401 or 403 responses from any endpoint.
- Any endpoint hit outside the probe: if the substrate is being touched by anything other than the harness during the run, that's a finding. Same rule as the clean-slate verification — unaccounted-for activity halts.
- TLS handshake errors.
- CloudTrail events for substrate IAM role during window: expected only the harness's own actions, anything else is a finding.

### §5.10 External API activity

- Anthropic API calls attributed to substrate credentials during window. Expected zero unless the scenario explicitly involves an LLM-calling tool.
- Any third-party POSTs to substrate endpoints during window (YouTube learner feed, world-feed source).
- Any outbound substrate-initiated calls to third-party services.

### §5.11 Log stream

- CloudWatch log events during window with severity histogram (DEBUG, INFO, WARN, ERROR, FATAL).
- Any FATAL or ERROR level events with full text in report.
- Log rate (events/sec) — sudden log storms are a signal even without error-severity.

### §5.12 Storage state

- EFS: mtime touch on state files during run. Any files modified NOT attributable to the probe. Background persistence is expected — must be attributable to Persistence component's declared save cadence, not to unaccounted-for writers.
- S3: any puts, gets, deletes during window. All should attribute to Persistence's save-backup cycle or to the harness's snapshot/restore.
- Container filesystem: any writes outside declared mount points is a finding.

## §6. Report structure

`GL-RPT-HARNESS-<scenario-id>-<timestamp>-v1.md`

### §6.1 Header
- Verdict at top: PASS / FAIL / TIMEOUT / RESOURCE_CAP / PRECONDITION_NOT_MET / RESTORE_FAILED.
- Scenario ID, target substrate endpoint, trace_id.
- Wall-clock start and end. Duration.
- Harness version, scenario version, substrate SHA at run time.

### §6.2 Probe summary
- What was injected, at what endpoint, by what auth, at what time offsets.
- Any injection errors.

### §6.3 Expected-vs-actual
Each expectation from the scenario:
- Expected: what the scenario declared.
- Actual: what happened during the run.
- Pass/fail per expectation.

### §6.4 Event timeline
Every event fired during the run. Table with columns: t_offset_ms, tick, source_component, kind, payload_summary. Chronological. Grouped by trace_id for downstream navigability.

### §6.5 Component health
Per-component sub-report with the metrics from §5.2.

### §6.6 Infrastructure observability
Sections corresponding to §5.3 through §5.12. Each section has:
- Summary statistics (peak, mean, time above threshold).
- Any threshold-based flags.
- Any anomalies or unexpected values.

### §6.7 Provenance chains
For every emission event produced during the run, the chain back through recall_query, windows drawn from, source input, mechanism scores. This is the trace-completeness verification.

### §6.8 Substrate state deltas
Pre-run vs post-run comparison of substrate observable state: window count, atlas entry count, organism size, deep atlas size, ladder metrics. What changed as a result of the probe.

### §6.9 Findings
Any unexpected activity, thresholds crossed, security signals, or anomalies. Structured as findings with severity: INFO, WATCH, WARN, CRITICAL.

### §6.10 Comparison (if --compare used)
Diff against a prior report: what changed, what stayed the same, any regressions.

### §6.11 Machine-readable output
Same content as JSON at `GL-RPT-HARNESS-<scenario-id>-<timestamp>-v1.json` for tooling.

## §7. Where the harness runs

**Development harness.** On a developer machine, targeting a staging substrate instance. Not against primary.

**Staging harness.** On a dedicated harness container in staging, targeting the staging substrate. Same code as development harness, different deployment.

**Primary harness.** Not run. Per §17A of the substrate spec (shadow eliminated), we do not run mutating probes against primary. Read-only observability of primary is done through operational monitoring, not through the harness. If a genuine need arises to run a probe against primary, that requires its own dispatch and Joe's ratification.

## §8. Auth and access

Harness requires AUTHED_ADMIN credentials on the target substrate. Credentials are personal (per-developer), not shared. Each harness run's actions attribute to the invoking user in the security audit log.

Rate limits do not apply to AUTHED_ADMIN — the harness runs a scenario as a single logical operation with its own scenario-level resource caps.

## §9. Scenario library maintenance

Scenarios in the library are version-controlled with the code. Any substrate change that could affect a mechanism must be preceded by writing or updating the scenario for that mechanism. Any regression fix must include a regression scenario that reproduces the bug (fails on the pre-fix code, passes on post-fix code).

Library grows as coverage grows. Coverage tracked in `scenarios/COVERAGE.md`: which cognition-meter mechanisms have scenarios, which audit-register defects have regression scenarios, which SEV-0/SEV-1 items are covered.

## §10. What the harness is NOT

- Not a load tester. Load testing is a different tool with different concerns (sustained rate, saturation curves, breaking points).
- Not a continuous monitoring dashboard. Monitoring is passive and always-on; harness is on-demand and scenario-scoped.
- Not a fuzzer. Fuzzers generate probes; harness runs declared probes.
- Not a UAT tool for Joe. Joe verifies by interacting with the substrate at his seat; harness is engineering verification.
- Not a shadow. It's an active probe against a live substrate, not a parallel observation of primary.

## §11. Deferred, not this spec

- Distributed harness (multiple runners coordinating on one scenario) — deferred until multi-instance substrate.
- Automated scenario generation from audit findings — could be built later; manual authoring is the current model.
- Continuous scenario execution triggered by every commit — a v2 concern.
- Cross-scenario dependencies (scenario B requires scenario A's outputs) — the current cleanup model resets state between scenarios; if this needs revisiting, separate spec.

## §12. What this spec means for Phase 3

Phase 3 of the substrate spec is end-to-end tracing infrastructure. That phase's deliverable is: the harness built, the observability streams (§5) wired to the harness runner, the initial scenario library populated with at least one scenario per Phase 4 mechanism.

Phase 4 verification then runs by executing scenarios. Each mechanism's PASS on its scenario is the definition of "live and functioning" — not a status field claim, not an ad-hoc read. A scenario run that produces a PASS report with matching observability metrics is the acceptance test.

Under this discipline, Phase 4 becomes tractable: 30 mechanisms × one scenario each × one report each. Each report is comparable to prior reports. The work stops feeling like a losing battle because each mechanism has an answerable question and a documented answer.

---

### Changelog
- v1 (2026-07-06, Eve): initial spec. Written after Joe's ratification of the substrate spec (`GL-SPEC-SUBSTRATE-FOUNDATION-EVE-20260706-v1`) and his ruling that end-to-end verification harness is Phase 3's real deliverable. Full-stack observability section (§5) covers substrate events, component health, CPU, memory, disk/EFS including burst credit balance, network including TCP retransmits and DNS, async/OS concurrency signals, AWS-side signals including ALB and ECS health, security signals, external API activity, log stream, storage state — the infrastructure layers Joe explicitly asked to include because they were invisible from his seat during tonight's failures.
