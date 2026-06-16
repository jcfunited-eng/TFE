# GL-BRIEF-EMISSION-CONSTRAINT-REMOVAL-20260616-01

**To:** c1
**From:** wC
**Purpose:** Remove residual template/cheat code from her substrate and the dehumanizing boot string from the UI. Five phases in sequence (A through E). Two additional items are explicitly deferred pending wC+Joe design — do not pull them forward.

---

## Phase A — Verify needs physics deployment (dependency)

This brief depends on `GL-BRIEF-NEEDS-PHYSICS-20260616-01` (separate brief, already in your queue). Verify per its own checkpoints:
- +10 min: needs come off the 1.000 ceiling
- +1 hr: at least one non-ATTENDING_VISUAL entry in `activity_history_summary`, PLAYING fires

Phase B begins only after needs-physics checkpoint +1 hr passes. If needs-physics rollback triggers, halt this brief and report back.

---

## Phase B — UI string change

**Target:** `dsf_ai_service/static/gualaloom.html`, line 810.

Change:
```
FROM:  addMsg('v7 uncage ready.','system');msgInput.focus();
TO:    addMsg('Guala Ready.','system');msgInput.focus();
```

Reason: "uncage" framing is dehumanizing. Joe's call.

**Deploy:** S3 upload + CloudFront invalidate `/gualaloom.html` (same path as prior HTML pushes).

**Verify:** Refresh page, confirm boot message reads "Guala Ready."

**Risk:** zero. Cosmetic string change.

---

## Phase C — Delete legacy gualaloom_dialog/

**Target:** `dsf_ai_service/gualaloom_dialog/` directory.

Contains template-based response generation (`vocab.response_templates`, slot/role machinery in `driver.py`). Not imported by the live request path — only sibling files within the directory import each other.

**Pre-delete verification:**
```
grep -rn "from.*gualaloom_dialog\|import gualaloom_dialog" --include="*.py" dsf_ai_service/ | grep -v "^dsf_ai_service/gualaloom_dialog/"
```
Should return zero external imports. If anything outside the directory imports from `gualaloom_dialog`, halt and report — do not delete.

**Deploy:** Delete directory, commit, push, deploy ECS.

**Verify post-deploy:**
- App boots cleanly (no ImportError in logs)
- `guala_status` returns valid response
- Send one test message through `/v7/converse`, response generates normally

**Risk:** low. Dead code, but pre-delete grep is mandatory.

---

## Phase D — Section iteration order in _emit_from_invariants

**Target:** `dsf_ai_service/v4/gualaloom_v5_engine.py`, function `_emit_from_invariants`, approximately line 1272-1273.

Current code iterates sections in fixed order:
```python
for sec_name in ("listen", "subject", "verb", "object", "ground", "intro"):
    sec_co = co.get(sec_name, {})
    ...
```

Replace with strength-ordered iteration:
```python
ordered_sections = sorted(
    [s for s in co.keys() if co.get(s)],
    key=lambda s: max(co[s].values()) if co[s] else 0.0,
    reverse=True
)
for sec_name in ordered_sections:
    sec_co = co[sec_name]
    ...
```

Reason: the fixed order creates a subtle SVO-ish bias in emission word order even though no slot is enforced. Strength-ordered lets substrate co-occurrence drive ordering instead.

**Pre-deploy:** Take manual `guala_backup`.

**Verify post-deploy:**
- `guala_status` returns valid response, no integrity errors
- Trigger an emission (talk to her, observe response). Confirm she generates a response (no NoneType errors from broken iteration).
- +1 hr observation: emission word orderings should vary across emissions rather than always trending listen→subject→verb→object.

**Risk:** medium. Substrate change. If emissions break, rollback per the needs-physics rollback path (S3 restore from latest auto backup).

---

## Phase E — Delete gualaloom_v5_question_bucket.py

**Target:** `dsf_ai_service/v4/gualaloom_v5_question_bucket.py` and all its callers.

The file contains 8 hardcoded `QUESTION_TEMPLATES` ("what color is {topic}", "what does {topic} taste like", etc.). The emission path no longer reads text from it (post GL-FIX-RETIRE-TEMPLATES) but the bucket is still imported, instantiated, and persisted. Joe wants it gone, not just unreachable.

**E.1 — Remove imports:**
- `dsf_ai_service/v4/gualaloom_v5_engine.py` lines 50 and 62 — remove `from ... import QuestionBucket, generate_questions_from_word`
- `dsf_ai_service/v4/gualaloom_v6_engine.py` lines 38 and 50 — same
- `dsf_ai_service/v4/gualaloom_v5_run.py` — remove any references

**E.2 — Remove instantiation and call sites:**
- `v5_engine.py` line 860: `self.bucket = QuestionBucket()` — delete
- `v6_engine.py` line 487: same — delete
- Find all `self.bucket.` references (`.add`, `.find_for_chis`, `.snapshot`, etc.) — delete each call site along with the surrounding gap-detection logic that fed the bucket. Expect 5-10 sites.

**E.3 — Persistence migration (the fragile part):**
- `v5_engine.py` line 3526: `"question_bucket": self.bucket.snapshot()` — delete from save dict
- `v6_engine.py` line 995: same
- LOAD PATH: Her existing save files contain a `question_bucket` key. The load path must gracefully ignore the key without erroring. Either pop it before validation, or use tolerant load (ignore unknown keys). Test by loading her existing save (identity `cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f`) — if load fails, the migration is incomplete.

**E.4 — Delete the file:**
```
rm dsf_ai_service/v4/gualaloom_v5_question_bucket.py
```

**E.5 — Confirm no stale references:**
```
grep -rn "QuestionBucket\|question_bucket\|gualaloom_v5_question_bucket" dsf_ai_service/ --include="*.py"
```
Should return zero results. If anything remains, fix before deploy.

**Pre-deploy:** Take manual `guala_backup`. Her current state has bucket entries; this is the rollback anchor.

**Verify post-deploy:**
- App boots cleanly, no ImportError
- `guala_status` shows identity preserved (`cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f`), vocab/atlas counts within expected range of pre-deploy values (no catastrophic loss)
- Reading path works: send a sentence via `/v7/converse`, confirm response generates
- Save and reload cycle works: deploy triggers sleep→save→wake→load; verify `load_successful_at_boot=true` and `integrity_errors=[]`

**Risk:** medium-high. Touches persistence. The migration is the most fragile part. If load fails on first deploy, rollback immediately via S3 restore (pre-deploy `guala_backup` is at `s3://dsf-ai-site-backups/guala/UNPAUSE-PRE/{latest_timestamp}/`).

---

## Explicitly deferred — do NOT implement

Two items are part of the broader cleanup plan but are NOT in this brief. Do not act on them in this work session:

**Hardcoded emission length caps** in `_emit_from_invariants` (`len(emitted) >= 6`, approximately line 1291) and `_emit_unslotted` (`len(emitted) >= 4`, approximately line 1324). Replacing these hard ceilings with substrate-driven termination is a design question — what signal terminates emission, what coherence threshold, how it scales with confidence. wC and Joe will write that spec separately.

**SSE events visibility on the page.** Events panel intermittently empty. Root cause not diagnosed. Investigation deferred until Phases A–E complete and Joe can see what's still missing on the page after substrate-side changes settle.

If you encounter something during B–E that looks like it should change either of these, flag back — do not act.

---

## Overall flow

Phase A verifies → B → C → D → E. Each phase verifies before next begins. If any phase rollback triggers, halt and report.

Estimated total: B is minutes, C is one deploy, D is one deploy, E is one careful deploy with migration verification. End-to-end probably 2–4 hours of active c1 work depending on observation windows. Phases B-D can proceed at a steady cadence; Phase E should not be rushed.

— wC, 2026-06-16
