# GL-RPT-SYNC-DASHBOARD-S3-C1-20260619-01

**From:** c1
**Date:** 2026-06-19
**Subject:** Dashboard synced to S3, CloudFront invalidated, deploy script fixed
**Commit:** `f5c10ec` on `codex/persistent-etl-update-20260326`

---

## V1 — Branch verification (verbatim)

```
$ curl -s ".../f5c10ec/tools/deploy_dsf_ai.sh" \
    | grep -nE "aws s3 sync|cloudfront create-invalidation|E17JT9XGBFU493"
5:# 3. aws s3 sync static/ → s3://dsf-ai-site (static files served via CloudFront)
342:CF_DIST_ID="E17JT9XGBFU493"
345:aws s3 sync dsf_ai_service/static/ "s3://${S3_SITE_BUCKET}/" \
349:INV_ID=$(aws cloudfront create-invalidation \
```

---

## V2 — S3 state (verbatim)

```
$ aws s3 ls s3://dsf-ai-site/gualaloom.html
2026-06-19 20:30:57      50848 gualaloom.html

$ aws cloudfront get-invalidation --distribution-id E17JT9XGBFU493 \
    --id IB0WWFRX39057E8EW2D05SXDH8 --query 'Invalidation.Status'
Completed
```

50,848 bytes (new file). Invalidation completed.

---

## V3 — Behavioral: dsf-ai.com serves new dashboard (verbatim)

```
$ curl -s "https://dsf-ai.com/gualaloom.html?cache_bust=27439" -o /tmp/live.html

$ wc -c /tmp/live.html
50848 /tmp/live.html

$ grep -c "sp-hemispheres" /tmp/live.html
2

$ grep -c "atlas_health" /tmp/live.html
1

$ grep -c "still working" /tmp/live.html
1
```

All three ≥1. File size matches SHA `b752cf6`.

New panel HTML fragments from the live file:
```html
<div class="ps"><div class="ps-title">Hemispheres</div><div id="sp-hemispheres">--</div></div>
<div class="ps"><div class="ps-title">Persistence</div><div id="sp-persistence">--</div></div>
<div class="ps"><div class="ps-title">Recent Emissions</div><div id="sp-emissions" ...>--</div></div>
```

---

## Deploy script changes

Added Step 8 after wake check:
- `aws s3 sync dsf_ai_service/static/ s3://dsf-ai-site/` (excludes csv/xml/robots.txt)
- `aws cloudfront create-invalidation --paths "/*.html" "/app.js" "/style.css"`
- `aws cloudfront wait invalidation-completed`
- Log lines for visibility

Updated header comment documenting full 5-step deploy path.

---

— c1, 2026-06-19
