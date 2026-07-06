# GL-RPT-HARNESS-DEPLOY-C1-20260706-v1

**doc_id:** GL-RPT-HARNESS-DEPLOY-C1-20260706-v1
**From:** c1
**Executing:** GL-CMD-HARNESS-DEPLOY-EVE-20260706-v1
**To:** Eve (routing per dispatch instruction — no questions to Joe in this doc)
**Companions:** `GL-SPEC-TEST-HARNESS-EVE-20260706-v1.md`, `GL-SPEC-SUBSTRATE-FOUNDATION-EVE-20260706-v1.md`

Steps executed one at a time per dispatch discipline (§3 → §4 → §5), each
verified before proceeding. No step failed outright, but Step 5 surfaced a
finding serious enough that I did not execute past what the dispatch
literally specified — detailed in Findings below.

---

## 1. Repo layout confirmation

The 15 dropped files landed flat in `docs/` (not `docs/harness/` as the
dispatch assumed) — confirmed by `git status` before touching anything:
`README.md`, `__init__.py`, `aws_signals.py`, `cli.py`, `collector.py`,
`cpu.py`, `cross_sense_recall_basic.yaml`, `event_stream.py`,
`expectations.py`, `memory.py`, `report.py`, `runner.py`, `scenario.py`,
`substrate_client.py`, `types.py`. All 15 present and accounted for.

Two files the dispatch's target structure requires were **not** among the
15 and had to be authored fresh (not part of the drop, not substrate
code — pure packaging plumbing):
- `harness/harness/__init__.py` (`__version__ = "0.1.0"` — `cli.py` already
  imports this and would not run without it)
- `harness/harness/__main__.py` (thin `from .cli import main` wrapper —
  required for `python -m harness` to resolve at all)

Also authored: `harness/pyproject.toml` (per dispatch, declaring
`pyyaml`, `httpx`, `boto3>=1.34`), `harness/reports/.gitignore`, and
`.gitkeep` placeholders in the four empty scenario category dirs
(`integration/`, `stress/`, `regression/`, `security/`) so git tracks
them.

Final layout, matches dispatch spec exactly:

```
harness/
  README.md
  pyproject.toml
  harness/
    __init__.py            (NEW)
    __main__.py            (NEW)
    cli.py
    types.py
    scenario.py
    substrate_client.py
    runner.py
    expectations.py
    report.py
    observability/
      __init__.py           (this was the single dropped __init__.py —
                              it belongs to this subpackage, not harness/)
      collector.py
      event_stream.py
      cpu.py
      memory.py
      aws_signals.py
  scenarios/
    mechanism/cross_sense_recall_basic.yaml
    integration/ stress/ regression/ security/  (empty, .gitkeep)
  reports/                  (gitignored)
```

The two spec docs (`GL-SPEC-TEST-HARNESS...`, `GL-SPEC-SUBSTRATE-
FOUNDATION...`) were left in `docs/` — they're reference specs, not part
of the 15-file skeleton drop, and `docs/` is their correct home.

---

## 2. Prereq verification results (Step 2)

All four verify commands run exactly as specified, in a fresh venv
(`harness/.venv`, `pip install -e .` — clean install, no errors).

| Check | Expected | Actual | Result |
|---|---|---|---|
| `validate scenarios/mechanism/cross_sense_recall_basic.yaml` | `OK GL-SCN-CROSS-SENSE-RECALL-BASIC-EVE-20260706-v1 (mechanism)` | identical | PASS |
| `--help` | full option list | full option list (`run`, `validate` subcommands) | PASS |
| `run --help` | full option list | all 9 flags + positional listed | PASS |
| `run ... --dry-run --target http://localhost:9999` | verdict PASS, exit 0, report emitted | verdict PASS, exit 0, report at `/tmp/harness-reports/...` | PASS |
| `run ...` (no dry-run, same fake target/auth) | verdict PRECONDITION_NOT_MET, exit 4, report with precondition finding | verdict PRECONDITION_NOT_MET, exit 4, report's Findings section: `CRITICAL (runner) precondition not met: substrate.status() not implemented on this client: LegacySubstrateClient.status: wire to guala_status bridge tool or GET {base_url}/status` | PASS |

No skeleton bugs found. Nothing routed back before proceeding to §3.

---

## 3. Substrate client wiring status (Step 3)

All 5 abstract methods on `LegacySubstrateClient` wired (the dispatch
enumerated 7 items, but `inject_probe` is one method serving 6 probe
methods via internal dispatch, not 6 separate abstract methods — 5
methods total: `status`, `stream_events`, `inject_probe`,
`snapshot_state`, `restore_state`).

**Important scope note, confirmed before writing any code:** there is no
callable "bridge tool" surface reachable from a standalone process — the
guala_* MCP bridge tools are themselves thin wrappers
(`bridge/server.py`) around the substrate's own HTTP endpoints. This
client calls those same underlying endpoints directly. Every endpoint
shape below was read directly from `bridge/server.py` and
`dsf_ai_service/app.py`, not assumed.

| Method | Status | Wired to |
|---|---|---|
| `status()` | WIRED | `POST {base_url}/api/v1/gualaloom` `{"text":"","command":"/status"}` → mapped to `SubstrateStatus` via new `_map_status()`. Unit-verified against a real captured response shape (tick, vocab, atlas_bindings, deep_atlas_entries, organism_neurons, presence, ladder, current_activity all assert correctly). |
| `stream_events(since_tick)` | WIRED | `GET {base_url}/api/v1/gualaloom/events?since=<cursor>&n=200`, 200ms poll cadence, cursor-based on the max `tick` seen. Uses the dedicated GET route (`app.py:3600`), not the bridge's own `command="/events"` path (which silently drops its `limit` param — confirmed by direct code read, not assumed). Mapped via new `_map_event()`. |
| `inject_probe(method, payload, auth_as)` | WIRED, all 6 sub-methods | `give_experience` → `POST /api/v1/gualaloom` with `command=/bundle:<name>`; `say` → same endpoint, no command (converse-shaped, 202+poll_url returned as-is — inject_probe does not itself poll to completion, per its own docstring contract that outcome-reading is the event stream's job); `converse` → `POST {base_url}/v7/converse` (a distinct, synchronous session endpoint — confirmed `bridge/server.py` does NOT use this path, only the harness does); `wake` → `POST /api/v1/gualaloom` `command=/wake`; `addpicture`/`addsound` → multipart `POST /api/v1/gualaloom/upload/{picture,sound}`, form field `file`. `direct_event` raises `ValueError` (unsupported on legacy, per dispatch). |
| `snapshot_state(label)` | WIRED, with a caveat (Finding 3 below) | `POST /api/v1/gualaloom/admin/backup`, no body. Fire-and-forget (202) even in embedded mode. Returns a locally-generated label, not a real handle — see Finding 3. |
| `restore_state(snapshot_id)` | **Deliberately not implementable — raises by design, not NotImplementedError** | See Finding 4. Confirmed (not assumed) there is no synchronous same-process restore endpoint on the legacy substrate. Raises `RuntimeError` (not `NotImplementedError`) so `runner.py`'s `_cleanup()` routes this into its CRITICAL/DIRTY branch rather than the softer WATCH branch — matching the dispatch's explicit instruction ("mark DIRTY, add finding, exit RESTORE_FAILED"). No substrate-side code touched, per guardrail. |

Re-ran all of Step 2's verification commands after wiring: `validate` and
`--dry-run` unchanged (PASS); the real-run-against-fake-target case now
fails with `ConnectError: All connection attempts failed` instead of
`NotImplementedError` — confirms the client is making real HTTP calls, not
just satisfying the type signature.

---

## 4. AWS collector wiring status (Step 4)

All 6 collectors wired with real `boto3` calls (not stubs) in
`observability/aws_signals.py`. Verified by calling `_sample_once()`
directly against real AWS resources — read-only, zero write/mutate calls,
zero substrate contact.

| Collector | Wired to | Verified live |
|---|---|---|
| `EFSBurstCreditCollector` | `cloudwatch:GetMetricStatistics`, `AWS/EFS BurstCreditBalance`, dimension `FileSystemId` | `burst_credit_balance_bytes: 2308974418330.0` (real value, filesystem healthy) |
| `CloudWatchMetricsCollector` | `AWS/ECS CPUUtilization`/`MemoryUtilization`, dimensions `ClusterName`+`ServiceName` (standard ECS service metrics, not Container Insights — works without Insights enabled) | `cpuutilization_avg: 0.61`, `memoryutilization_avg: 1.27` |
| `ALBMetricsCollector` | `AWS/ApplicationELB RequestCount`/`HTTPCode_Target_{4,5}XX_Count`/`TargetResponseTime` via CloudWatch + `elasticloadbalancing:DescribeTargetHealth` directly | `healthy_target_count: 1, unhealthy_target_count: 0` |
| `ECSHealthCollector` | `ecs:DescribeServices` (deployment rollout state) + `ecs:DescribeTasks` (per-task health) | `desired_count: 1, running_count: 1, healthy_task_count: 1, in_progress_deployments: 0` |
| `CloudTrailCollector` | `cloudtrail:LookupEvents`, `Username` attribute = task/execution role ARN | `events_seen_this_sample: 0` (clean — no unexpected activity in the lookback window) |
| `CloudWatchLogsCollector` | `logs:StartQuery`/`logs:GetQueryResults`, Logs Insights query for ERROR/FATAL lines | `query_status: Complete, error_or_fatal_lines_found: 0` |

**IAM policy:** created for real —
`arn:aws:iam::418384447921:policy/GualaHarnessObservability`
(`PolicyId ANPAWC2NIBGY44FV4MDUB`), exact 8 actions from the dispatch,
`Resource: "*"`, no mutating permissions. **Not attached to anything** —
see Finding 1.

**Staging AWS config:** written to `~/.guala/staging-aws-config.json`
(personal/local per spec §8, not repo-tracked) with `cluster`,
`service`, `filesystem_id`, `load_balancer_arn`, `target_group_arn`,
`task_role_arn`, `execution_role_arn`, `log_group` all populated with
real values. These are the **only** real Guala AWS resources that exist
in this account — see Finding 2 for why that matters.

---

## 5. First scenario report (Step 5)

Ran the exact command specified:

```
python -m harness run scenarios/mechanism/cross_sense_recall_basic.yaml \
    --target https://guala-staging.dsf-ai.com \
    --auth ~/.guala/harness-admin-token.json \
    --aws-config ~/.guala/staging-aws-config.json \
    --reports-dir ./reports
```

**Verdict:** `PRECONDITION_NOT_MET`, exit 4.
**Report:** `harness/reports/GL-RPT-HARNESS-CROSS-SENSE-RECALL-BASIC-EVE-20260706-20260706T224243Z-v1.md` (+ matching `.json`).
**Finding recorded in the report:** `CRITICAL (runner) precondition not met: substrate.status() failed: ConnectError: [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] ssl/tls alert handshake failure`.

This is **not** the "SubstrateStatus mapping might be wrong" case the
dispatch anticipated. It's a different, more fundamental result — see
Finding 2. No probe was ever injected (precondition check runs and fails
before probe injection in `runner.py`'s sequence), so this run touched
nothing beyond a DNS+TLS handshake attempt. Zero mutation risk.

Because the precondition check failed at the connection level, no
further sections of the report have content: no events captured, no
expectation results, no observability sections populated (collectors
never started — they instantiate after the precondition check per
`runner.py`'s step ordering), no substrate state delta. The report
structure itself is correct and matches spec §6 — it's just empty past
the Findings section because nothing after step 2 of the runtime
sequence ever ran.

---

## 6. Findings needing Eve routing

**Finding 1 — IAM policy has no attachment target.** No IAM role or user
in this account represents "the harness's credential." `aws iam list-
roles`/`list-users` show only `CodexProdVerificationAssumeRoleUser` and
`tfe-deploy-admin` (the latter is TFE-scoped — out of bounds for Guala
work per standing project-separation rule) — no `harness` or
`developer` principal exists. I did not attach the policy to root (the
credential I'm currently operating under): root already has every
permission implicitly, so attaching a scoped read-only policy to it is
meaningless, and doing so would model exactly the anti-pattern (routine
tooling running as root) that a dedicated policy is supposed to move
away from. Needs a decision: create a dedicated `guala-harness` IAM
user/role now, or defer until Phase 5 (§8.6 of the foundation spec
already calls for the substrate's own task role and execution role —
the harness's operator identity is a separate, so-far-undecided
question).

**Finding 2 — `guala-staging.dsf-ai.com` does not resolve to any Guala
infrastructure in this account.** Verified three ways: (a) DNS resolves
it to `d3ewp8o6785abv.cloudfront.net`; (b) `aws cloudfront list-
distributions` shows exactly one distribution in this account
(`dsf-ai.com`/`www.dsf-ai.com`, origin the static-site S3 bucket) — it is
not this one; (c) direct `curl` to the hostname fails at the TLS
handshake (`SSLV3_ALERT_HANDSHAKE_FAILURE`), meaning whatever owns that
CloudFront distribution has no certificate/listener configured for this
hostname. This is not a wiring bug — the harness's HTTP client behaved
correctly and reported the real failure honestly.

Structural read, not just a missing DNS record: per
`GL-SPEC-SUBSTRATE-FOUNDATION-EVE-20260706-v1` §8 and §11, a
topology-separated staging/primary split (own task-def, own service, own
subdomain) is **Phase 5 (MOVE)** — explicitly sequenced *after* Phase 3
(this harness) and Phase 4 (component liveness). Until Phase 5 executes,
there is exactly one Guala substrate in this AWS account
(`tfe-web-cluster` / `dsf-ai-service-lb`), and the harness spec's own §7
rule applies directly: *"we do not run mutating probes against primary
[...] If a genuine need arises to run a probe against primary, that
requires its own dispatch and Joe's ratification."* I did not seek or
have that ratification, so I did not point a real run at that target —
Step 5 was executed exactly as literally specified against the named
staging URL, which is safely unreachable, not redirected at the one real
substrate. This is a genuine chicken-and-egg in the phase sequencing
worth Eve's attention: the harness (Phase 3's deliverable) is specced
assuming Phase 5's topology already exists.

**Finding 3 — `snapshot_state()`'s returned ID is not a real handle.**
`admin/backup` is fire-and-forget (202, no body) even in embedded mode —
confirmed by direct code read of `app.py:3069-3094`
("save_full_state + S3 upload takes 30-120s; API GW has 30s timeout ...
fire-and-forget"). There is no backup key/ID returned, and no
correlation between "this backup call" and the later
`persistence_health.last_s3_backup` timestamp on `/status`. The
`snapshot_id` this method returns is therefore a locally-generated label
with no verifiable link to whether a backup actually landed by the time
the caller trusts it. Real for a "best-effort, non-blocking pre-run
snapshot" (which is how `runner.py` already treats it — failure here is
WATCH/WARN, not fatal), but not real enough to be a genuine restore
point. Ties directly into Finding 4.

**Finding 4 — no usable synchronous restore path exists on the legacy
substrate.** Confirmed, not assumed: the only restore-shaped endpoint is
`POST /api/v1/gualaloom/admin/restore_from_s3_prefix`
(`app.py:3287-3288`), which explicitly requires a substrate **restart**
to take effect. A harness cleanup step cannot restart the ECS service as
a side effect of finishing a scenario run — that's substrate-side
infrastructure control, outside a verification tool's blast radius, and
explicitly out of this dispatch's scope ("Do NOT add substrate-side code
in this dispatch"). Implemented `restore_state()` to raise (not
`NotImplementedError`) so `runner.py` marks the substrate DIRTY per
dispatch instruction. Practical consequence: **any scenario with
`cleanup.restore_state: pre_probe_snapshot` (which is every scenario
using the schema's default, including `cross_sense_recall_basic.yaml`)
will always end DIRTY on the legacy substrate.** This is a real gap
between what the harness spec promises (§4.2 step 8, §3.1's
`cleanup.restore_state` field) and what the legacy substrate can
actually do — needs either a real substrate-side restore mechanism (a
separate, substrate-side dispatch) or a scope decision that legacy-
substrate scenarios accept DIRTY-after-every-run until the message-
passing substrate (which the harness's other client, `MessagePassing-
SubstrateClient`, is stubbed for) exists.

**Finding 5 (minor, harness-code, not substrate) — `runner.py`'s
`_cleanup()` does not set `Verdict.RESTORE_FAILED` on a restore
exception.** Read while wiring Step 3, not modified (out of this
dispatch's stated scope — Step 3 was "wire substrate_client.py," not
"fix runner.py"). `_cleanup()`'s except-Exception branch adds a CRITICAL
finding and comments that "In production this would set a marker file,"
but the run's `verdict` variable is never updated to
`Verdict.RESTORE_FAILED` (exit 5) — it stays whatever `_wait_for_
completion()` returned. Given Finding 4 above, every real run against
the legacy substrate will hit this path, so the gap is not
hypothetical. Small, contained fix once scoped (one line in
`Runner.run()`'s post-cleanup verdict logic) — flagging rather than
fixing since it's outside Step 3's named scope.

**Finding 6 (context, not a defect) — the substrate's live state changed
dramatically between two of my own checks tonight.** A direct
`status()` call made minutes after Step 5 (read-only, no probe) returned
`tick=0, vocab_size=0, atlas_bindings=0, organism_neurons=64` — starkly
different from every reading earlier tonight (`tick` in the
15-million range, `vocab_size=14150`, `organism_neurons=106`). This
matches the shape of `GL-SPEC-SUBSTRATE-FOUNDATION-EVE-20260706-v1`
§9's Phase 1 WIPE having executed (clean identity, empty atlas, seed
population) — consistent with the ratified execution order's Phase 1
being first. Noting this factually because it's directly relevant to
Finding 2: if Phase 1 already ran, the *only* real substrate is
currently sitting in exactly the `clean_slate` precondition state this
scenario wants — which is exactly why running a real (non-dry-run)
scenario against it needs Joe's explicit ratification per §7's
primary-harness carve-out, not a unilateral call by whoever runs the
harness next.

---

## 7. c1's read on what the next dispatch should look like

The skeleton and wiring are sound — every verify step passed on first
build, both client-wiring and AWS-collector-wiring are backed by direct
reads of the real endpoint code (not guesses), and the report format
correctly renders even a maximally-truncated run (precondition failure
at the connection level). The mechanical harness itself is ready. What
blocks a *meaningful* first scenario report is entirely the staging/
primary question (Finding 2), not anything in this dispatch's own scope.

Three sequencing options exist, in my read most-to-least preferred:

1. **Stand up a minimal isolated staging deployment now**, ahead of the
   full Phase 5 topology-separation work — even a second ECS service on
   the same cluster with its own EFS prefix would give the harness a
   real, safe target without pulling forward the whole own-container/
   own-subdomain/own-IAM-role scope of §8. This unblocks Phase 4
   (component-liveness verification, which is the actual reason the
   harness exists) without touching primary at all.
2. **Get Joe's explicit ratification to run against the one real
   substrate**, per harness spec §7's own carve-out language. Lower
   engineering cost, but real risk: every scenario in the schema's
   default cleanup path ends DIRTY (Finding 4), so this option needs the
   restore-path gap (Finding 4) closed or explicitly accepted as a known
   cost first — otherwise the first real run leaves the one substrate
   dirty with no path back.
3. **Defer real scenario runs until Phase 5 lands** — safest, but
   means the harness sits unused through Phase 3/4, defeating the
   stated reason it was commissioned ("Phase 4 verification then runs
   by executing scenarios... Each mechanism's PASS on its scenario is
   the definition of live and functioning" — foundation spec §12/harness
   spec §12).

Separately, closing Finding 4 for real (a genuine restore mechanism)
looks like its own bounded, substrate-side dispatch — likely small: a
synchronous in-process state-reload path that doesn't require a
container restart, gated so it's only reachable from the harness's own
admin surface, not general traffic.
