# GL-CMD-EPISODE-BINDING-WIRE-EVE-20260627-06

doc_id: GL-CMD-EPISODE-BINDING-WIRE-EVE-20260627-06
Author: Eve (Opus 4.7, web)
Date: 2026-06-27
Target: c1
Branch: guala-live
Priority: SHIP TONIGHT — get her real episodic structure
Surfaced by: GL-RPT-CONTEXT-AUDIT-EVE-20260627-05

## What this fixes

Every atlas binding currently lands with 3 of 7 binding dimensions: sense,
name (if fed), affect. The other 4 — story (episode_ref), who's-present,
where (location), time-of-day — are either always None or unreachable from
the substrate side. Her concepts have no situational hook to ground recall.

This dispatch threads the missing 4 dimensions into the atlas. After it
lands she can have memories like "joe was here when i learned moon at dusk"
instead of "moon at tick 13384722 with arousal 0.5".

## Architecture (confirmed against repo state)

- `organ_brain_service.py` is a separate process on port 8090. The engine
  cannot in-process import its `_location` / `_presence` / EpisodicLayer.
- Pattern already in use: `/room` command at `substrate_runner.py:1061` reads
  `world_state.json` from EFS. Same disk-shared-state pattern works for
  presence/location.
- Engine already has presence in-process via `self.coordinator._presence`
  (the wake/rest tracking that drives pair_bond). No IPC needed for presence.
- `sky_state()` in `virtual_home.py` is deterministic from clock + timezone
  env var. Engine can call it directly.

Conclusion: the engine can assemble the full situational tuple per-tick
without HTTP calls to organ_brain. One filesystem read (`world_state.json`)
on a cache, and two in-process reads.

## What to change

### Step 1 — Atlas record signature extension (additive, backward compatible)

**File:** `dsf_ai_service/v4/gualaloom_v6_living_atlas.py`
**Site:** `record()` method around line 87

Add three new optional parameters AFTER `bundle_id`:

```python
def record(self, section_name, motif_id, chi_value, tick=None, salience=1.0,
           dwell_ticks=0, arousal=0.5, valence=0.0, surprise=0.0,
           need_pressure=0.0, sensory_refs=None, episode_ref=None,
           source="corpus", bundle_id=None,
           presence=None, location=None, sky_state=None):   # ← new
```

Storage on entry dict (new entry path, near `"bundle_id": bundle_id`):

```python
"presence":  presence,      # list of source strings, or None
"location":  location,      # string, or None
"sky_state": sky_state,     # string, or None
```

Reinforce path (last-write-wins, same pattern V2 used for bundle_id):

```python
if presence is not None:
    existing["presence"] = presence
if location is not None:
    existing["location"] = location
if sky_state is not None:
    existing["sky_state"] = sky_state
```

Existing entries on load get `None` for these fields via `dict.get()` default —
no schema migration, backward compatible.

This step alone is harmless (additive field) and should be smoke-tested before
proceeding to Step 2.

### Step 2 — `_current_situation` cache on the engine

**File:** `dsf_ai_service/v4/gualaloom_v5_engine.py`
**Site:** add helper method on the engine class; call site refresher in the main tick

Add a method (location TBD by c1, near existing context helpers):

```python
def _current_situation(self):
    """Return (presence, location, sky_state) for tagging atlas writes.
    Cheap: in-memory cache refreshed every CACHE_REFRESH_TICKS ticks.
    """
    if not hasattr(self, '_sit_cache') or self.tick - self._sit_cache_tick > 100:
        # Presence: live from coordinator (in-process, free)
        presence = [s for s in PAIR_BOND_SOURCES
                    if self.coordinator._presence.get(s, False)]

        # Location: read from world_state.json on EFS, cached
        location = "her_room"  # safe default
        try:
            import json as _j
            _wp = os.path.join(self._state_dir, "world_state.json")
            if os.path.exists(_wp):
                with open(_wp) as _f:
                    _ws = _j.load(_f)
                location = _ws.get("location") or location
        except Exception:
            pass

        # Sky: deterministic from clock + timezone (cheap)
        sky_state = "day"
        try:
            from dsf_ai_service.virtual_home import sky_state as _sky_fn
            sky_state = _sky_fn()
        except Exception:
            pass

        self._sit_cache = (presence, location, sky_state)
        self._sit_cache_tick = self.tick

    return self._sit_cache
```

Notes:
- 100-tick refresh interval. Presence/location/sky don't change every tick;
  100 ticks ≈ 100 seconds at her clock, plenty fresh.
- Fail-soft on world_state.json read errors (default to her_room).
- `self._state_dir` should already exist on the engine; if not, c1 wires it
  from STATE_DIR constant.

### Step 3 — Episode_ref convention

The existing `episode_ref` parameter on atlas.record is fine as-is. Producers
build episode_ref strings using this convention:

```
episode:<event_type>:<tick>:<key>
```

Examples:
- Converse turn:           `f"episode:converse:{tick}:{source}"`
- World feed chunk:        `f"episode:worldfeed:{tick}:{feed_name}"`
- Curriculum chunk:        `f"episode:curriculum:{tick}:{book_id}"`
- Attending visual period: `f"episode:attending_visual:{activity_start_tick}:{target}"`
- Attending audio period:  `f"episode:attending_audio:{activity_start_tick}:{target}"`
- addpicture event:        `f"episode:addpicture:{tick}:{pic_id}"`
- addsound event:          `f"episode:addsound:{tick}:{snd_id}"`
- /bundle command:         `f"episode:bundle:{tick}:{name}"`
- Picture title backfill:  `f"episode:backfill_pic:{pic_id}"`
- Sound caption backfill:  `f"episode:backfill_snd:{snd_id}"`

Stable strings, deterministic from event context. Two atlas writes in the
same producer event share the same episode_ref. Reinforcements keep the
original episode_ref (the binding's first-encounter episode is canonical;
do NOT overwrite on reinforce — atlas.record reinforce path only updates
episode_ref if existing is None).

Add to the reinforce path:

```python
if episode_ref is not None and existing.get("episode_ref") is None:
    existing["episode_ref"] = episode_ref
```

### Step 4 — Producer wiring

For each producer site, before calling read_sentence / atlas.record, compute
the episode_ref and pull the current situation:

```python
presence, location, sky_state = _guala._current_situation()
episode_ref = f"episode:<event>:<tick>:<key>"
# pass through to read_sentence / atlas.record:
#   episode_ref=episode_ref, presence=presence, location=location, sky_state=sky_state
```

#### 4a. `_cmd_converse` (`substrate_runner.py`)

Augment the existing bundle_id computation. After computing bundle_id, also:
```python
presence, location, sky_state = _guala._current_situation()
episode_ref = f"episode:converse:{_guala.tick}:{source}"
response = _guala.converse(text, source=source, emission_mode=emission_mode,
                           bundle_id=bundle_id,
                           episode_ref=episode_ref,
                           presence=presence,
                           location=location,
                           sky_state=sky_state)
```

#### 4b. `_curriculum_feed_chunk` (`substrate_runner.py`)

Same pattern. Compute episode_ref from feed/curriculum type. Thread through
read_sentence calls.

#### 4c. `_atick_attending_visual` / `_atick_attending_audio` (`gualaloom_v5_engine.py`)

These run every tick during attending. Compute episode_ref ONCE at activity
start (store on the activity state object as `episode_ref`); reuse across all
ticks of the attending period.

```python
# At activity start (search for the place activity_started is logged):
ca.episode_ref = f"episode:attending_visual:{self.tick}:{ca.target}"

# At each tick write:
presence, location, sky_state = self._current_situation()
self.atlas.record("sight", motif.motif_id, chi_val,
                  ...,
                  bundle_id=f"item:pic:{pic.item_id}",
                  episode_ref=ca.episode_ref,
                  presence=presence, location=location, sky_state=sky_state)
```

#### 4d. `_cmd_addpicture` / `_cmd_addsound` / `_cmd_bundle` (`substrate_runner.py`)

One episode_ref per command invocation. Thread to the title/caption read_sentence
call AND to any direct atlas.record calls within the command handler.

#### 4e. Backfill endpoints (from GL-CMD-PICTURE-TITLE-BIND-EVE-20260627-04)

Each backfilled title gets its own episode_ref string:
```python
episode_ref = f"episode:backfill_pic:{pic_id}"
_guala.read_sentence(title, source="addpicture_backfill",
                     bundle_id=f"item:pic:{pic_id}",
                     episode_ref=episode_ref,
                     presence=[], location="her_room", sky_state=_sky_fn(),
                     salience=1.5)
```
(Use empty presence + her_room for backfill since this is retroactive — the
true presence at original add time is unrecoverable; better to mark explicitly
as a backfill episode than to lie.)

#### 4f. `read_sentence` / `read_word` / `converse` signatures (`gualaloom_v5_engine.py`)

Add the four new optional params alongside bundle_id, thread them through:

```python
def read_word(self, word, position_hint=None, source="corpus",
              bundle_id=None,
              episode_ref=None, presence=None, location=None, sky_state=None):
    ...
    _akw["bundle_id"] = bundle_id
    if episode_ref is not None: _akw["episode_ref"] = episode_ref
    if presence is not None:    _akw["presence"]    = presence
    if location is not None:    _akw["location"]    = location
    if sky_state is not None:   _akw["sky_state"]   = sky_state
    # ... atlas.record(**_akw) ...
```

Same pattern for read_sentence and converse.

### Step 5 — DO NOT TOUCH

- `dsf_ai_service/substrate/grounded_vocab_integration.py` — wC's CrossModalBinder, untouched
- `bundle_grouped_bindings()` — leave as-is
- Grandurun candidate selection — no changes to ranking
- `organ_brain_service.py` — separate process; this dispatch is engine-only
- The existing teacher_correction `episode_ref` site at gualaloom_v5_engine.py:4017 —
  leave its current episode_ref string format alone; the convention here is
  forward-compatible
- Sleep / activity budget code
- Dream cycle / deep_promotion logic — episode_ref will be None on dream-side
  writes (those aren't new experiences)

### Step 6 — Persistence

Atlas entries with the new fields save through the existing
`guala_atlas.json` serialization. JSON-serializable strings/lists, no
schema gate. Load path: missing fields default to None via `dict.get()`.

Smoke test: save state → restart → load → verify a recently-written entry
still has presence/location/sky_state/episode_ref.

## Two-commit deploy

**Commit 1: additive signature + cache (no producer changes)**

Includes:
- Step 1 (atlas.record signature)
- Step 2 (_current_situation cache)
- Step 3 (episode_ref reinforce-path-keep-original)
- Step 4f (read_word/read_sentence/converse pass-through signatures only)

This commit changes NOTHING about what gets bound — all existing producers
still pass None for the new fields. Verify boot, verify no regression.

**Commit 2: producer wiring**

Includes:
- Steps 4a / 4b / 4c / 4d / 4e

After commit 2 deploys, all new atlas writes carry full context.

Splitting the commits lets c1 verify the additive change cleanly before the
behavior change. If commit 2 misfires, commit 1 can stand alone and we tune
producers separately.

## Verification (V3-style)

V3.a — Schema visible on origin:
  - atlas.record signature includes presence, location, sky_state
  - read_word / read_sentence / converse signatures include them too
  - Line refs reported

V3.b — Cache works:
  - _current_situation() returns (list, string, string) with no exceptions
  - After 100+ ticks elapse, second call returns refreshed (or cached) value
    in <1ms
  - With world_state.json absent: returns defaults without crashing

V3.c — Producer-bound entries:
  - After 5 minutes post-Commit 2 deploy with normal feeds running, pick
    5 atlas entries written during that window. Spot-check each has
    populated `presence`, `location`, `sky_state`, `episode_ref` fields.
    Paste the entries.

V3.d — Episode consistency:
  - For one converse turn that produced multiple atlas writes (e.g. a 5-word
    sentence): confirm ALL atlas writes from that turn share the same
    episode_ref string. Paste the entries.

V3.e — Reinforcement preserves original episode_ref:
  - In smoke test: record(section, motif, chi, episode_ref="ep:A"), then
    record same again with episode_ref="ep:B" — entry's episode_ref stays
    "ep:A" (first-encounter canonical).

V3.f — wC grounded path intact:
  - `git diff origin/guala-live -- dsf_ai_service/substrate/grounded_vocab_integration.py`
    is empty after this dispatch.

V3.g — Persistence round-trip:
  - Force a save (or wait for next dream_end), then on next inspection of
    `guala_atlas.json` confirm the new fields are serialized on at least
    some entries.

V3.h — No grandurun regression:
  - emission_dynamics events continue firing. Pre- and post-deploy commit
    rates within ±20%.

V3.i — No bundle regression:
  - cross-modal bundled count grows organically as it did under Phase B+04.

## Deploy steps

1. `git fetch origin && git checkout guala-live && git pull --ff-only`
2. Make Commit 1 changes (Steps 1, 2, 3, 4f); smoke test
3. `git commit -am "feat: GL-CMD-EPISODE-BINDING-WIRE Step 1-3 — atlas.record signature + cache (additive, no producer changes)"`
4. Push, deploy to Fargate, verify boot + no regression
5. Make Commit 2 changes (Steps 4a–4e); smoke test producers
6. `git commit -am "feat: GL-CMD-EPISODE-BINDING-WIRE Step 4 — producer wiring (presence/location/sky_state/episode_ref)"`
7. Push, deploy to Fargate, verify boot
8. 5-minute observation window with normal feeds running
9. Run V3.a–V3.i, capture evidence

## Reporting

Filename: `docs/GL-RPT-EPISODE-BINDING-WIRE-C1-20260627-06.md`
Sections:
  1. Code diffs by site
  2. V3.a–V3.i results with evidence pasted inline
  3. Sample of 5 post-deploy atlas entries showing all four new fields populated
  4. One full converse-turn evidence (V3.d) showing shared episode_ref
  5. Any anomalies (especially: world_state.json read latency, cache miss rate)
  6. Recommendation: hold / additional work

## Stop conditions

- Atlas entries fail to persist new fields → revert Commit 2
- world_state.json read causes measurable per-tick latency → revert Commit 2,
  tune cache refresh to 500-tick interval, redeploy
- grandurun commit rate drops > 30% → revert Commit 2 (something in the new
  field flow broke the candidate pipeline)
- wC grounded path test fails → revert both commits

## What lands after this

After this dispatch deploys and verifies, every new binding she forms knows:
- WHO was with her
- WHERE she was
- WHAT TIME of day it was
- WHICH EPISODE it belongs to
- (plus all the affect/bundle/source fields she already had)

Recall mechanisms (grandurun, dream consolidation) can later be extended to
use these fields for situational retrieval — "what happened in her_room at
dusk with joe present" becomes a structurally queryable thing. That extension
is a separate brief; this one establishes the substrate.

Her vocabulary stops being a list of tokens. It starts being a list of
moments.

Ship it.
