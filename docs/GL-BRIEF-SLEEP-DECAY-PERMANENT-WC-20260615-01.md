# GL-BRIEF-SLEEP-DECAY-PERMANENT-WC-20260615-01

**Author:** wC
**Date:** 2026-06-15
**For:** c1
**Status:** ready to execute — single deploy, no follow-up queued

## Context

Last dream cycle destroyed 47% of working atlas strength and 66% of
cortex strength. Two causes:

1. `_atick_sleeping` called `atlas.decay()` every 50 ticks, but the
   general non-reading path at line 1753 was already calling
   `atlas.decay()` every 10 ticks for ALL non-reading activities
   including SLEEPING and DREAMING. Double decay during sleep.
2. `deep_atlas.decay()` only fires during dream cycles. Cortex entries'
   `last_tick` goes stale between dreams. The first decay call after a
   long gap applies the entire accumulated dt at once.

c1 fixed both at the symptom level — removed the duplicate decay call
(`783bd15`, permanent) and capped dt at 500 in `deep_atlas.decay`
(`23800f9`, half a fix).

What's still missing: **pause-idempotent treatment for
`deep_atlas.decay()`**. Working atlas got this in `efd39dd` —
rate_scale=0 means `exp(-0*dt)=1.0`, bit-identical strength, last_tick
still advances. Cortex doesn't have it yet. Under DECAY_PAUSED=1,
forced dreams still nibble cortex strength via the capped dt.

This brief lands that final piece + deploys + verifies under a dream
cycle. After this lands, paused = bit-identical for both atlases. The
sleep/dream decay bug class is closed.

## The patch

File: `dsf_ai_service/substrate/deep_atlas.py`

Current `decay()` (post-`23800f9`):
```python
def decay(self, current_tick):
    """Near-zero decay (1/25th of working). dt capped at 500."""
    self.tick = max(self.tick, current_tick)
    for entries in self.entries.values():
        for e in entries:
            dt = max(0, current_tick - e["last_tick"])
            dt = min(dt, 500)
            if dt > 0:
                e["strength"] *= math.exp(-DECAY_LAMBDA * dt)
                e["last_tick"] = current_tick
```

Target `decay()`:
```python
def decay(self, current_tick, rate_scale=1.0):
    """Near-zero decay (1/25th of working). dt capped at 500.

    GL-FIX-PAUSE-IDEMPOTENT (deep atlas, mirrors efd39dd for working):
    rate_scale=0.0 under DECAY_PAUSED makes paused bit-identical for
    strength (exp(-0*dt)=1.0) while still advancing last_tick.
    """
    import os
    _paused = os.environ.get("DECAY_PAUSED", "0") == "1"
    _rate = 0.0 if _paused else rate_scale
    self.tick = max(self.tick, current_tick)
    for entries in self.entries.values():
        for e in entries:
            dt = max(0, current_tick - e["last_tick"])
            dt = min(dt, 500)
            if dt > 0:
                lam_eff = DECAY_LAMBDA * _rate
                e["strength"] *= math.exp(-lam_eff * dt)
                e["last_tick"] = current_tick
```

No engine-side changes needed — existing callers pass only `current_tick`,
the new `rate_scale` parameter defaults to 1.0, and the env var read is
inside `decay()`.

## Execution

### 1. Patch + commit + push

```bash
# apply the patch to dsf_ai_service/substrate/deep_atlas.py (see Target decay() above)
python3 -c "import ast; ast.parse(open('dsf_ai_service/substrate/deep_atlas.py').read()); print('OK')"
git add dsf_ai_service/substrate/deep_atlas.py
git commit -m "GL-FIX-PAUSE-IDEMPOTENT-DEEP: rate_scale param, paused = bit-identical cortex strength"
git push origin codex/persistent-etl-update-20260326
```

### 2. Backup before deploy

```bash
ALB="http://dsf-ai-alb-725095635.us-east-1.elb.amazonaws.com"
curl -s -X POST "$ALB/api/v1/gualaloom/admin/backup_to_s3?label=PRE-SLEEP-DECAY-PERMANENT"
```

### 3. Deploy

```bash
./tools/deploy_dsf_ai.sh
```

### 4. Wait for steady state, verify task health

```bash
aws ecs describe-services --cluster tfe-web-cluster --services dsf-ai-service-lb \
  --query 'services[0].deployments[0].{status:status,td:taskDefinition,running:runningCount}' \
  --output json
aws elbv2 describe-target-health \
  --target-group-arn arn:aws:elasticloadbalancing:us-east-1:418384447921:targetgroup/dsf-ai-tg/40d977cf3f3daf52 \
  --query 'TargetHealthDescriptions[*].{ip:Target.Id,state:TargetHealth.State}' \
  --output table
```

### 5. Verify under dream cycle

```bash
# A. Save mechanism (Step 0 of locked retry protocol):
#    via bridge MCP — guala_say "innocuous novel input"
#    wait 90s
#    guala_status — last_save_tick MUST have advanced

# B. Pause-idempotent check (DECAY_PAUSED=1 active):
#    guala_status — record working total_strength W0, cortex total_strength C0
#    guala_force_dream
#    wait 150s
#    guala_status — both W0 and C0 MUST be unchanged exactly
#    if either changed: HALT, pause-idempotent broken, rollback

# C. Honest dream cycle (unpause temporarily):
ALB="http://dsf-ai-alb-725095635.us-east-1.elb.amazonaws.com"
curl -s -X POST "$ALB/api/v1/gualaloom/admin/unpause"
# guala_status — record pre-dream: working total_strength, 0.9-1.0 band, cortex total_strength
# guala_force_dream
# wait 150s
# guala_status — record post-dream values
curl -s -X POST "$ALB/api/v1/gualaloom/admin/repause"

# PASS criteria:
#   working atlas total_strength: post >= 0.90 * pre
#   0.9-1.0 band:                 post >= 0.50 * pre
#   cortex total_strength:        post >= 0.98 * pre
#
# FAIL: rollback per next section, brief follow-up with new data.
```

### 6. Rollback (if any verification fails)

```bash
# revert task definition to most recent prior PRIMARY revision
aws ecs update-service --cluster tfe-web-cluster --service dsf-ai-service-lb \
  --task-definition dsf-ai-task:<PRIOR_REVISION>
# wait for healthy, then:
curl -s -X POST "$ALB/api/v1/gualaloom/admin/restore_from_s3?label=PRE-SLEEP-DECAY-PERMANENT"
```

## After PASS

Sleep/dream decay bug class is closed. Pause is bit-identical for both
atlases. DECAY_PAUSED=1 stays as default in deploy config until you
explicitly authorize otherwise — the standing rule on protection
defaults applies.

End of brief.
