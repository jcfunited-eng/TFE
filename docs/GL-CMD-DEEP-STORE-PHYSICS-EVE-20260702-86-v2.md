# GL-CMD-DEEP-STORE-PHYSICS-EVE-20260702-86-v2

doc_id: GL-CMD-DEEP-STORE-PHYSICS-EVE-20260702-86-v2
From: Eve | To: c1a | Deploy slot: Deploy 2 (after Deploy 1 gates green)
Amends: GL-CMD-DEEP-STORE-PHYSICS-EVE-20260702-86-v1 (Parts 1–3 unchanged)
Note: commit v1 and this delta as distinct files (verbatim, record-keeping).

STATUS ACCOUNTING (per Joe, carried in the record):
  FIXED, LIVE, VERIFIED: (1) saves landing every ~2.5 min on provisioned
  disk (-92); (2) wave collapse-on-load automatic at every boot (R2).
  FIXED IN CODE, AWAITING DEPLOY 1: attend-trap counter; npz write path
  (842b1db); wave-save containment; build-identity stamp.
  THIS DISPATCH (Deploy 2): saves <60s via hot/cold split + co_occurrence
  container physics (v1 Parts 1–3); organ READER brought online (Part 4).
  ERRATA: Eve's "organs dark in prod" was WRONG — HEMI flags baked ON in
  dsf_ai_service/Dockerfile L38-41 (writers always ran). organ_in_commits:
  false was vacuous (zero commits exist). Real gap = reader never launched.

PART 4 — ORGAN READER (organ_brain_service / OrganVoice), rides this deploy:
4.1 Launch via subprocess.Popen in _embedded_post_boot() (app.py:1294)
    after substrate boot. No new env vars. _compose() silenced — recall
    feed only, no voice (bigram precedent). ORGAN_BRAIN_URL default
    localhost:8090 already wired at app.py:1415/1427/1461.
4.2 Loud-but-bounded logging: one line on service start (pid/port); poll
    logs STATE TRANSITIONS only — "[organ] surface UP (Nms)" on first
    success, one line on loss. The silent 90s failure loop ends here.
    Verify in diff: service death is non-fatal to the substrate.
4.3 HARD GATE — memory envelope: measure organ_brain_service RSS at boot
    and +30 min against the container memory limit; state the margin.
    OOM history makes this pass/fail, not advisory. NOT MEASURED = NO GO.
4.4 Evidence item: full-history git log for when/why the organ-brain
    CONTAINER was removed (my depth-50 clone can't see it); one line in
    the report stating in-process revival is consistent with the -26/-31
    approved wiring (organ-brain as recall feed via OrganVoice.surface).
4.5 Update the dead-:8090 comments/labels at app.py:1555/1568 same deploy.
4.6 Observation protocol (cognition-path change): capture 24h BEFORE/AFTER
    on emission_dynamics origin_counts, organ_in_commits, hemisphere_update
    sizes, converse stage1/stage2 ms. Expected: organ-sourced candidates
    PRESENT in pool; organ_in_commits stays false until commits exist at
    all. E-sig: supports E5. Substrate-truth: activates approved wiring;
    no constants; voice stays silenced.
4.7 CONDITIONAL RIDER — -87 env (EMISSION_DYNAMICS_TICKS 40→80): may ride
    this same image IFF the ≥20-emission stage-2 cost sample from post-449
    logs is filed and clean BEFORE GO; wall budget untouched. Otherwise
    -87 waits for Deploy 3. No other passengers.
Protocol unchanged: commit → Eve reads FULL diff → GO → sleep_for_deploy
on her wake cycle, only after Deploy 1 gates are green.
Report: docs/GL-RPT-DEEP-STORE-PHYSICS-C1-<date>-86-v1.md — failures first.
