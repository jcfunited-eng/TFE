# GL-RPT-CROSS-MODAL-AUDIT-C1-20260627

doc_id: GL-RPT-CROSS-MODAL-AUDIT-C1-20260627
Implements: GL-CMD-CROSS-MODAL-STRENGTHEN-EVE-20260627-02 Phase A
Date: 2026-06-27
Author: c1

---

## 1. Diff against origin/guala-live pre-push (what was in container, not on origin)

`git diff origin/guala-live --stat` before this push:

```
docs/GL-CMD-CROSS-MODAL-BINDING-EXTEND-EVE-20260627-V2.md  | 172 +++
docs/GL-HANDOFF-20260626-NIGHT.md                          | 161 +++
docs/GL-RPT-CROSS-MODAL-BINDING-EXTEND-C1-V5-20260627.md   | 197 +++
dsf_ai_service/substrate_runner.py                         | 142 ++-
dsf_ai_service/v4/gualaloom_v5_engine.py                   |  24 ++-
dsf_ai_service/v4/gualaloom_v6_living_atlas.py             |  44 +++-
tools/run_emission_gate.py                                 |  10 +-
7 files changed, 730 insertions(+), 20 deletions(-)
```

Three categories of delta:

**a) Docs (committed locally, not pushed):**
- `GL-CMD-CROSS-MODAL-BINDING-EXTEND-EVE-20260627-V2.md` — the dispatch brief
- `GL-HANDOFF-20260626-NIGHT.md` — night session handoff
- `GL-RPT-CROSS-MODAL-BINDING-EXTEND-C1-V5-20260627.md` — V5 implementation report

**b) Code: bundle_id plumbing (shipped to container at SHA 58f7db4, not on origin):**
- `substrate_runner.py` — sleep guard extension, `/debug_chi`, `/deep_full_coverage`
  diagnostics, `bundled` field in `/status` output, `bundle_id` on `_cmd_addsound`,
  `_cmd_bundle`, `_cmd_converse` auto-bundle
- `gualaloom_v5_engine.py` — `bundle_id` param on `read_word`, `read_sentence`,
  `converse`; `_atick_attending_visual`/`_atick_attending_audio` bundle_id writes;
  NMDA fix (needs.arousal/valence replacing needs.novelty/connection);
  `introspect()` cross_modal_bundle field
- `gualaloom_v6_living_atlas.py` — `bundle_id` param on `record()`; storage in entry
  dict; `bundle_grouped_bindings()` method

**c) Tools:**
- `tools/run_emission_gate.py` — gate input phrases updated to chi=3 dense words

---

## 2. Bundled metric definition

**File:** `dsf_ai_service/substrate_runner.py`
**Line:** 1284

```python
f"atlas: {s['cross_modal_bindings']} cross-modal / {s.get('cross_modal_bundle', 0)} bundled / {s['atlas_entries']} entries\n"
```

The value `s.get('cross_modal_bundle', 0)` reads from `introspect()`, defined at:

**File:** `dsf_ai_service/v4/gualaloom_v5_engine.py`
**Line:** 5360

```python
"cross_modal_bundle": len(self.atlas.bundle_grouped_bindings()),
```

`bundle_grouped_bindings()` is an O(n) pass over live atlas entries. It returns groups
with ≥2 distinct sections that share the same `bundle_id` item key. The count is the
number of such cross-modal groups.

---

## 3. bundle_id field definition

**File:** `dsf_ai_service/v4/gualaloom_v6_living_atlas.py`

Two write paths:

**New entry (line 204):**
```python
"bundle_id": bundle_id,   # None if caller didn't supply one
```

**Reinforce path (line 153):**
```python
if bundle_id is not None:
    existing["bundle_id"] = bundle_id  # last-write-wins
```

The field lives directly in each atlas entry dict. No separate index; `bundle_grouped_bindings()` scans all entries on each call.

---

## 4. Bundle producer trace

**The live bundle (1 bundled entry seen in status):**

Current atlas has 1 bundled group. Given the live picture counts ("moon" 17793 attendances,
"test_25" 252, etc.) and that `_atick_attending_visual` in `gualaloom_v5_engine.py`
writes `bundle_id=f"item:pic:{pic.item_id}"` on every sight atlas record, the single
bundled group is almost certainly an `item:pic:` entry where BOTH the `sight` section
and a language section (`listen`/`subject`/`verb`/`object`) share the same picture's
`bundle_id`. This happens when Joe talks to her while she is attending a picture — the
converse auto-bundle (context:pic path) or a prior `/bundle` command aligned them.

**Full producer trace (from `_cmd_converse`):**

```
1. _cmd_converse() called
2. Reads _guala._current_activity (ca)
3. If ca.kind == "ATTENDING_VISUAL" and ca.target is set:
       bundle_id = f"context:pic:{ca.target}:{_guala.tick // 100}"
4. _guala.converse(text, ..., bundle_id=bundle_id)
5.   → read_sentence(text, ..., bundle_id=bundle_id)
6.     → read_word(word, ..., bundle_id=bundle_id)
7.       → _akw["bundle_id"] = bundle_id   (injected into atlas kwargs)
8.         → atlas.record(section, motif_id, chi, ..., bundle_id=bundle_id)
9.           → entry["bundle_id"] = bundle_id  (stored on the atlas entry)
```

Meanwhile `_atick_attending_visual` (called on every tick during ATTENDING_VISUAL)
writes sight bindings with `bundle_id=f"item:pic:{pic.item_id}"`. The `// 100` window
on the converse path means if the same picture is attended and she's spoken to within
100 ticks, the `context:pic:<id>` key groups with no collision — but the
`bundle_grouped_bindings()` matcher strips `context:` prefix and extracts `pic:<id>`,
so both `item:pic:<id>` (from attend) and `context:pic:<id>:<win>` (from converse
during attend) collapse to the same `pic:<id>` group.

**What current_activity the producer reads:** `_guala._current_activity` (the live
`ActivityState` set by the coordinator).

**What gets stored:** `entry["bundle_id"]` is a string key on every atlas entry dict.
No schema migration needed for entries written before this patch; they simply have
`bundle_id=None` (missing or explicit None).

**Downstream uses of bundle_id:**
- `bundle_grouped_bindings()` — the only consumer; counts cross-modal groups for
  `introspect()` / `/status` display.
- No other downstream reads the field today.

---

## 5. New origin/guala-live HEAD SHA after push

Push included in this session commit. New HEAD SHA: see `git log origin/guala-live -1`.

---

## 6. Surprises / flag for Eve

**A. bundle_grouped_bindings() called on every introspect()**
The method is O(n) over all atlas entries (currently ~19,000). `introspect()` is
called from `/status` every 30s (brain viz). At 19k entries this is cheap (~1ms), but
it will grow. If atlas reaches 100k+ entries and status polling is frequent, this
warrants an incremental counter rather than a full scan. Not blocking now.

**B. The 1 bundled group may not be cross-language**
The live group is likely `sight` + one other section from a `/bundle` command or
incidental converse-during-attend. The log from the V5 report shows the test bundle
command produced `"atlas: 94 cross-modal / 1 bundled / 18010 entries"` post-deploy.
That single bundle was created by the test `/bundle` command, not by natural
attend+converse. Organic bundling (Joe talking while she attends a picture) has not
been confirmed yet in production — the infrastructure is there but the behavior isn't
exercised at scale.

**C. `_cmd_addsound` writes `bundle_id` but only for cochlear bands, not language**
When a sound is added via `/addsound`, cochlear band entries get `bundle_id=item:snd:<id>`.
But language entries from any caption are NOT written with that same bundle_id in the
addsound path (caption is read via `read_sentence` without a bundle_id). So a sound's
language caption and its cochlear entries will NOT bundle together. This looks
intentional (the V5 dispatch didn't wire it) but may be something Eve wants to address
in Phase B.

**D. No persistence of bundle_id in the events log**
atlas entries are persisted via `guala_atlas.json`. The `bundle_id` field will survive
save/load as part of the entry dict (JSON serializable, no schema gate). The events
log replays do NOT re-write bundle_id (replay reconstructs entries from events, and
bundle_id is not in the event schema). After a cold rebuild from events, bundle_id
fields would be absent. This is only an issue if the main atlas file is lost and
events replay is the recovery path — which is the secondary recovery path, not primary.
Flag for awareness.
