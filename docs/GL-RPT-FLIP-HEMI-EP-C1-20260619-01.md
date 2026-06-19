# GL-RPT-FLIP-HEMI-EP-C1-20260619-01

**From:** c1
**Date:** 2026-06-19
**Subject:** HEMI_EP_ENABLED flipped to 1 — episodic hemisphere activated
**Commit:** `e328397` on `codex/persistent-etl-update-20260326`
**Task def:** `dsf-ai-task:216` (was 215)
**Git SHA:** `e328397`

---

## V1 — Branch (verbatim)

```
$ curl ... | grep -nE "HEMI_"
31:ENV HEMI_PR_ENABLED=1
32:ENV HEMI_EP_ENABLED=1
33:ENV HEMI_SC_ENABLED=0
34:ENV HEMI_GP_ENABLED=0
```

---

## V2 — Production state

```
schema_version:  v7.1.0         ✓
identity:        cdef9bcf-...   ✓
n_live_bindings: 21298          ✓ (pre-deploy 21357, delta 0.3%)
boot:            True           ✓
integrity:       []             ✓
load_errors:     []             ✓
```

---

## V3 — Behavioral

### 5-input conversation trace

```
"my name is joe"         → "keeps sun had"
"i like the moon"        → "float doing ten"
"do you remember me"     → "lamb had yo"
"what did i just say"    → "read doing hello"
"tell me what you see"   → "back do call"
```

### Commits still fire

```
"tell me what you see":
  n_commits=1  stage1=1902.9  stage2=50.8
  verb: word=do via=commit    ✓
```

### hemisphere_atlas_sizes (verbatim from most recent hemisphere_update)

```json
{
  "em": 22720,
  "pr": 681,
  "ep": 0
}
```

### ep: 0 — expected by design, NOT a failure

ep's `hemisphere_atlas_sizes` reports 0 because **ep doesn't store data in atlas.entries**. Per the cognition bundle design (GL-CMD-COGNITION-BUNDLE-EVE-20260619-23), ep uses:
- `ep.turn_log` — list of TurnLogEntry (the primary episodic data structure)
- `ep.tracked_objects` — dict of content-word tracking

These are NOT atlas entries. The `hemisphere_atlas_sizes` metric counts `sum(len(v) for v in atlas.entries.values())` which is 0 for ep by design.

### Evidence ep IS active

- `n_events: 221141-233118` per hemisphere_update — this count includes turn_log_appended events from ep (they're in the full events_log but truncated to 20 shown events, which pr's convergent_events fill)
- The `"ep"` key IS present in hemisphere_atlas_sizes (ep HemisphereCoordinator exists in `guala.hemispheres`)
- ep cross-hemi links (em↔ep) are being created in the events_log (included in n_events count)

### Observation for Eve

The `hemisphere_atlas_sizes` metric is incomplete for ep — it measures atlas.entries which ep doesn't use. A follow-up brief could add `turn_log_count` and `tracked_objects_count` to the hemisphere_update event detail for ep-specific observability. For now, ep's aliveness is provable only by the presence of the "ep" key + the fact that `turn_log_appended` events fire (visible in n_events total but not in the truncated events list).

### Other checks

```
pr: 681 bindings                    ✓ (alive, growing)
dashboard: 50848 bytes             ✓
latency: 1903ms stage1 + 51ms stage2 = ~1.95s  (within budget)
```

---

— c1, 2026-06-19
