# harness — GualaLoom substrate verification harness

Skeleton v0.1.0. Per `GL-SPEC-TEST-HARNESS-EVE-20260706-v1.md`.

## What works

- **Scenario loading and validation** — YAML → typed dataclasses. Precise errors on malformed scenarios. `python -m harness validate <path>` runs schema check without executing.
- **Runner orchestration** — full runtime sequence per spec §4.2. Every failure mode returns a defined verdict + exit code (PASS=0, FAIL=1, TIMEOUT=2, RESOURCE_CAP=3, PRECONDITION_NOT_MET=4, RESTORE_FAILED=5).
- **Two working observability collectors** (CPU via `/proc/stat`, memory via `/proc/self/status` + `/proc/meminfo`).
- **Substrate event stream collector** — full subscription loop, ready to hook up as soon as SubstrateClient methods are wired.
- **Expectations checker** — per-expectation pass/fail against events + collector snapshots + status deltas.
- **Report emission** — markdown + JSON per spec §6, canonical `GL-RPT-HARNESS-...-v1` doc_id.
- **Async throughout** — collectors run concurrently with probe injection.
- **Failure isolation** — collector exceptions marked degraded, runner continues; substrate exceptions become findings, runner continues to next step.

## What is skeleton (real interface, honest stub implementation)

- **`LegacySubstrateClient`** — every method raises `NotImplementedError` with the specific endpoint or bridge tool to wire. Wiring is a bounded follow-up dispatch (see below).
- **`MessagePassingSubstrateClient`** — placeholder. The message-passing substrate does not exist yet (Phase 3-4 rewrite).
- **AWS collectors** (`aws_signals.py`) — six collectors (CloudWatch metrics, EFS burst credit balance, ALB metrics, ECS health, CloudTrail, CloudWatch Logs). Each has the right interface + sample interval; each marks itself degraded on first sample instead of silently omitting.

## What is deferred

- Detailed network collector (`/proc/net/snmp`, TCP retransmits, DNS) — spec §5.6 covers, deferred until AWS wiring lands since ALB metrics cover the external network surface.
- Concurrency signals collector (event loop lag, task queue depth, blocked tasks) — spec §5.7 covers, more useful under message-passing substrate.
- Storage state collector — spec §5.12 covers, requires EFS mount access from the harness which means in-cluster deploy, deferred.
- `--compare` flag for report diffing — flagged in CLI, implementation pending.

## Layout

```
harness/
  harness/                       # the package
    __init__.py                  # version
    __main__.py                  # python -m harness entrypoint
    cli.py                       # argparse CLI
    types.py                     # Verdict, TraceId, Finding
    scenario.py                  # scenario schema + loader
    substrate_client.py          # abstract client + Legacy + MessagePassing
    runner.py                    # the orchestrator
    expectations.py              # expected-vs-actual checker
    report.py                    # markdown + JSON emission
    observability/               # collectors
      __init__.py                # instantiation entry point
      collector.py               # base Collector class
      event_stream.py            # substrate events (load-bearing)
      cpu.py                     # /proc/stat
      memory.py                  # /proc/self/status + meminfo
      aws_signals.py             # six AWS collectors (skeleton)
  scenarios/
    mechanism/
      cross_sense_recall_basic.yaml
    integration/
    stress/
    regression/
    security/
  reports/                       # runtime output
```

## Usage

```bash
# Validate a scenario without running
python -m harness validate scenarios/mechanism/cross_sense_recall_basic.yaml

# Dry run (skips substrate calls, exercises runner path)
python -m harness run scenarios/mechanism/cross_sense_recall_basic.yaml \
    --target https://guala-staging.dsf-ai.com \
    --auth ~/.guala/admin-token.json \
    --dry-run

# Real run — will PRECONDITION_NOT_MET until SubstrateClient is wired
python -m harness run scenarios/mechanism/cross_sense_recall_basic.yaml \
    --target https://guala-staging.dsf-ai.com \
    --auth ~/.guala/admin-token.json \
    --reports-dir ./reports
```

## Follow-up dispatches this skeleton implies

1. **`GL-CMD-HARNESS-SUBSTRATE-CLIENT-WIRING`** — implement the seven methods on `LegacySubstrateClient` (status, stream_events, inject_probe for each probe method, snapshot_state, restore_state). Bounded scope, per-method table already in the docstrings.

2. **`GL-CMD-HARNESS-AWS-WIRING`** — wire the six AWS collectors to boto3 clients. IAM policy needed: `cloudwatch:GetMetricStatistics`, `logs:StartQuery`, `logs:GetQueryResults`, `ecs:DescribeTasks`, `ecs:DescribeServices`, `cloudtrail:LookupEvents`. Scope is per-collector, well-bounded.

3. **First real end-to-end run** — once (1) is done, run the cross-sense recall scenario against staging. First real report tells us whether the mechanism actually works, and whether the harness itself needs adjustments.

4. **Scenario library grows** — one scenario per cognition-meter mechanism, one regression scenario per SEV-0/SEV-1 audit finding. Coverage tracked in `scenarios/COVERAGE.md`.

## Dependencies

- Python 3.11+
- `pyyaml` (installed via `pip install pyyaml`)
- Standard library everything else — deliberately no boto3, httpx, pydantic in the skeleton. AWS wiring dispatch adds boto3.

## Design decisions worth naming

- **argparse over click** — stdlib, no dependency.
- **dataclasses over pydantic** — stdlib, precise error messages.
- **asyncio throughout** — collectors and probe injection run concurrent naturally.
- **Failure never silent** — every collector that can't sample marks degraded; every skipped step raises a finding; unimplemented methods raise `NotImplementedError` with the specific wiring to do.
- **Runner does not judge** — checker judges. Runner gathers evidence.
- **Two client flavors present from day one** — legacy vs message-passing, same interface. Prevents the harness from becoming tightly coupled to the substrate that will be replaced.
