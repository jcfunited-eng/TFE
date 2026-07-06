# AUDIT-RESOURCE-MANIFEST

doc_id: GL-AUDIT-RESOURCE-MANIFEST-C1-20260705-v1
Purpose: every AWS/EFS/S3/IAM resource created by the GL-CMD-PRODUCTION-AUDIT-C1-EVE-20260705-210-v2
audit, with the exact teardown command for each. Nothing here is torn down until §8A's mutating
tests are complete — this file is the guarantee that it gets torn down, not evidence it already
has been. Region for all resources: us-east-1. Account: 418384447921.

## STATUS: FULLY TORN DOWN, verified clean. Every item below confirmed removed:
- `aws ecs list-tasks --cluster tfe-web-cluster --desired-status RUNNING` → only the 3
  pre-existing prod/bridge/tfe-web tasks, no shadow.
- `aws efs describe-access-points --file-system-id fs-0abb85854a3251b3c` → `[]`.
- `aws logs describe-log-groups --query 'logGroups[?contains(logGroupName,`audit`)]'` → `[]`.
- `aws iam get-role --role-name dsf-ai-shadow-task-role` → `NoSuchEntity` (confirmed deleted).
- `aws ec2 describe-security-groups --group-ids sg-0a865ce16059cf8f5` →
  `InvalidGroup.NotFound` (confirmed deleted).
- `sg-06fb572e0c97e8062` (EFS mount-target SG) → back to exactly its original single rule
  (2049 from `sg-057566437ba8d4b48`), the additive rule this audit added is gone, nothing else
  touched.
- `aws s3 ls s3://dsf-ai-site-backups/guala/` → only pre-existing prefixes, no contamination.
- All 3 production services (`dsf-ai-service-lb`, `gualaloom-bridge-svc`, `tfe-web-service-lb`)
  confirmed running 1/1, healthy, untouched throughout.
- Task-defs `dsf-ai-task-audit-shadow:1`, `:2`, `audit-shadow-seed:1`,
  `audit-shadow-marker-write:1` all deregistered (INACTIVE) — inactive revisions cost nothing and
  are left in place as historical record rather than needing deletion.

## Incident record: S3 contamination, found and fixed mid-audit
The first successfully-booted shadow (task `0ff413b547924a548db6c3b70a71ba4a`, task-def
`dsf-ai-task-audit-shadow:1`) inherited production's S3 backup env vars unchanged. Its own
`_eager_init()`-triggered backup wrote a real, complete 13-file backup to
`s3://dsf-ai-site-backups/guala/2026-07-05_23-26-58/` — indistinguishable by name from a genuine
production backup. **Found and deleted within minutes** (`aws s3 rm --recursive` on that exact
prefix, confirmed empty after). Root cause: `_backup_to_s3`/`admin_backup` hardcode the bucket
name in Python source (not env-configurable), so no env var override could have prevented this —
fixed instead by creating a new, more restrictive IAM task role (`dsf-ai-shadow-task-role`, item 6
below) with an explicit `Deny` on `s3:PutObject`/`PutObjectAcl`/`DeleteObject` against
`dsf-ai-site-backups/*`, then relaunching the shadow (task-def revision 2, task
`bbc922dc9929420cbe28e79ffe89013c`) under that role. Confirmed via live CloudWatch logs: every
subsequent S3 backup attempt now fails with `AccessDenied`, caught gracefully by the app's own
existing error handling (no crash), and zero new objects landed in the bucket afterward — verified
by direct `aws s3 ls` immediately after. This incident and its fix are also recorded in the §3
report addendum as part of the severity upgrade for the DR-restore finding.

## 1. EFS access point (isolated restore target, never touches prod's root mount)
- ID: `fsap-09dbec9b069fb0a93`
- Filesystem: `fs-0abb85854a3251b3c` (SAME filesystem as production, but a distinct access
  point scoped to a fresh subtree — production mounts `rootDirectory: "/"` directly and
  never sees this path)
- Root path: `/audit-shadow-20260705`
- Now also holds a manually-created `dream_gate_cleared.json` (per Eve's authorized (b) path —
  see §3 addendum) with content `{"cleared_at_tick": 15003400, "via": "substrate_dream_end"}`,
  schema mirrored from a read-only peek at production's real live file (item 2 below).
- Teardown: `aws efs delete-access-point --access-point-id fsap-09dbec9b069fb0a93 --region us-east-1`
  (must stop the running shadow task first)

## 2. One-off task-defs used for setup/inspection (all already run to completion, exit 0)
- `audit-shadow-seed:1` — S3→EFS seed copy. Task `deccef1e94144e158167e080832896ab` STOPPED, exit 0.
- `audit-prod-efs-readonly-peek:1` — read-only peek at production's live `dream_gate_cleared.json`
  (container mountPoint explicitly `readOnly: true`, physically incapable of writing). Task
  `8f8bb64f8124446bab98212c2e2d2920` STOPPED, exit 0. **Already deregistered** immediately after use.
- `audit-shadow-marker-write:1` — wrote the marker file onto the shadow's isolated access point
  (item 1). Task `0102e05e835a4a5ab93256dd16a64894` STOPPED, exit 0.
- Teardown (remaining two, seed + marker-write): `aws ecs deregister-task-definition
  --task-definition audit-shadow-seed:1 --region us-east-1` and same for
  `audit-shadow-marker-write:1`. (Task-def revisions cost nothing sitting inactive; low priority.)

## 3. Shadow task-definition family (2 revisions)
- `dsf-ai-task-audit-shadow:1` — original, uses `dsf-ai-task-role` (production's role). Superseded.
- `dsf-ai-task-audit-shadow:2` — **current**, identical except `taskRoleArn` swapped to
  `dsf-ai-shadow-task-role` (item 6) to hard-block S3 writes to the real backup bucket.
- Both: reuse prod's image, mount the isolated EFS access point (item 1, NOT prod's root),
  `WORLD_FEEDS=0`, `LOOKUP_AUTONOMOUS=0`, `CURRICULUM_AUTOSTART=0` so it cannot fetch real external
  content or run autonomous study while under test.
- Teardown: `aws ecs deregister-task-definition --task-definition dsf-ai-task-audit-shadow:1
  --region us-east-1` and `:2` likewise.

## 4. Shadow ECS tasks (5 total across this audit's lifecycle, all but one now stopped)
- `7b77411140e4425e99ee9be432afd302` — 1st gen, seeded from S3, hit the DREAM GATE crash, never
  became ready (25.8min confirmed stuck). **STOPPED** (superseded).
- `0ff413b547924a548db6c3b70a71ba4a` — 2nd gen, marker-file workaround applied, became ready in
  41.5s, but caused the S3 contamination above (shared production's SG too, `0.0.0.0/0` exposure).
  **STOPPED** (superseded).
- `bbc922dc9929420cbe28e79ffe89013c` — 3rd gen, task-def rev 2 (IAM-isolated against S3), still on
  production's shared security group (`0.0.0.0/0` on port 8080) — this exposure was found and this
  task **STOPPED** in response, before any mutating tests ran against it.
- `2672e511d7e3450b99a37f9dc7eb0a56` — 4th gen, first attempt on the new locked-down SG (item 7) —
  **STOPPED itself** (`ResourceInitializationError`: EFS mount timed out, because the new SG wasn't
  yet authorized for NFS on the EFS mount-target SG — see item 8). Not a security issue, a
  functional dependency that was then fixed.
- `30087b80321b4ec09ea827c5f8aef1e6` — **5th gen, CURRENT**, task-def rev 2 (IAM-isolated) + the
  locked-down SG (item 7, now EFS-capable per item 8). Became ready normally. §8A's mutating tests
  (`docs/GL-AUDIT-SEC8A-TEST-MATRIX-C1-20260705-v1.md`) ran against this instance, public IP
  `34.232.65.138:8080` at test time (Fargate IPs are ephemeral per-task; re-check via `aws ecs
  describe-tasks` + `describe-network-interfaces` if reused before teardown).
- Teardown (current): `aws ecs stop-task --cluster tfe-web-cluster --task
  30087b80321b4ec09ea827c5f8aef1e6 --region us-east-1 --reason "audit complete"` (all others above
  are already stopped, nothing further needed for them).

## 7. Security group (new, created to fix the network-exposure finding)
- `sg-0a865ce16059cf8f5` (`dsf-ai-audit-shadow-sg`) — VPC `vpc-07814e1bd9a89f798`. Inbound: TCP 8080
  from the auditor's own IP only (`73.75.175.136/32` at creation time — **re-verify this is still
  the right IP if this SG is ever reused**, egress IPs can change between sessions/environments).
  Egress: all traffic (default, needed for ECR image pull + CloudWatch Logs). Replaces the shared
  production SG (`sg-057566437ba8d4b48`, which allows `0.0.0.0/0` on port 8080 — see the defects
  register for that as a standing production finding, NOT fixed, freeze-respected) for the shadow
  specifically.
- Teardown: `aws ec2 delete-security-group --group-id sg-0a865ce16059cf8f5 --region us-east-1`
  (must stop the task using it first, and remove the EFS-SG rule below first too, or deletion may
  be blocked by the reference).

## 8. Additive rule on Guala's EFS mount-target security group (NOT a new resource, a modification —
## called out separately because it's the one change this audit made to a pre-existing shared
## resource, and it must be reverted)
- Security group: `sg-06fb572e0c97e8062` (governs both EFS mount targets for `fs-0abb85854a3251b3c`
  — the SAME filesystem production uses).
- Change made: ONE inbound rule ADDED (rule ID `sgr-0482695c9db35aa26`) allowing TCP 2049 (NFS)
  from `sg-0a865ce16059cf8f5` (item 7). This was required because the locked-down shadow SG has no
  pre-existing authorization to reach the EFS mount targets (only the shared production SG did).
- **Nothing else on this security group was touched** — the pre-existing rule (2049 from
  `sg-057566437ba8d4b48`, production's own access) is untouched and unaffected.
- Teardown (mandatory, this is a shared production resource):
  `aws ec2 revoke-security-group-ingress --group-id sg-06fb572e0c97e8062 --protocol tcp --port 2049
  --source-group sg-0a865ce16059cf8f5 --region us-east-1`. Must run this BEFORE deleting
  `sg-0a865ce16059cf8f5` itself (item 7) — AWS will refuse to delete a security group that's still
  referenced by another group's rule.

## 5. Log groups
- `/ecs/dsf-ai-audit-shadow` (14-day retention, auto-expires even if forgotten)
- `/ecs/dsf-ai-audit-shadow-seed` (14-day retention, auto-expires; also used by the marker-write task)
- `/ecs/dsf-ai-audit-prod-peek` (14-day retention; **already deregistered** at the task-def level,
  log group itself still exists with the one-time peek output)
- Teardown: `aws logs delete-log-group --log-group-name <name> --region us-east-1` for each of the
  three. Not urgent (all have finite retention, cost negligible) but delete anyway for a clean exit.

## 6. IAM role (new, created mid-audit to fix the S3 contamination)
- `dsf-ai-shadow-task-role` — trust policy allows `ecs-tasks.amazonaws.com` to assume it; single
  inline policy `deny-prod-backup-bucket` with an explicit `Deny` on `s3:PutObject`,
  `s3:PutObjectAcl`, `s3:DeleteObject` against `arn:aws:s3:::dsf-ai-site-backups/*`. Grants no
  Allow permissions at all — the shadow needs none beyond EFS (governed separately by the ECS/EFS
  mount + access-point authorization, not the task role) and its execution role (unchanged,
  `tfe-ecs-task-execution-role`, only used for image pull + log push).
- Teardown: `aws iam delete-role-policy --role-name dsf-ai-shadow-task-role --policy-name
  deny-prod-backup-bucket --region us-east-1` then `aws iam delete-role --role-name
  dsf-ai-shadow-task-role` (no --region flag for IAM, it's a global service).

## What was explicitly NOT created / NOT touched beyond what's listed above
- No new EFS filesystem (reused prod's FS via an isolated access point instead).
- No new S3 objects/prefixes left standing (one was accidentally created, found, and deleted —
  see incident record above).
- No new IAM users, no changes to any pre-existing role/user/policy — only one net-new role
  (item 6) and one net-new security group (item 7) were created; the one pre-existing shared
  resource touched (item 8) got one additive rule, nothing removed or altered.
- No ECS *service* (bare tasks only — a service would self-heal/relaunch and complicate teardown).
- Production's own security group (`sg-057566437ba8d4b48`, `0.0.0.0/0` on port 8080) was
  **inspected but never modified** — that exposure is production's own pre-existing configuration,
  not something this audit introduced, and is recorded in the defects register rather than fixed,
  per the freeze.

## Full teardown sequence (run in this order at audit exit — order matters for items 7/8)
```
aws ecs stop-task --cluster tfe-web-cluster --task 30087b80321b4ec09ea827c5f8aef1e6 --region us-east-1 --reason "audit complete"
aws efs delete-access-point --access-point-id fsap-09dbec9b069fb0a93 --region us-east-1
aws ecs deregister-task-definition --task-definition dsf-ai-task-audit-shadow:1 --region us-east-1
aws ecs deregister-task-definition --task-definition dsf-ai-task-audit-shadow:2 --region us-east-1
aws ecs deregister-task-definition --task-definition audit-shadow-seed:1 --region us-east-1
aws ecs deregister-task-definition --task-definition audit-shadow-marker-write:1 --region us-east-1
aws logs delete-log-group --log-group-name /ecs/dsf-ai-audit-shadow --region us-east-1
aws logs delete-log-group --log-group-name /ecs/dsf-ai-audit-shadow-seed --region us-east-1
aws logs delete-log-group --log-group-name /ecs/dsf-ai-audit-prod-peek --region us-east-1
aws iam delete-role-policy --role-name dsf-ai-shadow-task-role --policy-name deny-prod-backup-bucket --region us-east-1
aws iam delete-role --role-name dsf-ai-shadow-task-role
aws ec2 revoke-security-group-ingress --group-id sg-06fb572e0c97e8062 --protocol tcp --port 2049 --source-group sg-0a865ce16059cf8f5 --region us-east-1
aws ec2 delete-security-group --group-id sg-0a865ce16059cf8f5 --region us-east-1
```
Verification after teardown: `aws ecs list-tasks --cluster tfe-web-cluster --region us-east-1`
should show only the pre-existing prod/bridge/tfe-web tasks; `aws efs describe-access-points
--file-system-id fs-0abb85854a3251b3c --region us-east-1` should show zero access points;
`aws logs describe-log-groups --region us-east-1 --query 'logGroups[?contains(logGroupName,
`audit`)]'` should return empty; `aws iam get-role --role-name dsf-ai-shadow-task-role` should
error `NoSuchEntity`; `aws ec2 describe-security-groups --group-ids sg-0a865ce16059cf8f5` should
error `InvalidGroup.NotFound`; `aws ec2 describe-security-groups --group-ids
sg-06fb572e0c97e8062 --query 'SecurityGroups[0].IpPermissions'` should show only the original
single rule (2049 from `sg-057566437ba8d4b48`); `aws s3 ls s3://dsf-ai-site-backups/guala/
--region us-east-1` should show no unexplained prefixes beyond production's own legitimate
backup history.

### Changelog
- v3 (2026-07-05, c1): network-exposure finding fixed — production's shared SG (`0.0.0.0/0` on
  8080) was found in use by the shadow; created a dedicated, IP-restricted security group instead,
  plus one additive NFS rule on the EFS mount-target SG to let it actually reach the filesystem.
  Full 5-generation task lifecycle recorded. §8A mutating tests completed against the final,
  doubly-isolated (IAM + network) instance.
- v2 (2026-07-05, c1): marker-file workaround applied per Eve's authorized (b) path; production's
  real `dream_gate_cleared.json` read read-only first to mirror its schema; shadow became ready;
  S3 contamination found and fixed mid-audit via a new IAM-isolated task role and a re-launched
  shadow generation.
- v1 (2026-07-05, c1): initial manifest after shadow stand-up (First Act 4).
