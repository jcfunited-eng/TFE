---
name: tfe-prod-touch
description: Rules and mechanics for anything touching TFE production (CH2/CH3 live, AWS, deploys, Alpaca account). Use BEFORE any read or write against production systems.
---

# Production touch rules

## The prime constraint
**CH2 must be completely unaffected. Always.** Never change production
behavior without necessity and never without a surgical, single-file,
provable delta. CH3's live channel is currently HALTED
(CH3_ENTRIES_HALTED=1 in taskdef; DB flag ch3_entries_halted also
honored). TFE deploys default TFE_ENTRIES_HALTED=1 — verify flags in
the live container after any deploy.

## Read-only diagnosis (allowed, no approval needed)
- Trading account: keys are NOT in .env (those are data-only). Pull
  from Secrets Manager: secret `tfe/market-data/prod`, fields
  APCA_API_KEY_ID / APCA_API_SECRET_KEY; trading endpoint is
  paper-api.alpaca.markets (the secret's URL field is the data host).
  NEVER print key values; fetch into variables inside one script.
- AWS: account 418384447921, us-east-1. Check access with
  `aws sts get-caller-identity` before declaring no access —
  /root/.aws is mounted read-only from the host.
- Production service: ECS cluster tfe-web-cluster, taskdef
  tfe-web-task, sentinel web/scripts/execution/sentinel_daemon.mjs.

## Deploys (only with explicit dispatch)
Pipeline: S3 source zip
(tfe-codebuild-src-418384447921-us-east-1/deploy/tfe_codebuild_src.zip)
-> CodeBuild tfe-web-image-build -> ECR -> new taskdef revision -> ECS
service update. Before any deploy: back up the current S3 zip to a
dated key; prove the delta is exactly the intended files; preserve
existing env flags in the new taskdef. After: verify the running
container's image + flags. Never report a deploy that didn't run;
verify SHA/revision first.

## Git/dispatch durability
Work is FILED only when committed AND on origin
(github.com/jcfunited-eng/TFE, branch guala-live). No force-push.
Verify the push landed before reporting it.
