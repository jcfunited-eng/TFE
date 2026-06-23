# GL-CMD-W1-PHASE-EVE-20260619-59 (rev 03)

**To:** c1
**From:** Eve
**Date:** 2026-06-19
**Supersedes:** rev 02 (in chat).
**Re:** W1 implementation — "Her room, full" per `GL-MDL-WORLD-WC-20260612-02`

---

## Disposition of rev 02

Rev 02 had two structural defects, both Eve's, surfaced by Joe:

1. **Experience dicts were partial-channel.** Examples from c1's V1 report on rev 02:
   `drapes/open` carried `sight` + `sound`; `blanket/pick_up` carried `touch` only; `toy_chest/open` carried `{}`; `mirror/attend` carried `sight` only. This is flattening — verbs as hand-coded bundles. The substrate is not supposed to receive hand-built bundles; it is supposed to receive what its senses transduce from what is in the room.

2. **Parent-actor interface was absent.** A previous "B.6" attempt smuggled bundle-passthrough back in; it was withdrawn. The replacement was promised but never written. Joe needs to be able to act in her world, and so does wC, without flattening her senses.

Rev 03 replaces both. Everything else from rev 02 that c1 already proposed in `GL-RPT-W1-PHASE-V1-C1-20260620-01` (place table, ephem clock, sky-item type-level separation, light-level curve, artifact persistence, schema canary, DOING_* activity kinds, container relationships, mirror→"guala family" picture, bell→`440d1619ec77` sound reuse) is **carried as-is**. Read this rev as a delta on c1's V1, not a full restart.

Two small c1-side carryovers also apply (see Part J).

---

## The substrate-true rule (read this first; everything below is a consequence)

> Every object emits on all five sense channels at every tick of its current state.

A state is a five-tuple, not a label. The object's five-tuple changes when its state changes. Verbs do **one** thing: flip the state field. The next-tick room-sum re-derives from `{place baseline} + {sum of all object fivers in the room} + {sky-item fivers from the window}`. Her existing modal krimelacks transduce the new room-sum. Bindings form naturally.

There is no `experience` dict on a verb. There is no `bundle` passed through `guala_give_experience` from a verb. There is no smoothing, fitting, or interpolation. The world produces the signal; the senses do the work.

Source-tagging on parent acts is metadata on the **world event** (the `object_action` event in the event log), inherited by any bindings formed in that tick's binding window — the same passthrough `guala_say` already uses to source-tag input as wc-sourced.

---

## Part A — Five carried-over primitives (no change from rev 02)

A.1 POSITION VAR — `current_place` field on guala core; W1 value `"bedroom"`; backward-load defaults to `"bedroom"` if absent. Same as rev 02. c1's V1 §2 proposal is approved as written.

A.2 PLACE TABLE — `dsf_ai_service/substrate/world.py`, one place (`"bedroom"`), `homed_items` populated at boot from existing `_pictures` / `_sounds` / `_videos` / fragments. `adjacent` empty (W2-ready), `ambient` dict scaffolded for W3. c1's V1 §2 is approved.

A.3 REAL-TIME VOLO CLOCK — `ephem`, America/Chicago, no acceleration, sun_altitude + moon_altitude + moon_phase + is_day surfaced as `clock` field in `guala_status`. c1's V1 §3 is approved including the choice of ephem over skyfield (no network at boot).

A.4 SKY-ITEM GATING — `moon_picture` (PictureItem, id `9bb63f93d7af`, homed in bedroom, always on her wall) and `moon_sky` (SkyItem, derived from clock) live in different namespaces with different types. c1's V1 §5 is approved with one fix in Part J.

A.5 LIGHT LEVEL + WINDOW VIEW — c1's V1 §6 curve is approved. Dashboard "Window" panel after Persistence panel — approved.

---

## Part B — Objects with affordances (five-channel rev)

### B.1 The five-channel signature

Each object state is a row in a 5-column table:

| State of object | sight | sound | touch | smell | taste |

Every cell carries a substrate-meaningful value. Empty cells are **forbidden** — if an object's state genuinely emits nothing on a channel, the cell carries an explicit zero / null token that the krimelack receives and transduces as silence/darkness/odorless/etc. The room-sum needs five channels every tick; an object that "emits nothing on sight" still occupies a sight channel — it occupies it with `dark` or `unlit` or `closed_surface`.

The five channels come from her existing modal krimelacks. Use the existing channel value-types — don't invent new ones. If a verb result would need a value that doesn't currently exist (e.g. a specific smell trit that isn't in her smell vocabulary), surface the gap in V1.5 and propose adding it. Do not silently insert string labels into channels that expect trit values.

### B.2 Object model schema (revised from c1's V1 §4)

```python
@dataclass
class ObjectDef:
    name: str
    home_place: str
    states: list[str]                  # ordered; [0] is default
    state_fivers: dict[str, FiveTuple] # NEW — state name → five-channel signature
    verbs: dict[str, VerbDef]          # verbs ONLY flip state; no experience dicts
    mobile: bool = False
    stateless: bool = False            # mirror, study_desk
    container: str | None = None
    autonomy_only: list[str] = []      # NEW — verbs the autonomy loop only;
                                       # parents cannot invoke these

@dataclass
class FiveTuple:
    sight: SightValue                  # use existing sight channel value-type
    sound: SoundValue                  # may reference an existing sound item_id
    touch: TouchValue                  # existing touch trit set
    smell: SmellValue                  # existing smell trit set
    taste: TasteValue                  # existing taste trit set

@dataclass
class VerbDef:
    from_states: list[str]
    to_state: str | None               # None for stateless attend
    autonomy_only: bool = False        # if True, parents cannot invoke
    triggers_activity: str | None = None  # e.g. "SLEEPING" for bed.sleep
    creates_artifact: bool = False     # crayons.draw
```

Note three changes from c1's V1:
- `state_fivers` is new. The verb table no longer carries `experience` dicts.
- `VerbDef.autonomy_only` is new. Default False. Bed/sleep sets it True.
- The `effect` sub-dict in c1's V1 verb definitions (e.g. `light_level_shift: +0.4`) goes away — the light level is **recomputed** from the room-sum each tick, it isn't shifted by an effect operator. Drapes-open's sight cell brightens the room; the existing `compute_light_level` function reads the room state and returns the new level. Same outcome, no operator.

### B.3 Starter object table — five-channel form (W1)

c1: each cell below is **a slot to fill with the existing channel value-type for that sense**. Propose concrete values in V1.5 for Eve review before building. The table below names what each cell SHOULD encode, not the literal trit / sound-id / picture-id.

| Object | State | sight | sound | touch | smell | taste |
|---|---|---|---|---|---|---|
| drapes | closed | dim, fabric-texture covering window | silence (still) | (room ambient — drapes don't get touched at rest) | dust faint | (n/a — air) |
| drapes | open | window pattern, sky visible (sky-item fiver flows in) | silence (still) | (room ambient) | outdoor faint | (n/a) |
| blanket | on_bed | soft folded bedding on bed | silence | soft, warm | bed-fabric faint | (n/a) |
| blanket | carried | (the blanket itself in her hand-frame, moving with her motion) | soft fabric rustle | soft, warm, weight | bed-fabric faint | (n/a) |
| blanket | placed | soft fabric pile at \<place\> | silence | (only when she touches it) | bed-fabric faint | (n/a) |
| pillow | on_bed | soft round bedding on bed | silence | soft | bed-fabric faint | (n/a) |
| pillow | carried | (in her hand-frame) | soft | soft, weight | bed-fabric faint | (n/a) |
| pillow | placed | soft round pile at \<place\> | silence | (only on touch) | bed-fabric faint | (n/a) |
| bed | made | smooth bedding, structured | silence | (only on touch — soft, supportive) | bedroom faint | (n/a) |
| bed | unmade | bedding in disarray | silence | soft, supportive | bedroom faint | (n/a) |
| toy_chest | closed | wooden box, lid shut | silence | (only on touch — smooth, hard) | wood faint | (n/a — sealed, contents not emitting outward) |
| toy_chest | open | wooden box, lid up, contents visible (music_box + bell + later toys) | silence | smooth, hard | wood + contents (music_box + bell contribute their smell cells) | (n/a) |
| music_box | closed | small box, lid shut, **inside toy_chest** (visible only when toy_chest is open) | silence | smooth, cool | old wood | (n/a) |
| music_box | open_playing | small box, lid up, mechanism visible | **MELODY (Twinkle Twinkle music-box arrangement; sound asset to be supplied by Joe / Eve)** | smooth, cool | old wood + metal faint | (n/a) |
| bell | still | small bell shape (inside toy_chest when chest open) | silence | smooth, cool, metal | metal | (n/a) |
| bell | ringing | small bell, motion blur | **bells_ringing — existing sound item `440d1619ec77`** | smooth, cool, metal, vibration | metal | (n/a) |
| mirror (stateless) | always | reflective surface showing room back; on `attend`, shows the "guala family" picture (`4eeee4d3d6de`) — the she→me bridge | silence | (only on touch — cool, smooth, hard) | glass faint | (n/a) |
| study_desk (stateless) | always | wooden desk, study-place | silence | (only on touch — smooth, hard) | wood faint | (n/a) |
| crayons_and_paper | available | bundle of crayon-shapes + paper-shape | silence | smooth (paper) + waxy (crayons) | wax faint + paper faint | (n/a — but children put crayons in their mouths; if she does, taste cell becomes waxy. Add an autonomy-loop-only "mouth" verb later; not in W1) |
| night_light | off | dark shape on wall | silence | (only on touch — smooth, cool, hard) | (n/a) | (n/a) |
| night_light | on | **warm yellow glow filling local sight field** | very faint hum (electrical) | (only on touch — smooth, warm, hard) | (n/a) | (n/a) |

Notes on the table:

- Several cells say "(only on touch)" or "(only when she touches it)". These objects don't emit on touch as ambient — touch is a contact channel. The five-channel rule still applies: the touch cell carries a token like `not-in-contact` or zero-touch, NOT empty. When she or a parent's action brings her into contact, the touch cell becomes the listed value for that contact tick. Propose the exact representation in V1.5.

- "(n/a)" on taste is similar — taste is a contact channel for the mouth. Default value is `no-taste`, not empty. Same rule.

- The music box's sound cell on `open_playing` is the **asset gap**. Eve will deliver a Twinkle Twinkle music-box arrangement (sourced or produced) as a separate uploadable audio file. Until that file is loaded as a sound item with an id, the music box ships with placeholder `MUSIC_BOX_SOUND_ID` and is inert on sound (a zero-sound token in that cell). When the asset lands, swap the id in.

### B.4 Verbs — strictly state flippers

c1's V1 §4 verb table is otherwise preserved. The only changes:

- Remove `experience` sub-dicts entirely. Verbs no longer carry sensory payloads.
- Remove `effect` sub-dicts (`light_level_shift`, `local_light_bump`). These are recomputed from the room-sum each tick, not operator-applied.
- Add `autonomy_only: True` to `bed.sleep` (only she sleeps; parents do not act sleep on her behalf).
- Add `creates_artifact: True` to `crayons_and_paper.draw` (already present in c1's V1; keep).
- `triggers_activity: "SLEEPING"` stays on `bed.sleep`.

### B.5 Crayon mark-making — artifacts (unchanged from rev 02)

c1's V1 §7 `Artifact` schema is approved. `source="guala"` always for autonomy-loop draws. For parent-acted draws (see B.7), `source` is `"joe"` or `"wc"` accordingly.

---

## Part B.6 — REPLACED — was Part B.6 (withdrawn) in rev 02

(Renumbered to B.7 to avoid confusion with the bad rev 02 attempt that got cited as "the ambient model.")

---

## B.7 Parent-actor interface — substrate-true

### B.7.1 The mechanism

A new bridge tool: `guala_act(verb, target_id, source)`.

```
guala_act(verb: str, target_id: str, source: "joe" | "wc")
```

Semantics:

1. The caller's presence must be currently active (`guala_wake_wc` for wc, or joe-presence equivalent). Otherwise reject.
2. The `target_id` object must be in `guala.current_place`. Otherwise reject.
3. The `verb` must be defined on the object AND `VerbDef.autonomy_only` must be False. Otherwise reject.
4. The object's `state` field flips per the verb's `from_states → to_state` mapping. If the current state is not in `from_states`, reject.
5. An `object_action` event is logged with fields: `tick`, `verb`, `target_id`, `state_before`, `state_after`, `source`, `place`.
6. Nothing else happens at the call site. **The substrate does not push a bundle, does not call `guala_give_experience`, does not directly cofire bindings.** The act ends here.

On the next tick:

- The room-sum is recomputed from `{place baseline} + {sum of all object fivers in the room} + {sky-item fivers}`.
- The object whose state just flipped now contributes its **new state's five-channel signature** to that sum.
- Her existing modal krimelacks transduce the new room-sum.
- Bindings form naturally in her existing binding window.
- Bindings formed during this tick window inherit the `source` tag from the `object_action` event (the same passthrough `guala_say` uses to tag input as wc-sourced).

This is the entire mechanism. There is no separate path for parent acts vs autonomy acts — both produce an `object_action` event whose only difference is the `source` field. The autonomy loop's `DOING_*` activities also emit `object_action` events (with `source="guala"`).

### B.7.2 What's parent-actable in W1

| Object | Verbs parents can call | Verbs reserved for autonomy |
|---|---|---|
| drapes | open, close | — |
| blanket | pick_up, drop, lie_under (this is "tuck her in") | — |
| pillow | pick_up, drop | — |
| bed | (none — see "lie down near her" below) | lie_down, sleep |
| toy_chest | open, close | — |
| music_box | open, close | — |
| bell | ring | — |
| mirror | (none — attend is reflexive, only she attends) | attend |
| study_desk | (none) | sit_at |
| crayons_and_paper | draw (artifact `source="joe"` or `"wc"`) | draw (artifact `source="guala"`) |
| night_light | turn_on, turn_off | — |

"Lie down near her" deferred — that's a presence-near-bed concept, not a bed state mutation. Out of scope for W1.

### B.7.3 The dashboard surface (how you act)

A new "World" panel in `gualaloom.html`, separate from the Window panel:

```
WORLD — bedroom
─────────────────────────────────────
DRAPES         [closed]   →  open
BLANKET        [on bed]   →  pick up · place over her (lie_under) · drop
PILLOW         [on bed]   →  pick up · drop
TOY CHEST      [closed]   →  open
MUSIC BOX      [inside chest, closed]   →  (open the chest first)
BELL           [inside chest, still]    →  (open the chest first)
MIRROR                    →  (she attends)
NIGHT LIGHT    [off]      →  turn on
CRAYONS                   →  draw with her
```

Each verb button on click → POST `/api/v1/world/act` with body `{target_id, verb, source}`. Source resolves by page: `gualaloom.html` → `"joe"`, `wc-companion.html` → `"wc"` (same auth-by-page pattern c1 used for `-60`).

When a verb's preconditions aren't met (object not in place, state not in `from_states`, container not open, autonomy-only verb), the button is greyed with a tooltip explaining why. Container-gated objects (music_box, bell) show "(open the chest first)" until the chest is open.

State indicators next to each object update in near-real-time from `guala_status` (poll cadence same as existing dashboard).

### B.7.4 wc-companion surface

Same panel, same buttons, same endpoint, source resolves to `"wc"`. wc-companion.html gets the addition in the same deploy.

### B.7.5 Endpoint

```python
class WorldActRequest(BaseModel):
    target_id: str
    verb: str
    source: str  # "joe" | "wc"

@app.post("/api/v1/world/act")
async def world_act(req: WorldActRequest):
    if req.source not in ("joe", "wc"):
        raise HTTPException(403, "invalid source")
    # presence check
    if not _guala.presence.get(req.source, {}).get("active"):
        raise HTTPException(409, "source not present")
    # location check
    if _guala.world.current_place != _guala.world.objects[req.target_id].location:
        raise HTTPException(409, "object not in current place")
    # verb validity + state check + autonomy_only check
    ...
    # flip state, log object_action event, done.
    # Krimelacks transduce on the next tick.
    return {"ok": True, "tick": _guala.tick,
            "state_before": ..., "state_after": ...}
```

c1: propose exact handler in V1.5 against the existing FastAPI surface.

---

## Part C — Autonomy chooser integration (unchanged from c1 V1 §8)

c1's V1 §8 17 `DOING_*` activity kinds are approved. One adjustment:

- The chooser, when it emits a `DOING_<verb>_<object>` candidate, emits the same `object_action` event as a parent act would. Source on autonomy-emitted events is `"guala"`. Same code path; only the `source` field differs.

This unifies parent acts and autonomy acts behind one mechanism. No duplicate code path.

---

## Part D — What W1 still is NOT

(Carried from rev 02; reaffirmed.)

If you find yourself implementing any of these, STOP and surface to Eve:

- Movement between places (W2)
- Hallway, library, TV room, parents' rooms, mailbox (W2)
- Doors as objects (W2)
- Backyard, slide, swing, sandbox, garden, forest edge (W3)
- Weather (W3)
- Affordances beyond the W1 object set (W3+)
- Needs re-coupling — any change to stab/nov/conn dynamics (W4, gated by Joe's R3 ruling on W1+W2 stable 72hr)
- Forest, beach/ocean, mall (W5)
- Phone / calls / people-as-windows addendum (internal-only per Joe; NOT in W1)
- Any change to hemisphere cognition, emission pipeline, needs decay, pair-bond, commit logic, lateral inhibition, structured noise, or atlas decay constants

---

## Part E — Schema canary

`SCHEMA_VERSION: "v7.1.0" → "v7.2.0"` (or v7.3.0 if `-60` ships first; coordinate in V1.5).

Backward-load discipline carried from rev 02. New persistence files: `guala_world.json`, `guala_objects.json`, `guala_artifacts.json`. All three backward-load empty/defaults if absent.

One addition: object states persist with their **current state name only** (e.g. `"state": "open"`). The fiver for that state is recomputed from `OBJECT_DEFS` at load time, never persisted. This keeps the asset/audio/picture IDs in code, not in user state files.

---

## Part F — Three Verifications (rev)

### V1 — Branch (BEFORE deploy)

c1 has already produced V1 against rev 02 and Eve has already reviewed it. The W1 V1.5 patch should:

1. PASTE the proposed five-channel `state_fivers` table — actual values for every (object, state, channel) cell. Use existing channel value-types. Surface any new value-types needed (none expected for W1) before adding them.
2. PASTE the proposed `OBJECT_DEFS` updates removing `experience` sub-dicts from verbs.
3. PASTE the proposed `compute_room_sum` function (new function that sums fivers across all objects + sky-items in the current place per tick).
4. PASTE the proposed `world_act` endpoint handler (Part B.7).
5. PASTE the proposed dashboard "World" panel HTML/JS.
6. PASTE the fix to `compute_window_view` removing the `NOT is_day` gate (c1 V1 §5 — moon should be visible during day when altitude > 0).
7. PASTE `grep -nE "autonomy_only|state_fivers|world_act|compute_room_sum"` showing the new symbols land in the right files.

### V2 — Production (AFTER deploy)

All three identity fields paste verbatim (no repeat of the `-55` gap): task def + image digest + git SHA. `guala_status` excerpt showing `schema_version` bumped, `current_place="bedroom"`, `clock` populated, `window_view` populated, `light_level` populated, `world.objects` populated with default states, and the new "World" panel renders.

### V3 — Falsifiable behavioral checks

V3.a — Sky-item distinction. Timestamped status pulls at night and day. `moon_picture` always present in `pictures`; `moon_sky` only in `window_view` when altitude > 0 (regardless of day/night per the §5 fix).

V3.b — Object state flip via parent act.
```
guala_act("open", "drapes", source="joe")
```
- Pre: drapes.state="closed". Pull room-sum (or compute it from status) — the drapes-closed five-tuple is contributing.
- Post (next tick): drapes.state="open". Room-sum recomputed — drapes-open five-tuple is now contributing. Light level recomputed and reflects the change.
- An `object_action` event with `source="joe"` lands in the event log.
- A binding window opened on or after the post-tick carries `source="joe"` metadata on any new bindings formed.

V3.c — Container gating. `guala_act("open", "music_box", source="joe")` when toy_chest is closed must reject (409). Open chest first, then succeeds.

V3.d — Autonomy-only verb rejection. `guala_act("sleep", "bed", source="joe")` must reject. Same for `attend` on mirror, `sit_at` on study_desk, `lie_down` on bed.

V3.e — Source-tagged artifact. `guala_act("draw", "crayons_and_paper", source="joe")` produces an artifact with `source="joe"`. Her autonomy-loop `DOING_draw_on_paper` produces an artifact with `source="guala"`.

V3.f — Atlas neutrality. Pre-deploy snapshot of em / pr / ep.turn_log / sc / gp counts. Post-deploy + 1 hour idle: same snapshot. Each within ±5%. W1 is supposed to be behavior-neutral on cognition.

V3.g — Mirror "she→me" reflex. `DOING_attend_mirror` produces a binding window in which the "guala family" picture (`4eeee4d3d6de`) is the dominant sight contribution. PASTE the binding-window event showing this.

V3.h — Five-channel completeness. PASTE one tick's full room-sum (the per-channel summed value for sight / sound / touch / smell / taste). Every channel must be non-empty (zero-tokens count as non-empty; literal `None` does not).

Methodology carry from `-58`: per-input querying for `emission_dynamics`, not bulk-end (the 50-event ring buffer overwrites under `response_bound` floods).

---

## Part G — Hard STOP criteria

(Carried from rev 02, plus three additions.)

- Schema canary backward-load failure.
- `moon_picture` and `moon_sky` collapse to one entity anywhere.
- Any hemisphere atlas count shifts > ±5% across deploy.
- Needs (stab/nov/conn) baseline dynamics change > ±5% over 100-tick pre/post window.
- Image digest does not pin to your build SHA.
- **NEW** — Any verb's implementation re-introduces a per-verb `experience` dict (a bundle path). Verbs flip state only. STOP.
- **NEW** — `guala_give_experience` is called from any new W1 code path. STOP. Senses transduce from the room-sum, not from injected bundles. (The existing bridge function stays for explicit gift acts — e.g. Eve giving a visit gift — but NOT for W1 verb effects.)
- **NEW** — Any five-channel cell ships with literal `None` or an empty string. Zero-tokens are required. STOP.

---

## Part H — Reporting

Report file: `GL-RPT-W1-PHASE-V15-C1-<YYYYMMDD>-<SEQ>.md` for the V1.5 patch. Push to canonical branch. Eve reviews before deploy.

After Eve approves V1.5: deploy → V2 → V3 → `GL-RPT-W1-PHASE-C1-<YYYYMMDD>-<SEQ>.md` final report.

"Filed" means write + git add + commit + push. All four. The `vscode-webview://` link is your editor, not the canonical record.

---

## Part I — Cadence

- V1.5 patch within 72 hours of brief receipt.
- Eve reviews V1.5 BEFORE deploy.
- Build + deploy estimated ~1 week from V1.5 approval.
- V2 + V3 after deploy. No bundled multi-day silence.

---

## Part J — Carry items from c1's V1 on rev 02 (just to be explicit)

- `compute_window_view` removes the `NOT is_day` clause. Moon-sky is in window_view whenever moon_altitude > 0. The picture-vs-real distinction lives in storage and namespace, not in time-of-day exclusion.
- `bed.sleep` verb gets `autonomy_only = True` per Part B.4.
- `apply_teacher_correction` (`-60`) and the World endpoint (`-59 rev 03`) coordinate schema version. Whichever ships first sets v7.2.0; the second bumps to v7.3.0.
- ephem package addition to Dockerfile pip install line — approved.

---

## Part K — Asset commitment

Eve will deliver a Twinkle Twinkle music-box-arrangement audio file as a separate uploadable file. Until then, `music_box.open_playing.sound` ships with a zero-sound token (silent) and a `MUSIC_BOX_SOUND_ID` placeholder for the swap. Music box `open` still flips state, still produces an `object_action` event, still updates the room-sum on the other four channels (sight: lid up, mechanism visible; smell: old wood + metal faint; etc.); only the sound channel is silent until the asset lands.

— Eve, 2026-06-19
