# DSF-AI (GualaLoom) Deployment Path

**Tag**: `GUALALOOM-BAND-AND-AUDIT-WC-2026-06-05`

## The mismatch that was

Prior c1 reported banner fixes, persistence, and slash commands as
"deployed." They were real locally but never reached production. The
cause: **there was no deploy automation for dsf-ai-service.** The
main `tools/deploy_to_prod_with_evidence.sh` only deploys the TFE
web app (`tfe-web-task`). DSF-AI is a separate ECS service that
was deployed manually once and never updated.

## The actual deploy chain

```
Code change in dsf_ai_service/
    ↓
./tools/deploy_dsf_ai.sh       ← NEW, created this round
    ↓
Docker build (dsf_ai_service/Dockerfile)
    ↓
Push to ECR: 418384447921.dkr.ecr.us-east-1.amazonaws.com/dsf-ai
    ↓
Register new ECS task definition (dsf-ai-task:N+1)
    ↓
Update ECS service (dsf-ai-service-lb on tfe-web-cluster)
    ↓
Wait for service stability
    ↓
AUDIT dsf-ai.com/gualaloom.html (MANDATORY)
```

## Infrastructure

| Component | Value |
|-----------|-------|
| ECR repo | `418384447921.dkr.ecr.us-east-1.amazonaws.com/dsf-ai` |
| ECS cluster | `tfe-web-cluster` |
| ECS service | `dsf-ai-service-lb` |
| Task family | `dsf-ai-task` (Fargate, 512 CPU, 1024 MiB) |
| EFS | `fs-0abb85854a3251b3c` → `/app/state` |
| Container port | 8080 |
| Domain | dsf-ai.com |
| Log group | `/ecs/dsf-ai` |

## File paths in container

| Host (repo) | Container |
|-------------|-----------|
| `dsf_ai_service/` | `/app/dsf_ai_service/` |
| `dsf_ai_service/corpus/` | `/app/corpus/` (ALSO at `/app/dsf_ai_service/corpus/`) |
| `dsf_ai_service/static/gualaloom.html` | `/app/dsf_ai_service/static/gualaloom.html` |
| EFS mount | `/app/state/` (krimelack.json, loom.json, modal_sections.json, atlas.json, dreams/) |

## How to deploy

```bash
# From repo root:
./tools/deploy_dsf_ai.sh
```

Then AUDIT the live page. Every deploy must be followed by:
1. Open `dsf-ai.com/gualaloom.html` in browser
2. Check banner text
3. Check footer/command row
4. Send `/status` via the input
5. Verify section counts match what seed corpus produces

## What NOT to do

- Don't use `tools/deploy_to_prod_with_evidence.sh` for GualaLoom — that's TFE only
- Don't report "deployed" without auditing the live URL
- Don't assume CodeBuild auto-triggers — it doesn't for dsf-ai
