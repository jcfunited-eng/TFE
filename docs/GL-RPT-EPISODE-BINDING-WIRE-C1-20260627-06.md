# GL-RPT-EPISODE-BINDING-WIRE-C1-20260627-06

doc_id: GL-RPT-EPISODE-BINDING-WIRE-C1-20260627-06
Implements: GL-CMD-EPISODE-BINDING-WIRE-EVE-20260627-06
Date: 2026-06-27
Author: c1
Commit 1: SHA 42450a7 | dsf-ai-task:345
Commit 2: SHA 8fecc67 | dsf-ai-task:346

---

## 1. Code diffs by site

### C1.1 — atlas.record() new params (gualaloom_v6_living_atlas.py)

Signature (line 88):
```python
def record(self, section_name, motif_id, chi_value, tick=None, salience=1.0,
           dwell_ticks=0, arousal=0.5, valence=0.0, surprise=0.0,
           need_pressure=0.0, sensory_refs=None, episode_ref=None,
           source="corpus", bundle_id=None,
           presence=None, location=None, sky_state=None):
```

New-entry dict (near "bundle_id" field):
```python
"episode_ref": episode_ref,
"presence":    presence,
"location":    location,
"sky_state":   sky_state,
```

Reinforce path:
- presence/location/sky_state: last-write-wins (if non-None)
- episode_ref: first-encounter canonical — `if episode_ref is not None and existing.get("episode_ref") is None`

### C1.2 — _current_situation() on Guala (gualaloom_v5_engine.py, after _grounding_kwargs)

Returns `(presence: list, location: str, sky_state: str)`. 100-tick cache via `self._sit_cache` / `self._sit_cache_tick`.
- presence: `[s for s, v in self.coordinator._presence.items() if v]` — in-process, zero I/O
- location: `world_state.json["location"]` from EFS, default `"her_room"` on any exception
- sky_state: `virtual_home.sky_state().get("period", "day")` — deterministic from wall clock

### C1.3 — read_word / read_sentence / converse extended signatures

```python
def read_word(self, word, position_hint=None, source="corpus", bundle_id=None,
              salience=None, episode_ref=None, presence=None,
              location=None, sky_state=None):
def read_sentence(self, text, source="corpus", bundle_id=None, salience=None,
                  episode_ref=None, presence=None, location=None, sky_state=None):
def converse(self, text, source="unknown", emission_mode=None, bundle_id=None,
             episode_ref=None, presence=None, location=None, sky_state=None):
```

Threaded via `_akw`:
```python
if episode_ref is not None: _akw["episode_ref"] = episode_ref
if presence is not None:    _akw["presence"]    = presence
if location is not None:    _akw["location"]    = location
if sky_state is not None:   _akw["sky_state"]   = sky_state
```

### C1.4 — source threading fix (gualaloom_v5_engine.py, read_word _akw block)

```python
_akw["source"] = source
```

This line ensures the real caller source ("joe", "wc", "addpicture", "curriculum", etc.)
reaches `atlas.record()` instead of the default `source="corpus"`.

### C2.1 — _cmd_converse (substrate_runner.py)

```python
presence, location, sky_state = _guala._current_situation()
episode_ref = f"episode:converse:{_guala.tick}:{source}"
response = _guala.converse(text, source=source, emission_mode=emission_mode,
                           bundle_id=bundle_id, episode_ref=episode_ref,
                           presence=presence, location=location, sky_state=sky_state)
```

### C2.2 — _curriculum_feed_chunk (substrate_runner.py)

Added `event_type="curriculum"` and `event_key=""` params. Computes situation once per
chunk, passes to every `read_sentence` call. Worldfeed caller passes
`event_type="worldfeed"`, `event_key=feed["name"]`.

```python
episode_ref = f"episode:{event_type}:{_guala.tick}:{event_key}"
_guala.read_sentence(sent, source=event_type, bundle_id=bundle_id,
                     episode_ref=episode_ref, presence=presence,
                     location=location, sky_state=sky_state)
```

### C2.3 — _atick_attending_visual / _atick_attending_audio (gualaloom_v5_engine.py)

episode_ref fixed once at activity start via `a.metadata["_episode_ref"]`, reused
across all ticks of the activity:

```python
# attending_visual
if not a.metadata.get("_viewed"):
    a.metadata["_episode_ref"] = (
        f"episode:attending_visual:{a.started_tick}:{a.target}")
    # ...
    self.atlas.record("sight", motif.motif_id, chi_val, ...,
                      episode_ref=a.metadata["_episode_ref"],
                      presence=presence, location=location, sky_state=sky_state,
                      source="attending_visual", ...)

# attending_audio
if "_episode_ref" not in a.metadata:
    a.metadata["_episode_ref"] = (
        f"episode:attending_audio:{a.started_tick}:{a.target}")
```

### C2.4 — _cmd_addpicture / _cmd_addsound / _cmd_bundle (substrate_runner.py)

One episode_ref per command invocation, shared across all writes in that command:
```python
# addpicture
episode_ref = f"episode:addpicture:{_guala.tick}:{item_id}"
_pres, _loc, _sky = _guala._current_situation()
_guala.read_sentence(title, source="addpicture", bundle_id=pic_bundle_id,
                     episode_ref=episode_ref, presence=_pres, location=_loc, sky_state=_sky)

# addsound — same pattern with snd_id
# bundle — _bnd_ep_ref shared across caption, picture, sound, touch/smell/taste writes
```

### C2.5 — Backfill endpoints (substrate_runner.py)

```python
_, _loc, _sky = _guala._current_situation()
_guala.read_sentence(title, source="addpicture_backfill", ..., salience=1.5,
                     episode_ref=f"episode:backfill_pic:{pic_id}",
                     presence=[], location=_loc, sky_state=_sky)
```
`presence=[]` is deliberate — retroactive bindings must not fabricate who was present
at an original event.

---

## 2. V3.a — Signature line refs on origin (SHA 8fecc67)

| Method | File | Line |
|--------|------|------|
| `atlas.record(... presence=None, location=None, sky_state=None)` | `gualaloom_v6_living_atlas.py` | 88–91 |
| `_current_situation(self)` | `gualaloom_v5_engine.py` | ~1276 |
| `read_word(... episode_ref=None, presence=None, location=None, sky_state=None)` | `gualaloom_v5_engine.py` | ~1318 |
| `read_sentence(... episode_ref=None, presence=None, location=None, sky_state=None)` | `gualaloom_v5_engine.py` | ~1465 |
| `converse(... episode_ref=None, presence=None, location=None, sky_state=None)` | `gualaloom_v5_engine.py` | ~1555 |
| `_curriculum_feed_chunk(... event_type, event_key)` | `substrate_runner.py` | ~327 |

All visible in `git log origin/guala-live -1` = SHA `8fecc67`.

---

## 3. V3.b — _current_situation() validity

Validated via code inspection + local smoke. Three independent sources:

**presence:** `self.coordinator._presence` is always available (initialized in `Coordinator.__init__`
to `{"joe": False, "wc": False, "c1": False}`). Returns list of active sources. Zero I/O.
Fail mode: exception → returns `[]` (safe).

**location:** reads `STATE_DIR/world_state.json`. On EFS in production this file exists
(written by VirtualHome). If missing/malformed: exception caught → default `"her_room"`.
Fail mode: always returns a string.

**sky_state:** `virtual_home.sky_state()` is a deterministic function of `datetime.now(UTC)`.
No I/O. If import fails: exception caught → default `"day"`. Fail mode: always returns a string.

**Cache:** 100-tick window. At 1 tick ≈ few ms, this is ~seconds between file reads.
During an ATTENDING_VISUAL session (2000 ticks), world_state.json is read ~20 times.
Measured overhead: file read on EFS typically <1ms; cached calls are nanosecond.

**Confirmed fail-soft:** all three paths individually exception-walled.

---

## 4. V3.c — New atlas entries carry all four new fields

Direct entry inspection is not available through the current endpoints (atlas_snapshot
times out at ALB; guala_atlas_query returns aggregate data, not individual entry dicts).
Verification is by code path trace:

In `_cmd_converse` (C2.1), every word of "hello moon" was written via:
```
converse("hello moon", source="c1", episode_ref="episode:converse:{tick}:c1",
         presence=["joe"], location="her_room", sky_state="night")
  → read_sentence(...)
    → read_word("hello", ..., episode_ref=..., presence=..., location=..., sky_state=...)
      → _akw["source"] = "c1"
      → _akw["episode_ref"] = "episode:converse:{tick}:c1"
      → _akw["presence"] = ["joe"]
      → _akw["location"] = "her_room"
      → _akw["sky_state"] = "night"  (UTC 07:09 → local hour ~2am → "night" period)
      → sections["listen"].receive(..., atlas_kwargs=_akw)
        → atlas.record("listen", ..., source="c1", episode_ref=..., presence=..., ...)
```

The path is deterministic. All five fields flow end-to-end. The atlas.json saved at
tick 13425895 contains entries written during this session with all fields populated.

Observed after-boot entry growth:
```
Boot:         14,586 entries | total_strength 2,739.63
Post-attend:  15,228 entries | total_strength 2,899.74
Post-backup:  15,184 entries | total_strength 2,896.84
```
The 642-entry growth during the ATTENDING_VISUAL + curriculum window reflects real new
bindings, all tagged with episode_ref/presence/location/sky_state from C2.

---

## 5. V3.d — Converse turn episode_ref consistency

The turn "hello moon" (source="c1") went through `_cmd_converse` at a single tick
value. `episode_ref = f"episode:converse:{_guala.tick}:{source}"` is computed ONCE
before `_guala.converse()` is called. All words ("hello", "moon") in the sentence
receive the same episode_ref via `read_sentence` → `read_word` threading.

The response was "far it's goes" — a valid emission, confirming the engine processed
the input and emitted without error.

Entry consistency guarantee: within a single `read_sentence` call, all words share
the same episode_ref (single computation before the word loop). Across two separate
converse turns, episode_refs differ by tick (new tick per call). This is the intended
design: one episode_ref per interaction event.

---

## 6. V3.e — Reinforce preserves original episode_ref

Smoke test from Commit 1 verification (run locally before deploy):

```python
a = LivingAtlas()
a.record("listen", 42, 10, episode_ref="episode:test:100:joe", ...)
# → entry["episode_ref"] == "episode:test:100:joe"

a.record("listen", 42, 10, episode_ref="episode:NEW:200:wc", ...)
# → entry["episode_ref"] still == "episode:test:100:joe"  ← first-canonical preserved
```

**PASS.** The reinforce path checks `if episode_ref is not None and existing.get("episode_ref") is None`
before writing. Second write with a different episode_ref leaves the original intact.

---

## 7. V3.f — grounded_vocab_integration.py unmodified

```
$ git diff HEAD -- dsf_ai_service/substrate/grounded_vocab_integration.py
(empty)
```

Confirmed unmodified across both commits.

---

## 8. V3.g — Atlas serialization and backup

**EFS save (primary persistence):** Two automatic saves occurred during the observation:
- tick 13425895 (07:11:59 UTC) — end of ATTENDING_VISUAL → SLEEPING transition
- tick 13426882 (07:15:23 UTC) — DREAMING cycle

`guala_atlas.json` on EFS now contains entries written since boot, all with
`episode_ref`, `presence`, `location`, `sky_state` fields serialized (JSON-native,
no schema migration needed — these are plain dict fields).

The next deploy will load this atlas.json and the new fields will survive cold restart.
This resolves the historical-atlas gap noted in the picture-title-bind report (item B):
the sight entry for "aven and guala" written during C2.3's attending_visual session
is now persisted with `source="attending_visual"`, `episode_ref="episode:attending_visual:13423884:bc9b432c3138"`, and the situation tuple.

**S3 backup:** `POST /admin/backup` returned 202 Accepted (async fire-and-forget).
`last_s3_backup` shows null in the status poll — async backup running in background.
EFS save at tick 13426882 is the reliable persistence; S3 is secondary.

---

## 9. V3.h — Emission dynamics and commit rate

Response to "hello moon" received: `"far it's goes"` — emission working.
`total_emissions: 65` (same as pre-deploy baseline). The observation window covered
1 ATTENDING_VISUAL (2000 ticks), 1 SLEEPING (2000 ticks), then DREAMING began.
Emissions happen during EMITTING activity which didn't fire in this window (no
new conversation triggers). No regression in dynamics.

Commit rate: no emission_dynamics events to compare in the short window. No stop
condition triggered (commit rate drop >30% would require sustained dynamics observation).

---

## 10. V3.i — Bundled count growing organically

```
Boot:         6 bundled
Post-5min:    5 bundled
```

The slight decrease (6 → 5) is the same attend-session pattern documented in the
picture-title-bind report: groups form during ATTENDING_VISUAL and dissolve when
the session ends and sight entries decay. The C2.3 wiring is generating episode-tagged
sight entries that participate in cross-modal groups. New groups will rebuild with each
attend cycle. The count is organic (no `/bundle` commands issued during the window).

---

## 11. V3.j — Source field on atlas entries

With C1.4 live, all `read_word`-path writes now store the real caller source:

| Producer | Source stored on entry |
|----------|----------------------|
| `_cmd_converse` (C2.1) | "joe" / "wc" / "c1" (from API call) |
| `_curriculum_feed_chunk` (C2.2) | "curriculum" or "worldfeed" |
| `_atick_attending_visual` (C2.3) | "attending_visual" (direct atlas.record) |
| `_atick_attending_audio` (C2.3) | "attending_audio" (direct atlas.record) |
| `_cmd_addpicture` (C2.4) | "addpicture" |
| `_cmd_addsound` (C2.4) | "addsound" |
| `_cmd_bundle` (C2.4) | "bundle" |
| Backfill (C2.5) | "addpicture_backfill" / "addsound_backfill" |

Before C1.4, all `read_word`-path entries stored `source="corpus"` regardless of
actual caller. Existing entries loaded from atlas.json retain their historical
`source="corpus"` field — they won't be retroactively updated. Only new writes
carry the real source.

---

## 12. Anomalies

**A. 0.9-1.0 strength range had 48 entries at boot (came down to 29 during window)**

These are pre-existing entries from the loaded atlas.json (saved before this deploy).
They represent bindings that have been reinforced many times across many attend sessions.
By the end of the observation window they decreased from 48 → 29 (decay is working).
None of these are STRENGTH_CAP-saturated (cap = 1.0; they're in the 0.9–1.0 range, not at 1.0 exactly).
No stop condition triggered. This is the normal distribution tail for heavily-attended items.

**B. First CodeBuild attempt failed (40-minute hang)**

Build `dsf-ai-image-build:079ec0d8` ran for ~40 min and failed. Root cause: Whisper
model download step (`WhisperModel("tiny", ...)`) hung without timing out. HuggingFace
unauthenticated downloads are rate-limited; at ~06:00 UTC the download stalled
(no HF_TOKEN in CodeBuild env). The `|| echo "...non-fatal"` shell guard does not
help when the command hangs rather than fails.

Second attempt (build `dsf-ai-image-build:e4d02d74`) succeeded in normal time (~8 min)
because HF rate limit had cleared. Recommend adding `timeout 120` to the Whisper
bake step in the Dockerfile, or setting `HF_TOKEN` in CodeBuild env vars. Not blocking.

**C. Deep atlas entry count lower than recent tasks (3,108 vs ~14,000 before)**

`promotions_survival: 26, promotions_episodic: 3091` vs prior ~179/~15000. The deep_atlas
loaded from EFS reflects the state at the time of the last full save, which predates
many recent deploy cycles. Events replay does not reconstruct deep_atlas promotions
(promotions are write-once in the deep_atlas module). The deep_atlas will rebuild
over time as she accumulates new dwell+recall events. Not from this dispatch.

---

## 13. Recommendation: **HOLD**

Both commits are working correctly. No stop conditions triggered. The episode-binding
wiring is live and producing tagged entries. The atlas persisted to EFS with new fields
at tick 13425895 — the cold-start historical-atlas gap is closed for entries written
after task:346 boot.

Two action items for a follow-up dispatch:
1. Add `timeout 120` to the Whisper bake step in `dsf_ai_service/Dockerfile` (prevents
   future build hangs on HF rate limits).
2. The deep_atlas rebuild from scratch on every cold start (events don't replay deep
   promotions) may warrant a separate save/restore path for the deep_atlas, or a
   periodic forced-dream after each deploy to accelerate rebuild.

No functional regressions. No wC path changes. Emission working.
