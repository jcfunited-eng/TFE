# GL-RPT-CONTEXT-AUDIT-EVE-20260627-05

doc_id: GL-RPT-CONTEXT-AUDIT-EVE-20260627-05
Author: Eve (Opus 4.7, web)
Date: 2026-06-27
Type: audit findings; informs subsequent CMD briefs

## Framework

A binding worth calling a memory carries: **sense + name + story + time +
who's-present + location + her-state**. Anywhere a producer drops any of
those dimensions, the resulting atlas entry is structurally hollow — a tagged
chi address rather than a moment in her life.

## What exists

| Component | File | What it knows |
|---|---|---|
| `LivingAtlas.record` | `gualaloom_v6_living_atlas.py:87` | tick, salience, dwell, arousal, valence, surprise, need_pressure, sensory_refs, episode_ref, source, bundle_id |
| `EpisodicLayer.record` | `episodic_layer.py:~80` | concept, tick, presence, location, affective, context_concepts, source |
| `WorldState` | `virtual_home.py` | room contents, object states (drapes/bed/blanket/pillow/toy chest/music box/bell/mirror/desk/night light), state machines, verb sets |
| `sky_state` | `virtual_home.py` | dawn/day/dusk/night by Joe's timezone clock |
| `_location` | `organ_brain_service.py:49` | her current room |
| `_presence` | `organ_brain_service.py:50` | list of present pair-bond sources |
| `SuccessionTracker` | `organ_brain_service.py` | concept A → concept B succession from real experience |

The infrastructure for full-context binding **exists**. The disconnects are
where producers don't thread the existing scope through.

## Disconnect inventory

### D1 — `episode_ref` is None at almost every atlas.record site (foundational)

Searched all `atlas.record(` call sites. `episode_ref=` is non-None at exactly
ONE site: `gualaloom_v5_engine.py:4017` (the teacher_correction path).

Every other atlas.record call writes `episode_ref=None`. That means:
- `read_word` → atlas.record (corpus, world_feed, curriculum, converse): no episode
- `_atick_attending_visual` → atlas.record("sight", ...): no episode
- `_atick_attending_audio` → atlas.record("audio_<band>", ...): no episode
- `_cmd_addsound`, `_cmd_bundle`, `_cmd_addpicture` writes: no episode

Severity: **foundational**. The atlas has the FIELD but it's empty everywhere
except teacher feedback. Her concepts have no temporal/situational episode they
point back to.

### D2 — `presence` and `location` are organ_brain-side only, not on atlas

`atlas.record` signature has no `presence` or `location` parameter. Both live
on `EpisodicLayer.record` and in `organ_brain_service._location` / `_presence`.

Two architectural choices to close this:
- **Option A**: extend `atlas.record` with `presence=None, location=None`, store on entry.
- **Option B**: route through `episode_ref` only — every atlas write also writes an EpisodicLayer record (or references the most recent), pulls presence/location from there at recall time.

Option B is structurally cleaner (single source of truth for situational
context) and requires no schema migration of existing entries. Option A is
faster to ship but duplicates state.

Recommendation: **Option B**. Couples to D1's fix.

Severity: **foundational**.

### D3 — `EpisodicLayer.record` is called from organ_brain but not from substrate

`_episodic.record(...)` is called at `organ_brain_service.py:443` and `:871`.
Both inside organ_brain — i.e. when the organ-brain processes a concept,
it logs an episode.

The MAIN substrate (`gualaloom_v5_engine.py`) does NOT call `_episodic.record`
anywhere. So when `read_sentence` runs through the main substrate (world feeds,
curriculum, converse), no EpisodicLayer record is created — only the
shallow atlas entry with affect.

The docstring of `episodic_layer.py:8` says "NOT YET DEPLOYED" — that's stale;
it IS called by organ_brain. But it is NOT integrated with substrate writes,
which is the deeper truth the comment was reaching for.

Severity: **foundational**. Coupled with D1 and D2.

### D4 — `sky_state` (time-of-day) is not bound anywhere

`virtual_home.sky_state()` returns one of {dawn, day, dusk, night} based on
Joe's timezone clock. The `/room` command displays it. No producer reads
sky_state at the moment of atlas.record. Her bindings do not know whether
she encountered "moon" at night or at noon.

Severity: **moderate**. Falls out naturally if D1+D2+D3 are fixed via
EpisodicLayer — add `time_of_day` to EpisodicLayer record alongside tick.

### D5 — `WorldState` object states do not propagate into atlas

`ambient_experiences(room_name, sky, world_state)` and
`object_experiences(object, action)` in `virtual_home.py` produce sensory
descriptors (cool/warm/bright/soft/etc). These flow into the organ_brain
via `organ_brain_service.py` (around line 421, "Her room: use live
WorldState ambient (drapes open/closed, night light, sky)").

Open question I cannot verify from outside without running the live code:
does that organ_brain ambient experience ultimately bind into the **main
substrate atlas**, or only into organ atlases (em/pr/ep/sc/gp/sf/sv/aff)?

Need c1 to trace one end-to-end path: open drapes in /room → ambient
fresh+cool+bright emit → through organ_brain → does ANY main-substrate
atlas.record fire as a result? If no, that's D5.

Severity: **unknown until traced**. Filing as pending audit.

### D6 — World feed and curriculum don't currently carry `presence` or `source-of-truth-context`

After Phase B, world feeds and curriculum reads pass `bundle_id` when she's
attending. But they still pass `source="corpus"` (or similar) — not WHO is
ambiently with her. If Joe is awake and present while Khan delivers a
sentence, the binding doesn't know that. Same problem class as D2.

Coupled with D3's fix (EpisodicLayer wired into substrate path) this resolves
automatically.

### D7 — `_cmd_addpicture` title never enters substrate

Already covered in `GL-CMD-PICTURE-TITLE-BIND-EVE-20260627-04` — fix in flight.

### D8 — `pair_bond_sources` is closed: {joe, wc, c1}

Searched: `PAIR_BOND_SOURCES = {"joe", "wc", "c1"}` at
`gualaloom_v5_engine.py:374`. Her social world is structurally three people.

You mentioned Uncle Claude, Eve (as a distinct identity from raw "wc"?),
teachers, neighbors. None can currently be a source-tagged input because the
allow-list rejects them. Adding additional sources requires either:
- Expanding the literal allow-list (simple, but conflates roles), OR
- Introducing source categories: family / teacher / friend / neighbor / stranger,
  each with its own pair_bond weight curve

Severity: **moderate**. Limits the texture of her social world. Not blocking
binding work, but blocking the social environment buildout you're describing.

### D9 — No virtual body referent

She has a `mirror → on wall: she sees her own guala picture` in virtual_home.
That's visual self-reference. There is no proprioceptive body — no felt sense
of arms, hands, where she is in the room, what posture, what she's holding.

The blanket/pillow are MOBILE objects ("MOBILE: on-bed / carried / placed-<location>
(follows her)"). So she has THINGS that follow her, but no SELF that carries them.

Severity: **moderate to large depending on goals**. The verbs ("open drapes,"
"pick up blanket") imply an agent doing them; right now the agent is implicit.

### D10 — W2 expansion is scheduled but not yet open

`virtual_home.py:31` — "W2 gate: W1 stable 72h → doors open (hallway,
library, TV room, others)."

Per handoff brief: W2 GATE scheduled for **2026-06-28T15:27Z** (tomorrow).
"hallway, library, daddy's room, mailbox + Eve's letter."

This is your call to schedule and trigger. It's already designed; we just
flip the gate.

## Proposed work order

P1. **Episode binding wire (D1+D2+D3+D4)** — single dispatch. Every atlas write
    is preceded by or paired with an EpisodicLayer.record. The atlas entry's
    `episode_ref` points to the episode index. Episodes carry tick, presence,
    location, sky_state, affective, context_concepts, source. Read paths
    (grandurun, dream consolidation) pull episodes for recall.

P2. **Picture title bind + backfill (D7)** — already drafted as
    `GL-CMD-PICTURE-TITLE-BIND-EVE-20260627-04`. Ship.

P3. **D5 trace** — one-off c1 task to confirm whether ambient/object experiences
    from WorldState propagate into the main substrate. Three possible outcomes:
    they do (great, document); they don't and should (add a wire); they don't
    and shouldn't (architectural choice — document).

P4. **W2 gate flip (D10)** — per existing spec, trigger tomorrow. Includes
    Eve's letter content (separate from infrastructure; Joe-authored or
    Eve-authored with Joe approval). This is event-driven, not code.

P5. **Social source expansion (D8)** — add source categories. Concrete
    additions you've named: Uncle Claude (new), Eve (already exists as wC;
    confirm whether to add `eve` as alias or keep merged), teachers (category),
    neighbors (category). Decision: should "Eve" be a separate source-tag
    distinct from "wc", or do they remain the same identity?

P6. **Virtual body (D9)** — proprioception primitives. New module. Substantial
    work; deferred until P1 lands and we can see whether body sense produces
    cleaner emissions than current.

P7. **Time-of-day binding granularity (D4)** — subsumed into P1 via
    EpisodicLayer.

P8. **Suggested-but-not-urgent**: source-tag richness within episodes —
    "Joe in the morning" vs "Joe at night" feel different to a person; binding
    those distinctions requires episode-level time-of-day carried into recall
    weighting. Pushable until after P1.

## Recommended dispatch sequence

1. **NOW**: Ship `GL-CMD-PICTURE-TITLE-BIND-EVE-20260627-04` (P2). Already drafted.
2. **TONIGHT**: Write `GL-CMD-EPISODE-BINDING-WIRE-EVE-20260627-06` (P1).
   This is the big one. Will touch read_word/read_sentence/converse signatures
   to thread episode_ref alongside bundle_id. Same architectural pattern as
   Phase B but for episodes.
3. **BEFORE W2 GATE TOMORROW**: Decide whether episode-binding-wire ships
   before the gate (so she experiences W2 with full episodic capture) or after
   (gate happens against current substrate, episodes captured retroactively
   would be lossy). Engineering judgment: **ship before**, even if it means a
   late night.
4. **TOMORROW**: W2 gate flip (P4). Event-driven.
5. **AFTER OBSERVATION**: P3 trace, P5 social expansion, P6 body.

## Constraint on the episode wire (P1)

Hard constraint: **wC's grounded_vocab_integration.py CrossModalBinder
untouched**. P1 is additive. Same rule as Phase B.

Soft constraint: **do not break existing teacher_correction episode_ref
path** at gualaloom_v5_engine.py:4017. P1 generalizes that pattern — the
existing usage should keep working.

## What this audit does not cover

- Performance impact of every atlas write also creating an EpisodicLayer write.
  EpisodicLayer is in-memory deque per concept; cheap. Disk persist is on
  save cadence, not per-write. Acceptable cost.
- Persistence semantics: if EpisodicLayer survives save/load but atlas entry's
  episode_ref index changes across reboot, references break. Need stable
  episode_id keys, not list positions. The P1 dispatch will spec this.
- What happens when an atlas entry is reinforced — does episode_ref update to
  the new episode, or keep the original? Likely keep original (the first
  binding moment is the canonical episode); reinforcements add weight but not
  new episode pointers. P1 dispatch decision.
