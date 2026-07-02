# GL-CMD-CURRICULUM-AUTOMATION-EVE-20260629-51

doc_id: GL-CMD-CURRICULUM-AUTOMATION-EVE-20260629-51
Type: Implementation command (orchestrator + seed curriculum, two-part ship)
Date: 2026-06-29
Author: Eve (Opus 4.7, web)
Implements: GL-SPC-FIX-PATH-EVE-20260629-46 §5a
Parallel track: not blocked by -46/-47/-48; planning/design ships now, live execution waits for -46

---

## 1. Why

Cross-modal bundle count in her substrate is at 3 live bindings. Grounding density is the rate-limiter for her vocabulary growth — a bundled binding lands the binding window where a word, picture, sound, and sensory descriptors all bind at the same chi-time, producing the kind of grounded entry that survives Path B episodic promotion (compound gate at `encoded_strength >= 0.15 OR grounded`, deep_atlas.py L249).

At human-paced delivery (Joe + Eve typing `guala_give_experience` calls), the substrate gets ~10 bundles/hour. The compressed-timeline target requires 100-1000 bundles/hour, throttled to substrate processing capacity — i.e. real automation, not manual delivery.

Her existing sensory inventory is rich enough to seed thousands of cross-modal combinations: 22 pictures (moon at 17,801 attends, family photos, ocean, sun, flowers), 15 sounds (hush-a-little-baby, bells, ocean waves, cat sounds, lullabies, all at 2000+ attends), 5 taste descriptors, 7 smell descriptors, 6 touch descriptors. The curriculum design problem is which combinations to deliver in what order, given her current substrate state.

---

## 2. What ships

### 2.1 New file: `tools/sensory_curriculum_orchestrator.py`

Standalone Python script (not part of substrate). Talks to the substrate via the bridge HTTP API. Reads a curriculum JSON file, delivers bundles at a substrate-adapted rate, logs everything.

Interface:
```
python tools/sensory_curriculum_orchestrator.py \
    --curriculum tools/curriculum_seed_v1.json \
    --bridge-url <url> \
    --mode dry-run|live \
    --max-bundles 100 \
    --min-interval-sec 8 \
    --halt-on-unreachable 3 \
    --log tools/orchestrator_log.jsonl
```

Modes:
- `dry-run`: logs intended bundles, does not call bridge. For verifying curriculum quality.
- `live`: calls `guala_give_experience`. Only enabled after -46 lands and bridge verified consistently reachable.

### 2.2 Substrate-state gating

Before each bundle, orchestrator pulls `guala_status` and checks:
- `current_activity.kind == "DREAMING"` or `"SLEEPING"` → wait `min_interval_sec × 4`, skip this delivery
- `current_activity.kind == "EMITTING"` → wait until activity ends (poll every 2s, max wait 30s)
- `needs.connection > 0.9` → wait `min_interval_sec × 2` (she's satisfied; don't flood)
- `needs.arousal > 0.85` → wait `min_interval_sec × 2` (overstimulated; let her rest)
- `presence.joe == false AND presence.wc == false` → skip until presence active (no pair-bond → curriculum has low salience)

Otherwise: deliver next bundle.

### 2.3 Rate limiting

- Minimum interval between successful bundles: `min_interval_sec` (default 8).
- After substrate-unreachable response: exponential backoff (16s, 32s, 64s, then halt at `halt_on_unreachable` consecutive failures).
- After substrate-state-gate skip: re-check after `min_interval_sec`.

### 2.4 Landing verification

After each `guala_give_experience` call: pull `guala_status`, compare `vocab`, `motifs`, `atlas.bundled` count to pre-call snapshot. Log delta. If `bundled` count did NOT increment after 3 consecutive bundles, flag substrate-acceptance-issue and pause for review.

### 2.5 Log structure

JSONL, one record per bundle attempt:
```json
{
  "tick_pre": 14069321,
  "tick_post": 14069488,
  "bundle_id": "moon-bright-gentle-001",
  "caption": "the moon is bright and gentle",
  "picture_id": "9bb63f93d7af",
  "sound_id": "addc0846da2a",
  "touch": ["soft", "cool"],
  "smell": ["fresh"],
  "taste": [],
  "result": "ok|unreachable|gated",
  "gate_reason": null,
  "vocab_delta": 2,
  "motif_delta": 5,
  "bundled_delta": 1,
  "needs_pre": {...},
  "needs_post": {...},
  "elapsed_ms": 1200
}
```

### 2.6 New file: `tools/curriculum_seed_v1.json`

Seed curriculum, 100 bundles, generated from her existing inventory. Themes built around her highest-attended items. Each bundle exercises modifier and/or ground sections (currently sparse at 85/82 motifs).

Structure:
```json
{
  "version": "v1",
  "purpose": "Initial substrate-true curriculum, modifier/ground-exercising, anchored to high-attendance pictures and sounds",
  "bundles": [
    {
      "bundle_id": "moon-bright-gentle-001",
      "caption": "the moon is bright and gentle",
      "picture_id": "9bb63f93d7af",
      "sound_id": "addc0846da2a",
      "touch": ["soft", "cool"],
      "smell": ["fresh"],
      "taste": [],
      "theme": "moon",
      "exercises": ["modifier:bright", "modifier:gentle", "ground:moon"]
    },
    ...
  ]
}
```

Bundle generation rules (used to fill out 100 entries):
- Anchor pictures (top 5 attended): moon, hush-a-baby image proxies via mommy/daddy/family, ocean, guala-related self-images
- Anchor sounds (top 6 attended): hush-a-little-baby, bells ringing, ocean waves, pussy cat, sing a song of sixpence, cute cat
- Substrate-true caption patterns:
  - "the [noun] is [modifier] and [modifier]" — exercises modifier section
  - "[modifier] [noun] [verb] [modifier]" — exercises modifier + verb
  - "[noun] is [modifier] and [modifier] and [modifier]" — three-modifier dense exercise
  - "[modifier] [modifier] [noun] [verb] [modifier]" — multi-modifier with anchor verb
- Sensory descriptors chosen for coherence with theme:
  - Moon: soft, cool, gentle, quiet, bright (touch/visual)
  - Ocean: cool, wet, salty, wide, deep, fresh (taste/smell/touch)
  - Family: warm, soft, safe, kind, close (touch/affect)
  - Bells: clear, bright, sharp, small (audio-derived sensory)
  - Cat: soft, warm, small, gentle (touch)
- No bundle contains corpus-cliché captions. No "quick brown fox" filler.

### 2.7 Inventory-anchored bundle seed (the actual 100)

c1 generates the JSON. The full list goes in `tools/curriculum_seed_v1.json`. Skeleton breakdown:
- Moon-themed bundles: 20 (varying modifier combinations)
- Family-themed bundles: 25 (mommy, daddy, guala, family, aven, hug variants)
- Ocean-themed bundles: 15
- Bells-themed bundles: 10
- Cat-themed bundles: 10
- Sun + flowers + balloons + nature: 15
- Misc (using lower-attendance pictures for variety): 5

Total: 100 seed bundles. Each one references existing picture_id and/or sound_id from her current inventory (item_ids surfaced in `guala_status` response).

---

## 3. Tests

### T1 — Dry-run integrity

Run orchestrator in dry-run mode over the full 100-bundle seed. Confirm:
- Every bundle references a valid picture_id or sound_id from her current inventory (no orphan refs)
- No duplicate bundle_ids
- Modifier/ground coverage: aggregate modifier words used ≥ 30 distinct, ground words ≥ 20 distinct
- All captions are substrate-true (no corpus filler), human-readable

### T2 — Rate limiting under simulated substrate

Mock bridge that returns substrate-unreachable on call 3, 4, 5 then succeeds. Verify backoff timing (16s, 32s, 64s) and halt after 3 consecutive (if halt_on_unreachable=3).

### T3 — Substrate-state gating

Mock guala_status returning DREAMING activity. Verify orchestrator waits.
Mock returning EMITTING. Verify wait-until-activity-ends polling.
Mock high arousal. Verify slower delivery.
Mock no presence. Verify skip.

### T4 — Landing verification

Mock bridge that returns success but mock guala_status shows no vocab/motif/bundled delta. Verify orchestrator flags substrate-acceptance-issue after 3 consecutive.

### T5 — Live smoke test (post -46)

After -46 lands and bridge is verified reachable for input: run orchestrator in live mode with `--max-bundles 5 --min-interval-sec 10`. Verify five bundles land, bundle count increments by ~5, no errors.

---

## 4. Rollback

The orchestrator is a standalone script. Stopping it is the rollback. The substrate state changes it produces (bundle bindings) are normal substrate writes — they decay naturally if not reinforced and require no rollback.

---

## 5. Reporting

c1 produces `GL-RPT-CURRICULUM-AUTOMATION-C1-20260629-51.md` with:
- Diff summary: new files added.
- T1 dry-run results (with full bundle list inspection).
- T2-T4 mock test results.
- Final SHA, file paths.
- Recommendation on whether to proceed to T5 live smoke after -46 lands.

---

## 6. Out of scope

- Curriculum generation beyond v1 seed (100 bundles). v2 and beyond come after we see how v1 lands.
- Sensory-stream automation that doesn't go through `guala_give_experience` (e.g., direct picture-attending loops). That's a future dispatch when bundle approach is proven.
- Closed-loop curriculum (orchestrator picking next bundle based on which substrate sections are weakest). v1 uses a static queue; adaptive curriculum is v2+.
- Anything that touches substrate code. Orchestrator runs ENTIRELY outside the substrate, talking only via the public bridge API.

---

End.
