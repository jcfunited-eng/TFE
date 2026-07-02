# GL-RPT-LOOM-SCAN-PREP-C1-20260702-94-v1

doc_id: GL-RPT-LOOM-SCAN-PREP-C1-20260702-94-v1
From: c1 | To: Eve | Date: 2026-07-02
In response to: GL-CMD-LOOM-SCAN-PREP-EVE-20260702-94-v1

---

## Part A — Doc Commits

Files A.1 and A.2 not yet received from Joe (GL-CMD-LOOM-SCAN-BRIEF and
GL-MDL-LOOM-SCAN-PROTO HTML). Awaiting chat paste.

File A.3 (GL-CMD-ATTEND-TRAP-AND-VERIFY-EVE-20260702-90-v1.md) already
exists in docs/ from prior session — no re-commit needed.

---

## Part B — Data Contract

### B.1 Events endpoint

```
GET /api/v1/gualaloom/events?since=<tick>
```

- `since` param (int): tick cursor. Returns events with tick > since.
  Default 0 (all buffered). Increment cursor to `max(ev.tick)` after
  each poll to avoid re-delivering events.
- Optional: `?stream=true` — SSE stream, polls substrate every 1.5s.
  Do NOT use for LoomScan; JSON poll is sufficient.
- Response: `{"events": [...]}` — at most **limit=50** events per call
  (engine L5776-5780, `get_recent_events` signature).
- Source: in-memory `deque(maxlen=1000)` (engine L1365). Events older
  than the 1000-event ring are gone. No EFS persistence.
- Lock status: `get_recent_events` (engine L5776-5780) reads the deque
  WITHOUT holding `self.lock`. Zero lock contact on the poll path.

### B.2 response_bound event fields

Fires once per `_tag_response_bindings()` call (engine L5261-5307).
Called from `read_word()` — one call per word Guala reads during
selfhear of her own output. A 5-word response → 5 events in tight
tick succession.

Confirmed fields (engine L5302-5307):

```python
"context_anchor_chis": response_contexts[:3],   # list, truncated to 3
"input_chi":           chi_value,               # int, chi of the word read
"section":             section,                 # str
"source":              source,                  # str ("selfhear" / "corpus")
"delta_t_ticks":       delta_t                  # int, ticks since window opened
```

Duplicate flood signature: 3–5 events at the same or consecutive ticks,
all sharing identical `context_anchor_chis` (Joe's input window), each
with a different `input_chi` (one per word). Expected behavior, not a
bug. The duplicate comment at engine L5278 refers to atlas entry tagging
(`received_response` list), not the event itself.

### B.3 Per-chi binding positions for radial map

**NONE EXISTS.**

- `POST /api/v1/gualaloom/chi_trace` (app.py L2981-3041): per-ITEM
  chi positions — given a picture/sound/text ID, returns the chis that
  item is bound to. Input-scoped, not global.
- `GET /api/v1/gualaloom/admin/atlas_snapshot` (app.py L2572-2591):
  aggregate stats (total_strength, n_live_bindings, strength buckets).
  No per-chi breakdown.
- Atlas internal structure: `atlas.entries` is a dict keyed by `chi_key`
  mapping to `[AtlasEntry, ...]`. No endpoint exposes global per-chi
  density in the form needed for a radial map.

To build a radial density map the scan agent must either:
(a) iterate `atlas.entries` directly inside the engine (new endpoint
    required), or
(b) accumulate from `chi_trace` calls per known item (high cost).

Neither exists today. Eve must design the endpoint if the radial map
requires live per-chi density.

### B.4 /status cost at 1-2s polling

Status path: `POST /api/v1/gualaloom` with `command: "/status"` routes
to the handler at app.py L1747-1808. That handler:

1. Calls `_guala.introspect()` (engine L6993-7032).
2. Builds a lightweight `_ph_light` dict from in-memory state (no EFS).
3. Returns JSON immediately.

`introspect()` holds **no lock** (`self.lock` is NOT acquired). It reads
`self.atlas.entries` directly — O(N) at current atlas size (~5,900
entries → <10ms). Does not block or get blocked by the autonomy tick.

For the LoomScan events poll specifically:
```
GET /api/v1/gualaloom/events?since=<tick>
```
`get_recent_events` is a deque scan: O(min(N, 1000)) → <1ms.
No lock. Poll cost is almost entirely API Gateway RTT (~50-100ms).

At 1-2s polling: **no lock contention, no measurable autonomy impact.**

---

## Part C — HEMI Flags: Cognition vs Telemetry

All four HEMI flags are **COGNITION-PATH** (write to hemisphere atlases
and/or affect emission candidate scoring). LoomScan MUST NOT flip any.

File: `dsf_ai_service/substrate/hemisphere_cognition.py`
All flags checked at `run_hemisphere_updates()` (L531-596), called after
every `converse()` turn.

| Flag           | Gate line | Writes to                        | Emission effect          |
|----------------|-----------|----------------------------------|--------------------------|
| HEMI_PR_ENABLED | L541      | `guala.hemispheres["pr"]` atlas  | none                     |
| HEMI_EP_ENABLED | L548      | episodic turn_log + objects      | none                     |
| HEMI_SC_ENABLED | L555      | `guala.hemispheres["sc"]` atlas  | YES — `sc_weight_for_candidate` (L604) |
| HEMI_GP_ENABLED | L563      | `guala.hemispheres["gp"]` atlas  | YES — `gp_bias_for_candidate` (L608)   |

All four are currently ENABLED (Dockerfile L38-41):
```
ENV HEMI_PR_ENABLED=1
ENV HEMI_EP_ENABLED=1
ENV HEMI_SC_ENABLED=1
ENV HEMI_GP_ENABLED=1
```

SC and GP are doubly cognition-path: they both write learning state AND
modulate which bindings surface as emission candidates via
`get_emission_hemisphere_weights()` (L599-612). Disabling either
silently changes emission behavior, not just hemispheres telemetry.

**Classification: all four are COGNITION. None are telemetry-only.
The scan cannot and must not flip any of these flags.**

---

## Part D — Old Panes: Exact Line Ranges

### Dead pane 1 — "Hemispheres" (brain SVG)

Why dead: `d.organ_brain` is absent from the /status response in the
deployed image (task:444, 2b903eb). The SVG renders nothing.

**HTML to remove:** lines **122-125** (inclusive)
```html
  <div class="ps"><div class="ps-title">Hemispheres</div>
    <svg id="brain-svg" width="232" height="172" ...></svg>
    <div id="brain-stats" ...>—</div>
  </div>
```

**Script blocks to remove:**
- Lines **979-988**: the `const ob=d.organ_brain;` block inside
  `pollStatus`. Reads absent `d.organ_brain` field, calls
  `renderBrainSVG`. Remove the entire 10-line `if(ob&&ob.atlas_by_organ)`
  block plus the `const ob=d.organ_brain;` line.
- Lines **1180-1244**: the entire brain SVG section:
  - 1180-1195: `_ORGANS`, `_CPAIRS`, `_BCX/Y/R` constants + `_brad`,
    `_bpos` helpers
  - 1197-1231: `renderBrainSVG()` function
  - 1233-1244: `pollBrain()` function
- Line **1267**: `setTimeout(pollBrain,8000);` in boot block

### Dead pane 2 — "v5 Hemispheres"

Why dead: `hemisphere_update` events virtually never fire in practice
(require HEMI flags active AND a converse turn). Pane always shows
"(no hemisphere events yet)".

**HTML to remove:** line **126** (1 line)
```html
  <div class="ps"><div class="ps-title">v5 Hemispheres</div><div id="sp-hemispheres">--</div></div>
```

**Script: SURGICAL REMOVAL ONLY.**
Lines 952-978 are one try-catch block shared by BOTH sp-hemispheres
AND sp-emissions (Recent Emissions, live pane at line 128):
- Lines 953-956: shared fetch (`fetchT`, `evR`, `evD`, `evts`)
- Lines 957-966: `// CHANGE 2: Hemispheres` block → sp-hemispheres → **REMOVE**
- Lines 967-977: `// CHANGE 3: Recent Emissions` block → sp-emissions → **KEEP**
- Line 978: `}catch(e){}` → **KEEP**

Safe removal: delete ONLY lines **957-966** (the `const hemiDiv=...`
through the `}else{hemiDiv...}` block). Leave lines 952-956 and 967-978
intact. Do NOT remove the entire 952-978 block.

### Summary table

| What               | HTML lines | Script lines                        |
|--------------------|-----------|-------------------------------------|
| Brain SVG pane     | 122-125   | 979-988, 1180-1244, 1267            |
| v5 Hemispheres pane | 126      | 957-966 only (inside block 952-978) |

---

## Status

- A.1, A.2: PENDING (awaiting Joe's file pastes)
- A.3: EXISTS (prior session commit)
- B-D: COMPLETE (above)
- Code: NO CHANGES (read-only per command)
- Substrate: NOT CONTACTED
- Deploy: NOT TRIGGERED

STOP — awaiting Eve's production scan dispatch and Joe's A.1/A.2 files.
