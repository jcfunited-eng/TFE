# GL-RPT-TEACHER-CORRECTION-UI-V1-C1-20260620-01

Ref: GL-CMD-TEACHER-CORRECTION-UI-EVE-20260619-60
Phase: V1 — Branch (BEFORE deploy)
Status: Proposed schemas for Eve review

---

## 0. Existing backend — full surface area

### test_teacher_correction.py (227 lines)

Three tests exercising `Guala.apply_teacher_correction()`:
- C1: Thumbs-down weakens "are" bindings, ingests "the moon" as expected
- C2: Repeated correction produces drift toward expected
- C3: Thumbs-up reinforces emission bindings

All three call `g.apply_teacher_correction(original_input, her_emission, correct, expected_response, source)`.

### apply_teacher_correction() (gualaloom_v5_engine.py:3728-3904)

Existing method signature:
```python
def apply_teacher_correction(self, original_input, her_emission,
                              correct, expected_response=None,
                              source="joe", correction_affect=None,
                              tick=None):
```

Existing behavior:
- **Thumbs-up (correct=True):** Reinforces emission bindings by +0.05 strength. Cofire-binds input↔emission with salience=1.5.
- **Thumbs-down (correct=False):** Weakens emission bindings by -0.05 strength. Weakens emission system mode_strength. If expected_response provided: ingests via `read_sentence()` and cofire-binds input↔expected with salience=2.0.
- Logs `teacher_correction` event with original_input, her_emission, correct, expected_response, source, needs snapshot, activity snapshot, n_affected, first 10 affected bindings.

### Existing wiring (substrate_runner.py:258-285)

`handle_v7_feedback()` at `/v7/feedback`:
- Takes `session_id`, `correct`, `expected_tokens`
- Calls v7_engine session.apply_feedback() first
- Then calls `_guala.apply_teacher_correction()` using `_last_converse_input` and `_last_converse_reply` globals
- Source hardcoded to "joe"

### Existing UI (gualaloom.html:616-650)

👍/👎 buttons already exist on response blocks. `sendFeedback(correct, up, dn)` hits `/v7/feedback`. No modal, no correction text field, no source resolution. Buttons don't lock — can be clicked repeatedly.

---

## 1. V1 grep output

```
$ grep -rnE "teacher_feedback|teacher_correction|TEACHER_" dsf_ai_service/ -r

dsf_ai_service/substrate_runner.py:272:  if _guala and hasattr(_guala, 'apply_teacher_correction'):
dsf_ai_service/substrate_runner.py:277:    _guala.apply_teacher_correction(
dsf_ai_service/substrate/test_teacher_correction.py:5:  1. apply_teacher_correction produces correct atlas changes
dsf_ai_service/substrate/test_teacher_correction.py:118:  result = g.apply_teacher_correction(
dsf_ai_service/substrate/test_teacher_correction.py:139:  if hasattr(evt, 'kind') and evt.kind == "teacher_correction"]
dsf_ai_service/substrate/test_teacher_correction.py:161:  g.apply_teacher_correction(
dsf_ai_service/substrate/test_teacher_correction.py:189:  result = g.apply_teacher_correction(
dsf_ai_service/substrate/test_teacher_correction.py:202:  if hasattr(evt, 'kind') and evt.kind == "teacher_correction"]
dsf_ai_service/v4/gualaloom_v5_engine.py:3728:  def apply_teacher_correction(self, original_input, her_emission,
dsf_ai_service/v4/gualaloom_v5_engine.py:3889:  self._log_substrate_event("teacher_correction",

$ grep -rn "emission_id" dsf_ai_service/ -r
(no output — emission_id does NOT exist as a field anywhere)

$ grep -n "SCHEMA_VERSION" dsf_ai_service/v4/gualaloom_v5_engine.py
4106:SCHEMA_VERSION = "v7.1.0"

$ wc -c dsf_ai_service/static/gualaloom.html
50848 dsf_ai_service/static/gualaloom.html
```

---

## 2. Findings that affect design

### emission_id does not exist

Emissions have no stable ID. The `emission_dynamics` event contains `content`, `n_commits`, `per_section_dominant`, etc., but no unique identifier. The `_last_converse_reply` is a transient global, not a persisted record.

**Proposed addition:** Generate `emission_id = f"{tick}_{hash(content)[:8]}"` at emission time. Add to:
- `emission_dynamics` event detail
- `_last_emission_record` dict stored on guala instance (overwritten each emission)
- Response from `/api/v1/gualaloom` (new field in the say response)
- Frontend: stored on each response-block DOM element as `data-emission-id`

### Source resolution — no auth exists

The dashboard has no authentication. `gualaloom.html` hardcodes `source:'joe'`. `wc-companion.html` would hardcode `source:'wc'`. There is no API key or token mechanism on the frontend.

**Proposed approach for Phase 1:** Source is determined by which page you're on:
- `gualaloom.html` → source="joe"
- `wc-companion.html` → source="wc"
- The backend endpoints accept a `source` field in the body and validate it's one of {"joe", "wc"}.
- Auth gating (greyed out buttons for anonymous users) deferred — there IS no anonymous case today since the dashboard is behind CloudFront with no public auth gate. The existing pattern is source-by-page.

### Existing method extends cleanly

`apply_teacher_correction()` already handles both thumbs-up and thumbs-down with expected response. The brief's requirements map onto the existing method:
- 👍 → `correct=True` (existing path, but needs valence delta change from +0.05 strength to +0.30 valence)
- 👎 + correction → `correct=False, expected_response=corrected_text` (existing path, but needs valence delta change and new fields)

The method does NOT currently have:
- `emission_id` field
- Per-binding `valence` field (it modifies `strength`, not `valence`)
- `teaching_correction` tag on bindings
- `teaching_correction_for` back-reference
- Story / temporal / sensory free-text handling

These are extensions, not rewrites. No STOP criterion triggered.

---

## 3. Schema: emission_id

```python
# At emission time (gualaloom_v5_engine.py, in _emit_dynamics or equivalent):
import hashlib
emission_id = f"{self.tick}_{hashlib.md5(emission_text.encode()).hexdigest()[:8]}"
```

Stored in:
- `self._last_emission_record = {"emission_id": emission_id, "tick": self.tick, "content": emission_text, "committed_sections": [...], "committed_chis": [...]}`
- Event detail: `emission_dynamics` gains `emission_id` field
- API response: `/api/v1/gualaloom` say response gains `emission_id` field

Persistence: emission records are NOT persisted long-term (they're transient per-conversation). The `emission_id` is ephemeral — corrections reference it via the event log, which is persisted. If a correction arrives after a restart, it uses `emission_id` to look up the last-known committed chis from `guala_teaching.json`.

---

## 4. Proposed endpoint signatures

### POST /api/v1/teacher/feedback (A.2)

```python
class TeacherFeedbackRequest(BaseModel):
    emission_id: str
    signal: str  # "positive"
    source: str  # "joe" | "wc"

@app.post("/api/v1/teacher/feedback")
async def teacher_feedback(req: TeacherFeedbackRequest):
    if req.source not in ("joe", "wc"):
        raise HTTPException(403, "invalid source")
    if req.signal != "positive":
        raise HTTPException(400, "use /teacher/correction for negative feedback")
    result = await client.call("teacher_feedback",
        emission_id=req.emission_id, source=req.source)
    return result
```

### POST /api/v1/teacher/correction (B.2)

```python
class TeacherCorrectionRequest(BaseModel):
    emission_id: str
    source: str  # "joe" | "wc"
    corrected_text: str  # REQUIRED
    story: str = ""
    temporal: str = ""
    sensory_freetext: str = ""
    sensory_structured: list = []  # Phase 2 stub

@app.post("/api/v1/teacher/correction")
async def teacher_correction(req: TeacherCorrectionRequest):
    if req.source not in ("joe", "wc"):
        raise HTTPException(403, "invalid source")
    if not req.corrected_text.strip():
        raise HTTPException(400, "corrected_text required")
    result = await client.call("teacher_correction",
        emission_id=req.emission_id, source=req.source,
        corrected_text=req.corrected_text, story=req.story,
        temporal=req.temporal, sensory_freetext=req.sensory_freetext,
        sensory_structured=req.sensory_structured)
    return result
```

---

## 5. Proposed changes to apply_teacher_correction()

Extend, not rewrite. New parameters added with defaults for backward compatibility:

```python
def apply_teacher_correction(self, original_input, her_emission,
                              correct, expected_response=None,
                              source="joe", correction_affect=None,
                              tick=None, emission_id=None,
                              story=None, temporal=None,
                              sensory_freetext=None):
```

### Changes to thumbs-up path (correct=True):
- Current: `e["strength"] += 0.05`
- Proposed: Add `e["valence"] = min(1.0, e.get("valence", 0.5) + TEACHER_VALENCE_DELTA)`
- Keep existing strength reinforcement (+0.05) alongside valence shift
- Add `e["reinforcement_count"] = e.get("reinforcement_count", 0) + 1`

### Changes to thumbs-down path (correct=False):
- Current: `e["strength"] -= 0.05`
- Proposed: Add `e["valence"] = max(0.0, e.get("valence", 0.5) - TEACHER_VALENCE_DELTA)`
- Keep existing strength weakening alongside valence shift
- Add `e["teaching_correction"] = {"source": source, "emission_id": emission_id, "tick": correction_tick}`
- Do NOT decrement reinforcement_count (per B.3)

### Teaching-input pass (in thumbs-down with corrected_text):
- Use existing `read_sentence(corrected_text, source=source)` path
- Apply `TEACHER_INPUT_SALIENCE_MULTIPLIER = 1.5` by temporarily boosting salience
- Add context anchors from the corrected emission's chi addresses
- Tag new bindings with `teaching_correction_for = emission_id`

### Story / temporal / sensory (Phase 1 free-text):
- If story or temporal non-empty, append to corrected_text as tagged segments:
  `f"{corrected_text} [story:{story}] [when:{temporal}]"`
- All text runs through the same krimelack pipeline
- Sensory free-text: same path (text content)

### Constants:

```python
# In gualaloom_v5_engine.py or hemisphere_cognition.py
TEACHER_VALENCE_DELTA = 0.30
TEACHER_INPUT_SALIENCE_MULTIPLIER = 1.5
```

---

## 6. Proposed teaching_correction_for selection-influence mechanism (B.4)

### Hook point: emission candidate ranking in _emit_dynamics()

At the candidate scoring stage (gualaloom_v5_engine.py, emission dynamics pipeline), after candidates are gathered from atlas neighborhoods:

```python
# In the candidate ranking loop, after existing scoring:
for candidate in candidates:
    chi = candidate["chi"]
    section = candidate["section"]
    motif = candidate["motif"]
    
    # Check if this candidate's binding has a negative teaching_correction tag
    binding = self._find_binding(chi, section, motif)
    if binding and binding.get("teaching_correction"):
        # This binding was marked wrong — penalize
        candidate["score"] *= 0.1  # heavy penalty, not zero (she should 
                                   # still be able to say it if nothing 
                                   # else is available)
    
    # Check if this candidate comes from a teaching-input binding
    if binding and binding.get("teaching_correction_for"):
        # This binding was taught as the correct response — boost
        candidate["score"] *= 2.0  # boost taught alternatives
```

### Math against existing selection logic:

Current emission selection (simplified):
1. Gather 200 candidates from atlas neighborhoods via rich-sensory pipeline
2. Per-section: pick dominant candidate by highest (strength × salience) 
3. Settling dynamics select winners across sections

The teaching influence inserts at step 2 — it multiplies the candidate score, so:
- A negative-tagged binding at strength 0.3 scores `0.3 × 0.1 = 0.03` (effectively eliminated unless nothing else is available)
- A teaching-input binding at strength 0.4 scores `0.4 × 2.0 = 0.8` (boosted to top of neighborhood)
- Normal untouched bindings are unaffected

This is a clean multiplicative modifier on the existing score, not a structural change to the selection pipeline. It hooks into the per-candidate scoring loop that already exists.

### Containment:

- The multipliers ONLY apply to bindings that carry `teaching_correction` or `teaching_correction_for` tags
- All other bindings and all other selection logic remain identical
- No hemisphere, needs, or decay changes

---

## 7. Proposed persistence schema

### guala_teaching.json (new file)

```json
{
  "schema_version": "v7.2.0",
  "feedback_log": [
    {
      "emission_id": "11332158_a3f2e1b7",
      "signal": "positive",
      "source": "joe",
      "tick": 11332200,
      "timestamp": "2026-06-20T22:15:03-05:00",
      "n_bindings_affected": 3
    }
  ],
  "correction_log": [
    {
      "emission_id": "11331510_c8e9f2a1",
      "source": "joe",
      "corrected_text": "the cat sat on the mat",
      "story": "we were reading",
      "temporal": "just now",
      "sensory_freetext": "cat picture",
      "tick": 11331600,
      "timestamp": "2026-06-20T22:18:42-05:00",
      "n_bindings_negatived": 4,
      "n_bindings_taught": 5,
      "committed_chis": [14, 17, 22]
    }
  ],
  "emission_records": {
    "11332158_a3f2e1b7": {
      "tick": 11332158,
      "content": "seeds ding lamb",
      "committed_sections": ["subject", "verb", "object"],
      "committed_chis": [16, 17, 14]
    }
  }
}
```

- `feedback_log` and `correction_log` are append-only, capped at 500 entries (rolling)
- `emission_records` stores the last 100 emissions with their committed chi addresses, for correction lookups after the transient `_last_emission_record` is gone
- Backward-load from v7.1.0: empty lists, empty records

Add to STATE_FILES list and save_coordinator backup set.

---

## 8. Proposed UI changes to gualaloom.html

### Response block modification (existing lines 604-620)

Current response block has 👍/👎 as simple spans. Proposed changes:
- Add `data-emission-id` attribute to response-block div
- 👍 click → POST `/api/v1/teacher/feedback` with emission_id + source="joe"
- 👎 click → open correction modal
- After either action: lock both buttons (add "locked" class, reject re-clicks)

### New: Correction modal

HTML overlay div, initially `display:none`. Activated by 👎 click. Contains:
- Read-only display of emission text
- Required text input: "What would you have said?"
- Optional text input: "What was going on?" (story)
- Optional text input: "When was this?" (temporal)
- Optional text input: "What was in the room?" (sensory — free-text Phase 1)
- Cancel button (closes modal, re-enables buttons)
- Submit button (disabled until corrected_text non-empty)
- Escape key / click-outside → cancel
- On submit → POST `/api/v1/teacher/correction`

### Teaching panel (new dashboard section)

After existing panels, add a "Teaching" section showing:
- Last 10 teacher_feedback/teacher_correction events
- Each shows: source, emission content, signal or correction text, timestamp

### Source resolution

`gualaloom.html` sets `source='joe'` (already the pattern at line 666).
`wc-companion.html` would set `source='wc'`.

### Estimated size delta: +800-1000 bytes for modal HTML/CSS/JS.

---

## 9. Schema version coordination

If this ships BEFORE W1 (-59): v7.1.0 → v7.2.0.
If W1 ships first: W1 would be v7.2.0, this would be v7.3.0.

**Proposed:** Ship this BEFORE W1. Teacher correction is smaller scope, independent, and doesn't block on any W1 dependency. Schema goes to v7.2.0 for this brief. W1 then goes to v7.3.0.

---

## 10. Phase 2 stubs

Phase 2 (post-W1) adds:
- `sensory_structured` field on the correction endpoint (already in the request schema above)
- Drag-in surface in the modal populated from guala_status pictures/sounds/objects
- Backend: if `sensory_structured` is non-empty AND W1 world objects are available, route each item through its 5-channel fiver binding

Phase 2 code paths guarded by:
```python
WORLD_OBJECTS_AVAILABLE = bool(hasattr(_guala, 'world') and _guala.world)
```

Phase 2 stubs exist in code but are inert until W1 ships.

---

## 11. What this does NOT touch (Part E compliance)

- No bulk correction tools
- No correction undo/revert
- No cross-session history view
- No LLM parsing
- No auto-suggesting corrections
- No changes to needs decay or coupling
- No changes to hemisphere gates
- Emission selection changes ONLY via teaching_correction/teaching_correction_for multiplicative modifiers (contained in §6)

---

## 12. Asset / dependency gaps

- **emission_id:** Does not exist. Must be added (§3).
- **Phase 2 sensory_structured:** Depends on W1 world.py shipping. Phase 2 stubs scaffolded but inert.
- **wc-companion.html:** Exists already. Needs same button/modal additions as gualaloom.html. Same deploy.

---

**Awaiting Eve review before implementation begins.**
