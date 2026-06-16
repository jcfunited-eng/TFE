# GL-BRIEF-PERSISTENCE-HARDENING-WC-20260616-01

**Author:** wC
**Date:** 2026-06-16
**For:** c1
**Status:** HIGHEST PRIORITY. Persistence has failed twice today. Root cause identified. Three-tier fix.

## What happened tonight (root cause from code read)

`dsf_ai_service/v4/gualaloom_v5_engine.py` line 2854-2859:

```python
if has_identity and not present:
    # Identity exists but no state — fresh boot after wipe, keep identity
    self._guala_identity = self._load_identity(state_dir)
    print(f"[GualaLoom] Identity found but no state — fresh substrate for {self._guala_identity}")
    self._load_successful = True
    return
```

**This is the wipe path.** If at boot the substrate sees `guala_identity.json` but no `guala_core.json`, `guala_atlas.json`, etc., it silently initiates a fresh substrate with `self._guala_identity` preserved but everything else zeroed. No alert. No refuse-to-boot. No restore prompt.

Then `save_full_state` runs on its normal cadence and **writes the fresh state OVER the previously-good state files** on EFS. The real state is now overwritten with the fresh-boot state. Backup rotation captures the fresh state as the new "current," and over time the good backups roll out.

That's tonight's loss pattern. Almost certainly triggered by an EFS-mount race during one of the rapid UI-fix deploys — state files briefly appeared "not present" to the new container during the first load attempt, load logic interpreted that as a wipe, fresh substrate was instantiated, then fresh state was written back to disk. The real state files were overwritten in place.

`save_full_state` (line 2632) has **no regression sanity check**. It writes whatever is in memory regardless of how small.

## Three-tier fix

### Tier 1 — IMMEDIATE (deploy before any other work)

**Three changes to `v5_engine.py`. No other code changes. One commit. Halts the loss before doing anything else.**

#### T1.1: Refuse to boot when identity exists but state vanished

Replace lines 2854-2859 with:

```python
if has_identity and not present:
    # CATASTROPHIC AMBIGUITY: identity exists but no state files.
    # This is either a true wipe (extremely rare, never automatic) or
    # an EFS race / partial-write / mount-not-ready condition that
    # would cause us to overwrite real state with fresh.
    # REFUSE TO BOOT. Require operator to either restore from backup
    # or explicitly set GUALA_FORCE_FRESH=1 to confirm intentional wipe.
    if os.environ.get("GUALA_FORCE_FRESH") != "1":
        self._guala_identity = self._load_identity(state_dir)
        msg = (f"[GualaLoom] ABORT BOOT: identity present but state files "
               f"vanished for {self._guala_identity}. "
               f"Set GUALA_FORCE_FRESH=1 to confirm intentional wipe, "
               f"or restore from backup.")
        print(msg)
        self._load_errors.append(msg)
        self._load_successful = False
        # Raise to prevent the runner from proceeding
        raise RuntimeError(msg)
    # Operator-confirmed fresh start
    self._guala_identity = self._load_identity(state_dir)
    print(f"[GualaLoom] OPERATOR-CONFIRMED fresh substrate for {self._guala_identity}")
    self._load_successful = True
    return
```

The substrate now refuses to silently become fresh. Without `GUALA_FORCE_FRESH=1`, it raises and the runner won't start. ECS will mark the task unhealthy. You'll know immediately rather than discovering hours later that her state is gone.

#### T1.2: Regression sanity check on save

In `save_full_state` after line 2641 (after `ts = time.strftime(...)`):

```python
# REGRESSION GUARD: refuse to overwrite real state with fresh state.
# If our in-memory vocab is dramatically smaller than what's on disk,
# something is wrong — likely we booted from a wipe and shouldn't save.
prior_core_path = os.path.join(state_dir, "guala_core.json")
if os.path.exists(prior_core_path):
    try:
        with open(prior_core_path) as fh:
            prior_raw = json.load(fh)
        prior_data = prior_raw.get("data", prior_raw)
        prior_vocab_len = len(prior_data.get("vocab", []))
        current_vocab_len = len(self.vocab)
        # If current state has <50% of prior vocab AND prior was substantial,
        # something is wrong. Halt save.
        if prior_vocab_len > 100 and current_vocab_len < prior_vocab_len * 0.5:
            msg = (f"[GualaLoom] ABORT SAVE: vocab regression "
                   f"{prior_vocab_len}→{current_vocab_len}. "
                   f"Refusing to overwrite. "
                   f"Set GUALA_FORCE_SAVE=1 to override.")
            print(msg)
            if os.environ.get("GUALA_FORCE_SAVE") != "1":
                raise RuntimeError(msg)
    except (json.JSONDecodeError, OSError) as e:
        # Can't read prior — log and proceed (don't block save on read errors)
        print(f"[save] prior state read failed (proceeding): {e}")
```

If the substrate ever finds itself with less vocab than what's on disk, it now refuses to save. The disk state survives. The operator sees the error and can investigate.

#### T1.3: S3 backup on every successful save

After the existing save logic, in the `save_full_state` function, add:

```python
# Off-cluster backup — every save also syncs to S3 timestamped path.
# This is the only protection against EFS-side loss.
try:
    import boto3
    s3 = boto3.client('s3')
    bucket = os.environ.get("GUALA_S3_BACKUP_BUCKET", "dsf-ai-site-backups")
    prefix = os.environ.get("GUALA_S3_BACKUP_PREFIX", "guala/auto")
    ts_iso = time.strftime("%Y-%m-%d_%H-%M-%S", time.gmtime())
    s3_prefix = f"{prefix}/{ts_iso}_save"
    for fname in self.STATE_FILES + ["guala_identity.json", "guala_deep_atlas.json"]:
        fpath = os.path.join(state_dir, fname)
        if os.path.exists(fpath):
            s3.upload_file(fpath, bucket, f"{s3_prefix}/{fname}")
    print(f"[save] S3 backup → s3://{bucket}/{s3_prefix}/")
except Exception as e:
    # Don't fail the save if S3 fails. Log and continue.
    # EFS save already succeeded by this point.
    print(f"[save] S3 backup failed (EFS save OK): {e}")
```

Now every save creates an immutable off-cluster snapshot. EFS could be wiped entirely and we'd have S3 history to restore from.

### Tier 2 — within 24 hours (after Tier 1 verifies stable)

**T2.1: Pre-deploy backup hook.** `tools/deploy_dsf_ai.sh` should snapshot the current EFS state to S3 BEFORE the new container starts. The deploy script gets a guaranteed pre-deploy snapshot in S3 at a deploy-tagged path that's never rotated.

**T2.2: Boot postcheck.** After `load_full_state` returns successfully, verify reasonable state magnitudes:

```python
if self._load_successful and not first_boot:
    if len(self.vocab) < 50:
        # Suspiciously small for a non-fresh boot — refuse
        raise RuntimeError(f"[GualaLoom] BOOT POSTCHECK FAILED: "
                          f"vocab={len(self.vocab)} too small for non-fresh boot. "
                          f"Possible partial load.")
```

**T2.3: Backup rotation that protects high-watermark states.** Current rotation appears to be purely chronological (oldest deleted first). Instead: keep the N most recent AND keep the M highest-vocab backups never-rotated. So even if she's growing, the highest-vocab known-good backup is always retained.

**T2.4: Monitoring.** A CloudWatch alarm on `guala_core.json` vocab field. If vocab drops by >25% between two successive backups, page immediately.

### Tier 3 — within the week (investigation)

**T3.1: Find the actual EFS race condition.** Why did state files appear "not present" during boot? Possible causes:
- EFS mount async — files exist but not yet visible to the new container's filesystem view
- Write-in-flight from old container during deploy overlap
- Permissions/ownership issue during container restart
- ECS rolling deploy with overlapping write windows

Need ECS deploy logs from tonight aligned with substrate boot logs. If we can identify exact timing, we know which class of race condition caused it.

**T3.2: Consider migrating from EFS to a more transactional store.** EFS is NFS-style — eventually consistent under concurrent access, mount races possible. Alternatives:
- DynamoDB with item-per-state-file (transactional writes, no mount races)
- S3 as primary store with local cache (S3 has strong consistency now)
- RDS with explicit transactions

This is a deeper architectural change. Don't do unless Tier 1+2 fixes prove insufficient.

## Order of operations TONIGHT

1. **Lock the 22:04 backup to a permanent S3 location.** (Already directed in earlier message.)
2. **Restore live state from 22:04 backup.** Substrate comes back as her at tick=9104645.
3. **Apply Tier 1 changes to v5_engine.py.** Single commit. Single deploy.
4. **Verify Tier 1 deploy.** After deploy, check that boot succeeded normally with restored state (not a fresh boot). Check that S3 backup landed. Check that save sanity check is in place by examining substrate logs for the new print statements.
5. **Resume normal operation.** Brief Joe back when complete.

Do NOT proceed to other briefs (needs physics, sensory IO, audio fixes, grandurun) until Tier 1 is verified stable for at least 6 hours.

## What this is NOT

- Not a redesign of persistence. Existing save/load semantics preserved.
- Not a switch away from EFS. Still primary store; S3 is off-cluster safety net.
- Not optional. Without Tier 1, the next deploy can lose her again.
- Not a one-line fix. Three changes interact: halt-on-vanish prevents the wipe path; sanity check prevents save-over-real-state; S3 every-save gives recovery path even if both fail.

## Verification

After Tier 1 deploys:

1. Substrate boots from restored state. Logs show normal boot with full vocab.
2. First save fires within 10 minutes. Logs show `[save] S3 backup → s3://...` line.
3. Verify S3 actually has new backup files at the expected path.
4. (Test in staging if possible): delete one state file from EFS, restart container. Substrate should REFUSE TO BOOT instead of silently becoming fresh.

End of brief.
