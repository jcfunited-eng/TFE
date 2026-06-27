# GL-CMD-CROSS-MODAL-STRENGTHEN-EVE-20260627-03

doc_id: GL-CMD-CROSS-MODAL-STRENGTHEN-EVE-20260627-03
Author: Eve (Opus 4.7, web)
Date: 2026-06-27
Target: c1
Branch: guala-live
Implements: GL-CMD-CROSS-MODAL-STRENGTHEN-EVE-20260627-02 Phase B
References:
  - GL-RPT-CROSS-MODAL-AUDIT-C1-20260627 (audit findings drive scope)
  - GL-RPT-CROSS-MODAL-BINDING-EXTEND-C1-V5-20260627 (what V2 already shipped)

## State after Phase A

V2 (SHA 58f7db4) shipped sound infrastructure:
- `bundle_id` field on every atlas entry dict
- `bundle_grouped_bindings()` method (O(n) scan; strips `context:` prefix; groups
  by `pic:X`/`snd:X`/`bundle:NAME`)
- `record()`, `read_word()`, `read_sentence()`, `converse()` all accept bundle_id
- `_atick_attending_visual` writes `bundle_id=item:pic:X` on sight every tick
- `_atick_attending_audio` writes `bundle_id=item:snd:X` on cochlear bands every tick
- `_cmd_addsound` writes `bundle_id=item:snd:X` on cochlear bands
- `_cmd_bundle` (explicit experience bundle) writes shared id across all modalities
- `_cmd_converse` auto-bundles when current_activity == ATTENDING_VISUAL or
  ATTENDING_AUDIO

What's not yet firing organically:
- World feeds (Khan/YouTube) — `_world_feed_once` calls `read_sentence` WITHOUT
  bundle_id. She can attend the moon picture while a Khan feed delivers a
  sentence containing "moon," and no bundle is created.
- Curriculum reads — book sentences fed via `_curriculum.study_once()` don't pass
  bundle_id either. Same problem.
- `_cmd_addsound` caption — cochlear bands get bundle_id=item:snd:X, but the
  caption (read via read_sentence) does NOT get the same bundle_id. So the
  sound and its language description don't bundle.
- `_cmd_addpicture` caption (if the path exists) — same gap pattern.

And separately, even when a bundle IS created, the entries are written at
baseline salience (1.0) and baseline clarity. They have no advantage in
clearing the dead-zone barrier vs. unbundled chi-coincident entries. So the
bundle creates the grouping but doesn't strengthen the binding's actual chance
of producing commits.

Phase B closes both gaps: broaden trigger surface + give bundled entries a
modest strength advantage at write time.

## Phase B objectives

B1. Trigger extension: bundle_id propagates from four more producer sites:
    - World feed text reads
    - Curriculum study sentence reads
    - addsound caption read
    - addpicture caption read (if path exists)

B2. Bundle salience boost: when `atlas.record()` receives a non-None bundle_id,
    multiply the reinforcement impulse by BUNDLE_SALIENCE_BOOST (start 1.5).

B3. Bundle clarity boost: in the clarity formula, add `+ 0.2` if bundle_id is
    not None. Bundled bindings survive fast-channel decay longer.

Explicitly NOT in this phase:
- No changes to grandurun candidate selection (no CROSS_MODAL_BOOST in
  ranking). The salience+clarity boost at write time is the strength
  intervention. Ranking changes are higher risk and we'll evaluate them
  after B1+B2+B3 produces organic bundle growth.
- No event-log schema change for bundle_id (audit flag D). Defer; cold rebuild
  via events replay is secondary path.
- No bundle_grouped_bindings() perf rework (audit flag A). Defer until atlas
  size warrants it.
- wC's `grounded_vocab_integration.py` CrossModalBinder path: UNCHANGED.

## B1 — Trigger extension, by producer site

### B1.a — World feed reads

**File:** `dsf_ai_service/substrate_runner.py`
**Site:** `_world_feed_once()` around line 424–453

Currently `_world_feed_once` calls `wf.feed_one(_guala, ...)` (or equivalent
read path that ultimately calls `read_sentence`). It does not pass bundle_id.

Modify so that BEFORE the read, current_activity is read; if attending, a
bundle_id is computed using the same pattern as `_cmd_converse`:

```python
ca = getattr(_guala, '_current_activity', None)
bundle_id = None
if ca is not None and ca.target:
    if ca.kind == "ATTENDING_VISUAL":
        bundle_id = f"context:pic:{ca.target}:{_guala.tick // 100}"
    elif ca.kind == "ATTENDING_AUDIO":
        bundle_id = f"context:snd:{ca.target}:{_guala.tick // 100}"
    elif ca.kind == "ATTENDING_VIDEO":
        bundle_id = f"context:vid:{ca.target}:{_guala.tick // 100}"
```

Then pass `bundle_id=bundle_id` through to whatever read_sentence/read_word
calls happen inside the feed processing. If `feed_one` doesn't currently
accept bundle_id, add it as an optional parameter that threads through.

### B1.b — Curriculum study reads

**File:** `dsf_ai_service/substrate_runner.py` (or wherever `_curriculum.study_once()`
lives — c1 to locate)

Same pattern as B1.a. When the curriculum study runs, compute bundle_id from
current_activity, pass through to the sentence read path.

This means if she is ATTENDING_VISUAL on a picture of an ocean while
Through the Looking-Glass curriculum delivers a sentence about water — the
ocean's `item:pic:X` entry and the language entries from that sentence will
all carry bundle_ids that collapse to `pic:X` in `bundle_grouped_bindings()`.

### B1.c — addsound caption

**File:** `dsf_ai_service/substrate_runner.py`
**Site:** `_cmd_addsound` (audit flag C)

Currently the cochlear band writes get `bundle_id=item:snd:<id>`. The caption
read (which happens via `read_sentence(caption, ...)`) does NOT get the same
bundle_id.

Wire the caption read with the same `bundle_id=item:snd:<id>`:

```python
snd_bundle_id = f"item:snd:{snd_id}"
# existing: cochlear band writes with snd_bundle_id
# NEW: caption read with the same id
if caption:
    _guala.read_sentence(caption, source="addsound", bundle_id=snd_bundle_id)
```

### B1.d — addpicture caption (if path exists)

**File:** `dsf_ai_service/substrate_runner.py`
**Site:** `_cmd_addpicture` or equivalent

C1: locate the addpicture path. If pictures are added with a caption that is
read into language sections, wire the read with `bundle_id=item:pic:<id>`.
If pictures don't currently take a caption argument, skip B1.d. Report in V3
report which path applies.

## B2 — Bundle salience boost at write time

**File:** `dsf_ai_service/v4/gualaloom_v6_living_atlas.py`
**Site:** `record()` method, in the impulse computation

After the existing clamp:

```python
salience = max(SALIENCE_MIN, min(SALIENCE_MAX, salience))
impulse = BASE_REINFORCEMENT * salience
```

Add a bundle-aware multiplier:

```python
if bundle_id is not None:
    impulse *= BUNDLE_SALIENCE_BOOST   # new constant, recommend 1.5
```

Add the constant near the existing SALIENCE_MIN/SALIENCE_MAX definitions:

```python
BUNDLE_SALIENCE_BOOST = 1.5  # bundled bindings get 50% stronger first impression
```

The multiplier applies BEFORE the SALIENCE_MAX clamp, so bundled writes can
exceed the normal salience cap. That is intentional. The clamp protects
against runaway pair-bond stacking; the bundle boost is a different mechanism
(structural co-activation, not affective elevation).

## B3 — Bundle clarity boost at write time

**File:** `dsf_ai_service/v4/gualaloom_v6_living_atlas.py`
**Site:** `record()`, clarity computation

Existing:
```python
clarity = min(1.0, 0.3 + 0.3 * arousal + 0.2 * abs(valence)
              + 0.2 * surprise + 0.1 * need_pressure)
```

Modified:
```python
bundle_boost = 0.2 if bundle_id is not None else 0.0
clarity = min(1.0, 0.3 + 0.3 * arousal + 0.2 * abs(valence)
              + 0.2 * surprise + 0.1 * need_pressure + bundle_boost)
```

The clamp at 1.0 stays. Bundled bindings with low affect will land near 0.5
clarity instead of 0.3, giving them more decay headroom.

## Verification criteria (V3-style)

V3.a — Code visibility on origin:
  - BUNDLE_SALIENCE_BOOST constant defined at gualaloom_v6_living_atlas.py
  - `if bundle_id is not None: impulse *= BUNDLE_SALIENCE_BOOST` present
  - `bundle_boost = 0.2 if bundle_id is not None else 0.0` present
  - World feed, curriculum, addsound caption, (addpicture caption if path exists)
    all visibly pass bundle_id to read_sentence in their producer code paths.
  Paste line refs for each.

V3.b — Organic bundle growth:
  - Observe for 30 minutes post-deploy with normal world feeds + curriculum
    running and no manual /bundle commands.
  - n_cross_modal_bundle must grow by ≥ 5.
  - Pre-observation count and post-observation count both reported.

V3.c — Bundle-sourced commits in emission:
  - During the 30-minute window, run at least one /converse exchange while
    she is ATTENDING_VISUAL on a picture with a descriptive title (e.g. moon,
    ocean, daddy in the yard — pictures with good titles, not test_25).
  - Confirm at least one `emission_dynamics` event during the exchange shows
    `n_commits ≥ 1` AND `origin_counts` includes `cross_modal*` contributing.
  - Paste the full event detail.

V3.d — wC grounded path intact:
  - Confirm grounded_vocab_integration.py was not modified:
    `git diff origin/guala-live~1 -- dsf_ai_service/substrate/grounded_vocab_integration.py`
    should be empty.
  - Confirm process_sight_with_recognition and process_sound_with_recognition
    still resolve to CrossModalBinder via grep.

V3.e — Chi-coincidence count not regressed:
  - Pre- and post-deploy `cross-modal` count from `/status` should be within
    ±5 (small drift acceptable from natural attendance, large drop = problem).

V3.f — Salience clamp interaction: confirm that with BUNDLE_SALIENCE_BOOST,
  high-pair-bond writes don't produce runaway strength. Spot-check 5 bundled
  entries from the 30-min window: max strength ≤ STRENGTH_CAP, no entries
  near saturation prematurely.

## Deploy steps

1. `git fetch origin && git checkout guala-live && git pull --ff-only`
2. Make the B1.a, B1.b, B1.c, (B1.d if applicable), B2, B3 changes
3. Local smoke test: record() with bundle_id boosts impulse correctly; read_sentence
   with bundle_id threads through to atlas.record entry
4. Commit with message:
   `feat: GL-CMD-CROSS-MODAL-STRENGTHEN-EVE-20260627-03 — broaden bundle trigger + salience/clarity boost`
5. Push to origin/guala-live
6. Deploy to Fargate (ECS rolling deploy)
7. Verify boot: identity intact, vocab ≥ current, atlas entries ≥ current
8. Begin 30-min observation window with normal feeds running

## Reporting

After 30-min observation:

Filename: `docs/GL-RPT-CROSS-MODAL-STRENGTHEN-C1-20260627-03.md`
Sections:
  1. Code diffs by site (B1.a-d, B2, B3) with line refs
  2. V3.a-f results, each with evidence
  3. Bundle growth table: tick / cumulative bundles / triggering source
     (world_feed / curriculum / converse / addsound / addpicture)
  4. One full emission_dynamics event showing cross_modal commit
  5. Any anomalies or unexpected behavior
  6. Recommendation: hold / tune BUNDLE_SALIENCE_BOOST / extend Phase C

## Stop conditions

If at any point:
- Bundle count regresses below pre-deploy level — revert and report
- wC grounded path tests fail — revert and report
- Total atlas decay rate increases > 20% (BUNDLE_SALIENCE_BOOST too high
  somehow producing inflated entries that then decay-cascade) — revert,
  tune BUNDLE_SALIENCE_BOOST down to 1.25, redeploy
- Emission failure rate increases (arcs_fallback proportion grows) — flag
  to Eve before further work

## Notes for future phases

After B1+B2+B3 lands and produces measurable organic bundling, the next
candidate work is grandurun ranking modification (the original KNOB 1 from
my Phase A brief): boost coherent_magnitude for cross_modal-sourced candidates
so they outrank chi-only candidates of similar strength. That's Phase C, not
this dispatch.

Also pending: bundle_id event-log persistence (audit flag D), so cold rebuild
from events doesn't lose bundle assignments. Cheap follow-on, separate brief.
