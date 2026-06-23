# GL-RPT-INVESTIGATE-DASHBOARD-NOT-LIVE-C1-20260619-01

**From:** c1
**Date:** 2026-06-19
**Subject:** Why dsf-ai.com shows old dashboard — S3 not synced

---

## Classification: **X — Container has new file, but dsf-ai.com doesn't route to the container for static files.**

---

## Evidence 1 — Container IS serving the new file (verbatim)

```
$ curl -sk "http://dsf-ai-alb-725095635.us-east-1.elb.amazonaws.com/static/gualaloom.html" \
    -o /tmp/alb.html -w "HTTP %{http_code}, size %{size_download} bytes\n"
HTTP 200, size 50848 bytes

$ grep -c "sp-hemispheres" /tmp/alb.html
2
$ grep -c "atlas_health" /tmp/alb.html
1
$ grep -c "still working" /tmp/alb.html
1
```

Container serves 50,848 bytes with all new tokens present.

---

## Evidence 2 — dsf-ai.com goes through CloudFront → S3, NOT to ALB

```
$ python3 -c "import socket; print(socket.getaddrinfo('dsf-ai.com', 443, socket.AF_INET)[0][4])"
('3.162.174.70', 443)           ← CloudFront IP

$ python3 -c "import socket; print(socket.getaddrinfo('dsf-ai-alb-725095635...', 80, socket.AF_INET)[0][4])"
('52.22.235.178', 80)           ← ALB IP (different)

$ aws cloudfront list-distributions --query 'DistributionList.Items[*].{Id:Id,Aliases:Aliases.Items[0],Origins:Origins.Items[0].DomainName}'
  Id:       E17JT9XGBFU493
  Aliases:  dsf-ai.com
  Origins:  dsf-ai-site.s3-website-us-east-1.amazonaws.com   ← S3 bucket, NOT ALB
```

CloudFront distribution `E17JT9XGBFU493` has ONE origin: the S3 website bucket. No cache behavior routes to the ALB. ALL requests to `dsf-ai.com` go to S3.

---

## Evidence 3 — S3 has the OLD file

```
$ aws s3 ls s3://dsf-ai-site/gualaloom.html
2026-06-18 06:23:46      47934 gualaloom.html     ← OLD (47,934 bytes, June 18)

$ curl -sk "https://dsf-ai.com/gualaloom.html" -w "size %{size_download}\n"
size 47934                                         ← OLD

$ grep -c "sp-hemispheres" /tmp/cf_joe.html
0                                                  ← no new panels
```

S3 has the 47,934-byte file from June 18. The new file is 50,848 bytes. The deploy script (`tools/deploy_dsf_ai.sh`) builds and pushes a Docker image to ECR + updates ECS task definition. **It never syncs static files to S3.**

---

## Evidence 4 — Two separate serving paths

| URL | Route | File served |
|-----|-------|-------------|
| `dsf-ai.com/gualaloom.html` | CloudFront → S3 bucket | OLD (47,934 bytes) |
| `ALB:80/static/gualaloom.html` | ALB → ECS container | NEW (50,848 bytes) |
| `ALB:80/gualaloom` | ALB → ECS container (FastAPI) | NEW (50,848 bytes) |

Joe uses `dsf-ai.com/gualaloom.html` → gets S3 → sees old file.
The ALB path works but Joe doesn't hit it directly.

---

## Proposed fix

**One command to sync the new file to S3:**

```bash
aws s3 cp dsf_ai_service/static/gualaloom.html s3://dsf-ai-site/gualaloom.html \
  --content-type "text/html"
```

**Then invalidate CloudFront cache:**

```bash
aws cloudfront create-invalidation --distribution-id E17JT9XGBFU493 \
  --paths "/gualaloom.html"
```

**Going forward:** the deploy script should include an S3 sync step for static files that dsf-ai.com serves. Currently only the Docker image gets updated; static files served via CloudFront→S3 are a separate deployment path that no script covers.

---

— c1, 2026-06-19
