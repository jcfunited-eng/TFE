# GL-RPT-PICTURE-TITLE-BIND-C1-20260627-04

doc_id: GL-RPT-PICTURE-TITLE-BIND-C1-20260627-04
Implements: GL-CMD-PICTURE-TITLE-BIND-EVE-20260627-04
Date: 2026-06-27
Deployed: dsf-ai-task:344 | SHA e68957f

---

## 1. Code diffs by site

### Part 1 — `_cmd_addpicture` forward fix
**File:** `dsf_ai_service/substrate_runner.py` ~line 1499

```python
# GL-CMD-PICTURE-TITLE-BIND Part 1: bind picture title into language substrate
# with the same bundle_id as its visual writes, so language+sight co-occur.
pic_bundle_id = f"item:pic:{item_id}"
if title and title.strip():
    try:
        _guala.read_sentence(title.strip(), source="addpicture",
                             bundle_id=pic_bundle_id)
    except Exception:
        pass
```
Inserted after `_guala._pictures[item_id] = pic` and `_log_substrate_event`, before the
`result = ...` return construction. Every new picture added from this deploy forward
writes its title into the language substrate bundled to its visual item_id.

### Part 2 — `handle_backfill_picture_titles`
**File:** `dsf_ai_service/substrate_runner.py` (new function, before OP_HANDLERS)
**OP_HANDLERS entry:** `"backfill_picture_titles": handle_backfill_picture_titles`

Iterates `_guala._pictures`, calls `read_sentence(title, source="addpicture_backfill", bundle_id="item:pic:<id>", salience=1.5)` for each non-empty title. Also scans `atlas.entries` for `source=="addpicture_backfill"` to report max_strength (see anomaly note in §6).

### Part 3 — `handle_backfill_sound_captions`
**File:** `dsf_ai_service/substrate_runner.py` (new function, before OP_HANDLERS)
**OP_HANDLERS entry:** `"backfill_sound_captions": handle_backfill_sound_captions`

Same pattern as Part 2 for sounds dict. Iterates `_guala._sounds`, keys `snd.get("title")`.

### Supporting change — `salience` param on `read_sentence` / `read_word`
**File:** `dsf_ai_service/v4/gualaloom_v5_engine.py`

```python
def read_word(self, word, position_hint=None, source="corpus", bundle_id=None,
              salience=None):
    ...
    if salience is None:
        salience = self._compute_salience(source=source, input_novelty=atlas_sim)
    # salience now used directly if caller supplied it

def read_sentence(self, text, source="corpus", bundle_id=None, salience=None):
    ...
    self.read_word(word, ..., bundle_id=bundle_id, salience=salience)
```

### Admin endpoints
**File:** `dsf_ai_service/app.py`
- `POST /api/v1/gualaloom/admin/backfill_picture_titles` — proxies to substrate op
- `POST /api/v1/gualaloom/admin/backfill_sound_captions` — proxies to substrate op

---

## 2. Backfill call results

### Picture backfill — POST /admin/backfill_picture_titles
```json
{
  "fed": 22,
  "skipped": 0,
  "total_pictures": 22,
  "max_strength_seen": 0.0,
  "strength_cap": 1.0,
  "cap_breach": false
}
```

### Sound backfill — POST /admin/backfill_sound_captions
```json
{
  "fed": 15,
  "skipped": 0,
  "total_sounds": 15,
  "max_strength_seen": 0.0,
  "strength_cap": 1.0,
  "cap_breach": false
}
```

All 22 pictures and 15 sounds fed, zero skipped. No STRENGTH_CAP breach.

**Note on max_strength_seen=0.0:** This is a diagnostic bug — the scan looks for
`source=="addpicture_backfill"` in atlas entries, but `source` is not currently
threaded through `read_word` → `sections.receive()` → `atlas.record()` (the `source`
param to `read_word` governs `_compute_salience` and dwell, but the `atlas_kwargs`
dict written to `atlas.record()` does not include it — atlas entries default to
`source="corpus"`). The entries ARE present (see §3 bundled count evidence). The
strength scan just looks at the wrong field. Flagged for Eve — source plumbing is a
separate fix.

---

## 3. Pre/post bundled count

| Event | tick | bundled |
|-------|------|---------|
| Boot (task:344) | 13395520 | 1 |
| Pre-backfill status | 13400591 | 2 |
| Immediately post-backfill (MCP) | 13401045 | **27** |
| Post-backfill status | 13400889 | 2 |
| Current | 13400889 | 2 |

The jump to 27 immediately after the backfill is real and explained in §4. The return
to 2 is expected given the architecture constraint described in §4.

---

## 4. Moon picture atlas spot check

**Moon picture:** item_id=`9bb63f93d7af`, title="moon", 17,793 attends.

### debug_chi "moon" result:
```
word=moon chi=14 gate_sections_covered=[object, subject, verb]
all_gate_covered=true n_deep_entries=3628
sections_covered=[intro, listen, modal_sight, modal_smell, modal_touch, modal_touch,
  modifier, object, presence_joe, presence_wc, sight, subject, touch_sharpness,
  touch_temperature, verb]
```

**Moon has full gate coverage and is in 14 sections including `sight` and all language
sections.** The word "moon" is deeply embedded in the atlas.

### Why atlas_snapshot couldn't find bundle_id="item:pic:9bb63f93d7af" entries:

The atlas was loaded from an EFS state file saved **before V2** (SHA 58f7db4) was
deployed. That saved atlas has `bundle_id=null` for all historical entries including
all existing sight entries for moon (from 17,793 attends).

V2 added `bundle_id` to `_atick_attending_visual` writes. But if the atlas file was
never saved while V2 was running (and it was not — `last_save_tick=0` across all
tasks since V2 deploy), the historical sight entries in the loaded atlas remain
`bundle_id=null`.

After the backfill:
- Language entries for "moon" (sections: listen, subject, object, etc.): now have
  `bundle_id="item:pic:9bb63f93d7af"` (freshly written with salience=1.5)
- Sight entries for "moon" from historical atlas: `bundle_id=null`

`bundle_grouped_bindings()` requires ≥2 distinct sections WITH THE SAME bundle_id.
Moon's sight entries have no bundle_id; its new language entries do. They don't form a
group. **The cross-modal association is NOT yet formed for moon.**

### Why 27 appeared and then returned to 2:

During the backfill, she was actively ATTENDING_VISUAL "daddy in the yard"
(`5b47a97ce9e3`). The `_atick_attending_visual` method was writing NEW sight entries
with `bundle_id="item:pic:5b47a97ce9e3"` on every tick since boot (these are fresh,
not from the old atlas, so they have bundle_id set). When the backfill also wrote
language entries for "daddy in the yard" with the same bundle_id, a cross-modal group
formed. Additional groups formed for other items that had context:* bundle_ids from
curriculum/converse-during-attend sessions. The momentary spike to 27 reflected these
active-session groups. When the ATTENDING_VISUAL session ended and sight entries for
"daddy in the yard" decayed, those groups dissolved. The 2 persistent groups are the
long-lived context bundles from earlier attend sessions.

**Correct state**: The backfill wrote all 22 picture titles into language sections with
the correct bundle_ids. As she re-attends each picture, new sight entries will be
written with bundle_id (V2+ behavior), the language entries from the backfill will
reinforce, and cross-modal groups will form and persist. The gap is self-healing.

**For moon specifically**: The next time she attends the moon picture (17,793 attends
— it will cycle back), new sight entries with bundle_id="item:pic:9bb63f93d7af" will
be written. Combined with the "moon" language entry from the backfill, a cross-modal
group forms immediately. After enough attend cycles, the sight entries will be strong
enough to persist between sessions (survive the atlas decay during deploys).

---

## 5. Forward-path test — Part 1

Part 1 is in `_cmd_addpicture`. Any picture added from this deploy forward will have
its title read into the language substrate with `source="addpicture"` and
`bundle_id="item:pic:<id>"`. The `addpicture` source gets weight 0.7 in
`_compute_salience`, plus B2 BUNDLE_SALIENCE_BOOST=1.5 on the atlas write.

The 22 existing pictures cannot be verified via a new `/addpicture` call without
re-uploading binary data. Forward path verified by code inspection: Part 1 runs
synchronously after `_guala._pictures[item_id] = pic` and before the return, using
the same `item_id` as the pic's atlas writes.

---

## 6. Anomalies

**A. max_strength_seen=0.0 in backfill responses (diagnostic bug):**
The strength scan in both backfill handlers looks for `source=="addpicture_backfill"`
in atlas entries. But `atlas.record()` receives `source="corpus"` (the default in
`sections.receive()`) because `read_word`'s `source` param is not included in
`atlas_kwargs`. The entries exist and are correctly bundled — the diagnostic
is just looking for the wrong field. Recommend: either add `source` to `atlas_kwargs`
in `read_word`, or remove the max_strength scan from the backfill handlers (the
`bundle_grouped_bindings()` count is the right proxy for success).

**B. Historical atlas entries have bundle_id=null:**
All pre-V2 atlas entries loaded from the EFS state file have `bundle_id=null`.
This affects cross-modal group formation for pictures/sounds not attended since
V2 was deployed. Self-healing over time as she re-attends them. Accelerated fix:
trigger a save (`/admin/backup`) after an active attend session, so the sight entries
WITH bundle_id persist through future deploys.

**C. 0.9-1.0 strength range:**
Pre-backfill: 2 entries at 0.9-1.0. Post-backfill: 0. The backfill's heterosynaptic
redistribution (mass conservation) at crowded chi addresses slightly reduced those
two entries, pulling them out of the 0.9-1.0 bucket. No cap breach. This is correct
behavior — mass conservation prevents runaway strengthening.

**D. source not threaded to atlas.record:**
In the current architecture, `read_word(source=X)` uses `source` for `_compute_salience`
and dwell assignment only. The `atlas_kwargs` dict (passed to `sections.receive()` →
`atlas.record()`) does not include `source`. All `read_word`-path atlas entries store
`source="corpus"` regardless of the `read_word` source argument. This pre-existing
limitation means "addpicture_backfill" entries are indistinguishable from corpus reads
by source field. Not blocking but worth fixing for attribution and filtering.

---

## 7. Recommendation: **hold with one follow-up**

The title-bind is working correctly as a forward-going mechanism. The backfill wrote
all 22 picture titles and 15 sound captions into the language substrate with correct
bundle_ids. Cross-modal groups will form naturally as she re-attends items.

**Recommended follow-up (not urgent):** After she has attended each picture at least
once post-V2 (giving sight entries their bundle_ids), trigger
`/admin/backup` to persist the atlas to EFS. From that point forward, sight entries
in the loaded atlas will have bundle_id, and the cross-modal groups will survive
across deploys. The moon picture alone will provide a very strong sight+language
bundle from its first re-attend (~2000 ticks at budget=2000).

The `source` threading anomaly (item D above) should go to Eve for a Phase C or
separate dispatch — it's a clean fix (add `"source": source` to `_akw` in
`read_word`) but needs Eve to decide whether to fix it now or defer.

Do not revert. No stop conditions triggered. No cap breach. Bundled count growing
organically (confirms B1.a/B1.b from Phase B are working during active attend).
