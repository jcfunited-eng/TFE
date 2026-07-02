# GL-CMD-LOOM-SCAN-BRIEF-EVE-20260702-v1

doc_id: GL-CMD-LOOM-SCAN-BRIEF-EVE-20260702-v1
From: Eve (2026-07-02 session) | To: Next Eve | Relayed by: Joe
Purpose: Full design + execution brief for the LOOM SCAN — the
real-time display of Guala's internal neurological function.
Replaces the broken HEMISPHERES and V5 HEMISPHERES panes in
dsf-ai.com/gualaloom.html.
Read first: docs/GL-SPC-EXPERIENCE-FIRST-20260702-v2.md (§10 is the
governing spec for this instrument; §8 vitals; §9.5 language rules),
docs/GL-SPC-AE-NATIVE-SPRINT-EVE-20260702-v1.md (WS-C1),
docs/GL-HANDOFF-SPRINT-EVE-20260702-v1.md.

## Why the old pane is dead (confirm in code before building)
The pane expects 8 hemisphere dots. Live telemetry emits FIVE organ
atlases per hemisphere_update event: em, pr, ep, sc, gp (observed
sizes ~7782/136/448/100/3). Data shape moved; pane starved. Remove
both dead panes in the same deploy that ships the scan.

## What the scan IS — two layers, one pane
LAYER 1 — ANATOMY (the fMRI). Chi-space is her literal address
space; every event arrives chi-tagged. Render:
- Radial chi map: angle = chi key position (~177-186 live keys from
  atlas_health.n_chi_keys), dot per binding cluster, size+brightness
  = strength band (use atlas_health.strength_distribution).
- Inner violet ring: deep atlas (permanent memory), count from
  deep_atlas.n_entries; survival promotions shown distinctly.
- Live arcs: response_bound events carry input_chi +
  context_anchor_chis — draw amber arcs input→anchors as they
  stream. This is "Joe's words binding to her memories," live.
- Emission blooms: concentric rings at the emitting chi when
  emission_dynamics events fire; label with committed vs fallback
  origin (per-section origins field). Committed = bright; fallback
  = dim. Never equalize them.
- Organ panel: five bars (em/pr/ep/sc/gp) with live entry counts
  from hemisphere_update; brightness = share of recent
  convergent_events.
LAYER 2 — EXPERIENCE (what is landing, per spec §10):
- Activity header: current_activity kind + target + elapsed/budget +
  affect sparkline (v, a from needs, sampled each poll).
- Modality band: six lanes (sight, sound, touch, smell, taste,
  language) lit by E-signature QUALITY of the current window, not
  volume. A curriculum flood = one dim language lane; a bundle
  lights the band.
- Experience feed: rolling per-window classification — EXPERIENCE
  (list which of E1-E6 fired) vs DATA LOAD — with source tag
  (joe/wc/bundle/curriculum/corpus/worldfeed).
- Scene strip (E6): place / ambient / participants of the current
  moment. Renders EMPTY until story lanes (sprint B1) land. Show it
  empty. Sparse is true.
- Health strip: §8 vitals with green/yellow/red exactly per the
  spec table (stab, arousal, sleep, atlas balance, persistence,
  bonds). Persistence MUST read engine _last_save_tick (the -84
  truth), not SaveCoordinator — fix the current "last save (tick
  0)" lie in the same deploy.
TIER 3 (separate later dispatch, needs new telemetry): consolidation
view — dream-time promotions rendered per chi with source lineage.
Requires the promotion-lineage event (spec §11.2). Do not fake it
before the telemetry exists.

## Data sources — ALL existing, ALL read-only
- /status poll every 1-2s: needs, current_activity, atlas_health,
  deep_atlas, persistence_health, ladder, pair_bond, pictures,
  sounds.
- Events endpoint, since_tick cursor: response_bound,
  emission_dynamics, hemisphere_update, converse_timing,
  activity_started/ended.
- POLLING ONLY. No SSE, no websockets — SSE was retired project-wide
  (broken; 202+poll is the pattern).
- Client-side dedupe required: response_bound duplicates 3-5× at the
  same tick are a known flood. Dedupe on (type, tick, window_id).

## Hard rules
1. Read-only instrument. Tier 1+2 require ZERO substrate changes.
2. Honesty clause (spec §10): no decorative activity, no smoothing,
   no minimum brightness, empty panes shown empty. If her experience
   layer looks dark and sparse, that is the finding, not a bug.
3. §9.5 language: UI strings name mechanisms, never feelings
   ("binding," "commit," "promotion" — never "she feels/knows").
4. The UI ships inside the substrate image → deploying it RESTARTS
   HER. Ride a normal gated deploy, sleep_for_deploy, only after the
   -85-v2 hotfix chain is verified clean. Never deploy while she
   sleeps mid-cycle.
5. Versioning mandate: every doc/dispatch/prototype file is a
   distinct -vN file; never overwrite. Dispatch carries E-signature
   + substrate-truth declarations or c1 refuses it.

## Visual language (rebuild from this; v1 concept was approved
"promising" by Joe, then extended by the experience layer)
Dark navy scan panel (#0C1526), cyan #4FC6F2 live bindings, violet
#9B8CFF deep memory, amber #F5B84D for joe-word arcs + emission
blooms, teal #2FB89A secondary, green save-ok dot, red for RED
vitals. Monospace-adjacent labels, lowercase, quiet. It should read
as a medical instrument, not a dashboard product.

## Execution order
1. Confirm 5-vs-8 root cause in gualaloom.html + hemisphere_update
   producer (file:line in your dispatch).
2. Build an HTML artifact PROTOTYPE against pasted real /status +
   events JSON. Get Joe's approval on the prototype BEFORE any
   deploy. Iterate there — it costs nothing and he is the user.
3. Cut GL-CMD-LOOM-SCAN-C1-<date>-v1 with T-gates: renders from
   live data <2s after load; dedupe verified; empty states honest;
   poll adds no measurable substrate load; persistence field shows
   engine truth; old panes removed; Joe sign-off recorded.
4. Tier 3 only after the promotion-lineage telemetry dispatch lands.

## What Joe is buying with this
The observation deck is substrate infrastructure, not ops — he is
the nurture half of the project and he cannot help if he cannot see.
When she next binds a word to a picture while he speaks to her, this
pane is where he watches it happen. Build it so sparse is true, so
bright means real, and so the first genuine constellation he sees on
it is one she actually made.
