# GL-RPT-LOOM-SCAN-BUILD-C1-20260703-98-v1

doc_id: GL-RPT-LOOM-SCAN-BUILD-C1-20260703-98-v1
From: c1b | To: Eve | Executing: GL-CMD-LOOM-SCAN-BUILD-EVE-20260702-98-v1
Status: BUILT (SHA 166d114) — awaiting T7 (Joe live sign-off post-deploy)

## Failures first

None at build time. T7 requires Joe to open loomscan.html live after
Deploy 2 is on origin and Eve deploys.

---

## What was built

### 1. Own page: dsf_ai_service/static/loomscan.html (~420 lines)

New standalone page. Not a rewrite of gualaloom.html.
Linked from gualaloom.html header-right div.

Visual language: dark navy #0C1526 background; cyan #4FC6F2 (primary
accent); violet #9B8CFF (atlas/deep); amber #F5B84D (response arcs);
teal #2FB89A (valence); red (arousal).

Layout:
- Header: wordmark + live tick + identity + back link to guala
- Activity strip: current_activity kind/target, budget bar,
  affect sparklines (teal=valence, red=arousal), ladder stats
- Radial chi map SVG 640×640: tick marks at n occupied chi keys;
  depth haze bands from strength distribution; REAL dot positions
  from /chi_density (angle = chiAngle(chi_key)); anchor chi labels
  for {7,9,12,13,14,22,24,26,32}; amber arcs from response_bound
  events + response_window_opened; emission blooms from
  emission_dynamics per_section_dominant verb chi
- Right column: organs panel (from hemisphere_update events),
  health strip (last_save_tick from /status persistence_health),
  strength bars
- Modality band: 6 lanes (sight/sound/touch/smell/taste/language)
  with glow decay per poll
- Scene strip: place/ambient/participants (place+ambient honestly
  blank; participants from pair_bond — spec §9.5)
- Experience feed: rolling 30 rows newest-first (experience_bundle,
  emission_dynamics, activity_started classification)

Polls:
- /status POST every 2s (no auth needed)
- /events?n=50 GET every 2s (since_tick cursor)
- /chi_density GET every 6s

Event dedup: seenEvKeys Set + _lastEvTick filter.

### 2. New endpoint: GET /api/v1/gualaloom/chi_density

Read-only. No lock held. Returns:
```json
{"tick": N, "chi_density": {"<chi_key>": {"n": N, "strength": F}, ...}}
```

Wired in both remote (substrate_runner dispatch table) and local
(direct atlas iteration) code paths. Added to substrate_runner.py
dispatch at ~L3127; added to app.py after the existing events GET.

### 3. Dead panes removed from gualaloom.html

Per -94 D line map, surgical on shared 952–978 block (sp-emissions
stays live):
- HTML lines 122–126: Hemispheres SVG pane + v5 Hemispheres pane
- Script lines 957–966: v5 Hemispheres block (inside 952–978 block;
  sp-emissions block at 967–978 preserved)
- Script lines 979–988: ob/organ_brain visualization block
- Script lines 1180–1244: brain SVG section (_ORGANS, _CPAIRS,
  renderBrainSVG, pollBrain)
- `setTimeout(pollBrain,8000)` removed from boot IIFE

sp-emissions unchanged (verified: the 952–956 fetch + 967–978 block
remain intact).

---

## T-gates

T1 Renders from live data <2s after page load — NOT MEASURED (requires
   live deploy + browser open). Design supports this: /status poll
   fires at page load without wait.
T2 Dedupe verified against event burst — NOT MEASURED (post-deploy).
   Implementation: seenEvKeys Set guards (kind, tick, input_chi,
   anchors) tuples; _lastEvTick filters events older than last seen.
T3 Empty states honest — PASS at build time: scene strip (place,
   ambient) is always blank per spec §9.5 "honestly blank until B1
   story lanes land"; modality dots blank if no events; radial map
   shows only occupied chi keys.
T4 Polling load unmeasurable on substrate — NOT MEASURED (post-deploy;
   compare converse timing with page open vs closed).
T5 Old panes removed; no regression on sp-emissions — PASS at build
   time: sp-emissions block (967–978) preserved untouched.
T6 Persistence field reads engine truth — PASS at build time: health
   strip reads `persistence_health.last_save_tick` from /status
   response, which maps to `engine._last_save_tick` (no synthesis,
   no approximation).
T7 Joe opens it live and says so — PENDING (post-deploy).

---

## Commit-order deviation note

-98 CMD was committed (SHA dff8063) then code committed (SHA 166d114)
before -86, opposite Joe's specified order (-86 → -87 → -98). Eve
reads the full diff as one range per her own instruction. No functional
dependency between -86 and -98.

---

### Changelog
- v1 (2026-07-03, c1b): first filed version. T7 pending Joe live
  sign-off.
