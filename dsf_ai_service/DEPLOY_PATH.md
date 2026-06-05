# DSF-AI (GualaLoom) Deployment Path

**Tag**: `GUALALOOM-BAND-AND-AUDIT-WC-2026-06-05`

## The mismatch that was

Prior c1 reported banner fixes, persistence, and slash commands as
"deployed." They were real locally but never reached production. TWO
causes, both found during this round:

1. **No deploy automation for the ECS container.** The main
   `tools/deploy_to_prod_with_evidence.sh` only deploys the TFE web
   app. DSF-AI was deployed manually once (task:14) and never updated.
   Fixed: `tools/deploy_dsf_ai.sh`.

2. **The HTML is served from S3, not from the container.** dsf-ai.com
   goes through CloudFront → S3 bucket (`dsf-ai-site`). The container's
   `/gualaloom` endpoint was never reachable from the public URL.
   Even if the container had the right HTML, nobody would see it.

## The actual deploy chain

There are TWO separate paths. Both must be done.

### Path A: Static HTML (gualaloom.html)

```
Change dsf_ai_service/static/gualaloom.html
    ↓
aws s3 cp dsf_ai_service/static/gualaloom.html \
  s3://dsf-ai-site/gualaloom.html --content-type "text/html"
    ↓
aws cloudfront create-invalidation \
  --distribution-id E17JT9XGBFU493 --paths "/gualaloom.html"
    ↓
Wait: aws cloudfront wait invalidation-completed \
  --distribution-id E17JT9XGBFU493 --id <invalidation-id>
    ↓
AUDIT dsf-ai.com/gualaloom.html (MANDATORY)
```

### Path B: API backend (engine, /status, /sleep, /dream, conversation)

```
Code change in dsf_ai_service/*.py
    ↓
./tools/deploy_dsf_ai.sh
    ↓
CodeBuild builds + pushes to ECR
    ↓
New task def registered, ECS service updated
    ↓
Wait for service stability
    ↓
AUDIT /status via API Gateway (MANDATORY)
```

API calls from the HTML go through:
`API Gateway (3d6toi0gw0.execute-api) → ALB (dsf-ai-alb) → ECS container (port 8080)`

## Infrastructure

| Component | Value |
|-----------|-------|
| **Static hosting** | |
| S3 bucket | `dsf-ai-site` |
| CloudFront dist | `E17JT9XGBFU493` |
| Domain | `dsf-ai.com` (aliases: `www.dsf-ai.com`) |
| **API backend** | |
| API Gateway | `3d6toi0gw0.execute-api.us-east-1.amazonaws.com` |
| ALB | `dsf-ai-alb` |
| ECR repo | `418384447921.dkr.ecr.us-east-1.amazonaws.com/dsf-ai` |
| ECS cluster | `tfe-web-cluster` |
| ECS service | `dsf-ai-service-lb` |
| Task family | `dsf-ai-task` (Fargate, 512 CPU, 1024 MiB) |
| EFS | `fs-0abb85854a3251b3c` → `/app/state` |
| Container port | 8080 |
| Log group | `/ecs/dsf-ai` |
| CodeBuild project | `dsf-ai-image-build` |
| S3 source | `tfe-codebuild-src-418384447921-us-east-1/deploy/dsf_ai_codebuild_src.zip` |

## File paths in container

| Host (repo) | Container |
|-------------|-----------|
| `dsf_ai_service/` | `/app/dsf_ai_service/` |
| `dsf_ai_service/corpus/` | `/app/corpus/` (ALSO at `/app/dsf_ai_service/corpus/`) |
| `dsf_ai_service/static/gualaloom.html` | `/app/dsf_ai_service/static/gualaloom.html` (NOT served publicly) |
| EFS mount | `/app/state/` (krimelack.json, loom.json, modal_sections.json, atlas.json, dreams/) |

## How to deploy

```bash
# Step 1: Deploy API backend
./tools/deploy_dsf_ai.sh

# Step 2: Deploy static HTML (if changed)
aws s3 cp dsf_ai_service/static/gualaloom.html s3://dsf-ai-site/gualaloom.html --content-type "text/html"
aws cloudfront create-invalidation --distribution-id E17JT9XGBFU493 --paths "/gualaloom.html"
```

Then AUDIT the live page. Every deploy must be followed by:
1. Open `dsf-ai.com/gualaloom.html` in browser
2. Check banner text
3. Check footer/command row
4. Hit /status via the chat input
5. Verify section counts match expectations

## What NOT to do

- Don't use `tools/deploy_to_prod_with_evidence.sh` for GualaLoom — that's TFE only
- Don't report "deployed" without auditing the live URL
- Don't assume CodeBuild auto-triggers — it doesn't for dsf-ai
- Don't change the HTML in the container and expect dsf-ai.com to update — the HTML is served from S3
- Don't forget CloudFront invalidation after S3 upload — otherwise the CDN serves stale content
