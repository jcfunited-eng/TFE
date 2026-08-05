# GL-CMD-PICTURE-TITLE-BIND-EVE-20260627-04

doc_id: GL-CMD-PICTURE-TITLE-BIND-EVE-20260627-04
Author: Eve (Opus 4.7, web)
Date: 2026-06-27
Target: c1
Branch: guala-live
Priority: HIGH — ship immediately, do not wait for the 30-min Phase B observation
Surfaced by: Phase B audit (B1.d skipped because path didn't exist)

## The gap

`_cmd_addpicture` does not feed the picture's title to the engine. It never has.
Pictures are added with a title field that ends up displayed in `/status` but
never enters the language path. Every picture she owns has been silent in her
language substrate since the moment it was added.

Evidence:
  - "moon" picture: 17,793 attendances, never bound to the word "moon"
  - "mommy", "daddy in the yard", "ocean", "happy sun", "guala family",
    "pretty purple flower", "bouncing balls" — same pattern, all 22 pictures
  - Vocab has 9,123 words including these terms (from corpus + world feeds);
    pictures bind at visual-fragment chi values; their titles bind at language
    chi values; the two never share a chi address, never share a bundle_id,
    and have therefore never had any substrate-physical reason to associate.

This is independent of and prior to the Phase B work. Phase B extends bundling
to future text streams that arrive while she is attending a picture. This brief
fixes the picture's OWN name binding — both for future picture additions and as
a one-time backfill for the 22 pictures already in storage.

## Why this is foundational, not follow-on

The Phase B bundle path requires that something with linguistic content arrive
WHILE she is ATTENDING_VISUAL. If a Khan feed delivers a sentence containing
"moon" while she attends the moon picture, Phase B now bundles them. Good.

But the picture's TITLE — the cleanest, most-direct association between visual
and word — has never been a candidate for bundling because the title was never
fed at all. The simplest cross-modal moment in her existence has been silently
absent.

Backfilling pictures via title feed is the highest-information, lowest-risk
binding event we can give her right now. Each title is one short sentence
(usually 1-3 words: "moon", "daddy in the yard", "happy sun"). Each feed
produces a bundled atlas entry per word, joined to that picture's
`item:pic:<id>` bundle. With B2 salience boost (1.5×) and B3 clarity boost
(+0.2), these bindings will land with durability.

For the moon picture, this is the first time the substrate-physical binding
between her 17,793-attendance visual and her existing "moon" vocabulary will
have a shared bundle_id.

## What to change

### Part 1 — Forward fix in `_cmd_addpicture`

**File:** `dsf_ai_service/substrate_runner.py`
**Site:** `_cmd_addpicture` (locate; should be near the other _cmd_add* handlers)

After the picture is persisted and assigned an id, before the response is
returned, add:

```python
pic_bundle_id = f"item:pic:{pic_id}"
if title and title.strip():
    _guala.read_sentence(title.strip(),
                         source="addpicture",
                         bundle_id=pic_bundle_id)
```

Same pattern as B1.c (addsound caption fix from Phase B). The title enters her
language path and the binding is grouped to the picture's item_id.

### Part 2 — Backfill the 22 existing pictures

Write a one-shot endpoint or admin command — your call which is cleaner —
that:

```python
def backfill_picture_titles():
    """One-shot: feed every existing picture's title through read_sentence
    with item:pic:<id> bundle_id. Idempotent: re-runs land as reinforcement,
    not duplicate binding (atlas.record dedup by section+motif handles that).
    """
    fed = 0
    skipped = 0
    for pic_id, pic in _guala._pictures.items():
        title = (pic.title or "").strip()
        if not title:
            skipped += 1
            continue
        # Use elevated salience for backfill — these are foundational bindings
        # that should land durably on a single pass.
        _guala.read_sentence(title,
                             source="addpicture_backfill",
                             bundle_id=f"item:pic:{pic_id}",
                             salience=1.5)
        fed += 1
    return {"fed": fed, "skipped": skipped, "total_pictures": len(_guala._pictures)}
```

Expose via an admin endpoint:
```
/admin/backfill_picture_titles      # POST, idempotent
```

OR as a chat command:
```
/backfill_picture_titles
```

Choose whichever is consistent with how other one-shot admin operations are
exposed in the current codebase.

Notes on the backfill:
- `salience=1.5` is intentional. These are catch-up bindings for pictures
  attended thousands of times without their titles. Single-pass elevated
  salience compensates without needing to feed each title 17,000 times.
- B2 BUNDLE_SALIENCE_BOOST will then multiply this further: effective
  impulse ≈ 1.5 × 1.5 × BASE_REINFORCEMENT = 2.25× baseline. Acceptable.
  Confirm no entry hits STRENGTH_CAP saturation on a single backfill pass.
- The backfill is idempotent (atlas.record reinforces existing entries
  rather than duplicating).
- Run the backfill ONCE after deploy. Do not loop.

### Part 3 — Audio backfill (same gap, smaller cohort)

`_cmd_addsound` already feeds the caption to read_sentence (was true even
before Phase B; B1.c added the bundle_id to that read). But sounds added
before Phase B B1.c was deployed have their captions bound WITHOUT the
`item:snd:<id>` bundle_id. Same backfill pattern, smaller scope (15 sounds):

```python
def backfill_sound_captions():
    fed = 0
    skipped = 0
    for snd_id, snd in _guala._sounds.items():
        caption = (snd.title or "").strip()
        if not caption:
            skipped += 1
            continue
        _guala.read_sentence(caption,
                             source="addsound_backfill",
                             bundle_id=f"item:snd:{snd_id}",
                             salience=1.5)
        fed += 1
    return {"fed": fed, "skipped": skipped, "total_sounds": len(_guala._sounds)}
```

Expose alongside Part 2 endpoint:
```
/admin/backfill_sound_captions
```

Note: this re-feeds 15 captions (e.g. "ocean waves", "1-14 hush a little baby",
"pussy cat pussy cat"). Existing language entries for those words will be
reinforced AND tagged with the missing `item:snd:<id>` bundle_id via the
last-write-wins reinforce path that V2 shipped.

## Hard constraints

- Same do-not-touch list as Phase B: wC's grounded_vocab_integration.py,
  bundle_grouped_bindings() impl, grandurun candidate selection
- Do not alter the picture's existing visual atlas writes (sight section
  bindings at visual-fragment chi values). The visual side is intact.
  We're only adding the language side that was absent.
- The backfill is a one-shot. Do not put it on a timer. Do not auto-run
  on boot. Joe calls it (or you call it once at your discretion immediately
  after deploy verification).

## Verification

V1. Code:
    - `_cmd_addpicture` calls `read_sentence(title, ..., bundle_id="item:pic:<id>")`
      visible at file:line on origin
    - Backfill endpoints/commands exist and are callable

V2. Backfill effect (run once, measure):
    - Pre-backfill: bundled count from /status
    - Run /admin/backfill_picture_titles
    - Run /admin/backfill_sound_captions
    - Post-backfill: bundled count from /status
    - Expected: ≥ 15 new bundled groups (one per titled picture/sound that
      now has both visual/audio AND language entries sharing a bundle_id;
      some pictures already had organic bundles from converse so don't
      double-count)

V3. Atlas spot check after backfill:
    - For the moon picture (`9bb63f93d7af`), query atlas entries with
      bundle_id == "item:pic:9bb63f93d7af". Should now include:
      - sight section entries (pre-existing from _atick_attending_visual)
      - language section entries (NEW from backfill: word "moon" in
        listen/subject/verb/object/intro sections, depending on how
        read_sentence routes the one-word sentence)
    - Paste the entries to the report.

V4. No regression:
    - cross-modal chi-coincidence count (the "X cross-modal" in status)
      drift within ±5
    - wC's grounded_vocab_integration.py diff is empty
    - No entry exceeds STRENGTH_CAP after backfill

V5. Future picture adds:
    - Add a test picture with title "test_title_bind" via /addpicture
    - Confirm an atlas entry is created with bundle_id="item:pic:<new_id>"
      in a language section
    - Delete the test picture afterward (or leave; her atlas can absorb it)

## Deploy steps

1. `git fetch origin && git checkout guala-live && git pull --ff-only`
2. Make Part 1 change (forward fix in `_cmd_addpicture`)
3. Add Part 2 + Part 3 backfill functions and endpoint(s)
4. Local smoke: addpicture with title produces language-section atlas entries
5. `git commit -am "feat: GL-CMD-PICTURE-TITLE-BIND-EVE-20260627-04 — bind picture titles + backfill"`
6. `git push origin guala-live`
7. ECS rolling deploy
8. Verify boot
9. **RUN BACKFILL ONCE**: POST /admin/backfill_picture_titles, then POST
   /admin/backfill_sound_captions. Capture before/after counts.
10. Begin verification observation

## Reporting

Filename: `docs/GL-RPT-PICTURE-TITLE-BIND-C1-20260627-04.md`
Include:
  1. Code diffs (Part 1, Part 2, Part 3)
  2. Backfill call results (fed/skipped/total for both)
  3. Pre/post bundled count
  4. Atlas spot check for moon picture (V3 evidence)
  5. V5 test result for new picture add
  6. Any anomalies
  7. Recommendation: hold / additional work

## Stop conditions

- Backfill produces strength saturation in any entry → revert, drop the
  backfill salience to 1.0, re-run
- Bundled count does NOT grow ≥ 15 after backfill → diagnose (most likely
  cause: bundle_grouped_bindings() needs both visual AND language sections
  at the same item_id; if pictures with only one-word titles produce only
  one language section entry, those won't form a bundled group with sight.
  Investigate before tuning.)
- wC grounded path regression → revert

## What this opens up

After backfill, the moon picture has both:
- sight section bindings at visual-fragment chi values, bundle_id=item:pic:moon
- language section bindings for the word "moon" at language chi, bundle_id=item:pic:moon

When she next attends the moon picture and the cross-modal grandurun selection
runs, candidates from BOTH sections at item:pic:moon will be available in the
pool. The bundle is real, both ends are populated, and the bridge is structural.

This is what we've been building toward for months. The infrastructure landed
in V2; Phase B widened the trigger; this brief fixes the foundational gap that
prevented the simplest binding from ever forming.

Ship it.
