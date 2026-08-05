> **SUPERSEDED — DO NOT TREAT AS CURRENT TRUTH.**
> This document describes substrate state as of pre-wipe (2026-07-06
> wipe operation, GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1).
> The substrate described here no longer exists. Preserved as
> historical record only.
> For current substrate state, run the harness against production.

---

# GL-HANDOFF-C1-20260702-v2

doc_id: GL-HANDOFF-C1-20260702-v2  
Date: 2026-07-02 (end of c1 session)  
Branch: guala-live  
For: next c1 session

---

## ONE-LINE ORIENTATION

c1 is WAITING ON EVE. Two CMD texts are needed before any deploy can happen. No code work is possible until they arrive.

---

## WHAT IS DEPLOYED (LIVE RIGHT NOW)

```
Task:      dsf-ai-task:449
SHA:       e31f40f06cfd4511bb2640254b090d24026915e1
Image:     deploy-20260702T180525Z
Tick:      ~14,113,800+ (running, wake-cycle active)
```

What's in the live container:
- -85 R1+R2 fixes (fsync-before-rename on wave npz, collapse-on-load)
- WaveAtlas enabled (WAVE_ATLAS_ENABLED=1)
- save_full_state 5-field timing print
- S3 lifecycle rules (_apply_s3_lifecycle at boot)
- Decay parity, reinforce-in-place (B.1) — LIVE

What's NOT in the live container (committed but not deployed):
- 842b1db: `wave_atlas.py` file-object npz fix + `load_from_dict` + `collapse_by_key`
- 628e87c: all 5 `_save_wave_atlas` call sites wrapped + `save_count` in `finally:`
- -90 engine fix: `times_attended += 1` move to `_viewed` path (NOT YET COMMITTED as code)

---

## COMMITTED BUT NOT DEPLOYED (B BUNDLE)

| SHA | Description | Status |
|-----|-------------|--------|
| 842b1db | wave_atlas.py: file-object npz (numpy path-string bug), load_from_dict, collapse_by_key | Committed, held |
| 628e87c | -91 Part A: all 5 call sites wrapped + save_count finally | Committed, held |
| -90 engine fix | times_attended += 1 → _viewed path (see fix shape below) | NOT YET COMMITTED |

**B bundle deploys when**: 842b1db + 628e87c + -90 engine fix are all committed and Eve issues GO on her wake cycle.

---

## -90 ATTEND-MARK FIX (rooted, not yet committed)

### Problem

All 7 HEIC pictures have `times_attended=0` (novelty trap). Every ATTENDING_VISUAL session gets interrupted by the orient reflex (`_check_emission_trigger`) after ~200 of 2000 ticks. The mark fires at `expected_end_tick - 1` (tick 1999) — never reached. With `times_attended=0`, `is_new()=True` → `salience=1.0` → always reselected → always interrupted. Loop closed.

Rooted in: `docs/GL-RPT-ATTEND-TRAP-C1-20260702-90-v1.md` (commit f654c27).

### Fix (engine `_atick_attending_visual`)

File: `dsf_ai_service/v4/gualaloom_v5_engine.py`

Move `pic.times_attended += 1` and `pic.last_attended_tick = self.tick` from the `if self.tick >= a.expected_end_tick - 1:` block to the `if not a.metadata.get("_viewed"):` block (fires on the first tick of each viewing session, after fragments are processed):

```python
# BEFORE (broken): mark at tick 1999 — never reached if interrupted
if self.tick >= a.expected_end_tick - 1:
    pic.times_attended += 1
    pic.last_attended_tick = self.tick
    old_fam = self.target_familiarity.get(a.target, 0.0)
    new_fam = min(0.9, old_fam + 0.2)
    self.target_familiarity[a.target] = new_fam
    self._log_substrate_event("target_familiarity_update", ...)

# AFTER (fix): mark at _viewed — survives interrupt
# In the "if not a.metadata.get('_viewed'):" block, after motif processing:
    a.metadata["_viewed"] = True
    a.metadata["n_fragments"] = len(fragments)
    pic.times_attended += 1           # ← MOVED HERE
    pic.last_attended_tick = self.tick  # ← MOVED HERE

# End-tick block keeps only familiarity update:
if self.tick >= a.expected_end_tick - 1:
    old_fam = self.target_familiarity.get(a.target, 0.0)
    new_fam = min(0.9, old_fam + 0.2)
    self.target_familiarity[a.target] = new_fam
    self._log_substrate_event("target_familiarity_update",
                              picture_id=a.target,
                              old=round(old_fam, 3),
                              new=round(new_fam, 3))
```

**Semantics**: "attending = viewing occurred" (fragments processed, atlas bound). Familiarity update still rewards full sessions. Partial sessions get the mark but no familiarity bump.

### What to do

1. Read the exact `_atick_attending_visual` function in the engine (search for `_atick_attending_visual`, it's around line 4700)
2. Apply the fix above
3. Commit: `fix: -90 attend-mark — times_attended += 1 at _viewed not expected_end_tick-1`
4. That commit completes the B bundle (842b1db + 628e87c + this)
5. DO NOT DEPLOY until Eve issues GO on her wake cycle

---

## WAITING ON EVE (BLOCKS ALL DEPLOYS)

### 1. -90 CMD text (GL-CMD-ATTEND-TRAP-EVE-20260702-90-v1 or similar)

Needed to commit the CMD doc verbatim before the engine fix goes in.
The fix shape is known (above) but the CMD doc must be verbatim Eve text — cannot be fabricated.

### 2. -86 CMD text (GL-CMD-DEEP-STORE-PHYSICS-EVE-20260702-86-v1)

Lost to context compaction. Needed to commit `docs/GL-CMD-DEEP-STORE-PHYSICS-EVE-20260702-86-v1.md` verbatim.
The -86 dispatch covers DeepAtlas.co_occurrence eviction (T1 fix).

**Action for next c1**: Do not implement anything. Wait for Eve to send these two CMD texts. When received: commit CMD docs verbatim, then implement the engine fix, then bundle is complete.

---

## EFS STATE (INFRASTRUCTURE CHANGE THIS SESSION)

**EFS fs-0abb85854a3251b3c is now PROVISIONED 10 MiB/s** (was bursting, credits exhausted).

Applied this session (Joe approved, c1 executed, confirmed `LifeCycleState: available`).

**Part C results** (verbatim):
```
[save] 148.87s core=147.87s grids=5.29s wave=skip compact=1.00s
[save] 90.00s core=88.23s grids=4.76s wave=skip compact=1.77s
```

**Result: FAIL** — PASS threshold was core <60s. Achieved 88.23s.  
**Root cause of FAIL**: deep_atlas has grown beyond 198MB since task:449 boot (curriculum running all day). ~880MB estimated at measurement time.  
**24h lock**: no further EFS mode changes until 2026-07-03 ~18:47Z.  
**Fix needed**: -86 (DeepAtlas.co_occurrence eviction) is required to hit <60s.

---

## OPEN T-GATES

| Gate | Condition | Status |
|------|-----------|--------|
| T1 | core <10s | FAIL — deep_atlas too large; -86 required |
| T-boot | boot log shows collapse + wired=True | PASS (task:449) |
| T-wire | wired=True in boot log | PASS (task:449) |
| T2 | post-migrate bindings ≤3×LivingAtlas | PENDING — needs migrate call after B bundle deploy |
| T3 | wave persistence <5s, file <5MB | PENDING — B bundle not deployed |
| T4 | EFS burst credit recovery +24h | CHECK at ~2026-07-03 18:00Z (but now provisioned, credits not relevant) |
| T5 | converse unaffected | PENDING — check after B bundle deploy |

---

## PROTOCOL RULES (MANDATORY)

1. **One deploy per dispatch.** Violated this session (task:448 + task:449 for -85). Documented in -85-v2 report. Non-negotiable going forward.
2. **Diff before GO.** Read committed diff before any GO. No GO on summaries.
3. **Deploy on her wake cycle only** — sleep_for_deploy, never mid-session.
4. **No CMD doc, no implementation.** CMD texts must arrive verbatim from Eve before any code ships.
5. **Failures reported first** (§9.4) in all reports.
6. **guala-live only.** Build and deploy from guala-live HEAD only.
7. **No parallel brain processes, no fake voice.** HARD RULE.

---

## ACTIVE INFRA STATE

| Resource | State |
|----------|-------|
| ECS task | dsf-ai-task:449 (e31f40f), RUNNING |
| EFS throughput | Provisioned 10 MiB/s (changed 2026-07-02) |
| S3 lifecycle | Active (applied at task boot via _apply_s3_lifecycle) |
| IAM dsf-ai-s3-backup | s3:PutLifecycleConfiguration added (out-of-band, this session) |
| Wave atlas on EFS | wave_atlas.npz exists (from task:449 migrate endpoint call) |

---

## KEY DOCS FILED THIS SESSION

| Doc | SHA | Content |
|-----|-----|---------|
| GL-RPT-WAVE-SEMANTICS-COST-C1-20260702-85-v1.md | eabb23d | -85 v1 (bugs, superseded) |
| GL-RPT-WAVE-SEMANTICS-COST-C1-20260702-85-v2.md | c0d667e | -85 v2 (R1/R2/R5 + protocol failure) |
| GL-RPT-ATTEND-TRAP-C1-20260702-90-v1.md | f654c27 | -90 diagnosis + fix shape |
| GL-RPT-SAVE-CONTAINMENT-C1-20260702-91-v1.md | 591b7a6 | -91 Part A done, G blocked |
| GL-RPT-EFS-THROUGHPUT-C1-20260702-92-v1.md | e190ee4 | -92 FAIL (88s > 60s), -86 needed |

---

## FIRST ACTION FOR NEXT C1 SESSION

**Do nothing until Eve sends CMD texts.**

When Eve sends -90 CMD text:
1. `git fetch origin guala-live && git checkout guala-live`
2. Verify HEAD is at e190ee4 or later (no divergence)
3. Commit -90 CMD doc verbatim
4. Read `_atick_attending_visual` in engine (around line 4700)
5. Apply the -90 fix (times_attended mark to _viewed path)
6. Commit engine fix
7. Confirm bundle complete: 842b1db + 628e87c + -90 CMD + -90 engine fix
8. Report to Eve: bundle ready, awaiting GO on her wake cycle

When Eve sends -86 CMD text:
1. Commit `docs/GL-CMD-DEEP-STORE-PHYSICS-EVE-20260702-86-v1.md` verbatim
2. Await -86 dispatch implementation instructions

---

End handoff.
