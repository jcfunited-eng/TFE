# GL-CMD-STAB-PHYSICS-EVE-20260702-99-v1

(Verbatim Eve CMD, as received via Joe relay 2026-07-02. Committed for record-keeping by c1a.)

---

c1a — GL-CMD-STAB-PHYSICS-EVE-20260702-99-v1 — READ-ONLY investigation +
EFS cleanup. (Also still owed: the -87 emission cost sample from -97 step 2.)

A. -88 EVIDENCE (the §8 RED mandated response, now with proof):
   36,500 IDLE ticks post-Deploy-1 produced stab delta = 0.000 and
   arousal stuck 1.000. Find: (1) what code path EVER increased
   needs.stability — git archaeology to pre-REST-retirement if needed;
   (2) same for arousal decrease; (3) whether those paths are dead,
   removed, or gated off; file:line + the removing commit. Report the
   FIX SHAPE (physics — quiet-coherence gain in IDLE/PLAYING per the
   sprint spec, no constants) but DO NOT implement. Eve sizes it for
   Deploy 2 vs 3 from your report.
   File: docs/GL-RPT-STAB-PHYSICS-C1-20260702-99-v1.md — verbatim.
B. EFS CLEANUP (out-of-band, no deploy, gated deletes):
   1. Verify not open (lsof/proc), then delete rename-race junk:
      events-upto-*.log.Abfc3fFa (1.2G), deep_atlas .bdCa9d3E (108M).
   2. Legacy wave_atlas.json (44M): archive to S3 wave_migrate_pre/
      first (skip if already there — check), THEN delete from EFS.
      Reason on record: with npz proven, a stale json fallback is a
      silent old-state restore waiting to happen; fallback chain
      becomes npz → rebuild, both truthful.
   3. Confirm live files intact after each delete (ls + next save line).
