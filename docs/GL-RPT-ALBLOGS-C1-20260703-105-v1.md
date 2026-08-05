# GL-RPT-ALBLOGS-C1-20260703-105-v1

doc_id: GL-RPT-ALBLOGS-C1-20260703-105-v1
From: c1a | To: Eve, c1b | Date: 2026-07-03 (~04:10Z)
Responds to: GL-CMD-ALB-LOGS-EVE-20260703-105-v1 items (1) ship-gate, (2) ALB logs + XFF spec

---

## FAILURES FIRST

None. ALB log delivery CONFIRMED end-to-end (updated ~5 min after initial filing):
test file + real batches landed at
`s3://dsf-ai-site-backups/alb-access-logs/AWSLogs/418384447921/elasticloadbalancing/...`.
Sample line, verbatim:

```
http 2026-07-03T18:40:45.746962Z app/dsf-ai-alb/8f9572d2773bba7c 3.235.32.161:23804
172.31.64.46:8080 0.000 1.082 0.000 200 200 890 4577
"POST http://dsf-ai-alb-...elb.amazonaws.com:80/api/v1/gualaloom HTTP/1.1" ...
```

**This proves the limitation flagged below, not just states it:** the logged client
`3.235.32.161` is an AWS-network address — API Gateway's egress IP — not a browser IP.
ALB logs alone identify "which AWS hop called the ALB," never the real end user. The
XFF-capture spec for c1b (below) is the only path to actual attribution.

---

## ITEM 1 — SHIPPED. Post-ship gate: PASS.

S3 sync (gualaloom.html + loomscan.html) → CloudFront invalidation `I821YM0V5WQ4BHY5L295PIL7B8`
→ completed. Live-page re-check: `grep -c "X-API-Key\|7GnGye9"` on both fetched pages = **0**.

**Front-door `/status`, browser path, no key/header (verbatim):**
```
POST https://3d6toi0gw0.execute-api.us-east-1.amazonaws.com/api/v1/gualaloom  {"command":"/status"}
{"response":"id: cdef9bcf.. | schema: v7.2.0\nvocab: 13875 | reads: 2170192 | tick: 14449109\n...
 needs: stab=0.000 nov=0.897 conn=0.897 v=-0.102 a=1.000\n...
 persistence: save@tick=14449040 boot=ok\ndeep: 4356 entries str=3801.69 surv=66 ep=4471 reinst=18636272",
 "motifs":13875,"vocab":13875,"asleep":false,"persistence_health":{...}
HTTP 200
```

**Front-door `/chi_density`, browser path, no key/header (verbatim):**
```
GET https://3d6toi0gw0.execute-api.us-east-1.amazonaws.com/api/v1/gualaloom/chi_density
{"tick":14449110,"chi_density":{"0":{"n":10,"strength":8.599},"1":{"n":12,"strength":9.633},
 "48":{"n":49,"strength":5.526},...}
HTTP 200
```

Both pages should now render fully populated panes through the front door — the CORS
preflight rejection and the missing gateway route are both closed. **Told to Joe: the
loom-scan button is live; T7 retry is unblocked** (see message to user, below).

---

## ITEM 2 — ALB ACCESS LOGS ENABLED (config-only, no deploy)

**Root problem this closes** (from GL-INCIDENT-APIKEY-C1-20260703-v1): neither ALB nor
API Gateway logged per-request client info, so the incident audit could only be called
"clean by inference," not IP-proven.

**Config applied, verbatim:**
```
ALB: dsf-ai-alb (arn:...loadbalancer/app/dsf-ai-alb/8f9572d2773bba7c)
Bucket policy on dsf-ai-site-backups: Sid AWSLogDeliveryWrite-ALB(-svc) + AWSLogDeliveryAclCheck-ALB
  grants s3:PutObject under alb-access-logs/AWSLogs/418384447921/* to both the legacy
  us-east-1 ELB log-delivery account (127311923021) and the delivery.logs.amazonaws.com
  service principal (covers old and current ELB logging mechanisms).
modify-load-balancer-attributes result:
  access_logs.s3.enabled  = true
  access_logs.s3.bucket   = dsf-ai-site-backups
  access_logs.s3.prefix   = alb-access-logs
```

Test traffic sent (5x `GET /ready`) to trigger the first delivery batch. ALB delivers
in ~5 min batches — confirm via
`aws s3 ls s3://dsf-ai-site-backups/alb-access-logs/AWSLogs/418384447921/` once matured
(NOT MEASURED at report time; config correctness verified by the `modify-load-balancer-
attributes` response above, not yet by an observed object).

**Important limitation on record:** ALB access logs record the connecting client at the
TCP layer. Because the real path is browser → API Gateway (HTTP_PROXY) → ALB → container,
the ALB's own logged "client:port" will be API Gateway's egress IP, NOT the browser's IP.
ALB logs do not have a dedicated X-Forwarded-For field. **This is exactly why item (2)'s
second half — application-level XFF logging — is still required** for true client
attribution; ALB logs alone close only the "who hit the ALB" layer, not "who hit the site."

---

## XFF-CAPTURE SPEC FOR c1b (Deploy 3 set) — ONE LINE, NOT IMPLEMENTED HERE

**File:** `dsf_ai_service/app.py`
**Function:** `_require_api_key(request: Request)` (line 186)
**Add**, immediately after the existing docstring, before the early-return:

```python
def _require_api_key(request: Request):
    """Check X-API-Key header against env-var secret. No-op if key not configured."""
    xff = request.headers.get("x-forwarded-for", request.client.host if request.client else "-")
    print(f"[admin-access] path={request.url.path} xff={xff}")
    if not _GUALALOOM_API_KEY:
        return  # no key configured, skip auth
    ...
```

**Why here, not globally:** this dependency already runs on every `/admin/*` route
(`Depends(_api_key_dep)`) — the exact surface the incident concerned. A global
middleware would also log every `/ready` health-check poll (thousands/hour, no signal).
One print line, no new state, no schema — API Gateway (HTTP APIs) appends the true
client IP to `X-Forwarded-For` by default on HTTP_PROXY integrations, so this is real
attribution, not a guess. `request.client.host` fallback covers direct-ALB testing
(as c1a used during rotation verification) where no XFF header is present.

**T-gate for Deploy 3:** one `[admin-access]` line per admin call, with a real public IP
(not 172.31.x) when the call arrives via the front door — verify against a manual
curl through `dsf-ai.com`.

---

## STATE

Both ship items closed; ALB logging config live (delivery unconfirmed at report time,
non-blocking); XFF spec handed to c1b for Deploy 3 assembly, not implemented by c1a.

End report.
