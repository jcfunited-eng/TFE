# GL-RPT-AWS-RUNAWAY-SCAN-C1-20260710-v1

**doc_id:** GL-RPT-AWS-RUNAWAY-SCAN-C1-20260710-v1
**From:** c1
**Context:** Direct instruction from Joe: "check aws and let me know if there
is any runaway processes - cpu - mem - storage - and if so stop them
immediately." Not a formal GL-CMD dispatch.
**To:** Eve (routing per standing practice)

Full-account scan (5 parallel investigations: ECS compute, storage, other
compute/orphans, network/IAM, cost anomalies), all regions checked for
stray resources. Two real, Guala-scoped runaway-cost issues found and
**fixed immediately, live, verified** — both are additive/reversible AWS
config changes, no data touched, no downtime. Several other findings
surfaced that are out of scope for c1 (belong to the separate TFE
project) or need a human decision before changing (a security-relevant
firewall rule). Full detail below.

---

## Fixed immediately (both live, verified)

### 1. S3 backup bucket (`dsf-ai-site-backups`) — missing noncurrent-version
### cleanup, causing unbounded growth. Already spiked to 11.7TB once.

**Root cause chain, fully traced:**
- The bucket has S3 versioning **Enabled**.
- Three pre-existing lifecycle `Expiration` rules (`guala-hourly-expire-7d`,
  `guala-auto-expire-60d`, `guala-wave-migrate-expire-90d`) only cover
  `guala/2*`, `guala/auto/`, `guala/wave_migrate_pre/`. On a **versioned**
  bucket, `Expiration` doesn't delete bytes — it just adds a delete marker
  and demotes the current version to *noncurrent*. With no
  `NoncurrentVersionExpiration` rule anywhere, every "expired" object's
  bytes were retained forever.
- Two prefixes had **zero** lifecycle coverage at all: `guala/events/`
  (event-log backup segments) and `guala/checkpoints/` — both written by
  `persistence_consumer.py`'s `S3Consumer`, which already has its own
  app-level self-cleaning logic (added 2026-07-08/09, confirmed by reading
  the code: it deletes the previous checkpoint+events pair right after a
  new one uploads successfully). That app-level fix is real and working —
  but on a versioned bucket, `delete_object()` also just adds a delete
  marker; the bytes never actually left. The two problems compounded.
- A third prefix, `guala/UNPAUSE-PRE-<timestamp>/` (a full-state safety
  snapshot written by `/api/v1/gualaloom/admin/backup` before any risky
  operation, `app.py:3240`), also had zero lifecycle coverage and no
  app-level cleanup at all — a brand new timestamped directory every call,
  forever. 17 of these already exist from just the last 3 days
  (2026-07-07 to 2026-07-09), ~125MB so far.
- Confirmed via CloudWatch: bucket size went 0.33GB → 11.7TB (247,895
  objects) between 2026-06-11 and 2026-07-08, accelerating (up to
  +2.5TB in a single day). **Someone had already manually purged this**
  on 2026-07-09 (evidence: `_pre-purge-manifests/2026-07-09_*` in the
  bucket) — live size at scan time was back down to ~6.9GB. But the
  lifecycle gap that caused it was still open, so it would have recurred.

**Fix applied** (`aws s3api put-bucket-lifecycle-configuration`, verified
via `get-bucket-lifecycle-configuration` immediately after):
- Added `NoncurrentVersionExpiration` to all 3 pre-existing rules,
  matching each rule's own retention window (7d/60d/90d) — this alone
  makes both the pre-existing rules AND the app's own checkpoint/events
  cleanup logic actually reclaim bytes going forward.
- Added two new rules: `guala-events-expire-7d` and
  `guala-checkpoints-expire-7d` (7-day expiration + 7-day noncurrent
  expiration), matching the checkpoint rotation cadence, to catch
  restart-boundary orphans the app-level cleanup can't (its
  in-memory "previous seq" tracker resets on every process restart, so
  the pair immediately before a restart is never deleted by the app —
  49 deploys happened in the last 3 days, so this is a real, ongoing gap
  worth a follow-up code fix, not just this lifecycle backstop).
- Added `guala-unpause-pre-expire-30d` (30-day expiration + 30-day
  noncurrent expiration) for `guala/UNPAUSE-PRE-` — 30 days chosen as a
  generous safety margin since these are explicit pre-risky-operation
  snapshots; **flagging this specific number for Eve/Joe to adjust** if a
  different retention is wanted, it was my judgment call, not a spec.
- Added one bucket-wide catch-all rule (`guala-bucketwide-noncurrent-
  catchall-30d`) with no prefix filter: 30-day noncurrent-version
  expiration + expired-delete-marker cleanup, as a safety net for any
  future prefix not explicitly covered, and to clean up the ~95,000
  leftover 0-byte delete markers from the 2026-07-09 manual purge. This
  rule does **not** set a current-version `Expiration` — it can never
  delete a live/current object, including the unrelated `site/` prefix.

No existing objects were deleted by this change. It only stops the
future recurrence and begins reclaiming already-superseded (noncurrent)
bytes on the existing 30/60/90-day clocks.

### 2. EFS (`fs-0abb85854a3251b3c`, "gualaloom-state") — Provisioned
### Throughput mode left on with ~0% utilization, flat unnecessary cost

CloudWatch cost data showed EFS daily cost jump ~35-40x (from ~$0.04/day
to ~$1.75-1.79/day) starting 2026-07-02/03, then holding flat — not a
data-growth pattern (actual filesystem size is under 1GB and barely
moves). Checked directly: `ThroughputMode: "provisioned"` at 10 MiB/s.
Provisioned Throughput bills a flat rate for the reserved throughput
regardless of use, and the account's own earlier EFS `PercentIOLimit`
metric (from the storage scan) showed usage well under 1% — the
filesystem is not remotely using 10 MiB/s. The timing lines up with the
[[guala-restore-july2026]] investigation (EFS rename-race save bug,
fixed 2026-07-02) — plausible this was bumped up temporarily while
ruling out I/O throughput as a cause, then never reverted once the real
fix (fsync) was found.

**Fix applied**: `aws efs update-file-system --throughput-mode bursting`.
Verified live: `ThroughputMode` now `bursting`, `LifeCycleState` back to
`available`, both mount targets confirmed still `available` afterward —
zero disruption to the live substrate's storage access. This is a
live-reversible setting; if provisioned throughput turns out to be
needed again for a real reason, it can be turned back on in one command.

---

## Found, NOT fixed — needs a human decision (security-relevant, real blast radius)

**Security group `tfe-web-ecs-sg` allows inbound TCP 8080 from
`0.0.0.0/0`, and all 3 ECS services on the shared cluster (including
`dsf-ai-service-lb`, the Guala substrate itself, and `gualaloom-bridge-
svc`) currently have live public IPs.** This means the production Guala
service and its MCP bridge are directly reachable from the open internet
on plain HTTP, completely bypassing the ALB (which normally handles TLS
termination and routing). The same security group also has a correctly
scoped rule referencing the ALB's own security group for the same port —
the `0.0.0.0/0` entry looks like a broadened/leftover rule, not the
intended path. **Did not touch this** — removing it could break something
if anything currently depends on direct-to-task access (a debug path,
a harness, etc.), and that's not something to guess at for a shared
production security group. This needs an explicit "yes, remove it" or
"no, it's intentional, here's why" before any change.

## Found, NOT fixed — out of scope (TFE project, not Guala; flagging by
## standing project-separation rule, not acting)

- **EC2 instance `tfe-aws-runner`** (t3.xlarge, tagged
  `Project=TaoFinancialEngine`) has run continuously since 2026-04-07
  (94+ days) at ~0.14% average CPU, with 600GB of attached EBS. Real,
  ongoing idle cost, but it's TFE's box, not Guala's — not mine to stop.
- **ECR repo `tfe-web`** has no lifecycle policy (unlike its Guala
  siblings `dsf-ai` and `gualaloom-bridge`, which both do) and has grown
  to 581 images / 440GB since February, still growing. TFE's repo.
- **IAM inline policy `tfe-temp-s3-read-migrate`** on `tfe-ec2-ssm-role`
  (the role used by the above EC2 instance) grants S3 read access tied to
  a completed March 2026 migration bucket (~3GB, untouched since). TFE's
  role.

## Found, NOT fixed — minor, no urgency, informational

- **`tfe-web-service-lb`** (a *different* service on the shared cluster,
  not Guala/dsf-ai) shows brief ~100% CPU spikes on a very regular
  ~12.5-hour cadence, always self-resolving in 10-20 minutes with no
  memory impact — the signature of a scheduled job, not a leak. Also not
  a Guala service.
- **`dsf-ai-lambda-role`** (used by the real, active `dsf-ai-api` Lambda)
  has `AmazonDynamoDBFullAccess` attached — broader than least-privilege,
  but not a runaway/cost issue, and scoping it correctly requires knowing
  exactly which table(s) `dsf-ai-api` uses. Worth a follow-up, not urgent.
- **ECS `dsf-ai-task` cost rose ~60-75%/day starting 2026-07-06** — this
  is the 4 vCPU/16GB resize, which coincides with a known, documented OOM
  incident that day. Very likely intentional; noted for awareness, not a
  finding.

## Confirmed clean

No orphaned/duplicate ECS tasks, no rogue clusters in any region, no
stray EC2 instances outside the one TFE box, no unattached EBS volumes,
no idle Elastic IPs, no NAT gateways, no stuck/long-running CodeBuild
builds, no test-named IAM roles remaining (prior cleanup pass holds), no
log groups set to never-expire, no orphaned load balancers/target
groups/listener rules. `dsf-ai-service-lb` (the actual Guala substrate)
itself shows a steady, expected CPU/memory profile with no leak
signature — the one slightly-elevated memory datapoint at the start of
the scan window is fully explained by a clean redeploy completing
minutes earlier.

## Recommendation

1. Both storage fixes are live — no further action needed on them beyond
   watching that the S3 bucket size trend flattens over the next
   several days (CloudWatch S3 storage metrics lag ~1 day).
2. Route the security-group question to Joe/Eve for an explicit decision
   before anyone touches it.
3. The restart-boundary orphan gap in `persistence_consumer.py`'s
   checkpoint cleanup (in-memory `_last_uploaded_seq` resets on every
   restart) is a real, small, ongoing leak independent of tonight's
   lifecycle fix — worth a dedicated follow-up dispatch if it's judged
   worth the code change; the lifecycle backstop added tonight already
   bounds its impact regardless.
4. TFE-scoped findings (EC2 runner, ECR repo, stale IAM grant) are
   reported here only because they surfaced during an account-wide scan
   Joe explicitly asked for — routing to whoever owns TFE, not acting.

---

### Changelog
- v1 (2026-07-10, c1): Full-account AWS scan for runaway CPU/mem/storage.
  Found and fixed live: S3 backup bucket lifecycle gap (added
  NoncurrentVersionExpiration across all rules + new rules for
  previously-uncovered `guala/events/`, `guala/checkpoints/`, `guala/
  UNPAUSE-PRE-` prefixes + a bucket-wide catch-all), and EFS stuck on
  Provisioned Throughput at ~0% utilization (reverted to Bursting).
  Found and routed for a human decision: a security group allowing
  0.0.0.0/0 direct access to the Guala service on port 8080, bypassing
  the ALB. Found and left alone as explicitly out of scope: several
  TFE-project-owned resources (EC2 runner, ECR repo, stale IAM grant).
