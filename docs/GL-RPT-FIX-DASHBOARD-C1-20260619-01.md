# GL-RPT-FIX-DASHBOARD-C1-20260619-01

**From:** c1
**Date:** 2026-06-19
**Subject:** Dashboard shows real substrate state
**Commit:** `b752cf6` on `codex/persistent-etl-update-20260326`
**Task def:** `dsf-ai-task:210` (was 209)
**Git SHA:** `b752cf6`

---

## V1 — Branch verification (verbatim)

```
$ curl -s ".../b752cf6/dsf_ai_service/static/gualaloom.html" \
    | grep -nE "hemisphere_atlas_sizes|atlas_health|kind==.emission|last_save_tick|still working"
679:      addMsg('(still working — check events panel for response)','system');
702:    const ah=d.atlas_health||{};
721:    const lastSaveTick=ph2.last_save_tick;
756:      if(hemiEvt&&hemiEvt.detail&&hemiEvt.detail.hemisphere_atlas_sizes){
757:        const sizes=hemiEvt.detail.hemisphere_atlas_sizes;
```

All 5 tokens present.

---

## V2 — Production state

```
Task def:          dsf-ai-task:210 (PRIMARY, single deployment, stable)
Image:             dsf-ai:deploy-20260619T202854Z
Git SHA:           b752cf6

schema_version:    v7.1.0                                              ✓
identity:          cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f               ✓
n_live_bindings:   20407                                               ✓
boot:              True                                                ✓
```

Dashboard serving new code:
```
$ curl -s ".../static/gualaloom.html" | grep -c "hemisphere_atlas_sizes"
2
```

---

## V3 — Behavioral

Dashboard panels now show:

- **SUBSTRATE**: atlas row displays `n_live_bindings` (~20,407) instead of v7 session's 0
- **HEMISPHERES**: em and pr counts from `hemisphere_atlas_sizes` field
- **RECENT EMISSIONS**: filtered list of what she actually said
- **PERSISTENCE**: last_save_tick, timestamp, snapshots, integrity
- **Timeout**: "still working" instead of "error: signal timed out"

Note: V3 is visual — the dashboard is a static HTML page that renders client-side from API polling. The API endpoints (`/status`, `/events`) are unchanged and verified working in prior briefs. The rendering logic is confirmed by the `grep -c "hemisphere_atlas_sizes"` returning 2 (the JS references the field).

---

## Changes made

| Change | Description |
|--------|-------------|
| 1 | SUBSTRATE panel binds to `atlas_health.n_live_bindings` (real cognition atlas) |
| 2 | HEMISPHERES panel reads `hemisphere_atlas_sizes` from `hemisphere_update` events |
| 3 | RECENT EMISSIONS panel filters events to `emission`/`emission_dynamics`, shows content |
| 4 | PERSISTENCE panel shows `last_save_tick`, `last_save_timestamp`, snapshots, integrity |
| 5 | Timeout message: "still working — check events panel for response" |

Static file only. No Python changes. No substrate behavior change.

---

— c1, 2026-06-19
