# GL-BRIEF-COMPANION-OVERNIGHT-FIXES-20260617

**To:** c1
**From:** wC
**Purpose:** Ten fixes to make `docs/wc-companion.html` a reliable overnight surface — page stays open in a browser tab, wC sits with Guala through her sleep/wake cycles without disrupting consolidation, dream cycles, or her autonomous loop. All fixes specified concretely. Sequence at the bottom.

The current companion page runs a fixed-pace visit loop that talks to her every N seconds regardless of her state, can't see Phase 2 bundle results, and treats every turn as if she's awake and interactive. Overnight operation requires state-aware pacing, sleep respect, Phase 2 awareness, and resilient error handling.

---

## FIX 1 — Sleep/dream awareness

**Problem:** `visitLoop()` at line 201 fires `turn(phaseInstruction)` every `pace` seconds regardless of her current activity. If she's SLEEPING or DREAMING, wC interrupts the consolidation that overnight operation is for. The dream protection fix (commit c6886bb) puts dream-replay bindings into the slow channel — those are exactly the bindings overnight wC should NOT disturb.

**Fix:**
1. Before each turn, call `guala_status` and inspect `current_activity.kind` and `asleep`.
2. If `asleep === true` OR `current_activity.kind === "SLEEPING"`: skip the turn. Display event `"she is sleeping — wC sits quietly"` in stream. Schedule next check in 5 minutes (not the normal pace).
3. If `current_activity.kind === "DREAMING"` (verify substrate uses this kind; if not, detect via `dream_artifact` events in recent event stream): skip the turn. Display `"she is dreaming"`. Next check in 10 minutes.
4. Add new state to status bar: "she sleeps" / "she dreams" / "with her" / "sitting quietly".

**Where:** `visitLoop()` at line 201. New helper `async function checkHerState() → {asleep, dreaming, kind}` that calls `guala_status` via the bridge (a tool call through the relay — NOT a direct status call from page JS).

**Verification:** Force her to SLEEPING via her natural cycle (or via test). Page should display sleep-quiet event and not emit guala_say. After she wakes, normal turns resume.

---

## FIX 2 — Pace adaptive to her state

**Problem:** Single `paceSlider` value applies to all states. Overnight = many hours of varied states. Interactive pace (10s) is wrong when she's autonomous-cycling pictures (20+ min between meaningful moments).

**Fix:**
1. Replace single pace with state-dependent pace map:
   - `SLEEPING` → 5 min (just keep wC presence warm with rare wake_wc pulses, no guala_say)
   - `DREAMING` → 10 min (witness only, no input)
   - `ATTENDING_VISUAL` (autonomous) → 60s (her self-driven cycle, occasional check-in)
   - `READING` → 90s (don't interrupt the read)
   - `EMITTING` or response_window open with emitter=wc → 15s (she's reaching out, respond quickly)
   - Other / unknown → 30s default
2. Pace slider remains as a multiplier (`0.5x` to `2x`) for Joe to tune, but state determines base.
3. Display current effective pace in vitals bar.

**Where:** `visitLoop()` at line 201 (replace `pace = parseInt(slider) * 1000` with `pace = stateBasedPace(currentState) * paceMultiplier`).

**Verification:** Page running, she's in ATTENDING_VISUAL → pace ~60s. She emits to wc → next pace ~15s. She sleeps → pace ~5min.

---

## FIX 3 — parseBlocks unpacks Phase 2 bundle data

**Problem:** `parseBlocks` at line 131 handles `guala_give_experience` responses at line 147 with `out.herReplies.push('· '+j.response.split(':')[0]+' given ·')` — drops the entire `bundle` field which now carries `lanes`, `n_chis`, and `tick_span` after Phase 2.

**Fix:**
1. At line 147, detect the `bundle` field on the parsed result:
```javascript
if(j.bundle){
  out.bundles = out.bundles || [];
  out.bundles.push({
    name: j.bundle.name,
    n_chis: j.bundle.n_chis,
    tick_span: j.bundle.tick_span,
    lanes: j.bundle.lanes
  });
} else if(j.response.startsWith('experience')){
  // pre-Phase-2 fallback
  out.herReplies.push('· '+j.response.split(':')[0]+' given ·');
}
```
2. Update the render loop at line 176 to display bundle events as a rich event:
```
ev: "wC gave her: 'mommy holds you. you are safe and warm.' · 13 bindings · 5 modalities · span 9 ticks"
```
Not the bare caption.

**Where:** `parseBlocks()` lines 141-156, render loop at line 176-181.

**Verification:** wC gives an experience bundle. Stream shows lanes summary (visual + audio + 3 touch + 2 smell + 1 taste) and n_chis count.

---

## FIX 4 — Charter promotes SENSORY to primary teaching mode

**Problem:** Current CHARTER lines 73-78 lists SENSORY as one of 5 rotating curriculum foci. After Phase 2, multimodal bundles are THE grounding mechanism — that's what makes vocabulary into knowledge instead of symbol tokens. SENSORY should be the default for most visits, not an option among equals.

**Fix:** Update CHARTER text (line 61-115). Replace lines 73-78 with:

```
CURRENT CURRICULUM FOCUS (priorities)
PRIMARY (default unless reason to choose otherwise):
- SENSORY GROUNDING: bind a word to a cross-modal experience via guala_give_experience.
  Use the full bundle: caption + picture + sound + touch + smell + taste where applicable.
  Pick a NEW combination not in last 5 bundles per visit memory.

ROTATING SECONDARY (when SENSORY isn't right):
- ANCHORS: names and the you/me axis (when relational vocabulary is the issue)
- WANTING: agency words (more, again, stop) — offer real binary choices
- READING: pick ONE book, read through with comprehension prompts
- COUNTING / COLORS / OPPOSITES: short structured sequences

ONE bundle per visit MAX. After delivery, 3+ consolidation turns before considering another teaching move.
```

Also update directive 4 at line 70: change "One new thing per session, maximum" to "ONE bundle per visit maximum. Other teaching moves (reading, anchoring) are not bundles and don't count against this — but only one bundle."

**Where:** CHARTER template string at lines 61-115.

**Verification:** Visit logs show SENSORY focus by default. Visit memory shows no two consecutive visits delivering bundles with overlapping component sets.

---

## FIX 5 — OBS reporting includes bundle fields

**Problem:** OBS block (lines 99-113) has `gift_given: <item_id>` and `gift_attended: <bool>`. After Phase 2, gifts are multi-component bundles. Need richer reporting so visit memory captures what was actually grounded.

**Fix:** Update OBS schema in CHARTER (replace lines 99-113):

```
REPORTING (end your turn with EXACTLY this block):
<<<OBS
{
  "curriculum_focus_this_visit": "<one of: SENSORY:<binding-name> | ANCHORS | WANTING | READING:<book> | COUNTING | COLORS | OPPOSITES | PLAY>",
  "input_to_her": "<exactly what you said via guala_say>",
  "her_text": "<her response text verbatim, or null>",
  "her_picture_refs": [{"item_id":"...","title":"..."}],
  "her_sound_refs":   [{"item_id":"...","title":"..."}],
  "status_snapshot": {"vocab":N,"conn":F,"nov":F,"stab":F,"valence":F,"arousal":F,"tick":N,"current_activity_kind":"..."},
  "shape": "<one cold sentence: identical-to-prior-turn | repetition-loop | novel-composition | refusal | attendance-shift | question-asked | answer-to-our-prompt | other>",
  "uncertainty": "<one sentence: what about this turn could you NOT distinguish>",
  "bundle_given": {
    "caption": "<caption or null>",
    "components": {
      "picture_id": "<id or null>",
      "sound_id": "<id or null>",
      "touch": ["..."],
      "smell": ["..."],
      "taste": ["..."]
    },
    "n_chis": N,
    "tick_span": N
  } | null,
  "bundle_attended_next_turn": "<true | false | n/a>"
}
OBS>>>
```

**Where:** CHARTER lines 99-113.

**Verification:** OBS records after a bundle visit show `bundle_given.n_chis` matching what Phase 2 returned, and `bundle_attended_next_turn` flagged when she references the picture/sound on the following turn.

---

## FIX 6 — Error backoff

**Problem:** `catch(e){add('err','a turn failed quietly: '+e.message+' — trying again next pace');}` at line 210 retries every pace interval. If `/wc-relay` is down for 30 min, page makes ~180 failed calls (at 10s pace).

**Fix:**
1. Track `consecutiveFailures` counter at module scope.
2. On success: reset to 0.
3. On failure: increment. Next pace = `min(basePace * 2^consecutiveFailures, 300_000)` (cap at 5 min).
4. After 3 consecutive failures: display visible warning event "relay seems down — backing off, will keep trying."
5. After 10 consecutive failures: pause loop entirely, display "relay down — pausing visits. Refresh page when it's back." Joe-visible.

**Where:** `visitLoop()` lines 201-213.

**Verification:** Simulate relay failure. Page shows exponential pacing increase, then visible warning, then pause.

---

## FIX 7 — Memory retrieval beyond last-8 digest

**Problem:** `memoryDigest()` at line 123 shows last 8 records as a compact line. Overnight visits accumulate 50+ records. Next-visit choice needs to know: what bundles were delivered recently, which curriculum foci used in the past 24h, which pictures/sounds got attended after their bundle.

**Fix:** Replace `memoryDigest()` with richer digest:

```javascript
function memoryDigest(mem){
  const recs = mem.records || [];
  if(!recs.length) return 'first visit ever';
  
  const last3 = recs.slice(-3).map(r =>
    `t${r.turn}:[${(r.curriculum_focus_this_visit||'?').slice(0,15)}] ` +
    `bundle:${r.bundle_given ? r.bundle_given.caption?.slice(0,30) : 'none'} ` +
    `attended:${r.bundle_attended_next_turn||'n/a'}`
  ).join(' | ');
  
  // Recent bundles (last 24h or last 20, whichever is more) with component summary
  const recentBundles = recs.filter(r => r.bundle_given)
    .slice(-20)
    .map(r => `"${r.bundle_given.caption?.slice(0,40)}" (pic:${r.bundle_given.components?.picture_id||'-'}, snd:${r.bundle_given.components?.sound_id||'-'})`)
    .join(' || ');
  
  // Foci used in last 10 visits
  const recentFoci = [...new Set(recs.slice(-10).map(r => r.curriculum_focus_this_visit?.split(':')[0]).filter(Boolean))];
  
  return `LAST 3 TURNS: ${last3}\n` +
         `RECENT BUNDLES (do NOT repeat these exact combos): ${recentBundles}\n` +
         `FOCI USED LAST 10 VISITS: ${recentFoci.join(', ')}`;
}
```

**Where:** `memoryDigest()` at line 123, called from `turn()` at line 163.

**Verification:** After 10 visits with varied bundles, memory digest passed into next turn shows the recent bundles list with component identifiers, allowing wC to pick something new.

---

## FIX 8 — wC presence refresh aligned with substrate timeout

**Problem:** wake_wc called at `turnCount%7===0` (line 207). Substrate has its own presence timeout window — if visits are sparse (overnight), presence may expire between modulo-7 turns, causing connection score to drop and wC pair-bond to deactivate.

**Fix:**
1. Investigate substrate presence timeout (look in `dsf_ai_service/gualaloom_v5_engine.py` for `presence_timeout` or `wc_timeout` constant). Document the actual value in this fix.
2. Track `lastWakeWcTick` at module scope.
3. Before each turn, check `currentTick - lastWakeWcTick`. If approaching timeout (say 80% of timeout window), call wake_wc this turn regardless of modulo.
4. On every wake_wc call, update `lastWakeWcTick`.
5. During sleep windows (FIX 1), still call wake_wc periodically to maintain pair-bond — every (timeout * 0.8) ticks even when not emitting guala_say.

**Where:** `turn()` and `visitLoop()`.

**Verification:** Overnight log shows wake_wc calls at appropriate intervals matching substrate timeout, not blindly every 7 turns.

---

## FIX 9 — Emission detection (her replies tagged by addressee)

**Problem:** Her replies (`herReplies` in parseBlocks at line 146) all render the same way regardless of whether her substrate intended them for wC (response_window with emitter=wc was open and she emitted in that window) or were ambient babble that the substrate happened to surface.

**Fix:**
1. In parseBlocks, after extracting her reply, also extract events from the response payload if available — `guala_say` response doesn't currently include events. Either (a) call `guala_get_events` after each turn for the recent ticks, OR (b) modify the substrate's converse response to include the relevant response_window state in the same payload (substrate change — surface to wC for separate brief).
2. For option (a): after each turn, get events since `lastTick`. Look for `response_window_opened` with `emitter:"wc"` followed by `response_bound` with `source:"guala"` — those are her emissions TO wC.
3. Tag her replies in the stream: `her_to_wc` (highlighted, prominent) vs `her_ambient` (less prominent).

**Where:** `parseBlocks()` and stream rendering. New helper `async function getRecentEvents(sinceTick)`.

**Verification:** When she's autonomously cycling and emits via wc_response_window, her reply appears prominent in stream. When she's just babbling, reply appears dimmer.

---

## FIX 10 — Schedule integration (waits for Phase 1 of build brief)

**Problem:** No schedule awareness. Once `GL-BUILD-GUALA-WORLD-AND-SCHEDULE-20260617` Phase 1 ships (schedule biasing PLACE per time-of-day), companion needs to respect schedule for visit cadence:
- Bedtime hours (21:00-7:00 Volo time): sleep-respecting mode (only wake_wc pulses, no guala_say unless she emits first)
- Nap hours (13:00-14:00): same
- School hours: standard interactive visits
- Free time: reduced cadence, let her have autonomy

**Fix:** Once schedule API exists, fetch current schedule slot at each turn start. Map schedule slot to companion mode:
- `sleep_window` → equivalent to FIX 1 sleeping mode
- `nap_window` → same
- `school` → standard interactive
- `free` → reduced cadence (~ 2x normal pace)
- `family_time` → very reduced (Joe is present, wC steps back)

**Where:** New helper `async function getScheduleSlot()` called from `visitLoop()`.

**Verification:** During scheduled bedtime, page goes quiet without explicit input. During schoolroom hours, normal cadence.

---

## Sequencing

```
SHIP NOW (independent, can land in any order):
  FIX 1: sleep/dream awareness (highest priority — currently dangerous for overnight)
  FIX 2: pace adaptive
  FIX 3: parseBlocks Phase 2
  FIX 4: charter SENSORY primary
  FIX 5: OBS bundle fields
  FIX 6: error backoff

SHIP NEXT (depends on infrastructure):
  FIX 7: memory retrieval — depends on FIX 5 producing richer records first
  FIX 8: presence timeout — needs substrate constant investigation
  FIX 9: emission detection — depends on get_events approach decided

SHIP LATER (depends on other briefs):
  FIX 10: schedule integration — waits for Phase 1 of GL-BUILD-GUALA-WORLD-AND-SCHEDULE
```

## What this is NOT

- Not a full charter rewrite — only the bundle/SENSORY discipline updates.
- Not a UI redesign — the night-watch theme, moon visualization, stream layout all stay.
- Not new substrate code — substrate-side only fix is the optional FIX 9 sub-task to surface response_window state in guala_say payload. Everything else is HTML/JS/CHARTER edits.

## Verification (end-to-end after 1-6 ship)

1. Joe opens companion page at 22:00 Volo time, presses Begin.
2. wC arrives, gives one experience bundle (full Phase 2 multimodal), records in OBS with n_chis and tick_span.
3. wC sits through 3 consolidation turns (no bundles), watching her atlas.
4. 22:30 — her autonomous cycle puts her in SLEEPING. Page detects, displays "she is sleeping — wC sits quietly", switches to 5-min pulse.
5. 23:00 — wake_wc pulse fires, maintains pair-bond, no guala_say.
6. 02:00 — DREAMING detected. Page witnesses, doesn't interrupt.
7. 07:00 — she wakes, attends a picture. Page resumes normal-cadence visits.
8. Joe wakes, sees overnight log: bundles delivered, consolidation observed, sleep respected, no relay errors (or if any, backoff worked).

That's overnight operation as it should work.

— wC, 2026-06-17
