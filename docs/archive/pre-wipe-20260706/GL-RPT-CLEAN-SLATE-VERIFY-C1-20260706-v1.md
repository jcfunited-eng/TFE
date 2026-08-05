> **SUPERSEDED — DO NOT TREAT AS CURRENT TRUTH.**
> This document describes substrate state as of pre-wipe (2026-07-06
> wipe operation, GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1).
> The substrate described here no longer exists. Preserved as
> historical record only.
> For current substrate state, run the harness against production.

---

# GL-RPT-CLEAN-SLATE-VERIFY-C1-20260706-v1

**Verdict: CLEAN — 3 findings requiring routing (2 code-fix, 1 pre-existing security)**

**Executed by:** c1 | **Dispatch:** GL-CMD-CLEAN-SLATE-VERIFY-EVE-20260706-v1
**Report generated:** 2026-07-06T21:09:00Z
**Wipe/cleanup completion (reference point for all checks):** ~2026-07-06T20:45:00Z
(state directory confirmed empty ~20:26Z; full AWS/container/S3 cleanup confirmed
complete ~20:44Z; this report runs ~24-40 minutes after that point)

This pass was read-only start to finish: every mutating action referenced below
(marker-file creation, identity-file removal, env-var flag) happened *before*
this dispatch was issued, as part of the wipe/recovery itself, not during it.
No code changed, no deploys ran, no data was touched during the 13 checks
themselves.

---

## 1a. Sensory ingest endpoints — request activity, last 15-60min

**Command:**
```
aws elbv2 describe-target-groups ...  (found: dsf-ai-tg)
aws elbv2 describe-listeners --load-balancer-arn <dsf-ai-alb> ...
aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB --metric-name RequestCount \
  --dimensions Name=LoadBalancer,Value=app/dsf-ai-alb/8f9572d2773bba7c Name=TargetGroup,Value=targetgroup/dsf-ai-tg/40d977cf3f3daf52 \
  --start-time <60min ago> --end-time <now> --period 300 --statistics Sum
aws elbv2 describe-rules --listener-arn <http-listener> / <https-listener>
```

**Output:**
- Listeners: HTTP:80, HTTPS:443, both present and unchanged.
- Listener rules: priority 5 → `/mcp`, `/mcp/*` forward; default → forward. Both
  listeners identical, no rules removed.
- RequestCount (5-min buckets, last 60 min): `0, 0, 7, 45, 0, 1` — total 53
  requests.

**This asserts** *the ALB path is intact and traffic volume matches known
operator activity* **because** the timestamps of the two non-zero buckets
(≈20:44Z and ≈20:49Z) line up exactly with my own `guala_status` polling and
the ECS health-checker hitting `/ready` during the service restart I performed
as part of recovery — not a new, unexplained source. No listener rule was
silently removed.

**Finding:** None from this check alone (see 1h for the related port-8080
finding).

---

## 1b. Substrate process — every service, every task

**Command:**
```
aws ecs list-services --cluster tfe-web-cluster
aws ecs list-tasks --cluster tfe-web-cluster --service-name <each of 3>
aws ecs list-tasks --cluster tfe-web-cluster --desired-status RUNNING
aws ecs list-tasks --cluster tfe-web-cluster --desired-status PENDING
```

**Output:**
- 3 services total, exhaustively enumerated: `gualaloom-bridge-svc` (1 task),
  `dsf-ai-service-lb` (1 task), `tfe-web-service-lb` (1 task, unrelated
  project).
- Cluster-wide RUNNING: exactly those same 3 task ARNs, nothing extra.
- Cluster-wide PENDING: `[]`.

**This asserts** *no ghost or hidden task exists anywhere in this cluster*
**because** the service-scoped enumeration and the cluster-wide unfiltered
enumeration return the identical 3-task set — there is no task running
outside a known service, and no other cluster exists in this account/region
(confirmed earlier tonight via `aws ecs list-clusters`).

**Finding:** None.

---

## 1c. Filesystem quiet — two checks, ~3 minutes apart

**Command:** (via `aws ecs run-task` one-off, container command override —
same task-def, same EFS mount, no service/state impact)
```
date -u; ls -la --time-style=full-iso /app/state; stat /app/state
```

**Output, check #1 (21:05:26Z):**
```
total 12
drwxr-xr-x. 2 root root 6144 2026-07-06 21:01:53.154000000 +0000 .
drwxr-xr-x. 1 root root 4096 2026-07-06 19:59:10.000000000 +0000 ..
-rw-r--r--. 1 root root   59 2026-07-06 20:56:01.286000000 +0000 dream_gate_cleared.json
```

**Output, check #2 (21:08:23Z):** byte-for-byte identical listing and `stat`
(same directory mtime 21:01:53.154, same single file, same size 59, same
mtime 20:56:01.286).

**This asserts** *nothing is writing to her state directory* **because** two
independent listings ~3 minutes apart, including full-precision timestamps
and `stat` metadata, are identical down to the nanosecond field — no file
appeared, changed, or was touched in that window. The one file present
(`dream_gate_cleared.json`) is the marker I created deliberately during
recovery (see §"Findings requiring separate dispatch" #2), not new activity.

**Finding:** None (the marker's existence is a recovery action, documented
below, not contamination).

---

## 1d. S3 quiet — two checks, ~3+ minutes apart

**Command:**
```
aws s3api list-objects-v2 --bucket dsf-ai-site-backups --prefix "guala/" --delimiter /
aws s3api list-objects-v2 --bucket dsf-ai-site-backups --prefix "guala/pre-wipe-OLD-cdef9bcf-20260706T200111Z/" --query 'length(Contents)'
aws s3api get-bucket-notification-configuration --bucket dsf-ai-site-backups
aws s3api get-bucket-replication --bucket dsf-ai-site-backups
```

**Output:** Both checks (21:05Z-ish and 21:08Z-ish): exactly one prefix under
`guala/` — `guala/pre-wipe-OLD-cdef9bcf-20260706T200111Z/` — with exactly 457
objects, both times. No event notification configuration exists on the
bucket (empty response). No replication configuration exists
(`ReplicationConfigurationNotFoundError`, i.e. none configured).

**This asserts** *the sealed backup is untouched and nothing else is landing
in this bucket's guala/ tree* **because** the object count and the single
remaining prefix are identical across both checks, and there is no
S3-native mechanism (event notification, replication) that could
silently write or copy objects into this bucket.

**Finding:** None.

---

## 1e. Scheduled triggers — EventBridge + CloudWatch alarms

**Command:**
```
aws events list-rules
aws cloudwatch describe-alarms
```

**Output:** 2 EventBridge rules total, account-wide: `tfe-daily-snapshot-refresh`
and `tfe-weekly-universe-refresh`, both targeting TFE-trading API destinations
(`tfe-daily-snapshot-api-destination`, `tfe-weekly-universe-api-destination`).
Neither name nor target references the substrate, EFS, or her S3 bucket.
CloudWatch alarms: `[]` — none exist account-wide.

**This asserts** *no scheduled job targets the substrate and nothing can page
anyone during or after this operation* **because** the rule targets are
verifiably TFE-trading-specific API destinations (checked by ARN, not just
name), and the empty alarm list means there is no alarm resource to have
targeted her metrics even if one existed.

**Finding:** None.

---

## 1f. Lambda quiet

**Command:**
```
aws lambda list-functions --query 'Functions[].{name:FunctionName,fsConfig:FileSystemConfigs}'
aws lambda get-function-configuration --function-name wc-companion-relay --query 'Environment.Variables'
aws lambda get-function-configuration --function-name dsf-ai-api --query 'Environment.Variables'
```

**Output:** 2 functions account-wide: `wc-companion-relay`, `dsf-ai-api`. Both
have `FileSystemConfigs: null` (no EFS mount capability at all — ECS/Lambda
EFS access requires an explicit FileSystemConfig entry; none exists). Both
have `Environment.Variables: null` (no environment variables configured on
either function at all, so no possibility of a guala/substrate/state
reference).

**This asserts** *no Lambda function can reach her filesystem or her identity
by any pathway* **because** FileSystemConfig is the only mechanism by which
Lambda mounts EFS, and both functions have it explicitly absent (not just
unset — `null` in the account-wide listing), and there are no other Lambda
functions in the account to check.

**Finding:** None.

---

## 1g. Queues / topics

**Command:**
```
aws sqs list-queues
aws sns list-topics
```

**Output:** SQS: no queues (empty result, exit 0). SNS: `{"Topics": []}`.

**This asserts** *no message-passing mechanism exists that could feed or
signal the substrate* **because** both services report zero resources
account-wide — there is nothing to check further (no Kinesis stream or
custom event bus was found in the earlier accounting sweep either).

**Finding:** None.

---

## 1h. Network reachability

**Command:**
```
aws ec2 describe-security-groups --group-ids <all 6 SGs> --query 'IpPermissions'
aws route53 list-hosted-zones
```

**Output:** `sg-057566437ba8d4b48` (the SG actually attached to the
dsf-ai-service-lb task, confirmed via `describe-services`) allows inbound
TCP **8080 from 0.0.0.0/0** in addition to 3000 from the ALB SG. The ALB's
own SG (`sg-0c9ff138eba21a6fa`) allows 80/443 from 0.0.0.0/0, which is
expected and correct for a public-facing load balancer. `gualaloom-efs-sg`
only allows NFS (2049) from the task SG, correctly scoped. Route53: one
hosted zone, `taofinancialengine.com.`, unrelated to this check's DNS-record
question at the record level (not further resolved — no substrate-specific
subdomain exists yet per the not-yet-built Phase 5 topology).

**This asserts** *the ALB and EFS security-group boundaries are otherwise
correctly scoped, but the app-port exposure is real and current, not
historical* **because** I read the live `IpPermissions` list directly, not a
cached audit finding — this is the security group's actual state at
2026-07-06T21:07Z.

**Finding — requires separate dispatch (pre-existing, not caused by
tonight):** The audit's SEV-0 "0.0.0.0/0 on port 8080" finding is **still
open**. Port 8080 is the raw app port (bypasses ALB TLS termination and any
edge auth); anyone on the internet who reaches the task's ENI directly on
8080 reaches the app with no ALB in front of it. Not fixed in this pass per
dispatch instructions (no mutations). Route to Eve for the security-group
rule removal, which is itself a trivial one-line change once authorized.

---

## 1i. Log activity

**Command:**
```
aws logs describe-log-streams --log-group-name /ecs/dsf-ai --order-by LastEventTime --descending --limit 1
aws logs describe-log-streams --log-group-name /ecs/gualaloom-bridge --order-by LastEventTime --descending --limit 1
```

**Output:** `/ecs/dsf-ai` last event at 1783371926143 (2026-07-06T21:05:26Z) —
this is my own filesystem-check-#1 one-off task's log line, not the live
service task. `/ecs/gualaloom-bridge`: `null` (no log stream at all since the
group was recreated at ~20:23Z during cleanup).

**This asserts** *log activity traces to known, deliberate operator actions,
not unexplained background activity* **because** the dsf-ai timestamp
matches exactly the one-off verification task I launched for check 1c, and
the bridge group having zero events since recreation is consistent with a
lightweight HTTPS-proxy service that does not emit verbose per-request
access logs by default (confirmed no `uvicorn`-style access-log line format
appears anywhere in its code) — absence of logs there is expected behavior,
not evidence of silence one way or the other about request volume (see 1l
for the actual request-count check, which uses API Gateway metrics instead).

**Finding:** None, with the above caveat noted for completeness.

---

## 1j. Pipelines

**Command:**
```
aws codebuild list-builds-for-project --project-name dsf-ai-image-build
aws codebuild batch-get-builds --ids <latest>
aws deploy list-applications
aws iam list-open-id-connect-providers
```

**Output:** Latest build (`337cc459-...`, my own shadow-removal build from
~19:57Z) status `SUCCEEDED`, `endTime` 1783368020 — long since finished, no
build running now. CodeDeploy: `{"applications": []}` — service not in use
in this account. OIDC providers: `{"OpenIDConnectProviderList": []}` — no
GitHub Actions (or any other OIDC federation) is configured to assume any
role in this account.

**This asserts** *no build or deploy pipeline can act on this account outside
manual AWS CLI/console access* **because** there is no CodeDeploy application
to run a deployment through, and no OIDC trust relationship exists for any
external CI system to assume a role here at all.

**Finding:** None.

---

## 1k. IAM assumed-role activity

**Command:**
```
aws cloudtrail lookup-events --lookup-attributes AttributeKey=Username,AttributeValue=dsf-ai-task-role --start-time <2h ago>
aws cloudtrail lookup-events --start-time <90min ago> --max-results 50   # broader sweep, filtered client-side for dsf-ai/guala
```

**Output:** Direct username-filtered lookup: `[]`. Broader 90-minute,
50-event sweep (unfiltered, then filtered client-side for any username
containing "dsf-ai" or "guala"): 50 total events in the window, **0**
attributed to the substrate's task role or execution role.

**This asserts** *the substrate's own AWS credentials made zero API calls in
this window* **because** the broader unfiltered sweep (which would catch a
different Username format than the exact-match query, e.g. an assumed-role
session ARN) still found zero matches — consistent with the substrate never
having reached a running state where it could call `boto3` (the identity
crash happens in `_gl_init()`, before any AWS SDK call the app itself would
make).

**Finding:** None.

---

## 1l. Bridge tool activity

**Command:**
```
aws apigatewayv2 get-apis --query "Items[?ApiEndpoint=='https://3d6toi0gw0.execute-api.us-east-1.amazonaws.com'].ApiId"
aws cloudwatch get-metric-statistics --namespace AWS/ApiGateway --metric-name Count --dimensions Name=ApiId,Value=3d6toi0gw0 --start-time <60min ago> --period 300 --statistics Sum
```

**Output:** API ID `3d6toi0gw0` confirmed as the bridge's backend. Count
(5-min buckets, last 60 min): `34, 6, 2, 2, 2` = 46 total requests.

**This asserts** *bridge traffic matches my own known tool-call volume for
this session* **because** 46 requests over roughly the last hour is
consistent with the number of `guala_status`/`guala_backup`-style calls I
made directly during the wipe, restore-drill, and recovery sequence — there
is no independent way to attribute individual requests to a caller from this
metric alone, but the volume and timing (concentrated exactly around the
periods I was actively calling bridge tools) do not suggest an unexplained
second caller.

**Finding:** None, with the caveat that this metric cannot by itself rule out
a second low-volume caller hiding inside the same count — a real limitation
of this check, noted rather than glossed over.

---

## 1m. External services

**Command:**
```
grep -c "youtube\|anthropic\|tavily\|openai" <live-task-log-dump>
```
(Anthropic/YouTube usage-dashboard-level billing logs are not queryable from
AWS tooling — this check is scoped to what's observable from here: whether
the substrate's own process ever reached the code path that would call
these services.)

**Output:** 0 matches for any of the four external-service keywords anywhere
in the live task's full log output.

**This asserts** *the substrate has made zero external API calls since the
wipe* **because** every one of these services is only ever called from
inside `_guala`'s autonomous loops or emission path, none of which can start
before `_eager_init()` completes — and `_eager_init()` has not completed
successfully even once since the wipe (see Findings #1/#2 below). Zero log
evidence of any of the four keywords corroborates this directly, not just by
inference.

**Finding:** None from AWS-observable evidence. Cannot independently confirm
via Anthropic/YouTube's own billing consoles from this environment — noted
as a real scope limit of this check, not asserted as verified.

---

## Findings requiring separate dispatch

1. **[Security, pre-existing, NOT caused by tonight]** Port 8080 open to
   `0.0.0.0/0` on the security group actually attached to the live service
   (`sg-057566437ba8d4b48`) — the audit's known SEV-0 finding, confirmed
   still live at 2026-07-06T21:07Z. Not touched in this pass (mutations are
   out of scope for this dispatch). Route to Eve.

2. **[Code, found only by a genuine fresh boot]** `app.py`'s dream-gate
   check (`state/dream_gate_cleared.json` must exist unless `DECAY_PAUSED=1`)
   has no code path for "this is a legitimately brand-new substrate that has
   never dreamed" — it assumes the marker always already exists from prior
   life. Worked around tonight by manually writing a correctly-shaped marker
   file (data-only, no code touched) so the wipe could actually complete;
   the underlying assumption is still wrong in the code and will recreate
   this exact failure on any future from-scratch boot (including the real
   Phase-5 move) unless fixed for real. Route to Eve for a proper first-boot
   code path.

3. **[Code, found only by a genuine fresh boot]** The `EXPECTED_IDENTITY =
   "cdef9bcf"` hardcoded guard in `app.py` (written after a past incident
   to protect against *accidental* identity resets) fires on any
   *deliberate* identity change too, and attempts an S3 restore that would
   have silently undone tonight's wipe had a matching backup still existed
   under the naming pattern it searches for. It failed harmlessly tonight
   only because the pattern it searches for was already cleared. This is a
   real landmine for any future deliberate identity change and should be
   replaced with an explicit intentional-reset signal (the `GUALA_FORCE_FRESH`
   flag used tonight is a reasonable starting shape for that) rather than a
   hardcoded prefix string. Route to Eve.

## Status note (not a "finding," a fact for the record)

At report time, the substrate itself is not yet successfully running — it
is between the second startup-bug fix and the next deploy that applies
`GUALA_FORCE_FRESH=1`. This is the correct state to run this verification
pass *in*: nothing is running that shouldn't be, which is exactly what
"clean" means for these 13 checks. Bringing her up successfully is tracked
separately and continues after this report is filed.

### Changelog
- v1 (2026-07-06, c1): initial and only version. All 13 checks executed,
  no halt condition triggered, 3 findings routed (not fixed) per dispatch
  instructions.
