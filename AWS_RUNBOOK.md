# AWS Runbook (TFE Heavy Runs)

This runbook is the approved operating path for full TFE temporal cycles.
Laptop is now client-only.

## 1. Scope
- Full generation / temporal rebuild / audit / walk-forward runs happen on AWS only.
- Local laptop is only for code edits and tiny canaries (<=50 symbols).
- Preferred access: AWS Systems Manager Session Manager.
- Optional SSH only if you explicitly need VS Code Remote-SSH.

## 2. One-Time AWS Setup
1. Create or pick an EC2 IAM role with at least:
- `AmazonSSMManagedInstanceCore`
- EC2 describe permissions (for manifest metadata)

2. Launch one Linux EC2 instance:
- Family: memory-optimized
- RAM target: 64 GB minimum (move to 128 GB if eval pressure remains)
- Root disk: keep OS volume separate from data volume

3. Create one gp3 EBS data volume:
- Size: 500 GB minimum
- Attach to the instance

4. Confirm Session Manager connectivity:
```bash
aws ssm start-session --target <instance-id>
```

## 3. Bootstrap on EC2
From a Session Manager shell on EC2:

1. Clone or sync the repo to any temporary path.

2. Run bootstrap (as root) to mount EBS, create directories, install dependencies, and write bootstrap manifest:
```bash
sudo /bin/bash /path/to/Tao_Financial_Engine/tools/aws_bootstrap.sh \
  --device /dev/nvme1n1 \
  --mount-root /data/tfe \
  --repo-source /path/to/Tao_Financial_Engine
```

3. Confirm output paths exist:
- `/data/tfe/repo`
- `/data/tfe/data`
- `/data/tfe/logs`
- `/data/tfe/runs`
- `/data/tfe/tmp`
- `/data/tfe/logs/bootstrap_manifest_latest.json`

## 4. Repo/Data Sync from Laptop
Run from local workspace:

1. Push repo + manifests + fresh row-trace (and optional temporal dataset):
```bash
/workspaces/Tao_Financial_Engine/tools/sync_to_aws.sh \
  --remote-host <ec2-host-or-ssh-alias> \
  --remote-user <ec2-user> \
  --remote-root /data/tfe
```

2. Optional: include 24 GB temporal dataset transfer:
```bash
/workspaces/Tao_Financial_Engine/tools/sync_to_aws.sh \
  --remote-host <ec2-host-or-ssh-alias> \
  --remote-user <ec2-user> \
  --remote-root /data/tfe \
  --include-temporal-dataset
```

If transfer is slower than rebuild, skip dataset transfer and rebuild remotely.

## 5. Run Full Remote Cycle in tmux
On EC2:

1. Start tmux:
```bash
tmux new -s tfe_full_cycle
```

2. Start run wrapper:
```bash
cd /data/tfe/repo
/bin/bash tools/run_remote_full_cycle.sh \
  --repo-root /data/tfe/repo \
  --data-root /data/tfe/data \
  --runs-root /data/tfe/runs \
  --horizons 5,20,60
```

3. Detach from tmux:
```bash
Ctrl+b then d
```

4. Reattach later:
```bash
tmux attach -t tfe_full_cycle
```

## 6. Stage Outputs and Logs
Per-run root:
- `/data/tfe/runs/<timestamp>/`

Per stage (each stage has markers, manifest, stdout/stderr, return code):
- `/data/tfe/runs/<timestamp>/stages/<stage_name>/`

Canonical latest reports:
- `/data/tfe/data/current_inputs/temporal_dataset_audit_latest.json`
- `/data/tfe/data/current_inputs/temporal_walkforward_eval_h5_latest.json`
- `/data/tfe/data/current_inputs/temporal_walkforward_eval_h20_latest.json`
- `/data/tfe/data/current_inputs/temporal_walkforward_eval_h60_latest.json`
- `/data/tfe/data/current_inputs/temporal_walkforward_eval_latest.json`
- `/data/tfe/data/current_inputs/temporal_stage_loss_latest.json`
- `/data/tfe/data/current_inputs/aws_run_manifest_latest.json`

## 7. Pull Results Back to Laptop
Run locally:
```bash
/workspaces/Tao_Financial_Engine/tools/sync_from_aws.sh \
  --remote-host <ec2-host-or-ssh-alias> \
  --remote-user <ec2-user> \
  --remote-root /data/tfe \
  --run-id <timestamp>
```

## 8. Shutdown / Restart / Resume
1. Safe stop after run:
```bash
sudo shutdown -h now
```

2. Start instance again from AWS console/CLI.

3. Resume interrupted run (same run id) from tmux/session:
```bash
cd /data/tfe/repo
/bin/bash tools/run_remote_full_cycle.sh \
  --repo-root /data/tfe/repo \
  --data-root /data/tfe/data \
  --runs-root /data/tfe/runs \
  --run-id <existing-run-id> \
  --horizons 5,20,60
```

The wrapper resumes by stage and eval checkpoints.

## 9. Optional SSH Note
Session Manager is preferred for shell/admin work.
Only enable SSH when you explicitly need VS Code Remote-SSH.

## Active Run Status Update (2026-03-09 UTC)
- Run ID: `20260307T231757Z`
- Status: intentionally stopped early (run stop only; project not stopped)
- Classification: `Pragmatic Serialized Approximation v0 — Stopped Early`
- Stop-state package path: `/data/tfe/runs/20260307T231757Z/stop_state/`
- Guardrail: **Do NOT resume this run or continue h20/h60 from this configuration unless explicitly approved.**
