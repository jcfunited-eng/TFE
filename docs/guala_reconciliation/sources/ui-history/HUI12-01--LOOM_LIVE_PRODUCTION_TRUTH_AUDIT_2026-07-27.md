# Loom live-production truth audit — 2026-07-27

This is read-only audit evidence. It is not an active runtime authority,
deployment record, readiness claim, or substitute for live verification.

## Architecture honesty gate

- Requested architecture: a truthful, read-only Loom observation surface with
  full explicit DSF fields and truthful compute, RAM, and storage boundaries.
- Current live reality: the backend serves observation schema
  `guala.observation_snapshot.v4`, but the public S3 Loom page is the older
  `loomscan-live-v1`.
- Conflict: yes. The live page still renders chi-density position, lexical
  lanes, word-to-memory arcs, emission blooms, and legacy event telemetry.
- Mechanisms not extended: chi identity, scripted meaning, legacy event
  visualization, reduced DSF projections, ML, and speech integration.
- Exact next item: publish the already-staged observation-v2 static page only
  from a reviewed clean commit, then hash and browser-verify the public object.
- DSF evaluation: the backend observation explicitly exposes
  `D_k/M_k/R_rev_k/U_star_k/C_k/P_k/B_k` as required fields. The view is an
  explicitly lossy latest-tuple observation projection, not DSF decision
  authority.

## Highest-impact false production claim

The public page identifies itself as a read-only Loom instrument while it
actively presents chi and legacy event/emission telemetry as the scan.

Live object evidence:

- URL: `https://dsf-ai.com/loomscan.html`
- fetched object SHA-256:
  `8121baaa9996a4919a1e9413c6327add73bc4936591e1e854c4df8fc163658e7`
- fetched bytes: `52,900`
- document id: `loomscan-live-v1`
- S3 `Last-Modified`: `Sat, 25 Jul 2026 06:02:07 GMT`
- footer claim: chi dot positions are an exact projection from
  `/chi_density`
- active calls: `/events` and `/chi_density`
- both active calls returned HTTP 200 during this audit

This conflicts directly with the project rule that chi is routing only, never
identity or meaning. It also means the public page is not the locally staged
truthful observation-v2 surface.

## Backend observation evidence

The live backend returned:

- running source SHA: `9d3d167e26bb6c12f4a9d7955077de087b9b9fe0`
- observation schema: `guala.observation_snapshot.v4`
- observation response SHA-256:
  `7d8757c2d51955e559d56d4a79c7763aee7ca9a7efc2ced5d466f78c9215f9a6`
- observation response bytes: `61,716`
- full-field required fields:
  `D_k`, `M_k`, `R_rev_k`, `U_star_k`, `C_k`, `P_k`, `B_k`
- declared projection:
  `latest_exact_tuple_per_substream`
- declared projection loss: earlier temporal tuples are omitted
- decision authority: false

The static page and backend therefore belong to different observation
contracts.

## Compute and RAM

The active ECS service was healthy with exactly one running task:

- task definition: `dsf-ai-task:762`
- task CPU ceiling: `4096` CPU units / 4 vCPU
- task RAM ceiling: `16,384 MiB`
- task ephemeral-storage ceiling: `20 GiB`
- production mode: embedded
- active state path: `/app/guala/active`

Recent CloudWatch samples during the audit showed:

- memory: approximately `34.27%` of the 16 GiB task limit, with a sampled
  maximum of `43.01%`
- CPU: approximately `2.04%` of the 4-vCPU task limit after a sampled maximum
  of `26.95%`

The live `/status` response exposes measured engine tick rate and bounded
queue/drop counters, but it does not expose the ECS CPU or RAM ceiling or
utilization. Loom therefore cannot truthfully display those resource facts
from its current public inputs.

## Storage

The active EFS filesystem reported approximately `2,559,170,560` bytes at the
latest sampled point. The engine has multiple local component bounds,
including bounded event-log rotation and snapshot retention, but EFS itself is
elastic and the live `/status` response contains no whole-state storage usage
or global EFS capacity authority.

The lightweight live persistence response contained only:

- identity
- schema version
- last-save tick and timestamp
- last backup
- boot-load boolean

It did not contain:

- required files present or missing
- load-error details
- integrity-error details
- event-log bytes or rotation count
- whole active-generation bytes
- global persistent-storage ceiling

The locally staged observation-v2 page currently interprets absent integrity
arrays as empty and would display a green integrity result. That local
candidate must not be published until absence is rendered as unavailable or
the backend supplies the authenticated full persistence facts.

## Local candidate verification

The current shared worktree's modified observation-v2 page and related local
contracts passed:

```text
17 passed, 9 warnings in 2.86s
```

These are component/contract tests. They are not live proof.

## Why this stream did not edit or deploy

The corrective static page, its UI tests, the deployment program, and the
application are already modified by other work in the shared dirty worktree.
The production deployment program correctly refuses dirty or untracked source
and publishes static files only from the reviewed commit archive. Editing or
publishing those overlapping files here would violate both change ownership
and the clean immutable deployment contract.

No production file was changed by this audit. No deployment was attempted.
The live false claim remains present.
