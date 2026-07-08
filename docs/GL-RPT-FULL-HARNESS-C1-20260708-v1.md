# GL-RPT-FULL-HARNESS-C1-20260708-v1

**doc_id:** GL-RPT-FULL-HARNESS-C1-20260708-v1
**From:** c1
**To:** Eve (routing per standing rule — no questions to Joe in this doc)

**Verdict: NO REGRESSION.** All four mechanism scenarios in
`harness/scenarios/mechanism/` were run against the live production
substrate. All four halted at the same known, pre-existing
`PRECONDITION_NOT_MET` gap (`presence.wc expected True, actual False`)
described in every prior harness dispatch this project has run — no
new or unexpected finding emerged from any of the four runs. The
substrate's own `guala_status` snapshot is healthy and matches the
expected deployed commit.

---

## What was run

Target: `https://guala-staging.dsf-ai.com` (hosts-override to the live
ALB, pre-existing, untouched). Auth:
`~/.guala/harness-admin-token.json` (placeholder token, expected).
Harness invoked via `harness/.venv/bin/python -m harness run ... --reports-dir ./reports --verbose`,
in place, no worktree, no code changes.

Wall-clock window: 2026-07-08T01:45:52Z through 2026-07-08T01:46:16Z
(all four runs, back to back, each completing in 1.4-4.2 seconds).

| # | Scenario file | Verdict | Report doc_id |
|---|---|---|---|
| 1 | `binding_windows_acceptance.yaml` | PRECONDITION_NOT_MET | GL-RPT-HARNESS-BINDING-WINDOWS-ACCEPTANCE-EVE-20260706-20260708T014556Z-v1 |
| 2 | `cross_sense_recall_acceptance.yaml` | PRECONDITION_NOT_MET | GL-RPT-HARNESS-CROSS-SENSE-RECALL-ACCEPTANCE-EVE-20260706-20260708T014602Z-v1 |
| 3 | `cross_sense_recall_basic.yaml` | PRECONDITION_NOT_MET | GL-RPT-HARNESS-CROSS-SENSE-RECALL-BASIC-EVE-20260706-20260708T014610Z-v1 |
| 4 | `hemispheric_integration_acceptance_v3.yaml` | PRECONDITION_NOT_MET | GL-RPT-HARNESS-HEMISPHERIC-INTEGRATION-ACCEPTANCE-EVE-20260707-20260708T014615Z-v1 |

Each run exited with process code 4 (the harness's own
`PRECONDITION_NOT_MET` exit status), and each report shows an
identical shape: `probe_actions: []`, `events: []`,
`check_results: []`, `pre_status: null`, `post_status: null`, and a
single CRITICAL finding from the runner itself:

```
precondition not met: presence.wc expected True, actual False
```

## Per-scenario detail

**1. binding_windows_acceptance.yaml** — halted before any probe
action ran (4.2s wall). No expectations were evaluated because the
run never got past its own precondition check. This is the same
scenario (and same wall) that
`GL-RPT-HARNESS-BINDING-WINDOWS-LIVEVERIFY-C1-20260706-v1` hit on
2026-07-06/07: `presence.wc` is never established by the harness's
precondition-setup step. No mechanism-level evidence, positive or
negative, was produced about binding-windows itself — that remains
governed by the mechanism-level verification already on record and
unaffected by anything since.

**2. cross_sense_recall_acceptance.yaml** — same shape, 1.7s wall,
same single CRITICAL finding. No probe of the recall engine's
wiring was reached.

**3. cross_sense_recall_basic.yaml** — same shape, 2.6s wall, same
single CRITICAL finding. This scenario has now been run at least five
times across this project's history (prior reports dated
2026-07-06T22:42Z, 2026-07-06T23:06Z, 2026-07-07T00:43Z,
2026-07-07T00:45Z, 2026-07-07T01:00Z, all in `harness/reports/`); this
run reproduces the identical `presence.wc` gap every prior attempt
hit.

**4. hemispheric_integration_acceptance_v3.yaml** — same shape, 1.4s
wall, same single CRITICAL finding. Prior runs on record from
2026-07-07T04:29Z and 2026-07-07T05:05Z show the identical verdict
and finding, so this is a stable reproduction, not a new symptom.

## Known pre-existing gap vs. new findings

**Known pre-existing gap (not a regression, not actioned here):** all
four scenarios' preconditions check `presence.wc` (or, by extension,
`presence.joe`), and the harness's precondition-setup step has a
confirmed, long-standing gap — it does not itself call anything to
establish those presence flags before the check runs. This has been
observed identically across every dispatch that has exercised this
harness (binding-windows on 2026-07-06/07, cross-sense-recall builds
and re-runs through 2026-07-07, hemispheric-integration v3 through
2026-07-07). Nothing in this run's four results deviates from that
established pattern in any way — same finding text, same severity,
same halted-before-probe shape.

**Genuinely new or unexpected findings from this run: none.** All
four verdicts, all four finding messages, and all four report shapes
match the established gap exactly. No new CRITICAL/WARNING category
appeared, no scenario got further than the precondition check, and no
timing, error-code, or endpoint anomaly outside that gap was observed.

## guala_status cross-check

Called once, read-only, via `mcp__claude_ai_GualaLoom_Bridge__guala_status`
at 2026-07-08T01:45:42Z (immediately before the harness runs):

- `running_sha`: `f26ce7263f3e936fff15d53656e53b394669f46d` — **matches**
  the expected currently-deployed commit (task-def `dsf-ai-task:554`)
  stated in this dispatch. No drift detected.
- `guala_identity`: `0b4c244a-06fd-4ee4-af84-fb19d85db416`, schema
  `v7.2.0`, `load_successful_at_boot: true`.
- `tick`: 1,063,214. `tick_rate`: 0.19 (with
  `tick_rate_had_pending_work: true`).
- `current_activity`: `SLEEPING` (`asleep: true`), started at tick
  1,063,148, expected to end at tick 1,065,148 — consistent with the
  substrate's previously-documented sleep/dream cycling, not new.
- `presence`: `joe`, `wc`, and `c1` all show `present: false` in this
  snapshot — directly consistent with, and the root observable behind,
  the `presence.wc` precondition failures above.
- `persistence_health`: `last_save_tick: 1063197`,
  `last_save_timestamp: 2026-07-08T01:44:07Z`, most recent S3 backup
  `2026-07-08_01-05-54` (13 files). Saves are current and healthy —
  no repeat of the `last_save_tick=0` boot-time failure mode on
  record from the June/July restore incident.
- `frame_backpressure`: 0 dropped sight/sound frames, 0 inflight.
- `organism_worker`: 0 queued, 0 dropped, mean item cost 259.8ms
  (max 486.1ms) — no queue backlog.
- `atlas_health`: 8,040 live bindings / 8,085 total entries, 173 chi
  keys, total strength 732.58. `deep_atlas`: 1,011 entries, enabled,
  3,323 reinstatements since boot, no `recent_gate_rejects`.
- No anomalies (no dropped frames, no failed loads, no queue
  overflow, no sha drift) were observed in this snapshot beyond the
  already-known sleep-loop/presence gap reflected above.

## Top line

**Did anything regress relative to the substrate's current
known-good state? No.** Every scenario reproduced the exact same
pre-existing, already-documented `presence.wc` precondition gap that
every prior harness dispatch on this project has hit — nothing new,
nothing worse. `guala_status` shows a healthy, currently-saving,
correctly-versioned substrate (`running_sha` matches the expected
deploy) with no dropped frames, no queue backlog, and no persistence
failure. The standing recommendation from prior reports (the
precondition-setup gap and the underlying sleep/dream-loop
availability issue are worth fixing so these scenarios can actually
exercise their probes) still stands and is not re-litigated further
here.

## Underlying report files

- `harness/reports/GL-RPT-HARNESS-BINDING-WINDOWS-ACCEPTANCE-EVE-20260706-20260708T014556Z-v1.md`
  / `.json`
- `harness/reports/GL-RPT-HARNESS-CROSS-SENSE-RECALL-ACCEPTANCE-EVE-20260706-20260708T014602Z-v1.md`
  / `.json`
- `harness/reports/GL-RPT-HARNESS-CROSS-SENSE-RECALL-BASIC-EVE-20260706-20260708T014610Z-v1.md`
  / `.json`
- `harness/reports/GL-RPT-HARNESS-HEMISPHERIC-INTEGRATION-ACCEPTANCE-EVE-20260707-20260708T014615Z-v1.md`
  / `.json`

## Note on this run's file handling

`harness/reports/` carries its own `.gitignore` (`*`), and a check of
full project git history (`git log --all --diff-filter=A -- 'harness/reports/*.json' 'harness/reports/*.md'`)
turned up zero commits — no raw harness report file has ever actually
been committed to this repo. The prior "harness reports committed"
precedent this dispatch referenced turns out to be this document's
own genre: synthesized `docs/GL-RPT-*` write-ups (e.g.
`GL-RPT-HARNESS-BINDING-WINDOWS-LIVEVERIFY-C1-20260706-v1`), not the
raw `harness/reports/*.md`/`*.json` output. To avoid force-adding
gitignored files against the repo's own established convention, this
run leaves the four raw report pairs above local and gitignored, as
every prior run has, and commits only this synthesized report — which
is the actual established practice on inspection.
