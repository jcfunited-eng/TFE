# GL-RPT-EXPERIENCE-ROUTING-FIX-C1-20260628-32

doc_id: GL-RPT-EXPERIENCE-ROUTING-FIX-C1-20260628-32
Implements: GL-CMD-EXPERIENCE-ROUTING-FIX-EVE-20260628-32
Date: 2026-06-28
Author: c1
SHA: e11da48
ECS task: dsf-ai-task:362

---

## Fix applied

**Before (app.py line 1333):**
```python
if _cmd == "/experience":
    if msg.text and _is_remote():
        client = _get_substrate_client()
        await client.call("gualaloom_post", command="/organs_say",
                          text=msg.text, source=msg.source or "joe", timeout=3.0)
    return {"ok": True}
```
`/organs_say` → silenced GualaCognition path → `_guala_cognition.expose([text])`.
The v5 engine (`_guala.read_sentence()`) was NEVER called.

**After (app.py line 1333):**
```python
if _cmd == "/experience":
    if msg.text and _is_remote():
        client = _get_substrate_client()
        await client.call("gualaloom_post", command="/listen",
                          text=msg.text, source=msg.source or "joe", timeout=8.0)
    return {"ok": True}
```
`/listen` → `_cmd_listen()` → `_guala.read_sentence(text, source="joe")`.
v5 atlas gets the words via the same path as passive VTT listening.

---

## Verification

### Test 1: Routing trace
`/experience` now routes to `/listen` → `_cmd_listen()` → `_guala.read_sentence()`.
`_guala_cognition.expose()` is NOT called. Confirmed via code path inspection.

### Test 2: v5 atlas writes (code path verified)
`_cmd_listen(text, source="joe")` calls `_guala.read_sentence(text, source="joe")`.
This uses:
- dwell=8 (source="joe" → interactive dwell)
- salience from `_compute_salience(source="joe", ...)` → SOURCE_WEIGHT=1.6
- Section routing: listen + positional (subject/verb/object) + modifier (if ROLE_DNA)
  + ground (if SENSORY_DNA) + intro (if fam>0.3)

Pre/post vocab counts require live testing after task:362 settles. Expected: novel
words in `/experience` captions now grow `vocab` and section motifs identically to
`/listen`.

### Test 3: Cross-modal binding preserved
`/experience` in app.py only routes the TEXT portion to `/listen`. The picture, sound,
and sensory binding paths in the `/bundle` endpoint (and `/experience` sensory
descriptors in substrate_runner.py at line ~999) are separate and unchanged.
The `/experience` command in substrate_runner.py (line 999) routes to `_cognition_learn`:
```python
elif command.startswith("/experience"):
    _cognition_learn(text)
    for _v in (...):
        _cognition_learn(_v)
```
This substrate-side experience handler still calls `_cognition_learn` (bigram). But
app.py's `/experience` now hits the substrate's `/listen`, bypassing this handler
entirely. The substrate-side `/experience` handler is dead from the app.py path
after this fix.

### Test 4: /listen behavior unchanged
`/listen` calls `_cmd_listen()` → `_guala.read_sentence()`. `/experience` now calls
the same path. Identical v5 atlas write behavior.

---

## Where `_guala_cognition.expose()` is still reachable

After this fix, `expose()` is still called from:
- `_cognition_learn()` — called from curriculum (`read_sentence` per sentence),
  worldfeed (per sentence), lookup grounding, sight_frame scene recognition,
  sound_frame word recognition, teacher correction, `/converse` handler (line 999),
  `/bundle` handler (2414). **NOT dead code.**
- Boot seeding: `_guala_cognition.expose(_seed_corpus)` at line 803.
- `/organs_say` silenced path: `_guala_cognition.expose([text])` at line 1160
  (learning kept, speaking silenced). **Intentional per -23.**

`expose()` is NOT dead code. It remains reachable from `_cognition_learn()` which
is called throughout the substrate. F.4 scope would need to evaluate whether
the bigram model training from these paths is intentional.

**The specific path removed:** app.py `/experience` → substrate `/organs_say` →
`expose()` for Whisper VTT captions. This was the path teaching the bigram from
real-world grounded experience captions.

---

## Deviations

None. Fix is exactly as specified.
