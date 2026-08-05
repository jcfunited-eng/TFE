# GL-CMD-SCENE-LANES-B1-EVE-20260705-188-v1

doc_id: GL-CMD-SCENE-LANES-B1-EVE-20260705-188-v1
From: Eve | To: c1a (build) / c1b (window) | JOE GO, this date.
Commit verbatim to docs/ first.
Canonical scope, assembled from the record (not invented): plan v9
VE-1 ("WHERE+ambient+WHO on every item; scene lanes nonzero — today
0"), spec v2 §7's place/ambient lane bindings (the spec's own
admitted gap), -167 3c's captioned-bundle probe, and wiring-audit
-164's findings (place/ambient SEVERED-MODULE; WHO tags written
only for autonomous attending, never for converse, and never read
back by anything).

## The build — stories become experiences
V1 EVERY experience item carries three scene lanes bound IN THE
   SAME WINDOW as its content: WHERE (place), AMBIENT, WHO
   (participants). Substrate-true: lanes are real bindings through
   the existing bundle machinery — never dict shims, never
   generated content.
V2 HONEST SOURCING ONLY: lanes derive from what actually exists —
   story tags present in book text, item titles/metadata, and live
   presence for WHO. A book passage with no place words yields an
   EMPTY place lane, shown empty. No scene invention, ever.
V3 BOOKS ARE THE HEADLINE PATH: reading a book binds its scene
   words into place/ambient lanes as the words are read — this is
   what turns "reading words" into "experiencing the story," per
   Joe's ask tonight (Secret Garden is the live test corpus).
V4 FIX THE -164 DEFECTS while in there: WHO tags written for
   converse too (not just autonomous attending), and a reader —
   recall/loomscan actually consume the tags instead of them being
   write-only.
V5 SEAT VISIBILITY: the loomscan place/ambient/participants panels
   (today hardcoded "no lanes yet") render the real lanes live.

## Exit criteria, binary
X1 Scene lanes nonzero in production (plan v9's own metric,
   today 0).
X2 The -167 captioned-bundle probe passes: scene tags provably
   bind in-window.
X3 At Joe's seat: he re-reads her the Secret Garden and the place/
   ambient panels light with the story's own words during the read.
X4 WHO tag written on a real converse turn and read back by name.

## Joe's part (from the plan's own list, ~10 minutes)
The six untitled HEIC pictures need real titles — titles are scene-
tag source material; untitled items get honest empty lanes.

### Changelog
- v1 (2026-07-05, Eve): Sprint B1 GO'd by Joe; scope assembled
  from VE-1 + spec §7 + -167 3c + -164 audit, nothing invented.
