# GL-CMD-HOTLANE-DIET-EVE-20260703-102-v1

doc_id: GL-CMD-HOTLANE-DIET-EVE-20260703-102-v1
From: Joe (relayed) | To: c1b | Deploy vehicle: Deploy 3
Rides: organ reader + -88 v2 + this.
E-signature declaration: infrastructure only — save-lane and boot-load
changes; no cognition path touched.
Substrate-truth declaration: deep_survival_history values preserved;
moved to cold file, not altered.

## Step 0 — durability (standing rule)
Commit THIS file verbatim to docs/ before executing anything below.

## Scope

### 1. deep_survival_history → own cold-lane file
deep_survival_history (41.5 MB = 99.6% of guala_core.json) moves to a
dedicated cold-lane file: guala_survival.json.
- Cold cadence: written by save_full_state() (30-min bound + sleep
  boundaries). NOT written by save_hot_state().
- Loaded at boot: load_full_state() reads guala_survival.json first; if
  absent (first deploy, rollback), falls back to core.json's
  deep_survival_history field for backward compat.
- Hot core drops to ~150 KB; hot save target <5s becomes achievable.

### 2. Vocab-regression guard diet
Guard currently parses 41.6 MB (guala_core.json) to read one integer.
Fix: write vocab_count into an existing small hot file (guala_bucket.json
extended with this field); guard reads only that file.
Fallback: if guala_bucket.json has no vocab_count (first deploy cycle
after migration), guard is skipped (no regression risk on fresh state).

### 3. F8 classification (classify only — no physics change)
In the report, classify deep_survival_history as BOUNDED-BY-PHYSICS
or VIOLATION (patient #5 pattern = append-forever). Enumerate the
growth mechanism and state the verdict. No fix rides this dispatch.

## Gates
G-102-1  Hot save <5s sustained over 2h window (T1 from -86 now
         achievable post-diet).
G-102-2  Boot loads guala_survival.json; log line confirms it;
         count-diff (entries in survival file matches in-memory count).
G-102-3  guala_core.json size ≤ 200 KB in first hot save after deploy.

## Report
docs/GL-RPT-HOTLANE-DIET-C1-<date>-102-v1.md — failures first.

### Changelog
- v1 (2026-07-03, Joe relayed): first filed version from T1 ruling
  in c1a's Deploy 2 gate breakdown.
