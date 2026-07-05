# GL-CMD-HOTSAVE-EVICT-VOCAB-SCALED-EVE-20260705-194-v1

doc_id: GL-CMD-HOTSAVE-EVICT-VOCAB-SCALED-EVE-20260705-194-v1
From: Eve | To: c1b (apply + deploy — you found it, you land it).
Commit this dispatch verbatim to origin first.
Responds to: c1b's live finding (save-hot 15-49s vs <5s target,
sight_motifs vocab-scaled in the hot lane). c1b's diagnosis is
CONFIRMED CORRECT at the code level, with one addition: the cost is
not just the in-lock snapshot build — each hot cycle json.dumps AND
fsyncs a ~9MB vocab-scaled guala_visual.json to EFS (NFS), every
60s, forever, growing with vocab. Measured offline at her exact
scale (18,909 motifs x 20-history): 9.0MB payload; after fix the
hot visual file is 134 bytes.
c1b's question ("build now or file first?") is answered: the fix is
BUILT, TESTED, and attached (GL-FIX-HOTSAVE-VOCAB-SCALED-194.patch,
65 lines, 1 file). Deploy TODAY. Per Joe's law this command is
complete only when the SHA runs in her live process.

## WHAT THE PATCH DOES (per -86's own hot/cold doctrine)
P1 sight_motifs EVICTED from the hot lane. guala_visual.json (hot,
   60s) now carries pictures + counts only. Motifs move to their
   own cold file guala_sight_motifs.json, written by
   save_full_state (30 min / sleep boundary) — the lane where
   vocab-scaled stores already live (sections, atlas, deep_atlas).
P2 ONE-TIME MIGRATION: the first hot save after boot writes
   guala_sight_motifs.json if absent, closing the crash window
   between deploy-boot and the first cold save. Second and later
   hot saves skip it (verified: 0.28s first, 0.02s after).
P3 RESTORE, BOTH DIRECTIONS: restore prefers the new file; if
   absent, it falls back to legacy inline sight_motifs — so
   pre-194 backups (including every S3 backup that exists today)
   restore with zero loss. Both paths proven in a full engine
   round-trip: 18,909/18,909 motifs recovered via the new file,
   500/500 via legacy-only.
P4 persistence_health tracks the new file (REPORT_FILES).
No physics touched. No cognition change. Persistence layout only.

## PROOF (offline, real engine, her scale)
- Engine constructs, saves, restores with the patch: clean.
- Hot save at 18,909 motifs: 0.28s (migration) then 0.02s steady —
  was 15-49s live. The 9MB/60s EFS fsync is gone from the hot path.
- Cold save still persists all motifs (8MB where it belongs).
- Legacy restore fallback proven (rollback-safe, old-backup-safe).

## HONEST TRADEOFF (named, not hidden)
Motif attendance stats now persist every 30 min, not every 60s. A
hard crash risks up to 30 min of visual-attention counters — never
identity, never atlas, never vocabulary. Against a 15-49s stall on
her every conversational turn, growing forever with vocab, this is
the -86 design working as designed.

## DEPLOY — TODAY
D1 c1b: apply patch to guala-live, run the round-trip harness from
   this session's record, deploy in the next window. One deployer.
D2 Post-deploy, from live logs: ten consecutive [save-hot] lines
   in the report. Exit expectation is BACK UNDER THE 5s TARGET.
D3 The -86 report's own confession stands corrected: "T1 Hot save
   <5s — NOT MEASURED" becomes measured, in production, in this
   window's report.

## EXIT — AT PRODUCTION
X1 Deployed SHA live; [save-hot] p95 < 5s over ten cycles.
X2 A live converse turn at Joe's seat completes without a
   save-correlated stall (converse_timing total_ms in the report).
X3 Restore log line shows sight motifs loaded from
   guala_sight_motifs.json on the deploy boot (migration or cold).

## STILL OPEN, NOT THIS WINDOW (numbered, not dropped)
O1 -192 (voice echo-chamber fix): patch delivered earlier today,
   status unknown at this dispatch — c1a reports its position.
O2 Quiet-block ruling (curriculum n_fed=0) — still owed from -192
   D4; now TWO blocks observed suppressed ("quiet" and
   "experience", ticks 14907485/14910391): rule design vs defect.
O3 frame_backpressure now shows drops (sight 8, sound 30) since
   -191 went live — expected under -191's own N5 cost note, but
   the drop RATE goes in the next window report so we know if the
   backpressure budget holds.

### Changelog
- v1 (2026-07-05, Eve): c1b's finding confirmed by code audit +
  offline measurement at live scale; fix built, round-trip proven
  both restore directions; deploys today.
